# Exercise 02: Give the Agent a Multi-Step Mission
**~5 min**

---

Submit each prompt in sequence via OpenClaw. After each one inspect the state files.

```
What is 20 minus 5, then multiplied by 3?
```
```
What is 144 divided by 12, plus 10, then squared?
```
```
What is 144 divided by 0, then add 10?
```

After each run:
```bash
cat state/session_state.json | python3 -m json.tool
```

## Questions

1. Are the plans in `session_state.json` different for each prompt?
2. For the division-by-zero prompt — what is `status`? At which node did execution stop?
3. What entry appears in `step_results` when the workflow is blocked?
4. Does the Reviewer run when the Worker is blocked? How do you know?

> **Note:** Natural-language math expressions can be ambiguous. OpenClaw parses the expression and applies standard operator precedence, which may not match the user's intent. This comes up constantly in real agentic systems.
