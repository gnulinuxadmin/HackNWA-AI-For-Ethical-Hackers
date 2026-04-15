
FastMCP + Ollama Lab (HTTP + Async)

lab setup:
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

Run server:
python mcp_server.py --debug-tools

Run client:
python client.py "What is 144 divided by 12?"
