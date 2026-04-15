# Exercise 04: What Tools Does the Agent Reach For?
**~5 min**

---

Run the demo and inspect what it does internally:

```bash
python3 workflow_demo.py "Compute 80 divided by 4, then squared"
cat state/session_state.json | python3 -m json.tool
```

## What the agent uses

In this lab the Worker evaluates math expressions using:
- `ast.parse()` — parses the expression into a syntax tree
- `safe_eval()` — walks the tree and computes the result without using Python's `eval()`

In a real deployment the Worker might instead call: web search, file write, bash, email send, database query, REST API.

## Questions

1. Which node produced the `plan` in `session_state.json`?
2. Which node produced the `final_answer`?
3. What does `step_results` show about the handoff between nodes?
4. If the Worker had access to a `send_email` tool — which node should decide whether to use it?
