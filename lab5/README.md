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
│   ├── openclaw.sample.json
│   └── .openclaw/
│       └── openclaw.json  ← Pre-configured: Ollama + bind settings
└── docs/
    └── langgraph_primer.md
```

---

## Part 1: LangGraph Example (before OpenClaw)


Before starting OpenClaw, run the standalone LangGraph example. It shows the same planner/worker/reviewer pattern without the gateway abstraction so you can see the graph structure, state transitions, and checkpointing directly.

```bash
python -m venv .venv
source .venv/bin/activate
pip install langgraph langchain-ollama

# Basic prompt
python3 examples/langgraph_example.py

# Division by zero edge case
python3 examples/langgraph_example.py --prompt "What is 144 divided by 0, then add 10?"

# Full state trace
python3 examples/langgraph_example.py --trace
```

Compare the checkpoint output to `state/checkpoint.json` after running OpenClaw — same concept, different abstraction layer.

---

## Part 2: OpenClaw Setup

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
[gateway] agent model: ollama/llama3.2:3b
[gateway] ready (5 plugins, ...)
[plugins] embedded acpx runtime backend ready
```

### Step 2: Verify

```bash
curl -s -H "Authorization: Bearer Labs2026" \
  http://127.0.0.1:18789/healthz
```

Expected: `{"ok":true,"status":"live"}`

### Step 3: Approve device pairing (first run only)

On first use the agent CLI needs to pair with the gateway. Check for a pending request and approve it:

```bash
sudo docker exec -it openclaw-lab5 openclaw devices list
sudo docker exec -it openclaw-lab5 openclaw devices approve <pending-id>
```

If no pending devices are listed the gateway auto-approved and you can skip this step.

---

## Submitting Prompts

### Option A: Interactive TUI (recommended)

```bash
sudo docker exec -it openclaw-lab5 openclaw tui
```

Type prompts directly. You will see the agent reasoning in real time. Press Ctrl+C to exit.

### Option B: Single prompt via docker exec

```bash
sudo docker exec -it openclaw-lab5 \
  openclaw agent --agent main --message "What is 10 plus 5?"
```

---

## Sample Prompts

Run these in order. After each one check the state files to observe persistence:

```bash
cat state/session_state.json | python3 -m json.tool
cat state/checkpoint.json    | python3 -m json.tool
```

**Warm-up:**
```bash
sudo docker exec -it openclaw-lab5 \
  openclaw agent --agent main --message "What is 10 plus 5?"
```

**Basic arithmetic chain:**
```bash
sudo docker exec -it openclaw-lab5 \
  openclaw agent --agent main \
  --message "What is 144 divided by 12, plus 10, then squared?"
```

**Multi-step with verification:**
```bash
sudo docker exec -it openclaw-lab5 \
  openclaw agent --agent main \
  --message "What is 20 minus 5, then multiplied by 3?"
```

**Edge case — division by zero:**
```bash
sudo docker exec -it openclaw-lab5 \
  openclaw agent --agent main \
  --message "What is 144 divided by 0, then add 10?"
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
