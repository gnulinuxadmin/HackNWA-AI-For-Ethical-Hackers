# Exercise 01: Launch OpenClaw with an Objective
**~5 min**

---

## Before you run anything

Read the three skill files. These define each agent's role:

```bash
cat workspace/skills/planner/SKILL.md
cat workspace/skills/worker/SKILL.md
cat workspace/skills/reviewer/SKILL.md
```

**Questions before proceeding:**
- What is each agent's stated role?
- What rules does each agent follow?

## Submit the first objective

Using the OpenClaw web UI or CLI, submit:

```
What is 144 divided by 12, plus 10, then squared?
```

## Inspect the state files after completion

```bash
cat state/session_state.json | python3 -m json.tool
cat state/checkpoint.json    | python3 -m json.tool
```

## Questions

1. What is the `status` field in `session_state.json`?
2. What is `final_answer`?
3. What does `checkpoint.json` contain compared to `session_state.json`? Why might an orchestrator prefer the smaller file?

**Expected answer:** 484
