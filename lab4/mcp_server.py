#!/usr/bin/env python3
import argparse
import asyncio
import ast
import math
import operator as op
from fastmcp import FastMCP

mcp = FastMCP("Calculator MCP Server")
DEBUG_TOOLS = False

_ALLOWED_AST_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.Mod: op.mod,
    ast.USub: op.neg,
    ast.UAdd: op.pos,
}

def debug_print(msg: str) -> None:
    if DEBUG_TOOLS:
        print(msg)

def _safe_eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_AST_OPS:
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        return _ALLOWED_AST_OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_AST_OPS:
        value = _safe_eval(node.operand)
        return _ALLOWED_AST_OPS[type(node.op)](value)
    raise ValueError("Unsupported expression")

@mcp.tool()
async def add(a: float, b: float) -> float:
    """Add two numbers and return the numeric result."""
    debug_print(f"[tool] add({a}, {b})")
    return a + b

@mcp.tool()
async def subtract(a: float, b: float) -> float:
    """Subtract b from a and return the numeric result."""
    debug_print(f"[tool] subtract({a}, {b})")
    return a - b

@mcp.tool()
async def multiply(a: float, b: float) -> float:
    """Multiply two numbers and return the numeric result."""
    debug_print(f"[tool] multiply({a}, {b})")
    return a * b

@mcp.tool()
async def divide(a: float, b: float) -> float | str:
    """Divide a by b. Return an error string if b is zero."""
    debug_print(f"[tool] divide({a}, {b})")
    if b == 0:
        return "Error: Division by zero"
    return a / b

@mcp.tool()
async def power(a: float, b: float) -> float:
    """Raise a to the power of b and return the numeric result."""
    debug_print(f"[tool] power({a}, {b})")
    return a ** b

@mcp.tool()
async def sqrt(a: float) -> float | str:
    """Return the square root of a. Return an error string if a is negative."""
    debug_print(f"[tool] sqrt({a})")
    if a < 0:
        return "Error: Cannot take square root of negative number"
    return math.sqrt(a)

@mcp.tool()
async def mod(a: float, b: float) -> float | str:
    """Return a modulo b. Return an error string if b is zero."""
    debug_print(f"[tool] mod({a}, {b})")
    if b == 0:
        return "Error: Modulo by zero"
    return a % b

@mcp.tool()
async def calculate(expression: str) -> float | str:
    """Safely evaluate a numeric expression using +, -, *, /, %, **, and parentheses."""
    debug_print(f"[tool] calculate({expression})")
    try:
        tree = ast.parse(expression, mode="eval")
        return float(_safe_eval(tree.body))
    except ZeroDivisionError:
        return "Error: Division by zero"
    except Exception:
        return "Error: Unsupported expression"

async def main(debug_tools: bool) -> None:
    global DEBUG_TOOLS
    DEBUG_TOOLS = debug_tools

    if DEBUG_TOOLS:
        print("[+] Tool debug ENABLED")

    await mcp.run_async(
        transport="http",
        host="localhost",
        port=9000,
        show_banner=False,
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug-tools", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.debug_tools))
