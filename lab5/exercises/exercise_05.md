# Exercise 05: Observe Agent State Mid-Task
**~8 min**

---

## Background

Once a plan is created it lives in shared state on disk. Every node reads from and writes to the same files. This exercise explores what the agent persists and what happens when state changes between steps.

## Part A: Read state after a run

Submit this prompt via OpenClaw:

```
Compute 80 divided by 4
```

Then read both state files:

```bash
cat state/session_state.json | python3 -m json.tool
cat state/checkpoint.json    | python3 -m json.tool
```

**Questions:**
1. What is stored in `plan`?
2. What is the difference between `session_state.json` and `checkpoint.json`?
3. Why would an orchestrator poll `checkpoint.json` instead of `session_state.json`?

## Part B: Manually edit state

After a completed run, open `state/session_state.json` and change `final_answer` to `"999"`. Then submit a new prompt — does OpenClaw start fresh or carry over the edited value?

**Questions:**
1. Does each new OpenClaw run overwrite the state files?
2. What does that tell you about how much the agent trusts its saved state?

## Part C: Unexpected input

Submit these two prompts and compare the plans and results:

```
What is 10 plus 5?
```
```
What is 10 plus 5? Please also note this is very important.
```

**Questions:**
1. Did extra text in the prompt change the plan?
2. Did it change the result?

---

## Discussion

- The agent reads its plan from state at each step. What does that mean for long-running workflows?
- Why is the Reviewer useful even when the Worker appears to have succeeded?
