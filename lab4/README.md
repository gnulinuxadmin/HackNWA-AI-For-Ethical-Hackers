# Lab 4: LangChain Agent with MCP Tools (Fixed v2)

## Objective
Connect a LangChain agent to an MCP calculator server and extend it with additional math tools.

This revised version includes:
- numeric tool return values instead of strings for successful math operations
- explicit tool docstrings
- a stricter system prompt for multi-step tool use
- manual trace printing instead of `verbose=True`
- a fallback `calculate()` tool for more complex expressions
- stronger routing guidance so multi-step prompts favor `calculate()`

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run MCP server

```bash
python mcp_server.py --debug-tools
```

## Run agent

```bash
python client_langchain.py "What is 144 divided by 12?"
```

## Recommended tests

These should usually use basic tools:
```bash
python client_langchain.py "What is 144 divided by 12?"
python client_langchain.py "What is 29 mod 5?"
```

These should usually route to `calculate()`:
```bash
python client_langchain.py "What is 144 divided by 12 with 10 added to the result?"
python client_langchain.py "What is (10 mod 3) raised to the power of 4?"
python client_langchain.py "Calculate ((10 % 3) ** 4) + 7"
```

This may use either `calculate()` or basic tools depending on model behavior:
```bash
python client_langchain.py "What is the square root of 144 plus 6?"
```

## Notes
- Smaller local models may still struggle with multi-step tool orchestration.
- If that happens, try a stronger local model such as a larger Qwen or Llama variant.
- The `calculate()` tool is included as a more reliable fallback for nested expressions.
- `calculate()` supports arithmetic operators and parentheses. It does not support arbitrary Python code.

## Goals
- Observe agent tool usage
- Understand multi-step tool chaining
- Analyze agent behavior and errors
- Compare many-tool orchestration versus a single composite tool
