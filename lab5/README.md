# Lab 5: Stateful Multi-Agent Workflows with OpenClaw

## Overview

This lab moves past single-prompt LLM interactions into stateful agentic systems. You will observe how an autonomous agent decomposes goals, delegates to specialized sub-agents, persists state across steps, and how each of those properties affects system behavior.

The scenario is intentionally sandboxed — no browsers, no shell execution, no external APIs. The architecture mirrors real production agentic systems.

---

## Learning Objectives

- Explain the OpenClaw framework and its workspace skill model
- Describe how LangGraph models stateful agentic graphs
- Trace goal decomposition: user intent → plan → execution → review
- Observe multi-agent coordination and handoffs in a running system
- Explain how persistence and checkpoints support resume and recovery

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

## Lab Architecture

```
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

| Agent    | Role                                          |
|----------|-----------------------------------------------|
| Planner  | Decompose the goal into ordered steps         |
| Worker   | Execute each step, record intermediate results|
| Reviewer | Validate output, decide pass / fail / retry   |

---

## Files

```
lab5/
├── README.md
├── workflow_demo.py        ← Core stateful workflow (standalone)
├── docker-compose.yml
├── Containerfile
├── scripts/
│   ├── podman-start.sh
│   └── run_exercises.sh    ← Runs all demos in sequence
├── workspace/skills/
│   ├── planner/SKILL.md
│   ├── worker/SKILL.md
│   └── reviewer/SKILL.md
├── state/                  ← Written at runtime
│   ├── session_state.json
│   └── checkpoint.json
├── examples/               ← Sample prompts
├── exercises/              ← One file per exercise
│   ├── exercise_01.md  Launch OpenClaw with an objective
│   ├── exercise_02.md  Give the agent a multi-step mission
│   ├── exercise_03.md  Observe autonomous planning behavior
│   ├── exercise_04.md  What tools does it reach for?
│   ├── exercise_05.md  Observe agent state mid-task
│   ├── exercise_06.md  Group discussion — coordination patterns
│   └── exercise_07.md  Group discussion — real-world implications
├── config/
│   └── openclaw.sample.json
└── docs/
    └── langgraph_primer.md ← Concept reference (read before lab)
```

---


## Important Note

The OpenClaw container executes real agent workflows.

The Python demo (`workflow_demo.py`) shows a simplified, transparent version of the same architecture so you can inspect state and execution clearly.

## Setup

### Option A: Docker Compose
```bash
cp config/openclaw.sample.json config/openclaw.json
docker compose up -d
```

### Option B: Podman
```bash
cp config/openclaw.sample.json config/openclaw.json
chmod +x scripts/podman-start.sh
./scripts/podman-start.sh
```

### No container? Run standalone:
```bash
python3 workflow_demo.py "What is 144 divided by 12, plus 10, then squared?"
```

---


## Resume mid-run

You can simulate a failure and resume:

1. Start a run:
   ```bash
   python3 workflow_demo.py "What is 144 divided by 12, plus 10, then squared?"
   ```

2. Stop execution midway if you are stepping through the code.

3. Resume:
   ```bash
   python3 workflow_demo.py --resume
   ```

## Suggested Timing (45 min)

| Time     | Activity                                         |
|----------|--------------------------------------------------|
| 0–5 min  | Read `docs/langgraph_primer.md`, inspect skills  |
| 5–10 min | Exercise 1 — Launch with an objective            |
| 10–18 min| Exercises 2 & 3 — Multi-step mission, planning   |
| 18–28 min| Exercises 4 & 5 — Tools, state observation       |
| 28–45 min| Exercises 6 & 7 — Group discussion               |

---

## Sample Prompts

| Prompt | Demonstrates |
|--------|-------------|
| `What is 144 divided by 12, plus 10, then squared?` | Basic chain |
| `What is 20 minus 5, then multiplied by 3?` | Multi-step |
| `What is 144 divided by 0, then add 10?` | Error / blocked state |

---

