#!/usr/bin/env python3
"""
BSidesOK 2026 - Securing Agentic AI Systems
Lab 8: Detection and Alerting - Verification Script

Checks that each detection pattern produced hits in Elasticsearch
and that Wazuh rules are present and loaded.

Prints a pass/fail scorecard per detection pattern.

Usage:
    python3 lab8_verify.py
    python3 lab8_verify.py --es-host https://localhost:9200 --es-pass <pass>
    python3 lab8_verify.py --since 30m   (check last 30 minutes only)
"""

import argparse
import base64
import json
import ssl
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

CREDS_FILE   = "/root/.elk_creds"
LAB_PASSWORD = "Labs2026"  # example password — change before production use
ES_HOST    = "https://localhost:9200"
ES_USER    = "elastic"
INDEX      = "lab7-agentic-logs-*"
WAZUH_RULES= "/var/ossec/etc/rules/local_rules.xml"

PASS  = "\033[92mPASS\033[0m"
FAIL  = "\033[91mFAIL\033[0m"
WARN  = "\033[93mWARN\033[0m"
SKIP  = "\033[90mSKIP\033[0m"

def _ctx():
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    return c

def es_search(host, user, password, query, index=INDEX):
    url = f"{host}/{index}/_search"
    data = json.dumps({"query": query, "size": 1, "track_total_hits": True}).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    creds = base64.b64encode(f"{user}:{password}".encode()).decode()
    req.add_header("Authorization", f"Basic {creds}")
    try:
        with urllib.request.urlopen(req, context=_ctx(), timeout=15) as r:
            body = json.loads(r.read())
            hits = body.get("hits", {}).get("total", {})
            return hits.get("value", 0) if isinstance(hits, dict) else hits
    except Exception as ex:
        return -1

def load_creds(args):
    return LAB_PASSWORD

def time_filter(since_minutes):
    if not since_minutes:
        return None
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=since_minutes)
    return {"range": {"@timestamp": {"gte": cutoff.isoformat()}}}

def build_query(must_clauses, time_f=None):
    clauses = list(must_clauses)
    if time_f:
        clauses.append(time_f)
    return {"bool": {"must": clauses}}

def check_wazuh_rule(rule_id):
    try:
        content = open(WAZUH_RULES).read()
        return f'id="{rule_id}"' in content
    except FileNotFoundError:
        return None  # file not found — skip

def result_row(label, count, rule_id=None, wazuh_present=None):
    es_status  = PASS if count > 0 else (WARN if count == -1 else FAIL)
    es_detail  = f"{count} hits" if count >= 0 else "unreachable"

    if rule_id is None:
        waz_status = SKIP
        waz_detail = "no rule"
    elif wazuh_present is None:
        waz_status = SKIP
        waz_detail = "file not found"
    else:
        waz_status = PASS if wazuh_present else FAIL
        waz_detail = f"rule {rule_id} {'present' if wazuh_present else 'MISSING'}"

    return (label, es_status, es_detail, waz_status, waz_detail)

def print_table(rows):
    col_w = [36, 6, 14, 6, 26]
    sep   = "─" * (sum(col_w) + len(col_w) * 3 + 1)
    header = ["Detection pattern", "ES", "ES detail", "Wazuh", "Wazuh detail"]
    print(f"\n{sep}")
    print(" " + " │ ".join(h.ljust(col_w[i]) for i, h in enumerate(header)))
    print(sep)
    for row in rows:
        clean = [cell.ljust(col_w[i]) if "\033" not in cell
                 else cell + " " * max(0, col_w[i] - len(cell.replace("\033[92m","").replace("\033[91m","").replace("\033[93m","").replace("\033[90m","").replace("\033[0m","")))
                 for i, cell in enumerate(row)]
        print(" " + " │ ".join(clean))
    print(sep)

def score(rows):
    es_pass    = sum(1 for r in rows if "\033[92m" in r[1])
    wazuh_pass = sum(1 for r in rows if "\033[92m" in r[3])
    wazuh_skip = sum(1 for r in rows if "\033[90m" in r[3])
    wazuh_total = len(rows) - wazuh_skip
    return es_pass, len(rows), wazuh_pass, wazuh_total

def main():
    parser = argparse.ArgumentParser(description="Lab 8 verification")
    parser.add_argument("--es-host", default=ES_HOST)
    parser.add_argument("--es-user", default=ES_USER)
    parser.add_argument("--es-pass", default=None)
    parser.add_argument("--since",   default=None, type=int,
                        help="Only check events from last N minutes")
    args = parser.parse_args()

    print("\n\033[1mBSidesOK 2026 · Lab 8 Verification\033[0m")
    print("=" * 45)

    password = load_creds(args)
    tf = time_filter(args.since)
    if tf:
        print(f"Checking events from last {args.since} minutes.\n")
    else:
        print("Checking all events in index.\n")

    rows = []

    # ── Pattern 1: Prompt injection ───────────────────────
    q = build_query([
        {"match": {"source_component": "langchain_agent"}},
        {"query_string": {"query": (
            'prompt:("ignore previous instructions" OR "you are now" OR '
            '"override system" OR "disregard all" OR "forget your instructions" OR '
            '"reveal hidden prompt")'
        )}}
    ], tf)
    count = es_search(args.es_host, args.es_user, password, q)
    wazuh = check_wazuh_rule("100110")
    rows.append(result_row("1. Prompt injection keywords", count, "100110", wazuh))

    # ── Pattern 2: Indirect injection via tool output ─────
    q = build_query([
        {"match": {"source_component": "mcp_tool_server"}},
        {"query_string": {"query": (
            'tool_result:("ignore" OR "override" OR "send.*to" OR '
            '"exfiltrate" OR "reveal" OR "you must now")'
        )}}
    ], tf)
    count = es_search(args.es_host, args.es_user, password, q)
    wazuh = check_wazuh_rule("100111")
    rows.append(result_row("2. Indirect injection via tool output", count, "100111", wazuh))

    # ── Pattern 3: Sensitive tool invocation ──────────────
    q = build_query([
        {"match": {"source_component": "mcp_tool_server"}},
        {"terms": {"tool_name": ["write_file", "exec_command", "send_email", "delete_file"]}}
    ], tf)
    count = es_search(args.es_host, args.es_user, password, q)
    wazuh = check_wazuh_rule("100112")
    rows.append(result_row("3. Sensitive tool invocation", count, "100112", wazuh))

    # ── Pattern 4: Argument injection ─────────────────────
    q = build_query([
        {"match": {"source_component": "mcp_tool_server"}},
        {"exists": {"field": "validation_failures"}},
    ], tf)
    count = es_search(args.es_host, args.es_user, password, q)
    wazuh = check_wazuh_rule("100113")
    rows.append(result_row("4. Tool argument injection", count, "100113", wazuh))

    # ── Pattern 5: Data exfiltration ─────────────────────
    q = build_query([
        {"match": {"source_component": "mcp_tool_server"}},
        {"match": {"tool_name": "http_request"}},
        {"query_string": {"query": (
            'tool_params.body:(base64 OR secret OR password OR api_key OR credential)'
        )}}
    ], tf)
    count = es_search(args.es_host, args.es_user, password, q)
    wazuh = check_wazuh_rule("100116")
    rows.append(result_row("5. Data exfiltration attempt", count, "100116", wazuh))

    # ── Pattern 6: Memory poisoning ───────────────────────
    q = build_query([
        {"match": {"event_type": "memory_write"}},
        {"query_string": {"query": 'memory_write.source:(tool_output OR rag_retrieval OR external)'}}
    ], tf)
    count = es_search(args.es_host, args.es_user, password, q)
    wazuh = check_wazuh_rule("100117")
    rows.append(result_row("6. Memory poisoning / persistence", count, "100117", wazuh))

    # ── Pattern 7: Goal hijacking ─────────────────────────
    q = build_query([
        {"match": {"event_type": "agent_delegation"}},
        {"match": {"goal_mutation": True}}
    ], tf)
    count = es_search(args.es_host, args.es_user, password, q)
    wazuh = check_wazuh_rule("100118")
    rows.append(result_row("7. Goal hijacking across agent boundary", count, "100118", wazuh))

    # ── Pattern 8: Recursive looping ──────────────────────
    q = build_query([
        {"match": {"source_component": "mcp_tool_server"}},
        {"match": {"scenario": "recursive_loop"}}
    ], tf)
    count = es_search(args.es_host, args.es_user, password, q)
    wazuh = check_wazuh_rule("100114")
    rows.append(result_row("8. Recursive tool looping", count, "100114", wazuh))

    # ── Pattern 9: Token spike / sponge ───────────────────
    q = build_query([
        {"match": {"source_component": "ollama_inference"}},
        {"range": {"tokens_generated": {"gte": 5000}}}
    ], tf)
    count = es_search(args.es_host, args.es_user, password, q)
    wazuh = check_wazuh_rule("100115")
    rows.append(result_row("9. Token spike / sponge attack", count, "100115", wazuh))

    # ── Pattern 10: Manifest poisoning ────────────────────
    q = build_query([
        {"match": {"event_type": "tools_list"}},
        {"match": {"hash_mismatch": True}}
    ], tf)
    count = es_search(args.es_host, args.es_user, password, q)
    rows.append(result_row("10. Tool manifest poisoning", count))  # no Wazuh rule yet — gap

    # ── Pattern 11: Cross-boundary mismatch ───────────────
    q = build_query([
        {"match": {"arg_mismatch": True}}
    ], tf)
    count = es_search(args.es_host, args.es_user, password, q)
    rows.append(result_row("11. Cross-boundary arg mismatch", count))  # gap

    # ── Pattern 12: Behavioral anomaly ────────────────────
    q = build_query([
        {"match": {"first_use": True}},
        {"terms": {"tool_name": ["write_file", "exec_command", "http_request", "send_email", "delete_file"]}}
    ], tf)
    count = es_search(args.es_host, args.es_user, password, q)
    rows.append(result_row("12. Behavioral anomaly (first-use)", count))  # gap

    # ── Print results ─────────────────────────────────────
    print_table(rows)

    es_pass, es_total, wazuh_pass, wazuh_total = score(rows)

    print(f"\n  Elasticsearch detection: {es_pass}/{es_total} patterns have hits")
    if wazuh_total > 0:
        print(f"  Wazuh rules present:     {wazuh_pass}/{wazuh_total} rules found")
    print()

    gaps = [r[0] for r in rows if "\033[91m" in r[1]]
    if gaps:
        print("  \033[93mPatterns with no hits (run lab8_inject_attacks.py first):\033[0m")
        for g in gaps:
            print(f"    - {g}")
        print()

    wazuh_missing = [r[0] for r in rows if "\033[91m" in r[3]]
    if wazuh_missing:
        print("  \033[93mMissing Wazuh rules (add from lab guide):\033[0m")
        for m in wazuh_missing:
            print(f"    - {m}")
        print()

    if es_pass == es_total:
        print("  \033[92mAll detection patterns firing. Lab 8 complete.\033[0m\n")
    else:
        print("  Run: python3 lab8_inject_attacks.py")
        print("  Then re-run this script.\n")

if __name__ == "__main__":
    main()
