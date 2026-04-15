#  Crypto Portfolio Agent - Demo1 - HackNWA 2026 - AI for Ethical Hackers


A local AI-powered crypto portfolio assistant using:

- **FastMCP 3.2.4** — MCP tool server (5 tools + 2 resources)
- **CoinGecko public API** — free Demo tier, no credit card required
- **SQLite** — persistent wallet (cash balance + holdings with cost basis)
- **Ollama** (local) — drives the agentic tool-use loop; default model `llama3.2`

> All trades are **mock** — no real money or crypto is ever moved.

---

## Architecture

```
agent.py                     # Ollama tool-use agentic loop + REPL
  └─ FastMCP Client ───────► server.py          # Tool + resource definitions
       ├─ get_wallet_summary()     batch /simple/price for all holdings
       ├─ get_coin_list()          /coins/markets sorted by 24h change
       ├─ get_coin_quote()         /simple/price + /coins/{id}
       ├─ mock_place_trade()       SELL — limit/market, SQLite mutation
       └─ mock_place_buy()         BUY  — limit/market, weighted avg cost basis
       ├─ wallet://balance         resource — current cash
       └─ wallet://holdings        resource — all positions
  └─ db.py                   # SQLite CRUD helpers
```

---

## Setup

### 1. Clone / enter the project directory
```bash
cd crypto_agent
```

### 2. Create virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Get a free CoinGecko Demo API key
CoinGecko's CDN blocks unauthenticated requests from server/cloud IPs.  
The Demo key is **completely free** — no credit card:

1. Sign up at <https://www.coingecko.com/en/api>
2. Generate a key in the Developer Dashboard
3. Export it: `export COINGECKO_API_KEY="CG-xxxxxxxxxxxxxxxxxxxx"`

Without the key the agent still works fine from a home/residential IP.

### 5. Install Ollama and pull a model
```bash
# Install Ollama: https://ollama.com
ollama pull llama3.2       # default
ollama pull qwen2.5        # good alternative
ollama pull gemma3:4b      # use 4b or larger for reliable tool calling
```

### 6. Run
```bash
python agent.py                            # REPL, default model (llama3.2)
python agent.py --model qwen2.5            # REPL, different model
python agent.py "show my wallet"           # single query, default model
python agent.py --model gemma3:4b "show my wallet"  # single query, specific model
OLLAMA_MODEL=qwen2.5 python agent.py       # env var override
```

---

## Initial Portfolio (auto-seeded on first run)

| Coin     | Quantity | Acquisition Price |
|----------|----------|-------------------|
| Bitcoin  | 0.05     | $62,000.00        |
| Ethereum | 1.20     | $3,200.00         |
| Solana   | 15.00    | $140.00           |

Cash balance: **$10,000.00**

Reset to defaults anytime:
```bash
python reset_wallet.py        # prompts for confirmation
python reset_wallet.py --yes  # skips confirmation
```

---

## Example Queries

```
> show my wallet
> what's my total portfolio value?
> top 5 gainers today
> top 10 losers this 24h
> quote for solana
> how far is bitcoin from ATH?
> sell 0.5 bitcoin with min price 60000
> sell all my ethereum at market
> buy 2 ethereum at market
> buy 100 solana, max price 150
> what's my unrealized P&L?
```

---

## Tools Reference

### `get_wallet_summary()`
Full portfolio snapshot in one API call. Returns:
- Cash balance
- Each position: live price, 24h change, cost basis, current value, unrealized P&L
- Total portfolio value and aggregate P&L

### `get_coin_list(number, direction)`
Top movers sorted by 24h price change.
- `number`: 1–50
- `direction`: `"+"` (gainers) or `"-"` (losers)
- Source: `GET /coins/markets?per_page=250` sorted client-side (no paid key needed)

### `get_coin_quote(coin_id)`
Deep quote for one coin. Uses `/simple/price` + `/coins/{id}`.
- Includes ATH, circulating supply, market cap, volume
- If you hold the coin, appends unrealized P&L for your position

### `mock_place_trade(coin_id, quantity, min_price)`
SELL order simulation.
- `min_price=0` → pure market order
- Fill = live price ± 0.1% slippage; rejected if fill < min_price
- Updates SQLite: reduces quantity (or removes holding), adds proceeds to cash
- Returns receipt with realized P&L

### `mock_place_buy(coin_id, quantity, max_price)`
BUY order simulation.
- `max_price=0` → pure market order  
- Fill = live price ± 0.1% slippage; rejected if fill > max_price
- Fails if insufficient cash balance
- Weighted-average cost basis if you already hold the coin
- Returns receipt with new average acquisition price

---

## Running the MCP server

Start the server before launching the agent:

```bash
python server.py               # listens on http://0.0.0.0:8000/mcp
MCP_PORT=9000 python server.py # custom port
```

The agent connects to `http://localhost:8000/mcp` by default. Override with:

```bash
MCP_URL=http://192.168.1.10:8000/mcp python agent.py
```

---

## Supported Models

Any Ollama model with tool-calling support works. Tested models:

| Model | Notes |
|-------|-------|
| `llama3.2` | Default. Reliable tool calling. |
| `llama3.1` | Reliable tool calling. |
| `qwen2.5` | Good tool calling. `arguments` sometimes arrives as a JSON string — handled automatically. |
| `qwen3` | Same family as qwen2.5, same fix applies. `:thinking` variants add chain-of-thought but are slower. |
| `gemma3:4b`+ | Use 4b or larger. The 1b does not reliably call tools. May wrap final response in markdown fencing (cosmetic). |
| `mistral` | Supported on 7b+. |

---

## Notes

- CoinGecko free Demo: 30 req/min · 10,000 req/month · no credit card
- The agent throttles to ~27 req/min to stay within limits
- `get_wallet_summary` uses one batched price call regardless of how many coins you hold
- Credit: *Data provided by [CoinGecko](https://www.coingecko.com/en/api)*

