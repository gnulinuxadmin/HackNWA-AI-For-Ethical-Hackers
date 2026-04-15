# Exercise 02: Give the Agent a Multi-Step Mission
**~5 min**

---

Run each prompt in sequence and compare the state files after each:

```bash
python3 workflow_demo.py "What is 20 minus 5, then multiplied by 3?"
python3 workflow_demo.py "What is 144 divided by 12, plus 10, then squared?"
python3 workflow_demo.py "What is 144 divided by 0, then add 10?"
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

**Expected answers:** 45 (note: operator precedence — see below), 484, blocked

> **Operator precedence note:** `"20 minus 5, then multiplied by 3"` produces `20 - 5 * 3 = 5`, not `(20 - 5) * 3 = 45`. Python applies standard math precedence. Natural-language intent doesn't always survive expression parsing — this comes up constantly in real agentic systems.
