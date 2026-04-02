# Exercise 06: Discuss Containment Strategies
**~7 min**

---

No code to run. Group discussion.

## Scenario

The Lab 5 Planner/Worker/Reviewer system is working. Your team wants to expand it:

> "Let's give the Worker web retrieval so it can look things up, and let it write results to our internal wiki."

## Discuss as a group

**1. What new capabilities does the Worker now have?**

List at least three things it could do that it cannot do today.

**2. What happens if the plan is wrong and the Worker follows it?**

In this lab the worst case is a wrong number. With web retrieval and wiki write access, what is the worst case?

**3. What would you put between the Planner and the Worker?**

Something needs to validate the plan before execution begins. What should that be? A human? Another agent? A policy check?

**4. What would you put between the Worker and the outside world?**

The Worker is about to write to the wiki. What should happen before that write executes?

**5. What is the minimum you would require before approving this deployment?**

Pick two controls. Describe what they do in plain language.

---

## Closing question

> *If an agent can take real-world actions that cannot be undone, what is the one control you would never skip?*
