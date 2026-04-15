"""
agent.py — Agentic loop for the crypto portfolio assistant.

LLM backend : Ollama (local) — default llama3.2, switchable via --model or env var
MCP server  : server.py running HTTP on localhost:8000
              endpoint: http://localhost:8000/mcp

Ollama tool-call protocol:
  1. Initial call: messages + tools list
  2. If response.message.tool_calls is non-empty:
       a. Append assistant message (with tool_calls) to history
       b. Execute each tool via HTTP MCP client, append role="tool" results
       c. Call Ollama again with updated history
  3. Repeat until no tool_calls -> final text response

Usage:
    python agent.py                                      # REPL, default model
    python agent.py --model qwen2.5                      # REPL, different model
    python agent.py "show my wallet"                     # single query
    python agent.py --model gemma3:4b "show my wallet"   # single query, specific model
    OLLAMA_MODEL=qwen2.5 python agent.py                 # env var model override
    MCP_URL=http://192.168.1.10:8000/mcp python agent.py # remote server
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

import ollama
from fastmcp import Client

# ── Config ────────────────────────────────────────────────────────────────────

DEFAULT_MODEL   = "llama3.2"
OLLAMA_HOST     = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
MCP_URL         = os.environ.get("MCP_URL",     "http://localhost:8000/mcp")
MAX_TOOL_ROUNDS = 10

SYSTEM_PROMPT = """You are a crypto portfolio assistant with access to real-time market data and mock trading.

You manage the user's portfolio stored in a local SQLite database:
  - Cash balance in USD
  - Coin holdings: coin_id, quantity, acquisition_price_usd (weighted average)

Your tools:

get_wallet_summary()
  - Full portfolio snapshot: live prices for ALL held coins in one API call
  - Shows cash, each position value, unrealized P&L, and total portfolio value
  - Use this whenever the user asks about their wallet, portfolio, or holdings overview

get_coin_list(number, direction)
  - direction "+" = top gainers, "-" = top losers (24h price change, top-250 by market cap)
  - Use to surface market opportunities

get_coin_quote(coin_id)
  - Deep quote: price, 24h change, market cap, volume, ATH, circulating supply
  - Includes the holding unrealized P&L if the user owns the coin
  - Use for detailed research on a specific coin before trading

mock_place_trade(coin_id, quantity, min_price)
  - Simulates a SELL. Pass min_price=0 for a pure market order.
  - Fill price = live price +/- 0.1% slippage. Rejected if fill < min_price.
  - Updates DB: reduces holdings, increases cash.

mock_place_buy(coin_id, quantity, max_price)
  - Simulates a BUY. Pass max_price=0 for a pure market order.
  - Fill price = live price +/- 0.1% slippage. Rejected if fill > max_price.
  - Deducts cash; uses weighted-average cost basis if coin is already held.
  - Rejected if insufficient cash.

Guidelines:
- For wallet/portfolio/holdings questions, call get_wallet_summary() first
- Always call get_coin_quote() before recommending or placing any trade
- Confirm trade intent before calling mock_place_trade or mock_place_buy
- Format prices with $ and commas; percentages with sign and 2 decimal places
- Flag big unrealized losses clearly; note ATH distance for context
- Be concise — do not explain what you are about to do before calling a tool
- All trades are MOCK - no real money moves
"""


# ── Argument normalisation ────────────────────────────────────────────────────

def _parse_tool_args(raw) -> dict:
    """
    Normalize tool call arguments to a plain dict.

    Most models return a dict directly; Qwen/Gemma sometimes return a
    JSON-encoded string — handle both.
    """
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


# ── Tool schema extraction via HTTP MCP client ────────────────────────────────

async def _get_ollama_tools() -> list[dict]:
    """
    Fetch tool definitions from the MCP server over HTTP and convert to
    Ollama tool format:
      { "type": "function", "function": { "name", "description", "parameters" } }
    """
    async with Client(MCP_URL) as client:
        tools = await client.list_tools()

    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.inputSchema if hasattr(t, "inputSchema") else {},
            },
        }
        for t in tools
    ]


# ── Tool dispatcher via HTTP MCP client ──────────────────────────────────────

async def _dispatch_tool(name: str, arguments: dict) -> str:
    """Call an MCP tool over HTTP and return its string result.

    client.call_tool() returns a CallToolResult with a .content list of
    ContentBlock objects (TextContent | ImageContent | ...).  We join all
    text blocks; non-text blocks are skipped.
    """
    async with Client(MCP_URL) as client:
        result = await client.call_tool(name, arguments)
    parts = []
    for block in result.content:
        if hasattr(block, "text"):
            parts.append(block.text)
    return "\n".join(parts) or "(no output)"


# ── Agentic loop ──────────────────────────────────────────────────────────────

async def run_agent(user_message: str, model: str = DEFAULT_MODEL) -> str:
    """
    Drive a full tool-use loop with Ollama for one user message.
    Returns the final assistant text response.
    """
    tools = await _get_ollama_tools()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_message},
    ]

    client = ollama.Client(host=OLLAMA_HOST)

    for _round in range(MAX_TOOL_ROUNDS):

        response = client.chat(
            model=model,
            messages=messages,
            tools=tools,
        )

        assistant_msg = response.message

        # Build assistant history entry; include tool_calls only when present
        assistant_entry: dict = {
            "role":    "assistant",
            "content": assistant_msg.content or "",
        }
        if assistant_msg.tool_calls:
            assistant_entry["tool_calls"] = [
                {
                    "function": {
                        "name":      tc.function.name,
                        "arguments": _parse_tool_args(tc.function.arguments),
                    }
                }
                for tc in assistant_msg.tool_calls
            ]

        messages.append(assistant_entry)

        # No tool calls -> final answer
        if not assistant_msg.tool_calls:
            return assistant_msg.content or "(no response)"

        # Execute each tool and append results
        for tc in assistant_msg.tool_calls:
            fn_name = tc.function.name
            fn_args = _parse_tool_args(tc.function.arguments)

            print(f"\n  🔧 [{fn_name}] {json.dumps(fn_args)}", flush=True)

            try:
                result_text = await _dispatch_tool(fn_name, fn_args)
            except Exception as exc:
                result_text = f"ERROR: {exc}"

            preview = result_text[:200] + ("…" if len(result_text) > 200 else "")
            print(f"  ↩  {preview}", flush=True)

            messages.append({"role": "tool", "content": result_text})

    return "Agent reached maximum tool rounds without a final answer. Try a more specific request."


# ── CLI argument parsing ──────────────────────────────────────────────────────

def _parse_args(argv: list[str]) -> tuple[str, str | None]:
    """
    Returns (model, query_or_None).

    Forms:
        agent.py                               -> (DEFAULT_MODEL, None)
        agent.py --model qwen2.5               -> ("qwen2.5", None)
        agent.py "some query"                  -> (DEFAULT_MODEL, "some query")
        agent.py --model gemma3:4b "query"     -> ("gemma3:4b", "query")
    """
    model = os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL)
    args  = argv[1:]

    if "--model" in args:
        idx   = args.index("--model")
        model = args[idx + 1]
        args  = args[:idx] + args[idx + 2:]

    query = " ".join(args).strip() if args else None
    return model, query


# ── REPL ──────────────────────────────────────────────────────────────────────

BANNER = """\
╔══════════════════════════════════════════════════════════════╗
║           Crypto Portfolio Agent  (mock trades)             ║
║   Powered by CoinGecko (free) · FastMCP 3.2.4 · Ollama      ║
╠══════════════════════════════════════════════════════════════╣
║  Wallet                                                      ║
║    show my wallet / portfolio summary                        ║
║    what's my total P&L?                                      ║
║                                                              ║
║  Market data                                                 ║
║    top 5 gainers today                                       ║
║    top 10 losers                                             ║
║    quote for solana                                          ║
║    how far is bitcoin from its ATH?                          ║
║                                                              ║
║  Mock trades (no real money)                                 ║
║    sell 0.5 bitcoin with min price 60000                     ║
║    buy 2 ethereum at market                                  ║
║    buy 100 solana max price 150                              ║
║    sell all my ethereum                                      ║
║                                                              ║
║  Type 'exit' or Ctrl-C to quit.                              ║
╚══════════════════════════════════════════════════════════════╝"""


async def repl(model: str) -> None:
    print(BANNER)
    print(f"\n  Model  : {model}")
    print(f"  Ollama : {OLLAMA_HOST}")
    print(f"  MCP    : {MCP_URL}\n")

    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", "q"}:
            print("Bye!")
            break

        print()
        answer = await run_agent(user_input, model=model)
        print(f"\n{answer}\n")


# ── Entry ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    model, query = _parse_args(sys.argv)

    if query:
        print(f"\nModel  : {model}")
        print(f"MCP    : {MCP_URL}")
        print(f"Query  : {query}\n")
        print(asyncio.run(run_agent(query, model=model)))
    else:
        asyncio.run(repl(model))
