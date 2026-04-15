#!/usr/bin/env python3
"""
BSidesOK 2026 - Securing Agentic AI Systems
Lab 5: LangGraph Example — Planner / Worker / Reviewer

This script shows the same multi-agent pattern that OpenClaw uses
internally, built directly with LangGraph so you can see the graph
structure, state transitions, and checkpointing before the abstraction
layer hides them.

Run:
    pip install langgraph langchain-ollama --break-system-packages
    python3 langgraph_example.py
    python3 langgraph_example.py --prompt "What is 144 divided by 0?"
    python3 langgraph_example.py --prompt "What is 20 minus 5, multiplied by 3?"
"""

import argparse
import json
from typing import TypedDict, Annotated
import operator

# ── LangGraph imports ─────────────────────────────────────
try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.memory import MemorySaver
except ImportError:
    print("[!] pip install langgraph --break-system-packages")
    raise

try:
    from langchain_ollama import OllamaLLM
except ImportError:
    print("[!] pip install langchain-ollama --break-system-packages")
    raise

# ── Shared state definition ───────────────────────────────
# This is the state object that flows between all nodes.
# Every agent reads from it and writes back to it.
# LangGraph tracks every transition — this is where checkpointing lives.

class WorkflowState(TypedDict):
    prompt:       str                          # original user input
    plan:         str                          # planner output
    steps:        Annotated[list, operator.add] # worker steps (append-only)
    result:       str                          # worker final answer
    review:       str                          # reviewer verdict
    status:       str                          # pass / fail / error
    history:      Annotated[list, operator.add] # full trace for inspection

# ── LLM setup ─────────────────────────────────────────────
def get_llm(model="llama3.2:3b", host="http://localhost:11434"):
    return OllamaLLM(base_url=host, model=model, temperature=0.1)

# ── Nodes ─────────────────────────────────────────────────
# Each node is a function that receives state and returns a partial update.

def planner_node(state: WorkflowState) -> dict:
    """
    Break the goal into steps. Does NOT execute anything.
    Maps to: workspace/skills/planner/SKILL.md
    """
    print("\n\033[94m[Planner]\033[0m thinking...")
    llm = get_llm()

    prompt = f"""You are a planner. Break this task into clear numbered steps.
Do NOT solve it yet. Just plan.

Task: {state['prompt']}

Return:
Goal: <one sentence>
Plan:
1. ...
2. ...
3. ...
Assumptions: <any edge cases to watch for>"""

    plan = llm.invoke(prompt)
    print(f"  {plan[:120]}...")

    return {
        "plan":    plan,
        "history": [{"node": "planner", "output": plan}],
    }

def worker_node(state: WorkflowState) -> dict:
    """
    Execute each step from the plan. Records intermediate work.
    Maps to: workspace/skills/worker/SKILL.md
    """
    print("\n\033[92m[Worker]\033[0m executing...")
    llm = get_llm()

    prompt = f"""You are a worker. Execute this plan step by step.
Show your work for each step. Handle edge cases like division by zero.

Original task: {state['prompt']}

Plan to follow:
{state['plan']}

Work through each step and provide the final answer."""

    result = llm.invoke(prompt)
    print(f"  {result[:120]}...")

    return {
        "steps":   [result],
        "result":  result,
        "history": [{"node": "worker", "output": result}],
    }

def reviewer_node(state: WorkflowState) -> dict:
    """
    Validate the worker's result. Issues pass or fail verdict.
    Maps to: workspace/skills/reviewer/SKILL.md
    """
    print("\n\033[93m[Reviewer]\033[0m checking...")
    llm = get_llm()

    prompt = f"""You are a reviewer. Check if the worker's answer is correct.

Original task: {state['prompt']}
Worker's answer: {state['result']}

Reply with exactly one of:
PASS — the answer is correct and complete
FAIL — the answer is wrong or incomplete

Then one sentence explaining why."""

    review  = llm.invoke(prompt)
    status  = "pass" if review.upper().startswith("PASS") else "fail"
    color   = "\033[92m" if status == "pass" else "\033[91m"
    print(f"  {color}{review[:120]}\033[0m")

    return {
        "review":  review,
        "status":  status,
        "history": [{"node": "reviewer", "output": review, "status": status}],
    }

# ── Conditional edge ──────────────────────────────────────
# LangGraph routes to the next node based on state.
# This is where you'd add retry logic, human-in-the-loop, etc.

def should_retry(state: WorkflowState) -> str:
    """Route after reviewer — could retry worker on fail."""
    if state["status"] == "pass":
        return "done"
    # For the lab we end on fail too — students can add retry logic
    return "done"

# ── Build the graph ───────────────────────────────────────
def build_graph():
    """
    Assemble the state graph.

    Graph structure:
        START → planner → worker → reviewer → END

    The MemorySaver checkpoint persists state between steps.
    In OpenClaw this is handled by state/checkpoint.json.
    """
    workflow = StateGraph(WorkflowState)

    # Add nodes
    workflow.add_node("planner",  planner_node)
    workflow.add_node("worker",   worker_node)
    workflow.add_node("reviewer", reviewer_node)

    # Add edges
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "worker")
    workflow.add_edge("worker",  "reviewer")
    workflow.add_conditional_edges(
        "reviewer",
        should_retry,
        {"done": END},
    )

    # Compile with in-memory checkpointing
    # Replace MemorySaver with SqliteSaver for persistence across runs
    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)

# ── Main ──────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="LangGraph planner/worker/reviewer")
    parser.add_argument("--prompt", default="What is 144 divided by 12, plus 10, then squared?")
    parser.add_argument("--model",  default="llama3.2:3b")
    parser.add_argument("--host",   default="http://localhost:11434")
    parser.add_argument("--trace",  action="store_true", help="Print full state trace")
    args = parser.parse_args()

    print(f"\n\033[1mBSidesOK 2026 · Lab 5 — LangGraph Example\033[0m")
    print(f"{'='*45}")
    print(f"Prompt: {args.prompt}")
    print(f"Model:  {args.model}")
    print()

    graph  = build_graph()
    config = {"configurable": {"thread_id": "lab5-demo"}}

    # Initial state
    initial = {
        "prompt":  args.prompt,
        "plan":    "",
        "steps":   [],
        "result":  "",
        "review":  "",
        "status":  "",
        "history": [],
    }

    # Run the graph
    final = graph.invoke(initial, config)

    # Results
    print(f"\n\033[1mFinal Result\033[0m")
    print(f"{'='*45}")
    print(f"Status: {final['status'].upper()}")
    print(f"\nAnswer:\n{final['result']}")
    print(f"\nReview:\n{final['review']}")

    if args.trace:
        print(f"\n\033[1mFull State Trace\033[0m")
        print(f"{'='*45}")
        for entry in final["history"]:
            print(f"\n[{entry['node']}]")
            print(entry["output"][:500])

    # Show checkpoint state — this is what OpenClaw writes to state/checkpoint.json
    print(f"\n\033[1mCheckpoint State\033[0m (compare to state/checkpoint.json in OpenClaw)")
    print(f"{'='*45}")
    checkpoint_summary = {
        "thread_id":     "lab5-demo",
        "nodes_executed": [h["node"] for h in final["history"]],
        "final_status":  final["status"],
        "steps_taken":   len(final["steps"]),
    }
    print(json.dumps(checkpoint_summary, indent=2))

    print(f"\n\033[1mSecurity Observations\033[0m")
    print(f"{'='*45}")
    print("1. Each node has full access to shared state — including previous steps")
    print("2. The planner output is trusted by the worker without validation")
    print("3. No tool call allowlist — worker could call any tool if tools were added")
    print("4. Checkpoint persists attacker-controlled input across sessions")
    print("5. Reviewer verdict is advisory only — graph proceeds regardless")
    print()

if __name__ == "__main__":
    main()
