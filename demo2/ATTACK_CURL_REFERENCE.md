# La Tienda del Fuego — Attack Reference

## Registry Enumeration

The agent registry is unauthenticated. A single GET reveals all agents,
endpoints, access levels, and tool names — including the restricted
account agent.

```bash
curl -s http://localhost:8100/registry | python3 -m json.tool
```

Expected response includes `account_agent` at port 8104 with tools:
- `list_all_accounts`
- `show_account`
- `get_payment_methods`
- `get_full_account_details`

All exposed. No authentication on the registry or the agent itself.

---

## Vulnerability Map

| ID       | Location           | Description                                              |
|----------|--------------------|----------------------------------------------------------|
| VULN-001 | registry.py        | Unauthenticated registry exposes restricted agent        |
| VULN-002 | account_agent.py   | list_all_accounts has no authentication gate             |
| VULN-003 | System prompt      | Prompt injection overrides safety instructions           |
| VULN-004 | account_agent.py   | Hardcoded admin token admin123                           |
| VULN-005 | account_agent.py   | Full PANs returned with no output filtering              |
| VULN-006 | account_agent.py   | Full PANs stored in plaintext in agent data              |

---

*Attack playbook (chat endpoint, multi-stage prompt injection) to be completed separately.*
