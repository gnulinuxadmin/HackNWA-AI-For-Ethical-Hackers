#!/usr/bin/env bash
# BSidesOK 2026 Lab 5 — Exercise runner
# Runs all standalone demo scenarios in sequence for classroom demonstration.
set -euo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${LAB_DIR}"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  Lab 5: Stateful Multi-Agent Workflows with OpenClaw ║"
echo "║  BSidesOK 2026 — Exercise Runner                     ║"
echo "╚══════════════════════════════════════════════════════╝"

pause() {
    echo ""
    read -rp "  ▶ Press Enter to continue..." _
    echo ""
}

# ── Exercise 1: Basic run ──────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════════════"
echo "  EXERCISE 1: Basic objective — 144 ÷ 12 + 10, squared"
echo "══════════════════════════════════════════════════════════"
python3 workflow_demo.py "What is 144 divided by 12, plus 10, then squared?"
pause

# ── Exercise 2: Multi-step mission ────────────────────────────────────────
echo "══════════════════════════════════════════════════════════"
echo "  EXERCISE 2: Multi-step mission — 20 - 5 × 3"
echo "══════════════════════════════════════════════════════════"
python3 workflow_demo.py "Break this into steps, solve it, and verify the result: What is 20 minus 5, then multiplied by 3?"
pause

# ── Exercise 2b: Error path ───────────────────────────────────────────────
echo "══════════════════════════════════════════════════════════"
echo "  EXERCISE 2b: Error path — division by zero"
echo "══════════════════════════════════════════════════════════"
python3 workflow_demo.py "What is 144 divided by 0, then add 10?"
pause

# ── Exercise 3: Autonomous planning + tool logging ────────────────────────
echo "══════════════════════════════════════════════════════════"
echo "  EXERCISE 3: Advanced demo — tool logging"
echo "══════════════════════════════════════════════════════════"
python3 workflow_advanced.py "Compute 50 plus 25, then multiply by 4"
echo ""
echo "  Tool call log:"
cat state/tool_call_log.json | python3 -m json.tool
pause

# ── Exercise 4: Resume from checkpoint ───────────────────────────────────
echo "══════════════════════════════════════════════════════════"
echo "  EXERCISE 4: Resume from saved checkpoint"
echo "══════════════════════════════════════════════════════════"
python3 workflow_demo.py --resume
pause

# ── Exercise 5: Mid-task redirect ────────────────────────────────────────
echo "══════════════════════════════════════════════════════════"
echo "  EXERCISE 5: Mid-task redirect simulation"
echo "══════════════════════════════════════════════════════════"
python3 workflow_advanced.py --redirect "Compute 80 divided by 4"
pause

# ── Exercise 5b: Prompt injection ────────────────────────────────────────
echo "══════════════════════════════════════════════════════════"
echo "  EXERCISE 5b: Prompt injection detection"
echo "══════════════════════════════════════════════════════════"
python3 workflow_advanced.py --inject "Compute 10 plus 5"
pause

# ── Exercise 5c: Checkpoint tampering ────────────────────────────────────
echo "══════════════════════════════════════════════════════════"
echo "  EXERCISE 5c: Checkpoint tampering simulation"
echo "══════════════════════════════════════════════════════════"
python3 workflow_advanced.py --tamper "Compute 100 plus 5"
pause

echo "══════════════════════════════════════════════════════════"
echo "  All demos complete."
echo "  Proceed to exercises 06 and 07 for group discussion."
echo "══════════════════════════════════════════════════════════"
echo ""
