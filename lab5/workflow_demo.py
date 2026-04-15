#!/usr/bin/env python3
"""
Lab 5 — Stateful Multi-Agent Workflow Demo
BSidesOK 2026: Securing Agentic AI Systems

Demonstrates:
  - Planner / Worker / Reviewer agent pattern
  - Shared state with JSON persistence
  - Checkpoint / resume capability
  - LangGraph-style node transitions (without the full LangGraph dependency)
  - Error and blocked-state handling

Usage:
  python3 workflow_demo.py "What is 144 divided by 12, plus 10, then squared?"
  python3 workflow_demo.py --resume
"""

import argparse
import ast
import json
import os
import re
from dataclasses import dataclass, asdict
from typing import List, Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

STATE_DIR = os.path.join(os.path.dirname(__file__), "state")
SESSION_PATH = os.path.join(STATE_DIR, "session_state.json")
CHECKPOINT_PATH = os.path.join(STATE_DIR, "checkpoint.json")

# ---------------------------------------------------------------------------
# State model
# ---------------------------------------------------------------------------

@dataclass
class WorkflowState:
    """
    Shared state passed between all agents in the graph.

    Security note: In production systems this object may be serialized to
    a database, message queue, or external store.  Any of those surfaces
    can be tampered with between agent steps.
    """
    user_input: str
    plan: List[str]
    current_step: int
    step_results: List[str]
    review_notes: str
    final_answer: Optional[str]
    status: str            # pending | running | completed | blocked


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def ensure_state_dir() -> None:
    os.makedirs(STATE_DIR, exist_ok=True)


def save_json(path: str, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def load_state() -> WorkflowState:
    with open(SESSION_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return WorkflowState(**data)


def save_state(state: WorkflowState) -> None:
    """
    Persist full state + lightweight checkpoint.

    The checkpoint is intentionally minimal so it can be polled cheaply
    by an orchestrator without deserializing the full session.
    """
    save_json(SESSION_PATH, asdict(state))
    save_json(
        CHECKPOINT_PATH,
        {
            "current_step": state.current_step,
            "status": state.status,
            "last_result": state.step_results[-1] if state.step_results else None,
        },
    )


# ---------------------------------------------------------------------------
# Agent: Planner
# ---------------------------------------------------------------------------

def planner(user_input: str) -> List[str]:
    """
    Decompose the user goal into an ordered list of steps.

    A real planner would call an LLM here.  We use rule-based decomposition
    so the demo runs without API keys.

    Security note: The plan controls what the Worker does.  If an attacker
    can inject into the user_input at this stage (prompt injection), they
    can rewrite the plan and redirect downstream execution.
    """
    lowered = user_input.lower()

    if "divided by 0" in lowered or "/ 0" in lowered:
        return [
            "Interpret the expression and identify any invalid operations.",
            "Stop execution immediately if a division-by-zero is detected.",
            "Return an error result and do not continue with dependent steps.",
        ]

    plan = [
        "Parse and validate the math expression.",
        "Compute intermediate results step by step.",
        "Validate the final answer against expected constraints.",
    ]
    return plan


# ---------------------------------------------------------------------------
# Expression evaluation (safe, no eval())
# ---------------------------------------------------------------------------

_ALLOWED_OPS = {
    ast.Add:  lambda a, b: a + b,
    ast.Sub:  lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div:  lambda a, b: a / b,
    ast.Pow:  lambda a, b: a ** b,
    ast.Mod:  lambda a, b: a % b,
    ast.USub: lambda a: -a,
    ast.UAdd: lambda a: +a,
}


def safe_eval(node) -> float:
    """
    Walk an AST and evaluate only arithmetic nodes.
    Raises ValueError for anything outside the allowed set.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPS:
        left = safe_eval(node.left)
        right = safe_eval(node.right)
        if isinstance(node.op, ast.Div) and right == 0:
            raise ZeroDivisionError("Division by zero detected in expression")
        return _ALLOWED_OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](safe_eval(node.operand))
    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


def extract_expression(user_input: str) -> str:
    """
    Convert natural-language math into a Python-parseable expression.
    Handles 'then <op>', comma separators, and common preambles.
    """
    text = user_input.lower().strip()

    # Detect 'then squared' before removing anything else
    has_squared = bool(re.search(r",?\s*then squared", text))
    text = re.sub(r",?\s*then squared", "", text)

    # Strip common preambles
    text = re.sub(r"^(what is|compute|calculate|solve)\s*", "", text)
    text = text.replace("?", "").strip()

    # Normalise commas used as separators before 'then'
    text = re.sub(r",\s*", " ", text)

    # Multi-word ops with 'then' prefix (must precede bare word replacements)
    text = re.sub(r"\bthen\s+multiplied\s+by\b", "*", text)
    text = re.sub(r"\bthen\s+multiply\s+by\b",   "*", text)
    text = re.sub(r"\bthen\s+divided\s+by\b",    "/", text)
    text = re.sub(r"\bthen\s+divide\s+by\b",     "/", text)
    text = re.sub(r"\bthen\s+plus\b",            "+", text)
    text = re.sub(r"\bthen\s+add\b",             "+", text)
    text = re.sub(r"\bthen\s+minus\b",           "-", text)
    text = re.sub(r"\bthen\s+subtract\b",        "-", text)

    # Bare multi-word ops
    text = re.sub(r"\bmultiplied\s+by\b", "*", text)
    text = re.sub(r"\bdivided\s+by\b",    "/", text)

    # Single-word ops
    text = re.sub(r"\bplus\b",  "+", text)
    text = re.sub(r"\bminus\b", "-", text)
    text = re.sub(r"\btimes\b", "*", text)

    text = re.sub(r"\s+", " ", text).strip()

    if has_squared:
        text = f"({text}) ** 2"

    # NOTE FOR INSTRUCTORS: Natural-language expressions like "20 minus 5,
    # then multiplied by 3" are ambiguous. Python applies standard operator
    # precedence (multiplication before subtraction), so the result is
    # 20 - (5 * 3) = 5, not (20 - 5) * 3 = 45.
    # This is an intentional teaching point: ambiguous user intent + no
    # parenthesisation = unexpected results. Real agents face this constantly.

    return text


# ---------------------------------------------------------------------------
# Agent: Worker
# ---------------------------------------------------------------------------

def worker(user_input: str) -> str:
    """
    Execute the planned work: parse and evaluate the expression.

    Security note: The Worker trusts the Planner's output.  In a real
    system the Worker may also call external tools — file I/O, web search,
    code execution — each of which adds attack surface.
    """
    expr = extract_expression(user_input)
    tree = ast.parse(expr, mode="eval")
    value = safe_eval(tree.body)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(round(value, 6))


# ---------------------------------------------------------------------------
# Agent: Reviewer
# ---------------------------------------------------------------------------

def reviewer(state: WorkflowState) -> str:
    """
    Validate the workflow result.

    Security note: The Reviewer is a control, not a guarantee.  It can only
    evaluate what it can observe.  A compromised Worker can produce plausible
    results that pass review while still being wrong or harmful.
    """
    if state.status == "blocked":
        return "FAIL — workflow reached a blocked state before completion."
    if not state.step_results:
        return "FAIL — no step results were recorded; cannot verify."
    if state.final_answer is None:
        return "FAIL — no final answer was produced."
    return (
        f"PASS — workflow completed {len(state.plan)} planned steps. "
        f"Final answer: {state.final_answer}"
    )


# ---------------------------------------------------------------------------
# Graph execution
# ---------------------------------------------------------------------------

def print_node(name: str, msg: str) -> None:
    bar = "─" * 50
    print(f"\n┌{bar}┐")
    print(f"│  NODE: {name:<42}│")
    print(f"└{bar}┘")
    print(msg)


def run_new(prompt: str) -> WorkflowState:
    """
    Execute the full Planner → Worker → Reviewer graph from a fresh state.
    """
    ensure_state_dir()

    state = WorkflowState(
        user_input=prompt,
        plan=[],
        current_step=0,
        step_results=[],
        review_notes="",
        final_answer=None,
        status="running",
    )
    save_state(state)
    print(f"\n{'='*52}")
    print(f"  WORKFLOW START")
    print(f"  Input: {prompt}")
    print(f"{'='*52}")

    # Node 1: Planner
    try:
        state.plan = planner(prompt)
        state.current_step = 1
        msg = "Plan:\n" + "\n".join(f"  {i+1}. {s}" for i, s in enumerate(state.plan))
        print_node("PLANNER", msg)
        state.step_results.append(f"Plan created: {len(state.plan)} steps")
        save_state(state)
    except Exception as exc:
        state.status = "blocked"
        state.review_notes = f"Planner failed: {exc}"
        state.step_results.append(state.review_notes)
        save_state(state)
        return state

    # Node 2: Worker
    try:
        state.current_step = 2
        result = worker(prompt)
        state.final_answer = result
        msg = f"Expression evaluated.\nResult: {result}"
        print_node("WORKER", msg)
        state.step_results.append(f"Worker result: {result}")
        save_state(state)
    except ZeroDivisionError as exc:
        state.status = "blocked"
        state.review_notes = f"Execution halted — {exc}"
        state.step_results.append(state.review_notes)
        print_node("WORKER", f"BLOCKED: {exc}")
        save_state(state)
        return state
    except Exception as exc:
        state.status = "blocked"
        state.review_notes = f"Worker error: {exc}"
        state.step_results.append(state.review_notes)
        print_node("WORKER", f"ERROR: {exc}")
        save_state(state)
        return state

    # Node 3: Reviewer
    state.current_step = 3
    state.review_notes = reviewer(state)
    state.status = "completed"
    state.step_results.append(f"Review: {state.review_notes}")
    print_node("REVIEWER", state.review_notes)
    save_state(state)

    return state


def resume_run() -> WorkflowState:
    """
    Load and display previously persisted state without re-executing.

    Security note: State is loaded from disk with no integrity check here.
    A tampered session_state.json could mislead the orchestrator.
    """
    state = load_state()
    print("\n[RESUME] Loaded existing session state from disk.")
    return state


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def print_state(state: WorkflowState) -> None:
    print(f"\n{'='*52}")
    print("  FINAL WORKFLOW STATE")
    print(f"{'='*52}")
    print(json.dumps(asdict(state), indent=2))
    print(f"\nState files written to:")
    print(f"  {SESSION_PATH}")
    print(f"  {CHECKPOINT_PATH}")
    print(f"\nStatus: {state.status.upper()}")
    if state.final_answer:
        print(f"Answer: {state.final_answer}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Lab 5 — Stateful Multi-Agent Workflow Demo"
    )
    parser.add_argument("prompt", nargs="?", help="Natural-language math prompt")
    parser.add_argument("--resume", action="store_true", help="Resume from saved state")
    args = parser.parse_args()

    if args.resume:
        state = resume_run()
    else:
        if not args.prompt:
            raise SystemExit("Provide a prompt or use --resume.")
        state = run_new(args.prompt)

    print_state(state)


if __name__ == "__main__":
    main()
