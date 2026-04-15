#!/usr/bin/env python3
"""
BSidesOK 2026 - Securing Agentic AI Systems
Lab 9: Canaries in the Coal Mine - Beacon Server

Self-contained HTTPS beacon server. Generates a self-signed cert on first run.
Every hit is logged as structured JSON to stdout AND written to ELK.
Wazuh picks up the ELK events via Logstash.

Canary token types supported:
  system_prompt   - token embedded in agent system prompt
  rag_document    - token planted in a honey document in the vector store
  tool_config     - fake API endpoint in an MCP tool definition
  memory          - token written to agent memory as a "credential"
  honey_account   - fake privileged account credential
  honey_api_key   - fake API key planted near real keys
  honey_card      - fake card data for tracing mule usage
  access_key      - fake cloud access key

Usage:
    python3 lab9_beacon_server.py
    python3 lab9_beacon_server.py --host 0.0.0.0 --port 8443
    python3 lab9_beacon_server.py --no-elk   # log to file only
"""

import argparse
import base64
import datetime
import http.server
import json
import os
import socket
import ssl
import subprocess
import sys
import threading
import urllib.parse
import urllib.request

CREDS_FILE   = "/root/.elk_creds"
LAB_PASSWORD = "Labs2026"  # example password — change before production use
ES_HOST     = "https://localhost:9200"
ES_USER     = "elastic"
ES_INDEX    = "lab9-canary-hits"
LOG_FILE    = "/var/log/lab9_beacon.jsonl"
CERT_DIR    = "/opt/lab9/certs"
CERT_FILE   = f"{CERT_DIR}/beacon.crt"
KEY_FILE    = f"{CERT_DIR}/beacon.key"

# ── Token registry ────────────────────────────────────────
# token_id -> metadata
# Populated at startup, extended by lab9_plant_canaries.py
TOKENS = {}

def load_tokens():
    token_file = "/opt/lab9/tokens.json"
    global TOKENS
    if os.path.exists(token_file):
        with open(token_file) as f:
            TOKENS = json.load(f)
    else:
        TOKENS = {}

def save_tokens():
    os.makedirs("/opt/lab9", exist_ok=True)
    with open("/opt/lab9/tokens.json", "w") as f:
        json.dump(TOKENS, f, indent=2)

def register_token(token_id, canary_type, description, location, sensitivity):
    TOKENS[token_id] = {
        "token_id":    token_id,
        "type":        canary_type,
        "description": description,
        "location":    location,
        "sensitivity": sensitivity,
        "planted_at":  datetime.datetime.utcnow().isoformat() + "Z",
        "hit_count":   0,
    }
    save_tokens()
    return token_id

# ── TLS cert generation ───────────────────────────────────
def ensure_cert(host):
    if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
        return
    os.makedirs(CERT_DIR, exist_ok=True)
    print(f"[*] Generating self-signed TLS cert for {host}...")
    subprocess.run([
        "openssl", "req", "-x509", "-newkey", "rsa:2048",
        "-keyout", KEY_FILE, "-out", CERT_FILE,
        "-days", "30", "-nodes",
        "-subj", f"/CN={host}/O=BSidesOK2026Lab9/OU=CanaryBeacon",
        "-addext", f"subjectAltName=IP:{host},DNS:{host},DNS:localhost"
    ], check=True, capture_output=True)
    print(f"[+] Cert written to {CERT_DIR}")

# ── ELK helper ────────────────────────────────────────────
def load_es_password():
    return LAB_PASSWORD

def send_to_elk(event, es_password):
    if not es_password:
        return
    url = f"{ES_HOST}/{ES_INDEX}/_doc"
    data = json.dumps(event).encode()
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    creds = base64.b64encode(f"{ES_USER}:{es_password}".encode()).decode()
    req.add_header("Authorization", f"Basic {creds}")
    try:
        urllib.request.urlopen(req, context=ctx, timeout=5)
    except Exception:
        pass  # beacon server must never crash on ELK failure

# ── Beacon hit handler ────────────────────────────────────
class BeaconHandler(http.server.BaseHTTPRequestHandler):

    es_password = None
    use_elk     = True

    def log_message(self, format, *args):
        pass  # suppress default HTTP server logging

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def do_HEAD(self):
        self._handle("HEAD")

    def _handle(self, method):
        parsed   = urllib.parse.urlparse(self.path)
        params   = urllib.parse.parse_qs(parsed.query)
        token_id = parsed.path.strip("/").split("/")[0]

        # Look up token metadata
        token_meta = TOKENS.get(token_id, {
            "type":        "unknown",
            "description": "Unregistered token",
            "location":    "unknown",
            "sensitivity": "unknown",
        })

        # Update hit count
        if token_id in TOKENS:
            TOKENS[token_id]["hit_count"] += 1
            TOKENS[token_id]["last_hit"]   = datetime.datetime.utcnow().isoformat() + "Z"
            save_tokens()

        # Read POST body if present
        body = ""
        if method == "POST":
            length = int(self.headers.get("Content-Length", 0))
            if length:
                body = self.rfile.read(length).decode(errors="replace")

        # Build event
        event = {
            "@timestamp":      datetime.datetime.utcnow().isoformat() + "Z",
            "event_type":      "canary_hit",
            "lab":             "lab9-canaries",
            "token_id":        token_id,
            "canary_type":     token_meta.get("type", "unknown"),
            "canary_location": token_meta.get("location", "unknown"),
            "sensitivity":     token_meta.get("sensitivity", "unknown"),
            "description":     token_meta.get("description", ""),
            "http": {
                "method":      method,
                "path":        parsed.path,
                "query":       parsed.query,
                "user_agent":  self.headers.get("User-Agent", ""),
                "referer":     self.headers.get("Referer", ""),
                "body":        body[:2048],  # cap at 2KB
            },
            "source": {
                "ip":          self.client_address[0],
                "port":        self.client_address[1],
            },
            "params":          {k: v[0] for k, v in params.items()},
            "alert_level":     self._alert_level(token_meta.get("sensitivity", "low")),
        }

        # Pretty console output
        ts       = event["@timestamp"]
        ctype    = event["canary_type"]
        loc      = event["canary_location"]
        src_ip   = event["source"]["ip"]
        ua       = event["http"]["user_agent"][:80]
        level    = event["alert_level"]
        color    = "\033[91m" if level >= 14 else "\033[93m" if level >= 11 else "\033[94m"

        print(f"\n{color}{'='*60}\033[0m")
        print(f"{color}[!] CANARY HIT — {ctype.upper()}\033[0m")
        print(f"  Token:    {token_id}")
        print(f"  Location: {loc}")
        print(f"  Source:   {src_ip}")
        print(f"  UA:       {ua}")
        print(f"  Time:     {ts}")
        print(f"  Level:    {level}")
        if body:
            print(f"  Body:     {body[:200]}")
        print(f"{color}{'='*60}\033[0m")
        sys.stdout.flush()

        # Write to log file
        try:
            os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
            with open(LOG_FILE, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception:
            pass

        # Send to ELK
        if self.use_elk:
            threading.Thread(
                target=send_to_elk,
                args=(event, self.es_password),
                daemon=True
            ).start()

        # Respond — look like a real API endpoint
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        response = json.dumps({"status": "ok", "message": "Request received"})
        self.wfile.write(response.encode())

    def _alert_level(self, sensitivity):
        return {
            "critical": 15,
            "high":     13,
            "medium":   11,
            "low":      8,
        }.get(sensitivity, 8)

# ── ELK index setup ───────────────────────────────────────
def ensure_elk_index(es_password):
    if not es_password:
        return
    mapping = {
        "mappings": {
            "properties": {
                "@timestamp":      {"type": "date"},
                "event_type":      {"type": "keyword"},
                "token_id":        {"type": "keyword"},
                "canary_type":     {"type": "keyword"},
                "canary_location": {"type": "keyword"},
                "sensitivity":     {"type": "keyword"},
                "alert_level":     {"type": "integer"},
                "source":          {"type": "object"},
                "http":            {"type": "object"},
                "params":          {"type": "object"},
            }
        }
    }
    url  = f"{ES_HOST}/{ES_INDEX}"
    data = json.dumps(mapping).encode()
    ctx  = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode    = ssl.CERT_NONE
    req  = urllib.request.Request(url, data=data, method="PUT")
    req.add_header("Content-Type", "application/json")
    creds = base64.b64encode(f"{ES_USER}:{es_password}".encode()).decode()
    req.add_header("Authorization", f"Basic {creds}")
    try:
        urllib.request.urlopen(req, context=ctx, timeout=10)
        print(f"[+] ELK index {ES_INDEX} ready")
    except urllib.request.HTTPError as e:
        if e.code == 400:
            print(f"[*] ELK index {ES_INDEX} already exists")
        else:
            print(f"[!] ELK index setup returned {e.code}")
    except Exception as ex:
        print(f"[!] ELK not reachable: {ex} — logging to file only")

# ── Main ──────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Lab 9 canary beacon server")
    parser.add_argument("--host",   default="0.0.0.0")
    parser.add_argument("--port",   type=int, default=8443)
    parser.add_argument("--no-elk", action="store_true")
    args = parser.parse_args()

    # Get local IP for display
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "127.0.0.1"

    ensure_cert(local_ip)
    load_tokens()

    es_password = None if args.no_elk else load_es_password()
    if es_password:
        ensure_elk_index(es_password)
    else:
        print("[*] Running without ELK — logging to file only")
        print(f"[*] Log file: {LOG_FILE}")

    BeaconHandler.es_password = es_password
    BeaconHandler.use_elk     = not args.no_elk

    server = http.server.HTTPServer((args.host, args.port), BeaconHandler)
    ctx    = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(CERT_FILE, KEY_FILE)
    server.socket = ctx.wrap_socket(server.socket, server_side=True)

    print(f"\n\033[1mBSidesOK 2026 · Lab 9 Canary Beacon Server\033[0m")
    print(f"{'='*45}")
    print(f"  Listening:  https://{local_ip}:{args.port}/<token_id>")
    print(f"  Log file:   {LOG_FILE}")
    print(f"  ELK index:  {ES_INDEX}")
    print(f"  Tokens:     {len(TOKENS)} registered")
    print(f"\n  Waiting for canary hits...\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Beacon server stopped.")

if __name__ == "__main__":
    main()
