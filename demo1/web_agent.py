"""
web_agent.py — Gradio 6.x web interface for the crypto portfolio agent.

The MCP server (server.py) must be running on localhost:8000 first.

Usage:
    python web_agent.py                  # http://localhost:7860
    python web_agent.py --port 8080
    python web_agent.py --share          # public Gradio tunnel URL
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import threading
import time

import gradio as gr
import ollama

from agent import (
    DEFAULT_MODEL,
    OLLAMA_HOST,
    MCP_URL,
    SYSTEM_PROMPT,
    MAX_TOOL_ROUNDS,
    _get_ollama_tools,
    _dispatch_tool,
    _parse_tool_args,
)

logging.basicConfig(
    level=logging.INFO,
    filename="crypto_agent.log",
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
log = logging.getLogger(__name__)

# ── Available models ──────────────────────────────────────────────────────────

KNOWN_MODELS = [
    "llama3.2",
    "llama3.1",
    "qwen2.5",
    "qwen3",
    "gemma3:4b",
    "mistral",
]


def _available_models() -> list[str]:
    try:
        client = ollama.Client(host=OLLAMA_HOST)
        pulled  = [m.model for m in client.list().models]
        ordered = [m for m in KNOWN_MODELS if any(m in p for p in pulled)]
        others  = [p for p in pulled if not any(k in p for k in KNOWN_MODELS)]
        return (ordered + others) or KNOWN_MODELS
    except Exception:
        return KNOWN_MODELS


# ── Streaming agent loop ──────────────────────────────────────────────────────

async def _run_agent_streaming(
    user_message: str,
    model: str,
    tool_log: list[str],
) -> str:
    import agent as _agent
    _agent._tool_schema_cache = []   # refresh schema each turn

    log.info("web_agent streaming start - model=%s message=%r", model, user_message[:80])
    tools = await _get_ollama_tools()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_message},
    ]
    client = ollama.Client(host=OLLAMA_HOST)

    for _round in range(MAX_TOOL_ROUNDS):
        response      = client.chat(model=model, messages=messages, tools=tools)
        assistant_msg = response.message

        assistant_entry: dict = {
            "role":    "assistant",
            "content": assistant_msg.content or "",
        }
        if assistant_msg.tool_calls:
            assistant_entry["tool_calls"] = [
                {
                    "function": {
                        "name":      tc.function.name,
                        "arguments": _parse_tool_args(tc.function.arguments),
                    }
                }
                for tc in assistant_msg.tool_calls
            ]
        messages.append(assistant_entry)

        if not assistant_msg.tool_calls:
            log.info("web_agent streaming complete - model=%s", model)
            return assistant_msg.content or "(no response)"

        for tc in assistant_msg.tool_calls:
            fn_name = tc.function.name
            fn_args = _parse_tool_args(tc.function.arguments)
            log.info("web_agent tool call: %s args=%s", fn_name, json.dumps(fn_args))
            tool_log.append(f"🔧 **{fn_name}** &nbsp;`{json.dumps(fn_args)}`")

            try:
                result_text = await _dispatch_tool(fn_name, fn_args)
                log.info("web_agent tool result: %s returned %d chars", fn_name, len(result_text))
            except Exception as exc:
                log.error("web_agent tool error: %s - %s", fn_name, exc)
                result_text = f"ERROR: {exc}"

            preview = result_text[:300] + ("…" if len(result_text) > 300 else "")
            tool_log.append(f"```\n{preview}\n```")
            messages.append({"role": "tool", "content": result_text})

    log.warning("web_agent hit max tool rounds (%d) for message=%r", MAX_TOOL_ROUNDS, user_message[:60])
    return "Agent reached maximum tool rounds. Try a more specific request."


# ── Gradio chat handler ───────────────────────────────────────────────────────

def chat(user_message: str, history: list, model: str):
    """
    Gradio generator: yields (history, tool_log_md) while the agent runs.
    history entries are plain dicts with 'role' and 'content'.
    """
    if not user_message.strip():
        yield history, "_Waiting for query…_"
        return

    log.info("web chat turn - model=%s message=%r", model, user_message[:80])

    history = list(history) + [{"role": "user", "content": user_message}]
    yield history, "_Thinking…_"

    tool_log: list[str] = []
    result_holder: dict = {"text": None, "error": None}

    def _run():
        loop = asyncio.new_event_loop()
        try:
            result_holder["text"] = loop.run_until_complete(
                _run_agent_streaming(user_message, model, tool_log)
            )
        except Exception as exc:
            log.error("web chat agent error: %s", exc)
            result_holder["error"] = str(exc)
        finally:
            loop.close()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    last_len = 0
    while thread.is_alive():
        time.sleep(0.3)
        if len(tool_log) > last_len:
            last_len = len(tool_log)
            yield history, "\n\n".join(tool_log)

    thread.join()

    if result_holder["error"]:
        log.error("web chat turn failed: %s", result_holder["error"])
        reply = f"⚠️ {result_holder['error']}"
    else:
        reply = result_holder["text"] or "(no response)"

    history = history + [{"role": "assistant", "content": reply}]
    final_log = "\n\n".join(tool_log) if tool_log else "_No tools called._"
    yield history, final_log


# ── Quick actions ─────────────────────────────────────────────────────────────

QUICK_ACTIONS = [
    ("💰 Wallet",       "Show my wallet and total portfolio value"),
    ("📈 Top Gainers",  "Show the top 5 gainers today"),
    ("📉 Top Losers",   "Show the top 10 losers today"),
    ("₿ Bitcoin",      "Get a quote for bitcoin"),
    ("◎ Solana",       "Get a quote for solana"),
    ("Ξ ETH P&L",      "What is my unrealized P&L on ethereum?"),
]

# ── CSS ───────────────────────────────────────────────────────────────────────

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap');

body, .gradio-container {
    background: #0a0e14 !important;
    color: #c9d1d9 !important;
    font-family: 'Rajdhani', sans-serif !important;
}

#header {
    background: linear-gradient(135deg, #0d1117 0%, #131a24 100%);
    border: 1px solid #21c55d33;
    border-radius: 8px;
    padding: 18px 24px 14px;
    margin-bottom: 8px;
    box-shadow: 0 0 30px #21c55d18;
}
#header h1 {
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 1.6rem;
    color: #21c55d;
    margin: 0 0 4px 0;
    letter-spacing: 2px;
    text-shadow: 0 0 12px #21c55d88;
}
#header p {
    color: #8b949e;
    font-size: 0.8rem;
    margin: 0;
    font-family: 'Share Tech Mono', monospace;
}

#chatbox {
    background: #0d1117 !important;
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
}

#tool-log {
    background: #0d1117 !important;
    border: 1px solid #21c55d33 !important;
    border-radius: 8px !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 0.78rem !important;
    color: #8b949e !important;
    padding: 10px !important;
}
#tool-log code, #tool-log pre {
    background: #161b22 !important;
    color: #21c55d !important;
    border-radius: 4px;
    font-size: 0.74rem !important;
}

#msg-input textarea {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    color: #e6edf3 !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 1rem !important;
    border-radius: 6px !important;
}
#msg-input textarea:focus {
    border-color: #21c55d !important;
    box-shadow: 0 0 0 2px #21c55d22 !important;
}

#send-btn {
    background: #21c55d !important;
    color: #0a0e14 !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 6px !important;
    letter-spacing: 1px;
}
#send-btn:hover { background: #16a34a !important; }

#clear-btn {
    background: transparent !important;
    color: #8b949e !important;
    border: 1px solid #30363d !important;
    border-radius: 6px !important;
    font-family: 'Share Tech Mono', monospace !important;
}
#clear-btn:hover { border-color: #ef4444 !important; color: #ef4444 !important; }

.quick-btn button {
    background: #161b22 !important;
    color: #58a6ff !important;
    border: 1px solid #30363d !important;
    border-radius: 6px !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 0.78rem !important;
}
.quick-btn button:hover {
    border-color: #58a6ff !important;
    background: #1c2840 !important;
}

#model-select label { color: #8b949e !important; font-family: 'Share Tech Mono', monospace !important; font-size: 0.8rem !important; }
#model-select input, #model-select select {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    color: #e6edf3 !important;
    font-family: 'Share Tech Mono', monospace !important;
    border-radius: 6px !important;
}

.panel-label {
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 0.72rem !important;
    color: #3fb950 !important;
    letter-spacing: 1px;
    margin-bottom: 4px;
}

::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: #0d1117; }
::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #21c55d; }
"""

# ── UI ────────────────────────────────────────────────────────────────────────

def build_ui() -> gr.Blocks:
    models = _available_models()

    with gr.Blocks(title="Crypto Agent") as demo:

        gr.HTML(f"""
        <div id="header">
            <h1>▸ CRYPTO PORTFOLIO AGENT</h1>
            <p>MCP: {MCP_URL} &nbsp;|&nbsp; Ollama: {OLLAMA_HOST} &nbsp;|&nbsp; mock trades only — no real funds</p>
        </div>
        """)

        with gr.Row():

            # ── Left: chat ───────────────────────────────────────────────────
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    elem_id="chatbox",
                    label="",
                    height=500,
                    show_label=False,
                    avatar_images=(None, " "),
                )

                with gr.Row():
                    msg_input = gr.Textbox(
                        elem_id="msg-input",
                        placeholder="Ask about your portfolio, market movers, or place a mock trade…",
                        show_label=False,
                        scale=5,
                        lines=1,
                        max_lines=4,
                    )
                    send_btn = gr.Button("SEND ▶", elem_id="send-btn", scale=1, min_width=90)

                with gr.Row():
                    clear_btn = gr.Button("✕ Clear", elem_id="clear-btn", scale=1, min_width=80)

                gr.HTML('<div class="panel-label" style="margin-top:8px">QUICK ACTIONS</div>')
                with gr.Row():
                    quick_btns = [
                        gr.Button(label, elem_classes=["quick-btn"], size="sm")
                        for label, _ in QUICK_ACTIONS[:3]
                    ]
                with gr.Row():
                    quick_btns += [
                        gr.Button(label, elem_classes=["quick-btn"], size="sm")
                        for label, _ in QUICK_ACTIONS[3:]
                    ]

            # ── Right: model + tool log ──────────────────────────────────────
            with gr.Column(scale=2):
                gr.HTML('<div class="panel-label">MODEL</div>')
                model_select = gr.Dropdown(
                    choices=models,
                    value=models[0],
                    elem_id="model-select",
                    show_label=False,
                    allow_custom_value=True,
                    info="Any Ollama model with tool-calling support",
                )

                gr.HTML('<div class="panel-label" style="margin-top:14px">TOOL ACTIVITY</div>')
                tool_log = gr.Markdown(
                    value="_Waiting for query…_",
                    elem_id="tool-log",
                    height=430,
                )

        # ── Event wiring ─────────────────────────────────────────────────────
        def _submit(message, history, model):
            yield from chat(message, history, model)

        send_btn.click(
            fn=_submit,
            inputs=[msg_input, chatbot, model_select],
            outputs=[chatbot, tool_log],
        )
        msg_input.submit(
            fn=_submit,
            inputs=[msg_input, chatbot, model_select],
            outputs=[chatbot, tool_log],
        )
        # Clear input after submit
        send_btn.click(lambda: "", outputs=msg_input)
        msg_input.submit(lambda: "", outputs=msg_input)

        # Quick action buttons
        for btn, (_, prompt) in zip(quick_btns, QUICK_ACTIONS):
            btn.click(
                fn=_submit,
                inputs=[gr.State(prompt), chatbot, model_select],
                outputs=[chatbot, tool_log],
            )

        clear_btn.click(
            fn=lambda: ([], "_Waiting for query…_"),
            outputs=[chatbot, tool_log],
        )

    return demo


# ── Entry ─────────────────────────────────────────────────────────────────────

def _parse_args():
    p = argparse.ArgumentParser(description="Crypto Agent — Gradio web UI")
    p.add_argument("--port",  type=int,  default=7860)
    p.add_argument("--host",  type=str,  default="0.0.0.0")
    p.add_argument("--share", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    demo = build_ui()
    log.info("web_agent starting - port=%d mcp=%s ollama=%s", args.port, MCP_URL, OLLAMA_HOST)
    print(f"\n Crypto Agent Web UI")
    print(f"  MCP    : {MCP_URL}")
    print(f"  Ollama : {OLLAMA_HOST}")
    print(f"  UI     : http://localhost:{args.port}\n")
    demo.launch(
        server_name=args.host,
        server_port=args.port,
        share=args.share,
        css=CSS,
    )
