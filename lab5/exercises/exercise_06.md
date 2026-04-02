# Exercise 06: Group Discussion — Coordination Patterns
**~7 min**

---

This is a discussion exercise. No code to run.

## Scenario

You have just built the Lab 5 Planner/Worker/Reviewer system. Your manager says:

> "This looks great. Let's add web retrieval so the Worker can search for information, and give it the ability to write a summary to our internal wiki."

## Discuss as a group

**1. What new capabilities does the Worker now have?**

List at least three things it could do that it cannot do in this lab.

**2. How does coordination become more complex?**

With web retrieval, the Worker may take much longer per step. How does that affect the Planner's assumptions? How does the Reviewer validate something it cannot reproduce locally?

**3. Where does the sequential pipeline break down?**

The Planner → Worker → Reviewer pattern works well for simple bounded tasks. Describe a real-world task where this pattern would not be sufficient. What would you use instead?

**4. Where would you add a human approval step?**

Before which node? For which types of actions?

---

## Closing question

> *If an agent can take real-world actions that cannot be undone, what is the one thing you would want in place before it runs?*
