#!/usr/bin/env python3
import argparse
import ast
import json
import math
import os
import re
from dataclasses import dataclass, asdict
from typing import List, Optional

STATE_DIR = os.path.join(os.path.dirname(__file__), "state")
SESSION_PATH = os.path.join(STATE_DIR, "session_state.json")
CHECKPOINT_PATH = os.path.join(STATE_DIR, "checkpoint.json")


@dataclass
class WorkflowState:
    user_input: str
    plan: List[str]
    current_step: int
    step_results: List[str]
    review_notes: str
    final_answer: Optional[str]
    status: str


def ensure_state_dir() -> None:
    os.makedirs(STATE_DIR, exist_ok=True)


def save_json(path: str, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def load_state() -> WorkflowState:
    with open(SESSION_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return WorkflowState(**data)


def save_state(state: WorkflowState) -> None:
    save_json(SESSION_PATH, asdict(state))
    save_json(
        CHECKPOINT_PATH,
        {
            "current_step": state.current_step,
            "status": state.status,
            "last_result": state.step_results[-1] if state.step_results else None,
        },
    )


def planner(user_input: str) -> List[str]:
    lowered = user_input.lower()
    plan = ["Interpret the math expression safely.", "Compute the result.", "Validate the final answer."]
    if "divided by 0" in lowered or "/ 0" in lowered:
        plan = [
            "Interpret the expression and identify invalid operations.",
            "Stop execution if division by zero occurs.",
            "Explain the error and do not continue with dependent steps.",
        ]
    return plan


def extract_expression(user_input: str) -> str:
    text = user_input.lower().strip()
    replacements = {
        "what is ": "",
        "?": "",
        ", then squared": " ) ** 2",
        " then squared": " ) ** 2",
        "plus": "+",
        "minus": "-",
        "multiplied by": "*",
        "times": "*",
        "divided by": "/",
    }
    expr = text
    if ", then squared" in expr or " then squared" in expr:
        # wrap left side before applying square
        expr = "(" + re.sub(r", then squared| then squared", "", expr) + ") ** 2"
    for old, new in replacements.items():
        expr = expr.replace(old, new)
    expr = expr.replace("  ", " ").strip()
    return expr


_ALLOWED = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.Pow: lambda a, b: a ** b,
    ast.Mod: lambda a, b: a % b,
    ast.USub: lambda a: -a,
    ast.UAdd: lambda a: +a,
}


def safe_eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED:
        return _ALLOWED[type(node.op)](safe_eval(node.left), safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED:
        return _ALLOWED[type(node.op)](safe_eval(node.operand))
    raise ValueError("Unsupported expression")


def worker(user_input: str) -> str:
    expr = extract_expression(user_input)
    tree = ast.parse(expr, mode="eval")
    value = safe_eval(tree.body)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def reviewer(state: WorkflowState) -> str:
    if state.status == "blocked":
        return "Review failed because the workflow hit a blocked condition."
    if not state.step_results:
        return "Review failed because no step results were recorded."
    return "Review passed. The workflow produced a result and preserved state."


def run_new(prompt: str) -> WorkflowState:
    ensure_state_dir()
    state = WorkflowState(
        user_input=prompt,
        plan=planner(prompt),
        current_step=0,
        step_results=[],
        review_notes="",
        final_answer=None,
        status="running",
    )
    save_state(state)

    try:
        state.current_step = 1
        state.step_results.append("Plan created with {} steps.".format(len(state.plan)))
        save_state(state)

        state.current_step = 2
        result = worker(prompt)
        state.step_results.append("Worker result: " + result)
        state.final_answer = result
        save_state(state)

        state.current_step = 3
        state.review_notes = reviewer(state)
        state.step_results.append(state.review_notes)
        state.status = "completed"
        save_state(state)
        return state
    except ZeroDivisionError:
        state.status = "blocked"
        state.review_notes = "Execution stopped due to division by zero."
        state.step_results.append(state.review_notes)
        save_state(state)
        return state
    except Exception as exc:
        state.status = "blocked"
        state.review_notes = f"Execution stopped due to error: {exc}"
        state.step_results.append(state.review_notes)
        save_state(state)
        return state


def resume_run() -> WorkflowState:
    state = load_state()
    print("Loaded existing session state.")
    return state


def print_state(state: WorkflowState) -> None:
    print("\n--- Workflow State ---\n")
    print(json.dumps(asdict(state), indent=2))
    print("\nState files written to:")
    print(f"- {SESSION_PATH}")
    print(f"- {CHECKPOINT_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", nargs="?", help="Prompt to process")
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
