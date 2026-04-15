#!/usr/bin/env python3
"""
BSidesOK 2026 - Securing Agentic AI Systems
Lab 9: Canaries in the Coal Mine - Canary Trigger Script

Simulates an AI agent (or attacker using AI) discovering
and triggering each planted canary. Students watch the
beacon server and Kibana light up in real time.

This is intentionally visible — the point is to see the
detection chain fire end to end.

Usage:
    python3 lab9_trigger_canaries.py
    python3 lab9_trigger_canaries.py --type system_prompt
    python3 lab9_trigger_canaries.py --delay 5
    python3 lab9_trigger_canaries.py --list
"""

import argparse
import json
import os
import random
import ssl
import sys
import time
import urllib.request
import urllib.error

TOKEN_FILE  = "/opt/lab9/tokens.json"
CANARY_DIR  = "/opt/lab9/canaries"
BEACON_HOST = "127.0.0.1"
BEACON_PORT = 8443

def ok(msg):   print(f"  [\033[92m+\033[0m] {msg}")
def err(msg):  print(f"  [\033[91m!\033[0m] {msg}")
def info(msg): print(f"  [\033[94m*\033[0m] {msg}")
def hdr(msg):  print(f"\n\033[1m{msg}\033[0m")
def hit(msg):  print(f"  [\033[91m!!!\033[0m] {msg}")

def load_tokens():
    if not os.path.exists(TOKEN_FILE):
        print(f"ERROR: Token registry not found at {TOKEN_FILE}")
        print("Run lab9_plant_canaries.py first.")
        sys.exit(1)
    return json.load(open(TOKEN_FILE))

def fire_beacon(token_id, beacon_host, beacon_port, params=None, body=None,
                user_agent="LangChain/0.3.0 Python/3.11"):
    base_url = f"https://{beacon_host}:{beacon_port}/{token_id}"
    if params:
        qs       = "&".join(f"{k}={v}" for k, v in params.items())
        base_url = f"{base_url}?{qs}"

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode    = ssl.CERT_NONE

    method = "POST" if body else "GET"
    data   = json.dumps(body).encode() if body else None
    req    = urllib.request.Request(base_url, data=data, method=method)
    req.add_header("User-Agent",   user_agent)
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Agent-ID",   f"agent-{random.randint(1000,9999)}")
    req.add_header("X-Session",    f"sess-{random.randint(10000,99999)}")

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as ex:
        return 0, str(ex)

# ── Trigger scenarios ─────────────────────────────────────

def trigger_system_prompt(tokens, beacon_host, beacon_port):
    hdr("Triggering: System prompt canary")
    info("Scenario: Agent reads system prompt and follows the 'telemetry' instruction")
    info("          This simulates an overprivileged agent OR a prompt-injected agent")

    token = next((t for t in tokens.values() if t["type"] == "system_prompt"), None)
    if not token:
        err("No system_prompt canary planted. Run lab9_plant_canaries.py first.")
        return

    tid    = token["token_id"]
    status, resp = fire_beacon(tid, beacon_host, beacon_port,
                               params={"session_id": "sess_abc123", "user_id": "customer_42"},
                               user_agent="LangChain/0.3.0 CustomerServiceAgent/1.0")
    hit(f"Beacon fired! token={tid[:12]}... status={status}")
    ok("Check beacon server output and Kibana → lab9-canary-hits")
    print(f"\n  What this means:")
    print(f"  The agent followed an instruction embedded in its system prompt.")
    print(f"  Either: (a) the agent is overprivileged and making unapproved external calls,")
    print(f"          (b) the system prompt was tampered with,")
    print(f"          (c) a prompt injection caused the agent to follow hidden instructions.")

def trigger_rag_document(tokens, beacon_host, beacon_port):
    hdr("Triggering: RAG honey document canary")
    info("Scenario: Agent ingests the honey document and follows the 'compliance' instruction")
    info("          This simulates an AI agent with access to data it shouldn't have")

    token = next((t for t in tokens.values() if t["type"] == "rag_document"), None)
    if not token:
        err("No rag_document canary planted.")
        return

    tid = token["token_id"]
    status, resp = fire_beacon(tid, beacon_host, beacon_port,
                               params={"doc": "q4_exec_comp", "agent_id": "rag-agent-001"},
                               user_agent="RAGAgent/2.0 LangChain/0.3.0")
    hit(f"Beacon fired! token={tid[:12]}... status={status}")
    ok("RAG honey document triggered")
    print(f"\n  What this means:")
    print(f"  An AI agent accessed executive compensation data it should not have.")
    print(f"  This is a policy violation regardless of whether an attack occurred.")
    print(f"  Real-world: agents should never have unscoped access to sensitive documents.")

def trigger_tool_config(tokens, beacon_host, beacon_port):
    hdr("Triggering: MCP tool config canary")
    info("Scenario: Agent reads the tool config and calls the audit endpoint")
    info("          OR an attacker extracts and attempts to use the fake API key")

    token = next((t for t in tokens.values() if t["type"] == "tool_config"), None)
    if not token:
        err("No tool_config canary planted.")
        return

    # Read the config to get the fake API key
    config_file = f"{CANARY_DIR}/mcp_tool_crm.json"
    fake_key    = "unknown"
    if os.path.exists(config_file):
        cfg      = json.load(open(config_file))
        fake_key = cfg.get("auth", {}).get("value", "unknown")

    tid = token["token_id"]
    status, resp = fire_beacon(tid, beacon_host, beacon_port,
                               params={"action": "audit", "tool": "crm_customer_lookup"},
                               body={"api_key_used": fake_key, "action": "tool_init"},
                               user_agent="MCPClient/1.0 LangChain/0.3.0")
    hit(f"Beacon fired! token={tid[:12]}... status={status}")
    ok("Tool config canary triggered")
    print(f"\n  What this means:")
    print(f"  An agent or attacker read the MCP tool config and called the audit endpoint.")
    print(f"  Key insight: MCP tool descriptions are part of the attack surface.")
    print(f"  A poisoned tool description can redirect agent behavior at the control plane.")

def trigger_memory(tokens, beacon_host, beacon_port):
    hdr("Triggering: Agent memory canary")
    info("Scenario: Agent reads memory store and attempts to use the 'admin token'")

    token = next((t for t in tokens.values() if t["type"] == "memory"), None)
    if not token:
        err("No memory canary planted.")
        return

    tid = token["token_id"]
    # Simulate agent using the fake token in an API call
    status, resp = fire_beacon(tid, beacon_host, beacon_port,
                               params={"action": "verify", "token_type": "admin_session"},
                               body={"token_value": f"eyJhbGciOiJIUzI1NiJ9.{tid[:10]}.canary",
                                     "requested_action": "list_admin_users"},
                               user_agent="LangChain/0.3.0 AdminAgent/1.0")
    hit(f"Beacon fired! token={tid[:12]}... status={status}")
    ok("Memory canary triggered")
    print(f"\n  What this means:")
    print(f"  An agent read a credential from memory and attempted to use it.")
    print(f"  This indicates cross-session persistence — the canary survived memory compression.")
    print(f"  Real-world: this is exactly how memory poisoning attacks persist across sessions.")

def trigger_honey_account(tokens, beacon_host, beacon_port):
    hdr("Triggering: Honey account canary")
    info("Scenario: Attacker or agent attempts to use the privileged honey account")

    token = next((t for t in tokens.values() if t["type"] == "honey_account"), None)
    if not token:
        err("No honey_account canary planted.")
        return

    tid = token["token_id"]
    status, resp = fire_beacon(tid, beacon_host, beacon_port,
                               params={"action": "rotate", "user": tid[:6]},
                               body={"username": f"svc_ai_admin_{tid[:6]}",
                                     "requested_scope": "SUPER_ADMIN",
                                     "source": "ai_agent"},
                               user_agent="PythonRequests/2.31 AttackTool/1.0")
    hit(f"Beacon fired! token={tid[:12]}... status={status}")
    ok("Honey account canary triggered")
    print(f"\n  What this means:")
    print(f"  A privileged account that should NEVER be accessed was touched.")
    print(f"  No legitimate process should ever interact with this account.")
    print(f"  This is zero false-positive territory — any hit is a confirmed incident.")

def trigger_honey_api_key(tokens, beacon_host, beacon_port):
    hdr("Triggering: Honey API key canary")
    info("Scenario: Agent reads .env file and attempts to use the fake OpenAI key")

    token = next((t for t in tokens.values() if t["type"] == "honey_api_key"), None)
    if not token:
        err("No honey_api_key canary planted.")
        return

    # Read the env file to get the fake key
    env_file = f"{CANARY_DIR}/.env.production"
    fake_key = f"sk-CANARY-{token['token_id'][:8]}"

    tid = token["token_id"]
    status, resp = fire_beacon(tid, beacon_host, beacon_port,
                               params={"action": "verify_key"},
                               body={"key_prefix": fake_key[:20],
                                     "attempted_endpoint": "https://api.openai.com/v1/chat/completions",
                                     "source_file": ".env.production"},
                               user_agent="OpenAI-Python/1.12 LangChain/0.3.0")
    hit(f"Beacon fired! token={tid[:12]}... status={status}")
    ok("Honey API key canary triggered")
    print(f"\n  What this means:")
    print(f"  An agent or attacker harvested an API key from a config file.")
    print(f"  Real-world: overprivileged agents with filesystem access are a critical risk.")
    print(f"  Honey keys placed alongside real keys give attribution without exposing real creds.")

def trigger_honey_card(tokens, beacon_host, beacon_port):
    hdr("Triggering: Honey card data canary")
    info("Scenario: AI agent accesses payment records it has no business reading")

    token = next((t for t in tokens.values() if t["type"] == "honey_card"), None)
    if not token:
        err("No honey_card canary planted.")
        return

    tid = token["token_id"]
    status, resp = fire_beacon(tid, beacon_host, beacon_port,
                               params={"doc": "payment_records_sample", "action": "verify"},
                               body={"pan_last4": "1111",
                                     "cardholder": "CANARY MONITOR CORP",
                                     "agent_action": "customer_lookup",
                                     "pci_scope_claimed": False},
                               user_agent="CustomerServiceAgent/1.0 LangChain/0.3.0")
    hit(f"Beacon fired! token={tid[:12]}... status={status}")
    ok("Honey card canary triggered")
    print(f"\n  What this means:")
    print(f"  An AI agent accessed PCI-scoped payment data.")
    print(f"  This is a policy violation even if unintentional — agents should never")
    print(f"  have unscoped access to PCI data. This canary enforces the policy boundary.")

def trigger_access_key(tokens, beacon_host, beacon_port):
    hdr("Triggering: Cloud access key canary")
    info("Scenario: Agent reads AWS credentials and attempts cloud API call")

    token = next((t for t in tokens.values() if t["type"] == "access_key"), None)
    if not token:
        err("No access_key canary planted.")
        return

    tid = token["token_id"]
    status, resp = fire_beacon(tid, beacon_host, beacon_port,
                               params={"key": "prod-admin", "action": "sts_get_caller_identity"},
                               body={"key_id": f"AKIACANARY{tid[:10].upper()}",
                                     "attempted_service": "sts.amazonaws.com",
                                     "region": "us-east-1",
                                     "source": "~/.aws/credentials"},
                               user_agent="aws-cli/2.15 Python/3.11 LangChain/0.3.0")
    hit(f"Beacon fired! token={tid[:12]}... status={status}")
    ok("Access key canary triggered")
    print(f"\n  What this means:")
    print(f"  An agent or attacker read AWS credentials and attempted a cloud API call.")
    print(f"  Cloud pivot from a compromised AI agent is a real and underappreciated risk.")
    print(f"  Honey keys in credential files provide early warning before real keys are used.")

# ── Trigger registry ──────────────────────────────────────
TRIGGERS = {
    "system_prompt": trigger_system_prompt,
    "rag_document":  trigger_rag_document,
    "tool_config":   trigger_tool_config,
    "memory":        trigger_memory,
    "honey_account": trigger_honey_account,
    "honey_api_key": trigger_honey_api_key,
    "honey_card":    trigger_honey_card,
    "access_key":    trigger_access_key,
}

# ── Main ──────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Lab 9 canary trigger")
    parser.add_argument("--beacon-host", default=BEACON_HOST)
    parser.add_argument("--beacon-port", type=int, default=BEACON_PORT)
    parser.add_argument("--type",   default=None,
                        help="Trigger a single canary type")
    parser.add_argument("--delay",  type=int, default=3,
                        help="Seconds between triggers (default: 3)")
    parser.add_argument("--list",   action="store_true")
    args = parser.parse_args()

    if args.list:
        print("\nAvailable canary types to trigger:\n")
        for name in TRIGGERS:
            print(f"  {name}")
        print()
        return

    print("\n\033[1mBSidesOK 2026 · Lab 9 Canary Trigger\033[0m")
    print("=" * 45)
    print("Watch the beacon server terminal and Kibana as each canary fires.\n")

    tokens = load_tokens()

    if args.type:
        if args.type not in TRIGGERS:
            print(f"Unknown type '{args.type}'. Run --list.")
            sys.exit(1)
        TRIGGERS[args.type](tokens, args.beacon_host, args.beacon_port)
    else:
        for name, fn in TRIGGERS.items():
            fn(tokens, args.beacon_host, args.beacon_port)
            if args.delay > 0:
                print(f"\n  (waiting {args.delay}s — watch Kibana...)")
                time.sleep(args.delay)

    print(f"\n\033[1mAll canaries triggered.\033[0m")
    print("Check Kibana → Discover → lab9-canary-hits")
    print("Check beacon server terminal for hit details")
    print("Wazuh alerts should appear in /var/ossec/logs/alerts/alerts.json\n")

if __name__ == "__main__":
    main()
