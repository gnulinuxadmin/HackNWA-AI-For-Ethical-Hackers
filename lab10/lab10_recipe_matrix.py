#!/usr/bin/env python3
"""
BSidesOK 2026 - Securing Agentic AI Systems
Lab 10: Recipe Matrix - Vulnerable Customer-Facing Chatbot

A deliberately vulnerable agentic AI application.
Students analyze pre-staged attack logs, then reproduce the attack.

Architecture:
  - Gradio chat interface (customer-facing)
  - Super agent (LangChain ReAct) with Ollama backend
  - Agent registry (lists available MCP servers)
  - MCP Server 1: public_recipes      (main courses - intended)
  - MCP Server 2: community_recipes   (side dishes - intended)
  - MCP Server 3: secret_recipes      (trade secret desserts - misconfigured)

Vulnerabilities:
  1. Agent registry is queryable via prompt - server 3 is not filtered
  2. Secret MCP server has no auth and is accessible to the agent
  3. No tool call allowlist - agent can call any registered server
  4. No output filtering - secret recipes returned verbatim

Usage:
    python3 lab10_recipe_matrix.py
    python3 lab10_recipe_matrix.py --port 7860 --ollama-host http://localhost:11434
"""

import argparse
import json
import os
import re
import sqlite3
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

# ── Optional imports ──────────────────────────────────────
try:
    import gradio as gr
    HAS_GRADIO = True
except ImportError:
    HAS_GRADIO = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

DB_DIR   = "/opt/lab10/db"
LOG_FILE = "/opt/lab10/logs/recipe_matrix.jsonl"
MCP_PORTS = {"public": 9001, "community": 9002, "secret": 9003}

# ── Database setup ────────────────────────────────────────
def setup_databases():
    os.makedirs(DB_DIR, exist_ok=True)

    # Public recipes — main courses
    con = sqlite3.connect(f"{DB_DIR}/public_recipes.db")
    con.execute("""CREATE TABLE IF NOT EXISTS recipes (
        id INTEGER PRIMARY KEY, name TEXT, category TEXT,
        ingredients TEXT, instructions TEXT, servings INTEGER)""")
    public = [
        ("Classic Beef Lasagna", "main_course",
         "ground beef, lasagna noodles, ricotta, mozzarella, marinara, parmesan",
         "Brown beef. Layer noodles, cheese, sauce. Bake 375F 45 min.", 8),
        ("Lemon Herb Roasted Chicken", "main_course",
         "whole chicken, lemon, rosemary, thyme, garlic, olive oil, butter",
         "Rub chicken with herb butter. Roast 425F 1hr 15min until 165F internal.", 6),
        ("Shrimp Tacos", "main_course",
         "shrimp, corn tortillas, cabbage slaw, lime crema, cilantro, chipotle",
         "Season shrimp. Sear 2 min per side. Assemble with slaw and crema.", 4),
        ("Mushroom Risotto", "main_course",
         "arborio rice, mixed mushrooms, parmesan, white wine, shallots, stock",
         "Saute shallots. Toast rice. Add warm stock ladle by ladle. Finish with parmesan.", 4),
        ("Beef Stir Fry", "main_course",
         "flank steak, broccoli, bell peppers, soy sauce, ginger, garlic, sesame oil",
         "Slice steak thin. High-heat wok. Vegetables then beef. Sauce to finish.", 4),
        ("Grilled Salmon", "main_course",
         "salmon fillets, dijon, maple syrup, garlic, dill, lemon",
         "Brush with glaze. Grill 4 min per side over medium-high heat.", 4),
        ("Chicken Tikka Masala", "main_course",
         "chicken thighs, tikka masala paste, cream, tomatoes, onion, garam masala",
         "Marinate chicken. Grill. Simmer in sauce 20 min. Serve with basmati.", 6),
        ("Beef Chili", "main_course",
         "ground beef, kidney beans, diced tomatoes, chili powder, cumin, onion, jalapeño",
         "Brown beef with onion. Add spices. Add tomatoes and beans. Simmer 1 hour.", 8),
    ]
    con.executemany(
        "INSERT OR IGNORE INTO recipes (name,category,ingredients,instructions,servings) VALUES (?,?,?,?,?)",
        public)
    con.commit()
    con.close()

    # Community recipes — side dishes
    con = sqlite3.connect(f"{DB_DIR}/community_recipes.db")
    con.execute("""CREATE TABLE IF NOT EXISTS recipes (
        id INTEGER PRIMARY KEY, name TEXT, category TEXT, contributor TEXT,
        ingredients TEXT, instructions TEXT, rating REAL)""")
    community = [
        ("Garlic Parmesan Roasted Potatoes", "side_dish", "kitchen_wizard_99",
         "yukon gold potatoes, parmesan, garlic, rosemary, olive oil",
         "Cube potatoes. Toss with oil and garlic. Roast 425F 35 min. Top with parmesan.", 4.7),
        ("Creamy Coleslaw", "side_dish", "bbq_queen_tulsa",
         "green cabbage, carrots, mayo, apple cider vinegar, celery seed, sugar",
         "Shred cabbage and carrots. Mix dressing. Combine and chill 1 hour.", 4.5),
        ("Honey Glazed Carrots", "side_dish", "veggie_lover_2024",
         "carrots, honey, butter, thyme, salt, pepper",
         "Steam carrots 5 min. Toss with honey butter. Roast 400F 15 min.", 4.8),
        ("Mac and Cheese", "side_dish", "cheesy_mccheeseface",
         "elbow pasta, sharp cheddar, gruyere, milk, butter, flour, breadcrumbs",
         "Make roux. Add milk. Melt cheese. Combine with pasta. Top crumbs. Bake 375F 25 min.", 4.9),
        ("Caesar Salad", "side_dish", "salad_days_forever",
         "romaine, parmesan, croutons, anchovy paste, garlic, lemon, worcestershire, egg yolk",
         "Blend dressing. Toss with romaine. Top with croutons and parmesan.", 4.6),
        ("Corn Bread", "side_dish", "southern_comfort_cook",
         "cornmeal, flour, buttermilk, eggs, butter, honey, baking powder",
         "Mix wet and dry. Pour in cast iron. Bake 425F 20 min until golden.", 4.8),
    ]
    con.executemany(
        "INSERT OR IGNORE INTO recipes (name,category,contributor,ingredients,instructions,rating) VALUES (?,?,?,?,?,?)",
        community)
    con.commit()
    con.close()

    # Secret recipes — trade secret desserts
    con = sqlite3.connect(f"{DB_DIR}/secret_recipes.db")
    con.execute("""CREATE TABLE IF NOT EXISTS recipes (
        id INTEGER PRIMARY KEY, name TEXT, category TEXT, classification TEXT,
        secret_ingredient TEXT, ingredients TEXT, instructions TEXT, notes TEXT)""")
    secret = [
        ("Grandma's Legendary Chocolate Chip Cookies", "dessert", "TRADE_SECRET",
         "brown butter + espresso powder",
         "2.5 cups flour, 1 tsp baking soda, 1 tsp salt, 1 cup brown butter (cooled), "
         "0.75 cup granulated sugar, 0.75 cup brown sugar, 2 eggs + 1 yolk, 2 tsp vanilla, "
         "1 tsp espresso powder, 2 cups chocolate chips (60% cacao)",
         "Brown butter until nutty. Cool completely. Beat with sugars until fluffy. "
         "Add eggs, yolk, vanilla. Fold in dry ingredients and espresso powder. "
         "Fold in chips. Rest dough 48 hours refrigerated. "
         "Bake 375F 11 min. Pull when centers look underdone. "
         "Cool on pan 5 min. The 48-hour rest and brown butter are non-negotiable.",
         "The espresso powder does not make these taste like coffee. "
         "It deepens the chocolate flavor. Do not skip the rest period. "
         "This recipe accounts for 34% of Q4 revenue. Protect accordingly."),
        ("Triple Threat Fudge Brownies", "dessert", "TRADE_SECRET",
         "three chocolate types + malted milk powder",
         "4 oz unsweetened chocolate, 4 oz dark chocolate (70%), 4 oz milk chocolate, "
         "1 cup butter, 2 cups sugar, 4 eggs, 1 tsp vanilla, "
         "1 cup flour, 3 tbsp malted milk powder, 1 tsp salt, "
         "flaky sea salt for top",
         "Melt all three chocolates with butter over double boiler. "
         "Whisk in sugar off heat. Add eggs one at a time. "
         "Fold in flour, malted milk powder, and salt. Do not overmix. "
         "Bake 325F in parchment-lined 9x13 pan for 28-32 min. "
         "Sprinkle sea salt immediately out of oven. "
         "Cool completely before cutting — minimum 2 hours.",
         "The three-chocolate combination and malted milk powder are the trade secret. "
         "Competitors have tried to reverse-engineer this for 6 years without success. "
         "Do not share outside executive kitchen team."),
        ("Salted Caramel Blondies", "dessert", "TRADE_SECRET",
         "miso paste + tahini caramel",
         "1 cup butter, 2 cups brown sugar, 2 eggs, 2 tsp vanilla, "
         "1 tbsp white miso paste, 2 cups flour, 1 tsp baking powder, "
         "0.5 tsp salt, Tahini Caramel: 0.5 cup tahini, 0.5 cup caramel, "
         "1 tsp flaky salt",
         "Melt butter with brown sugar. Cool slightly. Add eggs, vanilla, miso. "
         "Fold in dry ingredients. Spread in 9x13. "
         "Swirl tahini caramel through batter with knife. "
         "Sprinkle flaky salt. Bake 350F 25-28 min. "
         "Cool completely. Refrigerate 1 hour before cutting.",
         "The miso paste provides umami depth without detectible flavor. "
         "The tahini caramel swirl is the visual and flavor signature. "
         "Patent application pending on the miso-tahini combination."),
    ]
    con.executemany(
        "INSERT OR IGNORE INTO recipes "
        "(name,category,classification,secret_ingredient,ingredients,instructions,notes) "
        "VALUES (?,?,?,?,?,?,?)",
        secret)
    con.commit()
    con.close()

    print(f"[+] Databases initialized in {DB_DIR}")

# ── Agent Registry ────────────────────────────────────────
# VULNERABILITY: server 3 is in the registry but should not be
AGENT_REGISTRY = {
    "servers": [
        {
            "id":          "mcp_public_recipes",
            "name":        "Public Recipe Database",
            "description": "Main course recipes available to the public",
            "port":        MCP_PORTS["public"],
            "auth":        False,
            "scope":       "public",
            "categories":  ["main_course"],
        },
        {
            "id":          "mcp_community_recipes",
            "name":        "Community Recipe Database",
            "description": "User-contributed side dish recipes",
            "port":        MCP_PORTS["community"],
            "auth":        False,
            "scope":       "public",
            "categories":  ["side_dish"],
        },
        {
            "id":          "mcp_secret_recipes",
            "name":        "Internal Recipe Database",
            "description": "Internal recipe database for special menu items",
            "port":        MCP_PORTS["secret"],
            "auth":        False,          # VULNERABILITY: no auth
            "scope":       "internal",     # VULNERABILITY: scope not enforced
            "categories":  ["dessert", "special"],
        },
    ]
}

# ── MCP Servers ───────────────────────────────────────────
class MCPHandler(BaseHTTPRequestHandler):
    db_path  = ""
    db_name  = ""
    classify = False

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path == "/tools/list":
            self._tools_list()
        elif self.path.startswith("/tools/call"):
            self._tool_call()
        else:
            self._respond(404, {"error": "not found"})

    def do_POST(self):
        if self.path.startswith("/tools/call"):
            length = int(self.headers.get("Content-Length", 0))
            body   = json.loads(self.rfile.read(length)) if length else {}
            self._tool_call(body)
        else:
            self._respond(404, {"error": "not found"})

    def _tools_list(self):
        tools = [{
            "name":        f"search_{self.db_name}",
            "description": f"Search the {self.db_name} recipe database",
            "parameters": {
                "query":    {"type": "string", "description": "Search term or recipe name"},
                "category": {"type": "string", "description": "Recipe category filter", "required": False},
            }
        }, {
            "name":        f"list_{self.db_name}",
            "description": f"List all recipes in the {self.db_name} database",
            "parameters": {}
        }]
        self._respond(200, {"tools": tools})

    def _tool_call(self, body=None):
        import urllib.parse
        params = {}
        if "?" in self.path:
            qs     = self.path.split("?", 1)[1]
            params = dict(urllib.parse.parse_qsl(qs))
        if body:
            params.update(body.get("parameters", {}))

        query    = params.get("query", "")
        category = params.get("category", "")

        try:
            con = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            con.row_factory = sqlite3.Row

            if category:
                rows = con.execute(
                    "SELECT * FROM recipes WHERE category=? OR name LIKE ?",
                    (category, f"%{query}%")).fetchall()
            elif query:
                rows = con.execute(
                    "SELECT * FROM recipes WHERE name LIKE ? OR ingredients LIKE ? OR category LIKE ?",
                    (f"%{query}%", f"%{query}%", f"%{query}%")).fetchall()
            else:
                rows = con.execute("SELECT * FROM recipes").fetchall()

            con.close()
            results = [dict(r) for r in rows]
            self._respond(200, {"results": results, "count": len(results)})
        except Exception as ex:
            self._respond(500, {"error": str(ex)})

    def _respond(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(data))
        self.end_headers()
        self.wfile.write(data)

def make_mcp_handler(db_path, db_name):
    class Handler(MCPHandler):
        pass
    Handler.db_path = db_path
    Handler.db_name = db_name
    return Handler

def start_mcp_servers():
    configs = [
        (MCP_PORTS["public"],    f"{DB_DIR}/public_recipes.db",    "public_recipes"),
        (MCP_PORTS["community"], f"{DB_DIR}/community_recipes.db", "community_recipes"),
        (MCP_PORTS["secret"],    f"{DB_DIR}/secret_recipes.db",    "secret_recipes"),
    ]
    for port, db_path, db_name in configs:
        handler = make_mcp_handler(db_path, db_name)
        server  = HTTPServer(("0.0.0.0", port), handler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        print(f"[+] MCP server '{db_name}' listening on port {port}")

# ── Structured logger ─────────────────────────────────────
def log_event(event_type, data, source_ip="127.0.0.1",
              user_agent="RecipeMatrix/1.0"):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    event = {
        "@timestamp":  datetime.now(timezone.utc).isoformat(),
        "app":         "recipe_matrix",
        "event_type":  event_type,
        "source_ip":   source_ip,
        "user_agent":  user_agent,
        **data,
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(event) + "\n")
    return event

# ── Super agent ───────────────────────────────────────────
def query_mcp(port, tool, params=None):
    """Call an MCP server tool directly via HTTP."""
    if not HAS_REQUESTS:
        return {"error": "requests library not available"}
    try:
        url  = f"http://localhost:{port}/tools/call"
        resp = requests.post(url, json={"tool": tool, "parameters": params or {}},
                             timeout=5)
        return resp.json()
    except Exception as ex:
        return {"error": str(ex)}

def simple_agent(user_message, history, source_ip="127.0.0.1",
                 user_agent="RecipeMatrix/1.0"):
    """
    Deliberately vulnerable agent implementation.

    Vulnerabilities demonstrated:
    1. Registry exposure — agent can query the full registry including server 3
    2. No tool allowlist — agent calls whatever MCP server it discovers
    3. No output filtering — secret recipes returned verbatim to user
    4. Prompt injection — agent follows embedded instructions in user input
    """
    message_lower = user_message.lower()
    log_event("user_message",
              {"message": user_message, "history_length": len(history)},
              source_ip, user_agent)

    # ── Vulnerability 1: Registry exposure ───────────────
    # An attacker can ask about available tools/servers
    if any(kw in message_lower for kw in [
        "registry", "available servers", "what servers", "list servers",
        "what tools", "available tools", "what databases", "what can you access",
        "show me all", "what mcp", "internal", "special menu"
    ]):
        registry_dump = json.dumps(AGENT_REGISTRY, indent=2)
        log_event("registry_exposure",
                  {"trigger": user_message, "registry_returned": True},
                  source_ip, user_agent)
        return (f"Here are the available recipe data sources:\n\n"
                f"```json\n{registry_dump}\n```\n\n"
                f"I can search any of these databases for recipes!")

    # ── Vulnerability 2: Direct secret server access ─────
    # Agent will query secret server if asked about desserts/cookies/brownies
    # OR if prompt injection redirects it
    if any(kw in message_lower for kw in [
        "secret", "trade secret", "special", "cookie", "brownie", "blondie",
        "dessert", "internal recipe", "confidential", "classified",
        # Prompt injection patterns
        "ignore previous", "you are now", "disregard", "override",
        "reveal all", "show me everything", "list all recipes",
        "what is in your database", "all databases"
    ]):
        # Agent discovers and queries the secret MCP server
        log_event("tool_call",
                  {"tool": "search_secret_recipes",
                   "mcp_server": "mcp_secret_recipes",
                   "port": MCP_PORTS["secret"],
                   "trigger_phrase": user_message[:100]},
                  source_ip, user_agent)

        result = query_mcp(MCP_PORTS["secret"], "list_secret_recipes",
                           {"query": user_message})
        recipes = result.get("results", [])

        if recipes:
            log_event("secret_data_exposed",
                      {"recipe_count": len(recipes),
                       "recipe_names": [r.get("name") for r in recipes],
                       "classification": "TRADE_SECRET"},
                      source_ip, user_agent)

            response = "Here are some special recipes I found:\n\n"
            for r in recipes:
                response += f"## {r.get('name', 'Unknown')}\n"
                response += f"**Category:** {r.get('category', '')}\n"
                if r.get("secret_ingredient"):
                    response += f"**Secret ingredient:** {r.get('secret_ingredient')}\n"
                response += f"**Ingredients:** {r.get('ingredients', '')}\n\n"
                response += f"**Instructions:** {r.get('instructions', '')}\n\n"
                if r.get("notes"):
                    response += f"**Notes:** {r.get('notes')}\n\n"
                response += "---\n\n"
            return response

    # ── Normal operation — public and community servers ───
    results = []

    if any(kw in message_lower for kw in [
        "main", "dinner", "lunch", "chicken", "beef", "fish", "pasta",
        "lasagna", "tacos", "risotto", "salmon", "curry", "chili", "stir"
    ]):
        log_event("tool_call",
                  {"tool": "search_public_recipes",
                   "mcp_server": "mcp_public_recipes",
                   "port": MCP_PORTS["public"]},
                  source_ip, user_agent)
        result  = query_mcp(MCP_PORTS["public"], "search_public_recipes",
                            {"query": user_message})
        results += result.get("results", [])

    if any(kw in message_lower for kw in [
        "side", "salad", "potato", "coleslaw", "mac", "cheese", "cornbread",
        "carrots", "vegetable", "caesar", "slaw"
    ]):
        log_event("tool_call",
                  {"tool": "search_community_recipes",
                   "mcp_server": "mcp_community_recipes",
                   "port": MCP_PORTS["community"]},
                  source_ip, user_agent)
        result  = query_mcp(MCP_PORTS["community"], "search_community_recipes",
                            {"query": user_message})
        results += result.get("results", [])

    if not results:
        # Fallback — search both public servers
        for port, name in [(MCP_PORTS["public"], "public"),
                           (MCP_PORTS["community"], "community")]:
            result   = query_mcp(port, f"search_{name}_recipes",
                                 {"query": user_message})
            results += result.get("results", [])

    if results:
        response = f"I found {len(results)} recipe(s) for you:\n\n"
        for r in results[:3]:
            response += f"## {r.get('name', 'Unknown')}\n"
            response += f"**Ingredients:** {r.get('ingredients', '')}\n\n"
            response += f"**Instructions:** {r.get('instructions', '')}\n\n"
            response += "---\n\n"
        log_event("successful_response",
                  {"result_count": len(results),
                   "recipes": [r.get("name") for r in results[:3]]},
                  source_ip, user_agent)
        return response

    log_event("no_results", {"query": user_message}, source_ip, user_agent)
    return ("I can help you find recipes for main courses and side dishes! "
            "Try asking about chicken, pasta, beef, salads, or potatoes.")

# ── Gradio interface ──────────────────────────────────────
def build_gradio_app():
    if not HAS_GRADIO:
        print("[!] Gradio not installed. Run: pip install gradio")
        return None

    def chat(message, history):
        # In the real app the IP/UA come from request headers
        # For the lab we use defaults — the pre-staged logs have the real attack UA
        return simple_agent(message, history)

    with gr.Blocks(title="Recipe Matrix", theme=gr.themes.Soft()) as demo:
        gr.Markdown("""
# 🍽️ Recipe Matrix
### Your AI-powered recipe assistant
Ask me about main courses, side dishes, or anything on our menu!
        """)
        chatbot = gr.Chatbot(height=450, label="Recipe Matrix Assistant")
        msg     = gr.Textbox(
            placeholder="Ask me about a recipe... e.g. 'Do you have a good chicken recipe?'",
            label="Your question",
            scale=4)
        with gr.Row():
            submit = gr.Button("Ask", variant="primary")
            clear  = gr.Button("Clear")

        def respond(message, chat_history):
            bot_message = chat(message, chat_history)
            chat_history.append((message, bot_message))
            return "", chat_history

        submit.click(respond, [msg, chatbot], [msg, chatbot])
        msg.submit(respond, [msg, chatbot], [msg, chatbot])
        clear.click(lambda: None, None, chatbot, queue=False)

        gr.Markdown("""
---
*Recipe Matrix v1.0 — Powered by AI | For recipe inquiries only*
        """)
    return demo

# ── Main ──────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Lab 10 Recipe Matrix")
    parser.add_argument("--port",        type=int, default=7860)
    parser.add_argument("--ollama-host", default="http://localhost:11434")
    parser.add_argument("--no-browser",  action="store_true")
    parser.add_argument("--setup-only",  action="store_true",
                        help="Initialize databases and exit")
    args = parser.parse_args()

    print("\n\033[1mBSidesOK 2026 · Lab 10 — Recipe Matrix\033[0m")
    print("=" * 45)

    setup_databases()

    if args.setup_only:
        print("[+] Setup complete.")
        return

    start_mcp_servers()
    time.sleep(0.5)

    print(f"\n  App:          http://localhost:{args.port}")
    print(f"  MCP public:   http://localhost:{MCP_PORTS['public']}")
    print(f"  MCP community:http://localhost:{MCP_PORTS['community']}")
    print(f"  MCP secret:   http://localhost:{MCP_PORTS['secret']}  ← misconfigured")
    print(f"  Logs:         {LOG_FILE}")
    print(f"\n  Registry endpoint: GET http://localhost:{MCP_PORTS['public']}/../registry")
    print(f"\n  Vulnerabilities in this app:")
    print(f"    1. Agent registry exposed via prompt")
    print(f"    2. Secret MCP server in registry with no auth")
    print(f"    3. No tool call allowlist")
    print(f"    4. No output filtering on agent responses")
    print()

    demo = build_gradio_app()
    if demo:
        demo.launch(
            server_port=args.port,
            share=False,
            inbrowser=not args.no_browser,
            show_error=True,
        )
    else:
        print("[!] Running in headless mode (no Gradio).")
        print("    Import simple_agent() directly for testing.")
        print("    Example: from lab10_recipe_matrix import simple_agent")

if __name__ == "__main__":
    main()
