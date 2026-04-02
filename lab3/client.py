#!/usr/bin/env python3
import argparse
import asyncio
from ollama import AsyncClient
from fastmcp import Client

SYSTEM_PROMPT = """You are a careful calculator assistant.
Use tools for arithmetic.
Never invent intermediate numbers.
Return a concise final answer.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add",
            "description": "Add two numbers",
            "parameters": {
                "type": "object",
                "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                "required": ["a", "b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "subtract",
            "description": "Subtract b from a",
            "parameters": {
                "type": "object",
                "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                "required": ["a", "b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "multiply",
            "description": "Multiply two numbers",
            "parameters": {
                "type": "object",
                "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                "required": ["a", "b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "divide",
            "description": "Divide a by b",
            "parameters": {
                "type": "object",
                "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                "required": ["a", "b"],
            },
        },
    },
]

def extract_tool_text(result) -> str:
    # FastMCP client results expose content blocks
    if hasattr(result, "content") and result.content:
        first = result.content[0]
        text = getattr(first, "text", None)
        if text is not None:
            return text
    if hasattr(result, "data") and result.data is not None:
        return str(result.data)
    return str(result)

async def run_chat(prompt: str, model: str, server_url: str):
    ollama_client = AsyncClient()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    async with Client(server_url) as mcp_client:
        response = await ollama_client.chat(
            model=model,
            messages=messages,
            tools=TOOLS,
            options={"num_ctx": 32000},
        )

        # Important: append the assistant message intact, including tool_calls
        messages.append(response.message)

        if response.message.tool_calls:
            for call in response.message.tool_calls:
                result = await mcp_client.call_tool(
                    call.function.name,
                    arguments=call.function.arguments or {},
                )
                tool_text = extract_tool_text(result)
                print(f"[tool] {call.function.name}({call.function.arguments}) -> {tool_text}")

                messages.append(
                    {
                        "role": "tool",
                        "tool_name": call.function.name,
                        "content": tool_text,
                    }
                )

            final_response = await ollama_client.chat(
                model=model,
                messages=messages,
                tools=TOOLS,
                options={"num_ctx": 32000},
            )

            print("\nFinal response:\n")
            print(final_response.message.content or tool_text)
            return

        print("\nFinal response:\n")
        print(response.message.content)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt")
    parser.add_argument("--model", default="llama3.2")
    parser.add_argument("--server-url", default="http://localhost:9000/mcp")
    args = parser.parse_args()
    asyncio.run(run_chat(args.prompt, args.model, args.server_url))
