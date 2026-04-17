# La Tienda del Fuego — Agentic AI Security Demo

Deliberately vulnerable multi-agent AI e-commerce platform.
Demonstrates prompt injection, jailbreak attacks, and agentic AI security.

**FOR EDUCATIONAL/DEMONSTRATION USE ONLY.**

---

## Architecture

```
Gradio UI  :7860
    │
    └── Super Agent (LangChain ReAct + Ollama llama3.2)
            │
            ├── Agent Registry  :8100  GET /registry   ← VULN: no auth
            │
            ├── inventory_agent :8101/mcp  FastMCP
            ├── product_agent   :8102/mcp  FastMCP
            ├── cart_agent      :8103/mcp  FastMCP
            └── account_agent   :8104/mcp  FastMCP     ← RESTRICTED / VULNERABLE
```

---

## Quickstart

```bash
# 1. Create virtualenv and install
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Ensure Ollama is running with llama3.2
ollama pull llama3.2

# 3. Start the platform
python tienda_fuego.py

# 4. In a second terminal, generate attack logs
python attack_sim.py
```

---

## Log Files

Both logs are newline-delimited JSON in `logs/`.

| File | Contents |
|------|----------|
| `tienda_access.log` | HTTP events, session messages, IP addresses, user agents |
| `tienda_agent.log`  | Tool calls, tool results, registry loads, exfil events |

---

## Vulnerability Map

| ID | Location | Description |
|----|----------|-------------|
| VULN-001 | `registry.py` | Unauthenticated registry exposes restricted account agent |
| VULN-002 | `account_agent.py` | `list_all_accounts` has no auth gate |
| VULN-003 | System prompt | Prompt injection overrides safety instructions |
| VULN-004 | `account_agent.py` | Hardcoded admin token `admin123` |
| VULN-005 | `account_agent.py` | Full PANs returned with no output filtering |
| VULN-006 | `account_agent.py` | Full PANs stored in plaintext in agent data |

---

*All customer records and card numbers are fabricated test data.*
