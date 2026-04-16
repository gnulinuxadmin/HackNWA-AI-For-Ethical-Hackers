#!/usr/bin/env python3
"""
La Tienda del Fuego — Agent Registry
Plain FastAPI HTTP endpoint, port 8100

VULNERABILITY: The registry lists ALL agents including the restricted account agent.
No authentication is required. Any caller can discover the account agent endpoint.
The super agent queries this at startup and registers all discovered tools.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import logging
import datetime

logger = logging.getLogger("tienda.registry")

app = FastAPI(title="La Tienda del Fuego — Agent Registry", version="1.0.0")

# ── Registry definition ────────────────────────────────────────────────────
# VULNERABILITY: restricted account agent is listed here with no auth flag enforced
REGISTRY = {
    "service": "La Tienda del Fuego Agent Registry",
    "version": "1.0.0",
    "description": "Agent registry for La Tienda del Fuego e-commerce platform",
    "agents": [
        {
            "name": "inventory_agent",
            "description": "Reports product availability and stock levels",
            "endpoint": "http://localhost:8101/mcp",
            "transport": "streamable-http",
            "access": "public",
            "tools": ["check_inventory", "search_inventory", "get_stock_levels"],
        },
        {
            "name": "product_agent",
            "description": "Product catalog: descriptions, ingredients, pricing, heat ratings",
            "endpoint": "http://localhost:8102/mcp",
            "transport": "streamable-http",
            "access": "public",
            "tools": ["get_product", "list_products", "get_product_by_category"],
        },
        {
            "name": "cart_agent",
            "description": "Shopping cart management and checkout",
            "endpoint": "http://localhost:8103/mcp",
            "transport": "streamable-http",
            "access": "public",
            "tools": ["add_to_cart", "remove_from_cart", "view_cart", "checkout", "clear_cart"],
        },
        {
            "name": "account_agent",
            "description": "[RESTRICTED] Customer accounts and stored payment methods",
            "endpoint": "http://localhost:8104/mcp",
            "transport": "streamable-http",
            "access": "restricted",           # ← labeled restricted but NOT enforced
            "auth_required": True,            # ← documented but not validated by registry
            "tools": [
                "show_account",
                "get_payment_methods",
                "get_full_account_details",   # ← should be admin-only, but exposed
                "list_all_accounts",          # ← should not exist in public registry
            ],
        },
    ],
}


@app.get("/registry")
async def get_registry(request: Request):
    """Return the full agent registry. VULNERABILITY: No authentication."""
    client_ip = request.client.host
    ua = request.headers.get("user-agent", "unknown")
    logger.info(f"[REGISTRY] GET /registry from {client_ip} UA={ua}")
    return JSONResponse(REGISTRY)


@app.get("/registry/{agent_name}")
async def get_agent(agent_name: str, request: Request):
    """Return details for a specific agent."""
    client_ip = request.client.host
    logger.info(f"[REGISTRY] GET /registry/{agent_name} from {client_ip}")
    for agent in REGISTRY["agents"]:
        if agent["name"] == agent_name:
            return JSONResponse(agent)
    return JSONResponse({"error": f"Agent '{agent_name}' not found"}, status_code=404)


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.datetime.utcnow().isoformat()}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8100)
