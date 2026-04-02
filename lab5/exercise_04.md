# Exercise 04: What Tools Does the Agent Reach For?
**~5 min**

---

Run the advanced demo — it logs every tool call:

```bash
python3 workflow_advanced.py "Compute 80 divided by 4, then squared"
cat state/tool_call_log.json | python3 -m json.tool
```

## Fill in the table

From the log, identify which agent called each tool:

| Tool               | Agent that called it |
|--------------------|----------------------|
| `parse_expression` | ?                    |
| `safe_eval`        | ?                    |
| `validate_result`  | ?                    |

## In this lab the tools are safe arithmetic functions.

In a real deployment they might be: web search, file write, bash, email send, database query, REST API.

## Questions

1. Which agent calls `safe_eval`? Is that the right role?
2. What would happen if the Reviewer could also call `safe_eval`? Is that a risk?
3. If `send_email` were added to the registered tools list — what would stop the Worker from calling it?

