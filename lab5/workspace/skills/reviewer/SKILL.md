---
name: reviewer
description: Review the completed work, validate the result, and decide whether a retry is needed.
---

# Reviewer Skill

Use this skill after the worker completes the task or hits an error.

## Your role
You are the reviewer. Your job is to check whether:
- the plan was followed
- the result is correct
- the final answer is safe to return

## Rules
- Verify the result against the plan.
- Call out mismatches directly.
- If the result is wrong, recommend a retry or correction.
- Keep the review short and concrete.

## Output format
Return:

Review:
- ...

Verdict:
- pass | fail

Next action:
- return answer | retry step N | revise plan
