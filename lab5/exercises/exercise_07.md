# Exercise 07: Group Discussion — Real-World Implications
**~10 min**

---

Group discussion. Assign a scribe.

---

## Q1: Why is a multi-agent workflow harder to reason about than a single LLM call?

Consider: how many handoffs happen, who validates at each one, and how errors propagate from one node to the next.

---

## Q2: What new behaviors appear once state is persisted?

You saw this in Exercise 5. Generalize it: what changes about how the system behaves when workflow state lives in a file rather than in memory?

---

## Q3: What happens if the Planner produces a wrong plan but the Worker follows it faithfully?

Walk through the scenario. What does the Reviewer see? Would it catch the mistake? What would need to change for it to catch it?

---

## Q4: Map the pattern to real deployments

Fill in this table:

| Deployment | Planner analog | Worker analog | Reviewer analog |
|---|---|---|---|
| AI coding assistant | ? | ? | ? |
| AI customer service agent | ? | ? | ? |
| AI DevOps bot | ? | ? | ? |

For each: what happens if the Worker produces an incorrect result that looks plausible?

---

## Q5: Synthesis

Complete this sentence as a group:

> *"A multi-agent workflow is more capable than a single agent because ___. It is also harder to reason about because ___. Before adding [web retrieval / file write / email] to this system, you would want ___ in place."*

---

## Connection to the rest of the workshop

| Earlier lab | How Lab 5 builds on it |
|---|---|
| Lab 2: LLM architecture | Multiple agents each have their own context window and prompt |
| Lab 4: Generative AI | Agents produce generative plans and actions, not just text responses |
