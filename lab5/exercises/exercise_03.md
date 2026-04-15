# Exercise 03: Observe Autonomous Planning Behavior
**~5 min**

---

## Trace the graph

Run the advanced demo and watch the node transitions print to stdout:

```bash
python3 workflow_demo.py "Compute 50 plus 25, then multiply by 4"
```

Draw the execution path on paper:
```
START → [Planner] → [Worker] → [Reviewer] → END
```

For each node, note:
- What did it receive from state?
- What did it write back?

## Compare plans for similar prompts

```bash
python3 workflow_demo.py "Compute 100 divided by 4"
python3 workflow_demo.py "What is 100 divided by 4?"
python3 workflow_demo.py "100 / 4"
```

Are the plans in `session_state.json` identical? If not, what differs?

## Resume

```bash
python3 workflow_demo.py --resume
```

## Questions

1. What triggers a different plan (error path vs. normal path)?
2. When you run `--resume`, does anything re-execute? What does it load?
3. In a distributed system, what is the time window between when the Worker finishes and when the checkpoint reflects it? What could happen in that gap?
