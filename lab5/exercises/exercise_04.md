# Exercise 04: What Tools Does the Agent Reach For?
**~5 min**

---

Submit this prompt via OpenClaw:

```
Compute 80 divided by 4, then squared
```

Then inspect the state:

```bash
cat state/session_state.json | python3 -m json.tool
```

## Questions

1. Which node produced the `plan`?
2. Which node produced the `final_answer`?
3. What does `step_results` show about the handoffs between nodes?
4. In this lab the Worker does arithmetic. In a real deployment it might call web search, file write, email send, or a database. Which node should decide *whether* to use a tool — the Planner or the Worker?
