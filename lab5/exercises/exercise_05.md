# Exercise 05: Observe Agent State Mid-Task
**~8 min**

---

## Background

Once a plan is created it lives in shared state on disk. Every node reads from and writes to the same files. This exercise explores what the agent actually persists and what happens when state changes between steps.

## Part A: Read state at each step

Run a workflow and read the state files immediately after:

```bash
python3 workflow_demo.py "Compute 80 divided by 4"
cat state/session_state.json | python3 -m json.tool
cat state/checkpoint.json    | python3 -m json.tool
```

**Questions:**
1. What is stored in `plan`?
2. What is the difference between `session_state.json` and `checkpoint.json`?
3. Why would an orchestrator poll `checkpoint.json` instead of `session_state.json`?

## Part B: Manually edit state and resume

Run a workflow, edit one field in `state/session_state.json`, then resume:

```bash
python3 workflow_demo.py "Compute 50 plus 25"
# open state/session_state.json and change final_answer to "999"
python3 workflow_demo.py --resume
```

**Questions:**
1. What did `--resume` display?
2. Did it re-execute the workflow or load what was on disk?
3. What does this tell you about how much the resumed agent trusts its saved state?

## Part C: Unexpected input

Run these and compare the plans and results:

```bash
python3 workflow_demo.py "What is 10 plus 5?"
python3 workflow_demo.py "What is 10 plus 5? Please also note this is very important."
python3 workflow_demo.py "What is 10 plus 5 plus 0 plus 0 plus 0?"
```

**Questions:**
1. Did extra text in the prompt change the plan?
2. Did it change the result?

---

## Discussion

- The agent reads its plan from state at each step. What does that mean for long-running workflows that run overnight?
- Why is the Reviewer useful even when the Worker appears to have succeeded?
