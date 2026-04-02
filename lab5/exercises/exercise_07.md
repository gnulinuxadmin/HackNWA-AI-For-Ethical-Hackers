# Exercise 07: Why Does This Matter for Security?
**~10 min**

---

Group discussion. Assign a scribe. This is the segue into the next lab.

---

## Q1: Why is a multi-agent workflow harder to reason about than a single LLM call?

Consider: how many handoffs happen, who validates at each one, and how errors compound across nodes.

---

## Q2: What new risks appear once state is persisted?

You saw in Exercise 5 that the plan lives in a file between steps. Generalize: what categories of things can go wrong when workflow state exists outside the agent process?

---

## Q3: The planner is the entry point

Everything the Worker does flows from the plan. If the plan is wrong — whether from a bad prompt, a misinterpretation, or something more deliberate — the Worker executes it faithfully and the Reviewer checks it against that same plan.

- Where is the earliest point an agent can be misdirected?
- What does that mean for how carefully we need to treat user input?

---

## Q4: Map the pattern to real deployments

Fill in this table:

| Deployment | Planner analog | Worker analog | Reviewer analog | What's the blast radius if Worker goes wrong? |
|---|---|---|---|---|
| AI coding assistant | ? | ? | ? | ? |
| AI customer service agent | ? | ? | ? | ? |
| AI security analyst (SIEM + LLM) | ? | ? | ? | ? |
| AI DevOps bot (auto-remediation) | ? | ? | ? | ? |

---

## Q5: The agentic attack surface

As agents gain capabilities, the attack surface grows with them. For each capability below, what new things become possible that weren't before?

| Capability added | What becomes possible |
|---|---|
| Persistent state | ? |
| Web retrieval | ? |
| File write access | ? |
| Autonomous retry | ? |
| Multi-agent delegation | ? |

---

## Q6: Synthesis

Complete this as a group:

> *"Autonomous agents expand the attack surface because ___. The Planner/Worker/Reviewer pattern helps because ___. But it doesn't fully solve ___. That's what we're going to dig into next."*

---

## Connection to the next lab

The questions you just discussed — misdirected plans, unchecked tool use, trusted state, blast radius — are the threat model for the next lab. Keep them in mind.
