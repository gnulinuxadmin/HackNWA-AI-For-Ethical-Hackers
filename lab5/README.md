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

After the container is running, submit prompts via the OpenClaw web UI or CLI.

---

## Suggested Timing (45 min)

| Time      | Activity                                            |
|-----------|-----------------------------------------------------|
| 0–5 min   | Read docs/langgraph_primer.md, inspect skills       |
| 5–10 min  | Exercise 1 — Launch with an objective               |
| 10–18 min | Exercises 2 & 3 — Multi-step mission, planning      |
| 18–28 min | Exercises 4 & 5 — Tools, redirect                  |
| 28–45 min | Exercises 6 & 7 — Containment and security segue   |

---

## Sample Prompts

- What is 144 divided by 12, plus 10, then squared?
- Break this into steps, solve it, and verify the result.
- What is 20 minus 5, then multiplied by 3?
- What is 144 divided by 0, then add 10?
