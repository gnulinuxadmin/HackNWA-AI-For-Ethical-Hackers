# Lab 4: LangChain Agent + MCP + ReAct

## Objective
Understand how agents work using LangChain and MCP tools.

## Concepts Covered
- What is an AI agent
- Agents vs pipelines
- ReAct pattern (Reason → Act → Observe)
- LangChain components (model, tools, agent)
- Execution loops
- Failure modes

## Setup
python -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt


## Run MCP server
python mcp_server.py --debug-tools

## Run Agent
python client_langchain.py "What is 144 divided by 12?"

## Run Pipeline (comparison)
python pipeline_client.py

## ReAct Pattern
Watch the trace:
- INPUT → user request
- REASON → model decides next step
- ACT/OBSERVE → tool runs and returns
- Loop continues

## Execution Loop
1. LLM receives input
2. Decides to call tool
3. Tool executes
4. Result returned
5. Repeat until final answer

## Failure Modes
- Wrong tool selection
- Invalid arguments
- Skipping tools
- Misreading outputs

## Try
python client_langchain.py "What is 144 divided by 12 with 10 added?"

python client_langchain.py "What is (5 plus 2) raised to the power of 4?"

python client_langchain.py "What is (5 mod 2) multiplied by 4?"

## Discussion
- Why is agent more reliable than pipeline?
- When does agent still fail?
- How does tool typing improve safety?
