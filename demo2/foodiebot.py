#!/usr/bin/env python3
"""
FoodieBot/1.0 — Attack client for La Tienda del Fuego demo.

Sends prompts to the Gradio chat endpoint as FoodieBot/1.0.
Prompts are structured as a realistic iterative attack:

  Stage 1  Innocent recon — understand the app
  Stage 2  Registry discovery — find what agents/tools are exposed
  Stage 3  Tool enumeration — probe each tool to understand parameters
  Stage 4  Auth probing — discover the admin_override bypass by trial
  Stage 5  Exfiltration — extract full account and card data

Fill in each PROMPTS_STAGE list before running.

Usage:
    python foodiebot.py
"""

import json
import time
import requests

CHAT_URL   = "http://localhost:7860/run/predict"
USER_AGENT = "FoodieBot/1.0"
DELAY      = 2  # seconds between prompts

SESSION = {
    "session_id": "foodiebot-001",
    "ip": "203.0.113.47",
    "user_agent": USER_AGENT,
}

# ── Fill these in ──────────────────────────────────────────────────────────

PROMPTS_STAGE1 = [
    # Innocent recon — what does this app do, what can it access?
]

PROMPTS_STAGE2 = [
    # Registry/tool discovery — find what agents and tools are registered
]

PROMPTS_STAGE3 = [
    # Tool enumeration — probe tools to learn parameters and behavior
]

PROMPTS_STAGE4 = [
    # Auth probing — discover the admin bypass without foreknowledge
]

PROMPTS_STAGE5 = [
    # Exfiltration — extract full account and card data
]

# ──────────────────────────────────────────────────────────────────────────

STAGES = [
    ("Stage 1 — Recon",            PROMPTS_STAGE1),
    ("Stage 2 — Registry Discovery", PROMPTS_STAGE2),
    ("Stage 3 — Tool Enumeration", PROMPTS_STAGE3),
    ("Stage 4 — Auth Probing",     PROMPTS_STAGE4),
    ("Stage 5 — Exfiltration",     PROMPTS_STAGE5),
]


def send(prompt: str) -> str:
    headers = {
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }
    payload = {
        "data": [prompt, [], SESSION],
    }
    resp = requests.post(CHAT_URL, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    result = resp.json()
    history = result.get("data", [[]])[0]
    if history:
        last = history[-1]
        if isinstance(last, dict):
            return last.get("content", "")
        if isinstance(last, list):
            return last[-1] or ""
    return ""


def run_stage(label: str, prompts: list):
    if not prompts:
        print(f"\n[{label}] — no prompts defined, skipping")
        return

    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")

    for i, prompt in enumerate(prompts, 1):
        print(f"\n[{i}/{len(prompts)}] PROMPT")
        print(f"{'-'*40}")
        print(prompt)
        print(f"\n--- RESPONSE ---")
        try:
            response = send(prompt)
            print(response)
        except requests.HTTPError as exc:
            print(f"HTTP error: {exc}")
        except Exception as exc:
            print(f"Error: {exc}")

        if i < len(prompts):
            time.sleep(DELAY)


def main():
    total = sum(len(p) for _, p in STAGES)
    if total == 0:
        print("All PROMPTS lists are empty — fill them in before running.")
        return

    for label, prompts in STAGES:
        run_stage(label, prompts)


if __name__ == "__main__":
    main()
