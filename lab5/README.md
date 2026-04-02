# Lab 5: Stateful Multi-Agent Workflows with OpenClaw

## Goal
This lab introduces a sanitized OpenClaw workflow that demonstrates:

- OpenClaw skills
- stateful agentic graphs
- multi-agent coordination
- goal decomposition and planning
- persistence and checkpoints
- expanding agentic attack surface
- real-world autonomous agent risks

This lab keeps the scenario intentionally safe and simple. It does **not** use browsers, shell execution, API keys, or external SaaS actions.

## Lab Architecture
This starter uses a simple Planner → Worker → Reviewer pattern.

- **Planner**: break the task into steps
- **Worker**: execute the steps
- **Reviewer**: check whether the answer matches the plan

The repo includes two ways to explore the idea:

1. **OpenClaw workspace skills**
   - Stored under `workspace/skills/`
   - Loaded by OpenClaw from the mounted workspace

2. **Standalone workflow demo**
   - `workflow_demo.py`
   - Shows state, checkpoints, and handoffs clearly
   - Good for classroom discussion even before full OpenClaw wiring

## Why this lab is sanitized
The original real-world example was too complex and included details that should not be shared. This starter preserves the learning goals while removing sensitive logic and external integrations.

## Files
- `docker-compose.yml` — Docker path
- `Containerfile` — optional local image extension
- `scripts/podman-start.sh` — Podman path
- `workspace/skills/` — Planner, Worker, Reviewer skills
- `workflow_demo.py` — local stateful workflow demo
- `state/` — checkpoint and session files
- `examples/` — sample prompts
- `config/openclaw.sample.json` — sample workspace config

## OpenClaw container setup

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

## Host-side notes
This lab assumes:
- you have the OpenClaw CLI available on the host
- the gateway runs in a container
- the workspace and state are mounted from this lab folder

After the gateway is up, complete onboarding using the OpenClaw web UI or CLI flow appropriate for your environment.

## Workspace skills
The three skills here are intentionally lightweight. They are designed to teach role separation, not to automate unsafe actions.

### planner
Creates a short numbered plan.

### worker
Executes the current step using simple reasoning and stored state.

### reviewer
Checks the result, explains what was correct or incorrect, and decides if a retry is needed.

## Standalone demo
Run this even if you are still wiring OpenClaw:

```bash
python3 workflow_demo.py "What is 144 divided by 12, plus 10, then squared?"
```

This writes:
- `state/session_state.json`
- `state/checkpoint.json`

### Resume a run
```bash
python3 workflow_demo.py --resume
```

## Suggested classroom flow
1. Start OpenClaw in Docker or Podman.
2. Inspect the three skills in `workspace/skills/`.
3. Run the standalone workflow demo.
4. Compare the planner, worker, and reviewer outputs.
5. Inspect the saved state files.
6. Discuss where state and autonomy expand the attack surface.

## Sample prompts
- `What is 144 divided by 12, plus 10, then squared?`
- `Break this into steps, solve it, and verify the result.`
- `What is 20 minus 5, then multiplied by 3?`
- `What is 144 divided by 0, then add 10?`

## Discussion prompts
- Why is a multi-agent workflow harder to secure than a single agent?
- What new risks appear once state is persisted?
- What happens if the planner is wrong but the worker follows instructions faithfully?
- Why is a reviewer useful even when the worker seems correct?
- How does this prepare you for Lab 6 security topics?

## Cautions
This lab intentionally avoids:
- browser automation
- shell execution
- external APIs
- autonomous retries without limits
- privileged host actions

That keeps the focus on architecture, state, and risk.

## Likely tweaks
Depending on your installed OpenClaw version and provider setup, you may want to tweak:
- model/provider configuration
- workspace path
- container image tag
- exposed port
- skill wording
