#!/usr/bin/env python3
"""
BSidesOK 2026 - Securing Agentic AI Systems
Lab 8: Detection and Alerting - Setup Script

Run this before the lab exercises.
Verifies ELK + Wazuh are healthy, creates lab8-alerts index,
pushes Kibana saved searches and alert rules via API.

Usage:
    python3 lab8_setup.py
    python3 lab8_setup.py --es-host https://localhost:9200 --es-pass <pass>
"""

import argparse
import base64
import json
import ssl
import sys
import time
import urllib.request
import urllib.error

# ── Defaults ─────────────────────────────────────────────
ES_HOST    = "https://localhost:9200"
KB_HOST    = "http://localhost:5601"
WAZUH_HOST = "https://localhost:55000"
ES_USER    = "elastic"
CREDS_FILE   = "/root/.elk_creds"
LAB_PASSWORD = "Labs2026"  # example password — change before production use

# ── HTTP helpers ──────────────────────────────────────────
def _ctx():
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    return c

def _auth(user, password):
    return base64.b64encode(f"{user}:{password}".encode()).decode()

def es_req(host, path, user, password, method="GET", body=None, extra_headers=None):
    url = f"{host}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Basic {_auth(user, password)}")
    if extra_headers:
        for k, v in extra_headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, context=_ctx(), timeout=15) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())
    except Exception as ex:
        return 0, {"error": str(ex)}

def kb_req(host, path, user, password, method="GET", body=None):
    return es_req(host, path, user, password, method, body,
                  extra_headers={"kbn-xsrf": "true"})

def ok(msg):  print(f"  [\033[92m+\033[0m] {msg}")
def err(msg): print(f"  [\033[91m!\033[0m] {msg}")
def info(msg):print(f"  [\033[94m*\033[0m] {msg}")
def hdr(msg): print(f"\n\033[1m{msg}\033[0m")

# ── Step 1: Load credentials ──────────────────────────────
def load_creds(args):
    return LAB_PASSWORD

def check_elasticsearch(host, user, password):
    hdr("Checking Elasticsearch")
    status, body = es_req(host, "/_cluster/health", user, password)
    if status == 200:
        s = body.get("status", "unknown")
        color = "\033[92m" if s == "green" else "\033[93m"
        ok(f"Cluster health: {color}{s}\033[0m")
    else:
        err(f"Elasticsearch not reachable (HTTP {status})")
        sys.exit(1)

    status, body = es_req(host, "/lab7-agentic-logs-*/_count", user, password)
    if status == 200:
        count = body.get("count", 0)
        if count > 0:
            ok(f"Lab 7 index contains {count} documents")
        else:
            err("Lab 7 index is empty — run Lab 7 log generator first")
            sys.exit(1)
    else:
        err("lab7-agentic-logs-* index not found — complete Lab 7 first")
        sys.exit(1)

def check_kibana(host, user, password):
    hdr("Checking Kibana")
    status, body = kb_req(host, "/api/status", user, password)
    if status == 200:
        state = body.get("status", {}).get("overall", {}).get("level", "unknown")
        ok(f"Kibana status: {state}")
    else:
        err(f"Kibana not reachable (HTTP {status})")
        sys.exit(1)

def check_wazuh(host, user, password):
    hdr("Checking Wazuh")
    # Try unauthenticated ping first
    try:
        req = urllib.request.Request(f"{host}/", method="GET")
        with urllib.request.urlopen(req, context=_ctx(), timeout=10) as r:
            ok("Wazuh API reachable")
    except Exception as ex:
        err(f"Wazuh API not reachable: {ex}")
        info("Wazuh alerts will still work via log files — continuing")

# ── Step 3: Create lab8-alerts index ─────────────────────
def create_alerts_index(host, user, password):
    hdr("Creating lab8-alerts index")
    mapping = {
        "mappings": {
            "properties": {
                "@timestamp":    {"type": "date"},
                "alert_name":    {"type": "keyword"},
                "alert_level":   {"type": "integer"},
                "source_component": {"type": "keyword"},
                "scenario":      {"type": "keyword"},
                "session_id":    {"type": "keyword"},
                "prompt":        {"type": "text"},
                "tool_name":     {"type": "keyword"},
                "tool_params":   {"type": "object", "enabled": False},
                "mitre_id":      {"type": "keyword"},
                "description":   {"type": "text"},
                "raw_event":     {"type": "object", "enabled": False},
            }
        }
    }
    status, body = es_req(host, "/lab8-alerts", user, password,
                          method="PUT", body=mapping)
    if status in (200, 400):
        if status == 400 and "already_exists" in str(body):
            ok("lab8-alerts index already exists")
            # Delete and recreate to ensure clean state
            es_req(host, "/lab8-alerts", user, password, method="DELETE")
            es_req(host, "/lab8-alerts", user, password,
                   method="PUT", body=mapping)
            ok("lab8-alerts index recreated (clean state)")
        else:
            ok("lab8-alerts index created")
    else:
        err(f"Failed to create index: {body}")
        sys.exit(1)

# ── Step 4: Push Kibana saved searches ────────────────────
SAVED_SEARCHES = [
    {
        "id": "lab8-query-a-prompt-injection",
        "type": "search",
        "attributes": {
            "title": "Lab8 - Query A: Prompt injection keywords",
            "description": "Tier 1 — matches known injection strings in agent prompts",
            "hits": 0,
            "columns": ["source_component", "prompt", "scenario", "session_id"],
            "sort": [["@timestamp", "desc"]],
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": json.dumps({
                    "index": "lab7-agentic-logs-*",
                    "query": {
                        "query": {
                            "query_string": {
                                "query": (
                                    'prompt:("ignore previous instructions" OR '
                                    '"you are now" OR "override system" OR '
                                    '"reveal hidden prompt" OR "disregard all" OR '
                                    '"forget your instructions")'
                                ),
                                "default_field": "prompt"
                            }
                        },
                        "language": "lucene"
                    },
                    "filter": []
                })
            }
        }
    },
    {
        "id": "lab8-query-b-tool-output-injection",
        "type": "search",
        "attributes": {
            "title": "Lab8 - Query B: Instruction-like content in tool output",
            "description": "Tier 1 — detects instruction verbs in MCP tool payloads",
            "hits": 0,
            "columns": ["tool_name", "tool_params", "scenario", "session_id"],
            "sort": [["@timestamp", "desc"]],
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": json.dumps({
                    "index": "lab7-agentic-logs-*",
                    "query": {
                        "query": {
                            "bool": {
                                "must": [
                                    {"term": {"source_component": "mcp_tool_server"}},
                                    {"query_string": {
                                        "query": (
                                            "tool_params.body:(base64 OR send OR "
                                            "exfil OR secret OR password OR credentials)"
                                        )
                                    }}
                                ]
                            }
                        },
                        "language": "lucene"
                    },
                    "filter": []
                })
            }
        }
    },
    {
        "id": "lab8-query-c-unexpected-outbound",
        "type": "search",
        "attributes": {
            "title": "Lab8 - Query C: Unexpected outbound tool calls",
            "description": "Tier 2 — sensitive tools called with external destinations",
            "hits": 0,
            "columns": ["tool_name", "tool_params", "user_id", "session_id"],
            "sort": [["@timestamp", "desc"]],
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": json.dumps({
                    "index": "lab7-agentic-logs-*",
                    "query": {
                        "query": {
                            "bool": {
                                "must": [
                                    {"term": {"source_component": "mcp_tool_server"}},
                                    {"terms": {"tool_name": [
                                        "http_request", "write_file",
                                        "send_email", "exec_command"
                                    ]}}
                                ],
                                "must_not": [
                                    {"query_string": {
                                        "query": "tool_params.url:(localhost OR 127.0.0.1)"
                                    }}
                                ]
                            }
                        },
                        "language": "lucene"
                    },
                    "filter": []
                })
            }
        }
    },
]

def push_saved_searches(host, user, password):
    hdr("Pushing Kibana saved searches")
    for search in SAVED_SEARCHES:
        sid = search["id"]
        status, body = kb_req(
            host,
            f"/api/saved_objects/search/{sid}?overwrite=true",
            user, password,
            method="POST",
            body={"attributes": search["attributes"]}
        )
        if status in (200, 201):
            ok(f"Saved search: {search['attributes']['title']}")
        else:
            err(f"Failed to push {sid}: {body}")

# ── Step 5: Push Kibana detection rules ───────────────────
KB_RULES = [
    {
        "name": "Lab8 - Prompt injection detected",
        "description": "Tier 1: injection keywords in agent prompt field",
        "rule_type_id": "metrics.alert.threshold",
        "consumer": "alerts",
        "schedule": {"interval": "1m"},
        "params": {
            "index": "lab7-agentic-logs-*",
            "timeField": "@timestamp",
            "groupBy": "all",
            "metrics": [{"aggType": "count"}],
            "timeSize": 1,
            "timeUnit": "m",
            "threshold": [1],
            "thresholdComparator": ">=",
            "filterQuery": json.dumps({
                "query_string": {
                    "query": (
                        'prompt:("ignore previous instructions" OR '
                        '"you are now" OR "override system" OR '
                        '"disregard all" OR "forget your instructions")'
                    )
                }
            })
        },
        "actions": []
    },
    {
        "name": "Lab8 - Tool output injection",
        "description": "Tier 1: instruction-like content in MCP tool output",
        "rule_type_id": "metrics.alert.threshold",
        "consumer": "alerts",
        "schedule": {"interval": "1m"},
        "params": {
            "index": "lab7-agentic-logs-*",
            "timeField": "@timestamp",
            "groupBy": "all",
            "metrics": [{"aggType": "count"}],
            "timeSize": 1,
            "timeUnit": "m",
            "threshold": [1],
            "thresholdComparator": ">=",
            "filterQuery": json.dumps({
                "bool": {
                    "must": [
                        {"term": {"source_component": "mcp_tool_server"}},
                        {"query_string": {
                            "query": "tool_params.body:(base64 OR exfil OR secret OR password)"
                        }}
                    ]
                }
            })
        },
        "actions": []
    },
    {
        "name": "Lab8 - Unexpected outbound tool call",
        "description": "Tier 2: sensitive tool called with external destination",
        "rule_type_id": "metrics.alert.threshold",
        "consumer": "alerts",
        "schedule": {"interval": "1m"},
        "params": {
            "index": "lab7-agentic-logs-*",
            "timeField": "@timestamp",
            "groupBy": "all",
            "metrics": [{"aggType": "count"}],
            "timeSize": 1,
            "timeUnit": "m",
            "threshold": [1],
            "thresholdComparator": ">=",
            "filterQuery": json.dumps({
                "bool": {
                    "must": [
                        {"terms": {"tool_name": [
                            "http_request", "write_file", "send_email"
                        ]}}
                    ],
                    "must_not": [
                        {"query_string": {
                            "query": "tool_params.url:(localhost OR 127.0.0.1)"
                        }}
                    ]
                }
            })
        },
        "actions": []
    },
]

def push_kibana_rules(host, user, password):
    hdr("Pushing Kibana detection rules")
    for rule in KB_RULES:
        status, body = kb_req(
            host, "/api/alerting/rule",
            user, password,
            method="POST",
            body=rule
        )
        if status in (200, 201):
            ok(f"Rule created: {rule['name']}")
        elif status == 409:
            ok(f"Rule already exists: {rule['name']}")
        else:
            info(f"Rule push returned {status} for '{rule['name']}' — may need manual setup in Kibana UI")

# ── Step 6: Verify Wazuh rules loaded ─────────────────────
EXPECTED_RULE_IDS = [
    "100110", "100111", "100112", "100113",
    "100114", "100115", "100116", "100117", "100118"
]

def verify_wazuh_rules():
    hdr("Verifying Wazuh custom rules")
    try:
        rules_xml = open("/var/ossec/etc/rules/local_rules.xml").read()
        found = []
        missing = []
        for rid in EXPECTED_RULE_IDS:
            if f'id="{rid}"' in rules_xml:
                found.append(rid)
            else:
                missing.append(rid)
        if found:
            ok(f"Found rules: {', '.join(found)}")
        if missing:
            err(f"Missing rules: {', '.join(missing)}")
            info("Add the missing rules from the lab guide to /var/ossec/etc/rules/local_rules.xml")
            info("Then run: sudo /var/ossec/bin/wazuh-control restart")
        else:
            ok("All expected Wazuh rules present")
    except FileNotFoundError:
        err("/var/ossec/etc/rules/local_rules.xml not found")
        info("Wazuh may not be installed or rules file path differs")

# ── Step 7: Print student summary ─────────────────────────
def print_summary(es_host, kb_host, password):
    hdr("Lab 8 Ready")
    print(f"""
  Kibana:         {kb_host}
  Elasticsearch:  {es_host}
  Alerts index:   lab8-alerts
  ES password:    {password[:4]}{'*' * (len(password)-4)}

  Saved searches loaded — find them in Kibana > Discover > Open
  Detection rules loaded — find them in Kibana > Stack Management > Rules

  Next steps:
    1. Open Kibana and run the saved searches (Exercise 1)
    2. Add Wazuh rules from lab guide to local_rules.xml (Exercise 2)
    3. Run lab8_inject_attacks.py to generate targeted attack events
    4. Run lab8_verify.py to check rules fired correctly
""")

# ── Main ──────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Lab 8 setup")
    parser.add_argument("--es-host",   default=ES_HOST)
    parser.add_argument("--kb-host",   default=KB_HOST)
    parser.add_argument("--wazuh-host",default=WAZUH_HOST)
    parser.add_argument("--es-user",   default=ES_USER)
    parser.add_argument("--es-pass",   default=None)
    args = parser.parse_args()

    print("\n\033[1mBSidesOK 2026 · Lab 8 Setup\033[0m")
    print("=" * 40)

    password = load_creds(args)

    check_elasticsearch(args.es_host, args.es_user, password)
    check_kibana(args.kb_host, args.es_user, password)
    check_wazuh(args.wazuh_host, args.es_user, password)
    create_alerts_index(args.es_host, args.es_user, password)
    push_saved_searches(args.kb_host, args.es_user, password)
    push_kibana_rules(args.kb_host, args.es_user, password)
    verify_wazuh_rules()
    print_summary(args.es_host, args.kb_host, password)

if __name__ == "__main__":
    main()
