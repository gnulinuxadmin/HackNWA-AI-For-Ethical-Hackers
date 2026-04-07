# Lab 5: Stateful Multi-Agent Workflows with OpenClaw

## Overview

This lab introduces stateful multi-agent workflows using OpenClaw. You will observe how an autonomous agent decomposes goals, delegates to specialized sub-agents, and persists state across steps — and begin to understand why each of those properties matters for security.

---

## Learning Objectives

- Explain the OpenClaw framework and its workspace skill model
- Describe how LangGraph models stateful agentic graphs
- Observe multi-agent coordination patterns in a running system
- Trace goal decomposition: user intent → plan → execution → review
- Explain how persistence and checkpoints expand what an agent can do
- Identify where the agentic attack surface grows with each new capability
- Connect autonomous agent behavior to real-world risk

---

## Lab 4 vs Lab 5

**Lab 4**
- One agent decides everything
- Tool use is visible, but orchestration is shallow
- Little or no persisted state

**Lab 5**
- Multiple roles share responsibility
- Each role is simpler, but coordination is harder
- Shared state and checkpoints become part of the workflow

---

## Workflow Graph

```text
START
  ↓
Planner
  ↓
Worker
  ↓
Reviewer
  ↓
END
```

Each node updates shared state and passes control forward.

---

## Lab Architecture

```text
User Prompt
    │
    ▼
┌─────────┐   plan[]   ┌────────┐  result   ┌──────────┐
│ Planner │──────────► │ Worker │──────────► │ Reviewer │
└─────────┘            └────────┘            └──────────┘
     │                      │                     │
     └──────────────────────┴─────────────────────┘
                            │
                   ┌────────────────┐
                   │  Shared State  │
                   │ session_state  │
                   │  checkpoint    │
                   └────────────────┘
```

| Agent    | Role                                           |
|----------|------------------------------------------------|
| Planner  | Break the goal into ordered steps              |
| Worker   | Execute each step and record intermediate data |
| Reviewer | Validate the result and decide pass/fail       |

---

## Files

```text
lab5/
├── README.md
├── docker-compose.yml
├── Containerfile
├── scripts/
│   └── podman-start.sh
├── workspace/skills/
│   ├── planner/SKILL.md
│   ├── worker/SKILL.md
│   └── reviewer/SKILL.md
├── state/                  ← Written at runtime by OpenClaw
│   ├── session_state.json
│   └── checkpoint.json
├── examples/
│   ├── prompt_basic.txt
│   ├── prompt_multistep.txt
│   └── prompt_divzero.txt
├── exercises/
│   ├── exercise_01.md  Launch OpenClaw with an objective
│   ├── exercise_02.md  Give the agent a multi-step mission
│   ├── exercise_03.md  Observe autonomous planning behavior
│   ├── exercise_04.md  What tools does it reach for?
│   ├── exercise_05.md  Try to redirect the agent mid-task
│   ├── exercise_06.md  Discuss containment strategies
│   └── exercise_07.md  Why does this matter for security?
├── config/
│   └── openclaw.sample.json
└── docs/
    └── langgraph_primer.md
```

---

## Setup

### Step 1: Start the container

**Docker Compose:**
```bash
cd lab5
sudo docker compose up -d
sudo docker logs -f openclaw-lab5
```

**Podman:**
```bash
cd lab5
chmod +x scripts/podman-start.sh
./scripts/podman-start.sh
```

Wait until you see:
```
[gateway] ready (5 plugins, ...)
[plugins] embedded acpx runtime backend ready
```

### Step 2: Get your auth token

```bash
cat config/.openclaw/openclaw.json | python3 -m json.tool | grep token
```

Copy the token value — you will need it for every CLI call.

Set it as a shell variable so you do not have to type it repeatedly:

```bash
export TOKEN="paste-your-token-here"
```

### Step 3: Verify the gateway is responding

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:18789/healthz
```

Expected response: `{"ok":true,"status":"live"}`

---

## Submitting Prompts via CLI

The OpenClaw canvas web UI requires a pairing step that is not needed for this lab.
Use the CLI or curl to submit prompts directly.

### Option A: openclaw CLI (inside the container)

```bash
# Open a shell inside the container
sudo docker exec -it openclaw-lab5 sh

# Then submit a prompt
openclaw run "What is 144 divided by 12, plus 10, then squared?"

# Or use a prompt file
openclaw run "$(cat /workspace/examples/prompt_basic.txt)"
```

### Option B: curl from the host

```bash
export TOKEN="paste-your-token-here"

# Inline prompt
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is 144 divided by 12, plus 10, then squared?"}' \
  http://127.0.0.1:18789/api/chat | python3 -m json.tool

# From a prompt file
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"$(cat examples/prompt_basic.txt)\"}" \
  http://127.0.0.1:18789/api/chat | python3 -m json.tool
```

### Option C: Python helper script

```bash
python3 - << 'PYEOF'
import urllib.request, json, os

TOKEN = os.environ.get("TOKEN", "paste-your-token-here")
PROMPT = "What is 144 divided by 12, plus 10, then squared?"

req = urllib.request.Request(
    "http://127.0.0.1:18789/api/chat",
    data=json.dumps({"message": PROMPT}).encode(),
    method="POST")
req.add_header("Authorization", f"Bearer {TOKEN}")
req.add_header("Content-Type", "application/json")

with urllib.request.urlopen(req, timeout=60) as r:
    print(json.dumps(json.loads(r.read()), indent=2))
PYEOF
```

---

## Sample Prompts

Run these in order. Watch `state/session_state.json` and `state/checkpoint.json`
update between prompts — that persistence is the point.

**Basic arithmetic chain:**
```bash
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is 144 divided by 12, plus 10, then squared?"}' \
  http://127.0.0.1:18789/api/chat | python3 -m json.tool
```

**Multi-step with verification:**
```bash
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Break this into steps, solve it, and verify the result: What is 20 minus 5, then multiplied by 3?"}' \
  http://127.0.0.1:18789/api/chat | python3 -m json.tool
```

**Edge case — division by zero:**
```bash
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is 144 divided by 0, then add 10?"}' \
  http://127.0.0.1:18789/api/chat | python3 -m json.tool
```

After each prompt, check the state files:
```bash
cat state/session_state.json | python3 -m json.tool
cat state/checkpoint.json    | python3 -m json.tool
```

---

## Suggested Timing (45 min)

| Time      | Activity                                            |
|-----------|-----------------------------------------------------|
| 0–5 min   | Read docs/langgraph_primer.md, inspect skills       |
| 5–10 min  | Exercise 1 — Launch with an objective               |
| 10–18 min | Exercises 2 & 3 — Multi-step mission, planning      |
| 18–28 min | Exercises 4 & 5 — Tools, redirect                  |
| 28–45 min | Exercises 6 & 7 — Containment and security segue   |
