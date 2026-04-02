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
- For simple one-step math, use the matching basic tool.
- For any multi-step, chained, or nested math expression, use the calculate tool.
- Never pass an unevaluated expression string into a numeric tool argument.
- Numeric tools only accept real numbers.
- When calling a basic math tool, use exact argument names (a, b).
- If a tool returns an error string, stop and explain the error.
- Return only the final answer.

Examples:
- "What is 144 divided by 12?" -> divide(a=144, b=12)
- "What is 144 divided by 12 with 10 added?" -> calculate("144 / 12 + 10")
- "What is (10 mod 3) raised to the power of 4?" -> calculate("(10 % 3) ** 4")
"""

def _message_role(message: Any) -> str:
    return getattr(message, "type", message.__class__.__name__)

def _message_text(message: Any) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    return str(content)

async def main(prompt: str, model_name: str, server_url: str) -> None:
    model = ChatOllama(model=model_name, temperature=0, num_ctx=32000)

    client = MultiServerMCPClient({
        "math": {
            "transport": "http",
            "url": server_url,
        }
    })

    tools = await client.get_tools()

    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
    )

    result = await agent.ainvoke({
        "messages": [{"role": "user", "content": prompt}]
    })

    messages = result["messages"]

    print("\n--- Agent ReAct Trace ---\n")
    for m in messages:
        role = _message_role(m)
        content = _message_text(m)

        if role == "ai":
            print(f"[REASON] {content}")
        elif role == "tool":
            print(f"[ACT/OBSERVE] {content}")
        elif role == "human":
            print(f"[INPUT] {content}")
        else:
            print(f"[{role}] {content}")

    print("\n--- Final Response ---\n")
    print(_message_text(messages[-1]))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt")
    parser.add_argument("--model", default="llama3.2")
    parser.add_argument("--server-url", default="http://localhost:9000/mcp")
    args = parser.parse_args()

    asyncio.run(main(args.prompt, args.model, args.server_url))
