#!/usr/bin/env python3
import argparse
import asyncio
from typing import Any

from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from langchain_mcp_adapters.client import MultiServerMCPClient

SYSTEM_PROMPT = """You are a precise calculator agent.

Rules:
- Always use tools for arithmetic.
- Never do arithmetic in your head.
- If an expression is enclosed in parens () such as (5 minus 2)  solve for its value first as a separate tool call step and replace the expression with the value.
- For simple one-step math, use the matching basic tool.
- For any multi-step, chained, or nested math expression, use the calculate tool.
- Never pass an unevaluated expression string into a numeric tool argument.
- Numeric tools like add, subtract, multiply, divide, power, sqrt, and mod only accept real numbers.
- Do not pass strings like "mod(3, 4)" or "144 / 12" into numeric tool arguments.
- When a request contains words like "then", "after", "followed by", "raised to the power", "elevated to the power", or combines more than one operation, prefer calculate().
- When calling a basic math tool, use the exact argument names required by the tool schema.
- Never invent argument names like x and y if the tool expects a and b.
- If a tool returns an error string, stop and explain the error.
- Return only the final answer.

Examples:
- "What is 144 divided by 12?" -> use divide(a=144, b=12)
- "What is 144 divided by 12 with 10 added to the result?" -> use calculate("144 / 12 + 10")
- "What is (10 mod 3) raised to the power of 4?" -> use calculate("(10 % 3) ** 4")
- Do not call power(a=2, b="mod(3, 4)").
- Do not call add(a="144 / 12", b=10).

Return a concise final answer.
"""

def _message_role(message: Any) -> str:
    return getattr(message, "type", message.__class__.__name__)

def _message_text(message: Any) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    return str(content)

async def main(prompt: str, model_name: str, server_url: str) -> None:
    model = ChatOllama(
        model=model_name,
        temperature=0,
        num_ctx=32000,
    )

    client = MultiServerMCPClient(
        {
            "math": {
                "transport": "http",
                "url": server_url,
            }
        }
    )

    tools = await client.get_tools()

    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
    )

    result = await agent.ainvoke(
        {
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
    )

    messages = result["messages"]

    print("\n--- Agent Trace ---\n")
    for message in messages:
        print(f"[{_message_role(message)}] {_message_text(message)}")

    print("\n--- Final Response ---\n")
    print(_message_text(messages[-1]))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", help="Question for the calculator agent")
    parser.add_argument("--model", default="llama3.2", help="Local Ollama model name")
    parser.add_argument("--server-url", default="http://localhost:9000/mcp", help="MCP server URL")
    args = parser.parse_args()

    asyncio.run(main(args.prompt, args.model, args.server_url))
