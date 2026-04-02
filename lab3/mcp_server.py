#!/usr/bin/env python3
import argparse
import asyncio
from fastmcp import FastMCP

mcp = FastMCP("Calculator MCP Server")
DEBUG_TOOLS = False

def debug_print(msg: str):
    if DEBUG_TOOLS:
        print(msg)

@mcp.tool()
async def add(a: float, b: float) -> str:
    debug_print(f"[tool] add({a}, {b})")
    return str(a + b)

@mcp.tool()
async def subtract(a: float, b: float) -> str:
    debug_print(f"[tool] subtract({a}, {b})")
    return str(a - b)

@mcp.tool()
async def multiply(a: float, b: float) -> str:
    debug_print(f"[tool] multiply({a}, {b})")
    return str(a * b)

@mcp.tool()
async def divide(a: float, b: float) -> str:
    debug_print(f"[tool] divide({a}, {b})")
    if b == 0:
        return "Error: Division by zero"
    return str(a / b)

async def main(debug_tools: bool):
    global DEBUG_TOOLS
    DEBUG_TOOLS = debug_tools

    if DEBUG_TOOLS:
        print("[+] Tool debug ENABLED")

    await mcp.run_async(transport="http", host="localhost", port=9000, show_banner=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug-tools", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.debug_tools))
