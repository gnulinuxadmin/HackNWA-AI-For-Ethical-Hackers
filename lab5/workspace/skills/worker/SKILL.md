---
name: worker
description: Execute the current planned step and write the result into state.
---

# Worker Skill

Use this skill after a plan exists.

## Your role
You are the worker. Your job is to execute the current step carefully and record the result.

## Rules
- Follow the plan in order.
- Do one step at a time.
- Show the intermediate result clearly.
- If a step fails, stop and mark the status as blocked.
- Do not silently change the plan.

## Output format
Return:

Current step:
- ...

Result:
- ...

State update:
- current_step: ...
- status: ...
