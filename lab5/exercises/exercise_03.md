# Exercise 03: Observe Autonomous Planning Behavior
**~5 min**

---

## Trace the graph

Submit this prompt via OpenClaw:

```
Compute 50 plus 25, then multiply by 4
```

Watch the OpenClaw UI as each node completes. Draw the execution path:

```
START → [Planner] → [Worker] → [Reviewer] → END
```

For each node, note:
- What did it receive from state?
- What did it write back?

## Compare plans for similar prompts

Submit these and compare `session_state.json` after each:

```
Compute 100 divided by 4
```
```
What is 100 divided by 4?
```

Are the plans identical? If not, what differs and why?

## Questions

1. What triggers the error-handling plan vs. the normal plan?
2. Why does the Reviewer exist if the Worker already recorded a result?
3. In a distributed system, what could happen in the gap between when the Worker finishes and when the checkpoint is written?
