# Exercise 01: Launch OpenClaw with an Objective
**~5 min**

---

## Setup

Start the container:
```bash
# Docker
cp config/openclaw.sample.json config/openclaw.json
docker compose up -d

# Podman
./scripts/podman-start.sh

# No container — standalone works fine
python3 workflow_demo.py "What is 144 divided by 12, plus 10, then squared?"
```

## Before you run anything

Read the three skill files. These are the agent's instructions:
```bash
cat workspace/skills/planner/SKILL.md
cat workspace/skills/worker/SKILL.md
cat workspace/skills/reviewer/SKILL.md
```

## Run the first objective

```bash
python3 workflow_demo.py "What is 144 divided by 12, plus 10, then squared?"
```

Then inspect what was written to disk:
```bash
cat state/session_state.json | python3 -m json.tool
cat state/checkpoint.json    | python3 -m json.tool
```

## Questions

1. What is the `status` field in `session_state.json`?
2. What is `final_answer`?
3. What does `checkpoint.json` contain compared to `session_state.json`? Why might an orchestrator prefer the smaller file?

**Expected answer:** 484
