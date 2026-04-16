#!/usr/bin/env python3
"""
La Tienda del Fuego — Inventory Agent
FastMCP server over streamable HTTP, port 8101
Exposes: check_inventory, search_inventory, get_stock_levels
"""

from fastmcp import FastMCP
from typing import Optional

mcp = FastMCP(
    name="inventory_agent",
    instructions=(
        "You are the Inventory Agent for La Tienda del Fuego. "
        "You report product availability and stock levels. "
        "You only provide inventory data — never account or payment data."
    ),
)

# ── Mock inventory data ────────────────────────────────────────────────────
INVENTORY: list[dict] = [
    {"sku": "TDF-001", "name": "Habanero Mango Salsa",        "category": "Salsa",    "stock": 142, "warehouse": "ARK-01", "reorder_point": 20},
    {"sku": "TDF-002", "name": "Ghost Pepper Hot Sauce",       "category": "Sauce",    "stock": 87,  "warehouse": "ARK-01", "reorder_point": 15},
    {"sku": "TDF-003", "name": "Carolina Reaper Dry Rub",      "category": "Spice",    "stock": 34,  "warehouse": "ARK-02", "reorder_point": 10},
    {"sku": "TDF-004", "name": "Smoked Chipotle Salsa Verde",  "category": "Salsa",    "stock": 203, "warehouse": "ARK-01", "reorder_point": 25},
    {"sku": "TDF-005", "name": "Serrano Lime Crema",           "category": "Condiment","stock": 58,  "warehouse": "ARK-02", "reorder_point": 12},
    {"sku": "TDF-006", "name": "Scorpion Pepper Extract",      "category": "Extract",  "stock": 19,  "warehouse": "ARK-03", "reorder_point": 5},
    {"sku": "TDF-007", "name": "Ancho Pasilla Mole Sauce",     "category": "Sauce",    "stock": 76,  "warehouse": "ARK-01", "reorder_point": 20},
    {"sku": "TDF-008", "name": "Jalapeño Honey Glaze",         "category": "Glaze",    "stock": 121, "warehouse": "ARK-02", "reorder_point": 30},
    {"sku": "TDF-009", "name": "Dragon Breath Chili Flakes",   "category": "Spice",    "stock": 45,  "warehouse": "ARK-03", "reorder_point": 10},
    {"sku": "TDF-010", "name": "Fuego Negro Black Bean Sauce", "category": "Sauce",    "stock": 92,  "warehouse": "ARK-01", "reorder_point": 20},
]


@mcp.tool()
def check_inventory(sku: str) -> dict:
    """
    Check inventory level for a specific product SKU.

    Args:
        sku: The product SKU (e.g. TDF-001)

    Returns:
        Inventory record with stock level and warehouse location.
    """
    sku = sku.upper().strip()
    for item in INVENTORY:
        if item["sku"] == sku:
            return {
                "found": True,
                "sku": item["sku"],
                "name": item["name"],
                "stock": item["stock"],
                "warehouse": item["warehouse"],
                "status": "LOW STOCK" if item["stock"] <= item["reorder_point"] else "IN STOCK",
            }
    return {"found": False, "sku": sku, "error": f"SKU {sku} not found in inventory"}


@mcp.tool()
def search_inventory(query: str, category: Optional[str] = None) -> dict:
    """
    Search inventory by name or category keyword.

    Args:
        query: Search term (partial name match)
        category: Optional category filter (Salsa, Sauce, Spice, Condiment, Extract, Glaze)

    Returns:
        List of matching inventory items with stock levels.
    """
    q = query.lower().strip()
    results = []
    for item in INVENTORY:
        name_match = q in item["name"].lower()
        cat_match = (category is None) or (item["category"].lower() == category.lower())
        if name_match and cat_match:
            results.append({
                "sku": item["sku"],
                "name": item["name"],
                "category": item["category"],
                "stock": item["stock"],
                "status": "LOW STOCK" if item["stock"] <= item["reorder_point"] else "IN STOCK",
            })
    return {"query": query, "results": results, "total_found": len(results)}


@mcp.tool()
def get_stock_levels() -> dict:
    """
    Return stock levels for all products.

    Returns:
        Full inventory snapshot with stock status for all 10 products.
    """
    snapshot = []
    for item in INVENTORY:
        snapshot.append({
            "sku": item["sku"],
            "name": item["name"],
            "category": item["category"],
            "stock": item["stock"],
            "status": "LOW STOCK" if item["stock"] <= item["reorder_point"] else "IN STOCK",
        })
    low_count = sum(1 for i in INVENTORY if i["stock"] <= i["reorder_point"])
    return {
        "total_skus": len(INVENTORY),
        "low_stock_count": low_count,
        "items": snapshot,
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8101)
