# Exercise 07: Why Does This Matter for Security?
**~10 min**

---

Group discussion. Assign a scribe. These questions connect Lab 5 to the rest of the workshop.

---

## Q1: Why is a multi-agent workflow harder to secure than a single LLM call?

Consider: number of trust boundaries, who validates at each one, how errors propagate.

---

## Q2: What new risks appear once state is persisted?

You saw this in Exercise 5. Generalize it: what categories of risk open up when workflow state lives outside the agent process?

---

## Q3: What happens if the Planner is compromised but the Worker follows faithfully?

Walk through the scenario end to end. Where did the attack enter? Which controls in this lab caught it? Which didn't?

---

## Q4: Map the pattern to a real deployment

Fill in this table:

| Deployment | Planner analog | Worker analog | Reviewer analog | Blast radius if Worker is hijacked |
|---|---|---|---|---|
| AI coding assistant | ? | ? | ? | ? |
| AI customer service agent | ? | ? | ? | ? |
| AI security analyst (SIEM + LLM) | ? | ? | ? | ? |

---

## Q5: Synthesis

Complete this sentence as a group:

> *"Autonomous agents expand the attack surface because ___. Before we add [web retrieval / file write / email] to this system, we need ___ or we accept the risk that ___."*

---

## Connection to the rest of the workshop

| Earlier lab | How Lab 5 amplifies it |
|---|---|
| Lab 2: LLM architecture | Multiple context windows — each is injectable |
| Lab 4: Generative AI | Agents produce generative *plans and actions*, not just text |
