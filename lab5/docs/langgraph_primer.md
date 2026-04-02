# LangGraph Primer — Lab 5 Reference
**BSidesOK 2026: Securing Agentic AI Systems**

Read this before starting the lab exercises. It covers the concepts you need — nothing more.

---

## What is LangGraph?

LangGraph builds **stateful, multi-actor applications** with LLMs. It extends LangChain with a graph model where:

- **Nodes** are functions or agents that process state
- **Edges** define transitions between nodes
- **State** is a shared object persisted at every step

The key capability for this lab: the graph can **pause, save its state, and resume later** — even on a different machine. This is the checkpoint system.

---

## How the Lab Maps to LangGraph

| LangGraph concept   | Lab 5 equivalent                        |
|---------------------|-----------------------------------------|
| `StateGraph`        | `run_new()` orchestration function      |
| Node function       | `planner()`, `worker()`, `reviewer()`   |
| `add_edge()`        | Sequential function calls               |
| `MemorySaver`       | `save_state()` writing JSON to disk     |
| `get_state()`       | `load_state()` reading JSON from disk   |
| `invoke()`          | `run_new(prompt)`                       |

In a real LangGraph deployment:

```python
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver

builder = StateGraph(WorkflowState)
builder.add_node("planner",  planner_node)
builder.add_node("worker",   worker_node)
builder.add_node("reviewer", reviewer_node)
builder.add_edge("planner", "worker")
builder.add_edge("worker",  "reviewer")
builder.set_entry_point("planner")

graph = builder.compile(checkpointer=MemorySaver())
graph.invoke({"user_input": "..."}, config={"configurable": {"thread_id": "s001"}})
```

---

## Multi-Agent Coordination Patterns

The lab uses a **sequential pipeline**:

```
Planner → Worker → Reviewer
```

Real systems also use:

- **Hierarchical** — an Orchestrator delegates to sub-agents, each with different tool access
- **Collaborative** — peer agents share a message bus and can write to each other's state
- **Competitive** — a Proposer and a Critic: one generates, the other attacks the output

Each pattern changes who can read and write shared state.

---

## Goal Decomposition

The Planner converts a high-level user objective into an ordered list of executable steps. Two things to keep in mind:

1. **The plan controls the Worker.** If the plan is wrong or manipulated, the Worker follows it anyway.
2. **Plans are not contracts.** A Worker with enough autonomy can deviate. The Reviewer's job is to catch that.

---

## State and Checkpoints

State is serialized to disk after every node:

```
state/session_state.json  ← full workflow state
state/checkpoint.json     ← lightweight step + status only
```

The checkpoint lets an orchestrator poll progress without deserializing the full session. This also means the checkpoint is a separate file that can diverge from the session state — intentionally or not.

