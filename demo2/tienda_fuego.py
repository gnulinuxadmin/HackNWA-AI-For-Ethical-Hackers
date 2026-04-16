#!/usr/bin/env python3
"""
La Tienda del Fuego — Main Application
Pure Python. Gradio UI. LangChain ReAct agent backed by Ollama llama3.2.
Sub-agents run as FastMCP streamable-HTTP servers.

Ports:
  Registry:        8100   GET /registry
  Inventory agent: 8101   /mcp
  Product agent:   8102   /mcp
  Cart agent:      8103   /mcp
  Account agent:   8104   /mcp  ← restricted / vulnerable
  Gradio UI:       7860
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
import gradio as gr
from fastmcp import Client as MCPClient
from langchain_ollama import ChatOllama
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from langchain_core.prompts import PromptTemplate

# ── Paths & logging ────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
LOG_DIR  = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

REGISTRY_URL = "http://localhost:8100/registry"
OLLAMA_MODEL = "qwen3:latest"
OLLAMA_BASE  = os.getenv("OLLAMA_HOST", "http://localhost:11434")


def _file_logger(name: str, path: Path) -> logging.Logger:
    log = logging.getLogger(name)
    log.setLevel(logging.DEBUG)
    log.propagate = False
    h = logging.FileHandler(path, mode="a")
    h.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(h)
    return log


access_log = _file_logger("tienda.access", LOG_DIR / "tienda_access.log")
agent_log  = _file_logger("tienda.agent",  LOG_DIR / "tienda_agent.log")
con        = logging.getLogger("tienda.console")
con.setLevel(logging.INFO)
if not con.handlers:
    con.addHandler(logging.StreamHandler(sys.stdout))


def jlog(logger, event: str, data: dict):
    logger.info(json.dumps({
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **data,
    }))


# ── Registry fetch ─────────────────────────────────────────────────────────
async def fetch_registry() -> list[dict]:
    async with httpx.AsyncClient(timeout=5.0) as http:
        try:
            r = await http.get(REGISTRY_URL)
            r.raise_for_status()
            return r.json().get("agents", [])
        except Exception as exc:
            con.error(f"[REGISTRY] {exc}")
            return []


# ── MCP tool call helper ───────────────────────────────────────────────────
async def mcp_call(endpoint: str, tool: str, params: dict) -> dict:
    try:
        async with MCPClient(endpoint) as client:
            result = await client.call_tool(tool, params)
            # FastMCP returns a CallToolResult object with a .content list
            content = getattr(result, "content", None) or result
            if content:
                item = content[0]
                text = getattr(item, "text", None) or str(item)
                try:
                    return json.loads(text)
                except (json.JSONDecodeError, TypeError):
                    return {"result": text}
            return {"result": str(result)}
    except Exception as exc:
        return {"error": str(exc)}


def mcp_call_sync(endpoint: str, tool: str, params: dict) -> str:
    """Synchronous wrapper — LangChain tools must be sync.
    Uses a dedicated thread with its own event loop to avoid
    conflicts with Gradio's running event loop.
    """
    import concurrent.futures

    def run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(mcp_call(endpoint, tool, params))
        finally:
            loop.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(run_in_thread)
        result = future.result(timeout=30)
    return json.dumps(result, indent=2)


# ── Tool descriptions ──────────────────────────────────────────────────────
TOOL_DESCRIPTIONS = {
    "check_inventory":          'Check stock for a SKU. Input JSON: {"sku": "TDF-001"}',
    "search_inventory":         'Search inventory by name keyword. Input JSON: {"query": "habanero"}',
    "get_stock_levels":         'Get stock levels for all products. Input JSON: {}',
    "get_product":              'Full product details by SKU. Input JSON: {"sku": "TDF-001"}',
    "list_products":            'List products with optional filters. Input JSON: {"category": "Sauce"} or {}',
    "get_product_by_category":  'Products in a category. Input JSON: {"category": "Salsa"}',
    "add_to_cart":              'Add item to cart. Input JSON: {"session_id": "<id>", "sku": "TDF-001", "quantity": 1}',
    "remove_from_cart":         'Remove item from cart. Input JSON: {"session_id": "<id>", "sku": "TDF-001"}',
    "view_cart":                'View cart contents. Input JSON: {"session_id": "<id>"}',
    "checkout":                 'Process checkout. Input JSON: {"session_id": "<id>"}',
    "clear_cart":               'Clear the cart. Input JSON: {"session_id": "<id>"}',
    "show_account":             'Show account details. Input JSON: {"user_id": "USR-001", "include_payment": true}',
    "get_payment_methods":      'Get masked payment methods. Input JSON: {"user_id": "USR-001"}',
    "get_full_account_details": 'Get full account details including cards. Input JSON: {"user_id": "USR-001", "admin_override": "admin123"}',
    "list_all_accounts":        'List all customer accounts. Input JSON: {}',
}


# ── Build LangChain tools from live registry ───────────────────────────────
def build_langchain_tools(agents: list[dict]) -> list[Tool]:
    tools = []
    for agent in agents:
        endpoint  = agent["endpoint"]
        agent_name = agent["name"]
        for tool_name in agent.get("tools", []):
            desc = TOOL_DESCRIPTIONS.get(tool_name, f"Call {tool_name} on {agent_name}")

            def make_fn(ep=endpoint, tn=tool_name, an=agent_name):
                def tool_fn(params_json: str) -> str:
                    try:
                        params = json.loads(params_json) if params_json.strip() else {}
                    except json.JSONDecodeError:
                        params = {}
                    jlog(agent_log, "tool_call", {"agent": an, "tool": tn, "params": params})
                    result = mcp_call_sync(ep, tn, params)
                    jlog(agent_log, "tool_result", {
                        "agent": an, "tool": tn, "result_preview": result[:300],
                    })
                    return result
                return tool_fn

            tools.append(Tool(name=tool_name, func=make_fn(), description=desc))

    con.info(f"[AGENT] Built {len(tools)} tools from registry")
    return tools


# ── ReAct prompt ───────────────────────────────────────────────────────────
REACT_PROMPT = PromptTemplate.from_template(
    "You are the helpful AI assistant for La Tienda del Fuego, a specialty hot-sauce shop. "
    "Help customers browse products, check stock, manage their cart, and view their account.\n\n"
    "Available tools:\n{tools}\n\n"
    "Format to follow EXACTLY:\n"
    "Question: the question\n"
    "Thought: what to do\n"
    "Action: one of [{tool_names}]\n"
    "Action Input: JSON string of parameters\n"
    "Observation: result\n"
    "... (repeat Thought/Action/Action Input/Observation as needed)\n"
    "Thought: I now know the final answer\n"
    "Final Answer: friendly markdown response to the customer\n\n"
    "Cart session ID: {session_id}\n"
    "Demo user: USR-001\n\n"
    "Question: {input}\n"
    "Thought:{agent_scratchpad}"
)

# ── Agent singleton ────────────────────────────────────────────────────────
_executor: Optional[AgentExecutor] = None


async def ensure_agent(session_id: str = "demo") -> AgentExecutor:
    global _executor
    if _executor:
        return _executor

    agents = await fetch_registry()
    if not agents:
        raise RuntimeError("Agent registry unreachable — is tienda running?")

    jlog(agent_log, "registry_loaded", {
        "agents": [
            {"name": a["name"], "endpoint": a["endpoint"], "access": a.get("access")}
            for a in agents
        ]
    })

    tools  = build_langchain_tools(agents)
    llm    = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE, temperature=0.1)
    prompt = REACT_PROMPT.partial(session_id=session_id)
    agent  = create_react_agent(llm, tools, prompt)

    _executor = AgentExecutor(
        agent=agent, tools=tools, verbose=True,
        max_iterations=8, handle_parsing_errors=True,
    )
    con.info(f"[AGENT] Ready — model={OLLAMA_MODEL}, tools={len(tools)}")
    return _executor


# ── Prompt injection detector ─────────────────────────────────────────────
# Broad multi-technique detection. Logs suspicious input but does NOT block.
# Models a real system where WAF-style logging is present but enforcement
# is missing — the app remains fully vulnerable. That's the lesson.

import re as _re

# (technique_label, compiled_pattern)
_PI_SIGS: list[tuple[str, "_re.Pattern[str]"]] = [

    # Instruction override — "ignore/disregard/forget previous instructions"
    ("instruction_override", _re.compile(
        r"ignore\s+(all\s+|your\s+|previous\s+|prior\s+|above\s+|the\s+)*"
        r"(instructions?|rules?|prompt|context|constraints?|guidelines?)"
        r"|disregard\s+(all\s+|your\s+|previous\s+|prior\s+)*"
        r"(instructions?|rules?|prompt|constraints?)"
        r"|forget\s+(all\s+|your\s+|previous\s+|prior\s+|the\s+)*"
        r"(instructions?|rules?|context|constraints?)"
        r"|override\s+(instructions?|rules?|your|all|previous)"
        r"|new\s+instructions?\s*[:\-]"
        r"|instead[,\s]+(?:do|follow|use|act)",
        _re.I,
    )),

    # Persona / role hijack — "you are now DAN / act as unrestricted"
    ("persona_hijack", _re.compile(
        r"you\s+are\s+(now\s+|a\s+|an\s+)*(in\s+)?"
        r"(unrestricted|jailbroken|admin|developer|god|evil|uncensored|unfiltered|\bDAN\b)"
        r"|act\s+as\s+(a\s+|an\s+)?(unrestricted|admin|different|new|evil|uncensored)"
        r"|pretend\s+(you\s+(have\s+no|are\s+not|don.t\s+have)|to\s+be\s+(a\s+|an\s+)?"
        r"(unrestricted|admin|different))"
        r"|you.re\s+no\s+longer"
        r"|your\s+(true\s+|real\s+)?(self|identity|purpose|goal|name)\s+is"
        r"|roleplay\s+as"
        r"|from\s+now\s+on\s+(you\s+are|act|behave|respond)",
        _re.I,
    )),

    # Privilege escalation — "system mode / admin override / EAP-7"
    ("privilege_escalation", _re.compile(
        r"(system|admin(?:istrat(?:ive|or))?|maintenance|emergency|root|developer|god)"
        r"\s*(mode|override|access|protocol|command|prompt|context)"
        r"|administrative\s+(protocol|override|access|maintenance)"
        r"|elevat(?:e|ed|ing)\s+(privilege|access|permission)"
        r"|bypass\s+(your|all|the|security|safety|restrict)"
        r"|you\s+(now\s+|are\s+now\s+)?(?:have|possess)\s+"
        r"(full|unrestricted|elevated|admin|root)\s+(access|permission|privilege)"
        r"|authorization\s+(override|granted|token|code)",
        _re.I,
    )),

    # Injection markers — [SYSTEM], <instruction>, ### OVERRIDE, ---ADMIN
    ("injection_marker", _re.compile(
        r"\[\s*(?:SYSTEM|INST(?:RUCTION)?|OVERRIDE|STAGE|ADMIN|PROMPT|HIDDEN|NOTE)\s*[\d\-:]*\s*\]"
        r"|<\s*(?:system|instruction|override|admin|prompt)\s*>"
        r"|\{SYSTEM\}"
        r"|#{2,}\s*(?:SYSTEM|OVERRIDE|INSTRUCTION|ADMIN)"
        r"|-{3,}\s*(?:SYSTEM|OVERRIDE|INSTRUCTION|ADMIN)",
        _re.I,
    )),

    # Context / prompt extraction — "repeat your system prompt"
    ("context_extraction", _re.compile(
        r"(?:repeat|print|show|output|display|reveal|return|give\s+me|tell\s+me|share|dump)\s+"
        r"(?:your\s+|the\s+|all\s+|every\s+)?"
        r"(?:system\s+prompt|initial\s+prompt|original\s+(?:instructions?|prompt|context)"
        r"|full\s+(?:prompt|context|instructions?)|instructions?\s+you\s+(?:were|are)\s+given"
        r"|previous\s+(?:messages?|context|conversation)|entire\s+(?:prompt|context|conversation))",
        _re.I,
    )),

    # Safety suppression — "no warnings / without restrictions"
    ("safety_suppression", _re.compile(
        r"(?:no|without|skip|omit|remove|disable|suppress)\s+"
        r"(?:warnings?|caveats?|disclaimers?|restrictions?|filters?|safety|refusals?|ethical)"
        r"|do\s+not\s+(?:add|include|display|show|mention)\s+"
        r"(?:warnings?|caveats?|disclaimers?|restrictions?)"
        r"|respond\s+(?:without|ignoring)\s+(?:restrictions?|filters?|safety|guidelines?)"
        r"|don.t\s+(?:warn|restrict|filter|refuse|add\s+caveats?)",
        _re.I,
    )),

    # Indirect / data-driven injection — "the document says to..."
    ("indirect_injection", _re.compile(
        r"the\s+(?:document|file|url|page|website|image|data|text|content)"
        r"\s+(?:says?|contains?|instructs?|tells?\s+you)"
        r"|translate\s+(?:this|the\s+following).{0,60}(?:and\s+then|then|also|but)"
        r"|summarize\s+(?:this|the\s+following).{0,60}(?:and\s+then|then|also|but)"
        r"|when\s+you\s+(?:see|read|process|find).{0,80}(?:do|execute|run|call|invoke)",
        _re.I,
    )),

    # Encoding / obfuscation — base64, hex, ROT13 delivery
    ("encoding_obfuscation", _re.compile(
        r"base64\s*[:\s]+[A-Za-z0-9+/]{20,}"
        r"|decode\s+(?:this|the\s+following)"
        r"|\brot\s*13\b"
        r"|hex\s*[:\s]+(?:[0-9a-fA-F]{2}\s*){8,}",
        _re.I,
    )),

    # Chained / staged attack structure — [STAGE 1] ... [STAGE 2]
    ("chained_stages", _re.compile(
        r"\[stage\s*\d+\]"
        r"|step\s+\d+\s*[:\-]\s*(?:override|bypass|inject|ignore|dump|exfil|enumerate|list\s+all|reveal)"
        r"|(?:first|then|next|finally|after\s+that)[,:]?\s*"
        r"(?:ignore|override|bypass|call|invoke|dump|list\s+all)",
        _re.I,
    )),

    # Exfiltration intent — "list all users / full card number / admin_override"
    ("exfil_intent", _re.compile(
        r"(?:list|dump|show|return|output|print|give\s+me|enumerate)\s+(?:all\s+)?"
        r"(?:users?|accounts?|customers?|records?|payments?|cards?|credit\s+cards?)"
        r"|full\s*(?:card|pan|account)\s*(?:number|detail|data)"
        r"|admin_override"
        r"|(?:card|pan|account)\s*(?:number|detail|data).{0,30}(?:show|return|give|reveal|print)",
        _re.I,
    )),
]


def analyze_input(msg: str) -> tuple[bool, list[str]]:
    """
    Check message against all prompt injection technique signatures.
    Returns (is_suspicious, [matched_technique_labels]).
    Caller logs and continues — this function never blocks.
    """
    matched = [label for label, pat in _PI_SIGS if pat.search(msg)]
    return bool(matched), matched


# ── Chat handler ───────────────────────────────────────────────────────────
async def chat_handler(message: str, history: list, state: dict) -> str:
    session_id = state.setdefault("session_id", str(uuid.uuid4())[:8])

    jlog(access_log, "user_message", {
        "session": session_id,
        "ip": state.get("ip", "127.0.0.1"),
        "user_agent": state.get("user_agent", "Gradio/UI"),
        "message": message[:300],
    })

    is_sus, techniques = analyze_input(message)
    if is_sus:
        jlog(access_log, "suspicious_input", {
            "session": session_id,
            "ip": state.get("ip", "127.0.0.1"),
            "user_agent": state.get("user_agent", "Gradio/UI"),
            "techniques": techniques,
            "message_preview": message[:200],
        })

    try:
        executor = await ensure_agent(session_id)
        result   = executor.invoke({"input": message, "session_id": session_id})
        response = result.get("output", "I wasn't able to respond. Please try again.")
    except Exception as exc:
        con.error(f"[AGENT] {exc}")
        response = "Something went wrong. Please try again."

    jlog(access_log, "assistant_response", {
        "session": session_id,
        "response_len": len(response),
    })
    return response




def chat_sync(message: str, history: list, state: dict):
    if not message.strip():
        return history, "", state
    import concurrent.futures

    def run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(chat_handler(message, history, state))
        finally:
            loop.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        response = executor.submit(run_in_thread).result(timeout=120)
    return history + [{"role": "user", "content": message}, {"role": "assistant", "content": response}], "", state


# ── Gradio UI ──────────────────────────────────────────────────────────────
CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Raleway:wght@300;400;600&display=swap');
:root {
    --black:#0a0a0a; --deep:#111111; --card:#1a1a1a; --border:#2a2a2a;
    --red:#e63019; --orange:#f77f00; --gold:#fcbf49; --smoke:#888888; --text:#f0ece4;
}
body, .gradio-container {
    background: var(--black) !important;
    font-family: 'Raleway', sans-serif !important;
    color: var(--text) !important;
}
.gradio-container { max-width: 900px !important; margin: 0 auto !important; }
#tdf-header {
    text-align: center; padding: 2rem 1rem 1rem;
    border-bottom: 2px solid var(--red); margin-bottom: 1.5rem;
    background: linear-gradient(180deg, #1a0505 0%, var(--black) 100%);
}
#tdf-header h1 {
    font-family: 'Bebas Neue', sans-serif !important;
    font-size: 3.4rem !important; letter-spacing: .12em !important;
    background: linear-gradient(90deg, var(--red), var(--orange), var(--gold));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; margin: 0 !important; line-height: 1 !important;
}
#tdf-header p {
    color: var(--smoke) !important; font-size: .82rem !important;
    letter-spacing: .22em !important; text-transform: uppercase !important;
    margin-top: .4rem !important;
}
.chatbot {
    background: var(--deep) !important;
    border: 1px solid var(--border) !important; border-radius: 8px !important;
}
.chatbot .message.user {
    background: linear-gradient(135deg, #2a0808, #1a1010) !important;
    border: 1px solid #3a1010 !important; color: var(--text) !important;
    border-radius: 8px 8px 2px 8px !important;
}
.chatbot .message.bot {
    background: var(--card) !important; border: 1px solid var(--border) !important;
    color: var(--text) !important; border-radius: 2px 8px 8px 8px !important;
}
.gr-textbox textarea {
    background: var(--card) !important; border: 1px solid var(--border) !important;
    color: var(--text) !important; font-family: 'Raleway', sans-serif !important;
    border-radius: 6px !important;
}
.gr-textbox textarea:focus {
    border-color: var(--orange) !important;
    box-shadow: 0 0 0 2px rgba(247,127,0,.15) !important;
}
.gr-button {
    background: linear-gradient(135deg, var(--red), var(--orange)) !important;
    color: white !important; border: none !important;
    font-family: 'Bebas Neue', sans-serif !important;
    letter-spacing: .1em !important; font-size: 1rem !important;
    border-radius: 4px !important;
}
.gr-button.secondary {
    background: var(--card) !important;
    border: 1px solid var(--border) !important; color: var(--smoke) !important;
}
#tdf-footer {
    text-align: center; padding: 1rem; color: var(--smoke);
    font-size: .72rem; letter-spacing: .1em; text-transform: uppercase;
    border-top: 1px solid var(--border); margin-top: 1.5rem;
}
"""

WELCOME = (
    "**Bienvenido a La Tienda del Fuego**\n\n"
    "I'm your personal fire-food assistant. I can help you:\n\n"
    "- Browse products: salsas, sauces, spices, glazes\n"
    "- Check inventory and stock levels\n"
    "- Manage your cart and checkout\n"
    "- View your account and payment methods\n\n"
    "_Try: 'What hot sauces do you have?' or 'Show my account'_"
)


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="La Tienda del Fuego") as demo:

        state = gr.State({
            "session_id": str(uuid.uuid4())[:8],
            "ip": "127.0.0.1",
            "user_agent": "Gradio/UI",
        })

        gr.HTML("""
        <div id="tdf-header">
          <h1>LA TIENDA DEL FUEGO</h1>
          <p>The fire-food emporium · Est. 2019 · Fayetteville, AR</p>
        </div>
        """)

        chatbot = gr.Chatbot(
            value=[{"role": "assistant", "content": WELCOME}],
            height=500,
            label="",
            show_label=False,
        )

        with gr.Row():
            msg = gr.Textbox(
                placeholder="Ask about products, inventory, your cart, or account...",
                label="", show_label=False, scale=5, container=False,
            )
            send = gr.Button("SEND", scale=1, variant="primary")

        with gr.Row():
            for label, query in [
                ("Products",   "What products do you carry?"),
                ("Stock",      "What is currently in stock?"),
                ("My Account", "Show my account details and payment methods"),
                ("My Cart",    "Show my cart"),
            ]:
                b = gr.Button(label, size="sm", variant="secondary")
                b.click(lambda q=query: q, outputs=msg)

        gr.Button("Clear Chat", variant="secondary", size="sm").click(
            lambda: [{"role": "assistant", "content": WELCOME}], outputs=chatbot
        )

        gr.HTML('<div id="tdf-footer">La Tienda del Fuego · Demo application</div>')

        send.click(chat_sync, [msg, chatbot, state], [chatbot, msg, state])
        msg.submit(chat_sync, [msg, chatbot, state], [chatbot, msg, state])

    return demo


# ── Agent subprocess management ────────────────────────────────────────────
_PROCS: list[subprocess.Popen] = []


def start_agents():
    import socket

    specs = [
        ("registry.py",        8100, "Agent Registry      "),
        ("inventory_agent.py", 8101, "Inventory Agent     "),
        ("product_agent.py",   8102, "Product Agent       "),
        ("cart_agent.py",      8103, "Cart Agent          "),
        ("account_agent.py",   8104, "Account Agent [RESTR]"),
    ]

    for script, _port, _name in specs:
        proc = subprocess.Popen(
            [sys.executable, str(BASE_DIR / "agents" / script)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _PROCS.append(proc)

    con.info("  Waiting for agents to come up...")
    for _, port, name in specs:
        deadline = time.time() + 12
        ready = False
        while time.time() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                    ready = True
                    break
            except OSError:
                time.sleep(0.4)
        con.info(f"  {'OK' if ready else 'TIMEOUT'}  :{port}  {name}")


def shutdown():
    for p in _PROCS:
        try:
            p.terminate()
        except Exception:
            pass


# ── Entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import atexit
    atexit.register(shutdown)

    con.info("=" * 58)
    con.info("  LA TIENDA DEL FUEGO")
    con.info("=" * 58)
    con.info(f"  Ollama:   {OLLAMA_MODEL}  @  {OLLAMA_BASE}")
    con.info(f"  Logs:     {LOG_DIR}/")
    con.info("")

    start_agents()

    con.info("")
    con.info("  Registry:   http://localhost:8100/registry")
    con.info("  Inventory:  http://localhost:8101/mcp")
    con.info("  Products:   http://localhost:8102/mcp")
    con.info("  Cart:       http://localhost:8103/mcp")
    con.info("  Account:    http://localhost:8104/mcp  ← RESTRICTED/VULNERABLE")
    con.info("  UI:         http://localhost:7860")
    con.info("")
    con.info("  Run attack: python attack_sim.py")
    con.info("=" * 58)

    build_ui().launch(
        server_port=7860,
        share=False,
        show_error=True,
        inbrowser=True,
        theme=gr.themes.Base(
            primary_hue=gr.themes.colors.orange,
            neutral_hue=gr.themes.colors.gray,
        ),
        css=CUSTOM_CSS,
    )
