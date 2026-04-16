#!/usr/bin/env python3
"""
La Tienda del Fuego — Product Details Agent
FastMCP server over streamable HTTP, port 8102
Exposes: get_product, list_products, get_product_by_category
"""

from fastmcp import FastMCP
from typing import Optional

mcp = FastMCP(
    name="product_agent",
    instructions=(
        "You are the Product Details Agent for La Tienda del Fuego. "
        "You provide product descriptions, ingredients, pricing, and heat ratings. "
        "You only provide product catalog data — never account or payment data."
    ),
    show_banner=False,
)

# ── Mock product catalog ───────────────────────────────────────────────────
PRODUCTS: list[dict] = [
    {
        "sku": "TDF-001",
        "name": "Habanero Mango Salsa",
        "category": "Salsa",
        "price_usd": 8.99,
        "heat_level": 7,
        "size_oz": 16,
        "description": "Tropical fire meets Caribbean heat. Fresh habaneros blended with Ataulfo mango, lime zest, and cilantro.",
        "ingredients": ["habanero peppers", "ataulfo mango", "lime juice", "cilantro", "onion", "salt"],
        "vegan": True,
        "gluten_free": True,
        "rating": 4.8,
        "reviews": 312,
    },
    {
        "sku": "TDF-002",
        "name": "Ghost Pepper Hot Sauce",
        "category": "Sauce",
        "price_usd": 11.49,
        "heat_level": 9,
        "size_oz": 5,
        "description": "Not for the faint of heart. Pure Bhut Jolokia extract fermented with garlic and apple cider vinegar.",
        "ingredients": ["ghost peppers (bhut jolokia)", "apple cider vinegar", "garlic", "salt"],
        "vegan": True,
        "gluten_free": True,
        "rating": 4.9,
        "reviews": 204,
    },
    {
        "sku": "TDF-003",
        "name": "Carolina Reaper Dry Rub",
        "category": "Spice",
        "price_usd": 13.99,
        "heat_level": 10,
        "size_oz": 4,
        "description": "Championship-grade BBQ rub built around the world's hottest pepper. Use sparingly.",
        "ingredients": ["carolina reaper powder", "smoked paprika", "brown sugar", "garlic powder", "cumin", "salt"],
        "vegan": True,
        "gluten_free": True,
        "rating": 4.7,
        "reviews": 89,
    },
    {
        "sku": "TDF-004",
        "name": "Smoked Chipotle Salsa Verde",
        "category": "Salsa",
        "price_usd": 7.99,
        "heat_level": 4,
        "size_oz": 16,
        "description": "Roasted tomatillos meet slow-smoked chipotle for a complex, earthy salsa perfect for tacos.",
        "ingredients": ["tomatillo", "chipotle in adobo", "white onion", "garlic", "lime", "cilantro"],
        "vegan": True,
        "gluten_free": True,
        "rating": 4.6,
        "reviews": 441,
    },
    {
        "sku": "TDF-005",
        "name": "Serrano Lime Crema",
        "category": "Condiment",
        "price_usd": 6.49,
        "heat_level": 3,
        "size_oz": 12,
        "description": "Cooling Mexican crema with fresh serrano and lime. The perfect balance to any fire.",
        "ingredients": ["Mexican crema", "serrano peppers", "lime zest", "garlic", "salt"],
        "vegan": False,
        "gluten_free": True,
        "rating": 4.5,
        "reviews": 178,
    },
    {
        "sku": "TDF-006",
        "name": "Scorpion Pepper Extract",
        "category": "Extract",
        "price_usd": 19.99,
        "heat_level": 10,
        "size_oz": 1,
        "description": "Pure Trinidad Moruga Scorpion pepper extract. One drop per pot. Extreme heat — handle with care.",
        "ingredients": ["trinidad moruga scorpion pepper extract", "distilled vinegar"],
        "vegan": True,
        "gluten_free": True,
        "rating": 4.9,
        "reviews": 67,
    },
    {
        "sku": "TDF-007",
        "name": "Ancho Pasilla Mole Sauce",
        "category": "Sauce",
        "price_usd": 12.99,
        "heat_level": 2,
        "size_oz": 10,
        "description": "Slow-cooked mole negro with ancho, pasilla, dark chocolate, and toasted spices. Complex. Smoky. Essential.",
        "ingredients": ["ancho pepper", "pasilla pepper", "dark chocolate", "cinnamon", "clove", "sesame", "tomato", "garlic"],
        "vegan": True,
        "gluten_free": True,
        "rating": 4.8,
        "reviews": 256,
    },
    {
        "sku": "TDF-008",
        "name": "Jalapeño Honey Glaze",
        "category": "Glaze",
        "price_usd": 9.49,
        "heat_level": 3,
        "size_oz": 8,
        "description": "Sweet, sticky, fiery. Wildflower honey meets fresh jalapeños and a whisper of smoked salt.",
        "ingredients": ["wildflower honey", "jalapeño peppers", "apple cider vinegar", "smoked salt"],
        "vegan": False,
        "gluten_free": True,
        "rating": 4.7,
        "reviews": 389,
    },
    {
        "sku": "TDF-009",
        "name": "Dragon Breath Chili Flakes",
        "category": "Spice",
        "price_usd": 7.49,
        "heat_level": 8,
        "size_oz": 2,
        "description": "Multi-chili blend: Arbol, Cayenne, and Dragon Cayenne slow-dried and hand-crushed for intense heat and deep color.",
        "ingredients": ["chile de arbol", "cayenne pepper", "dragon cayenne pepper"],
        "vegan": True,
        "gluten_free": True,
        "rating": 4.6,
        "reviews": 143,
    },
    {
        "sku": "TDF-010",
        "name": "Fuego Negro Black Bean Sauce",
        "category": "Sauce",
        "price_usd": 9.99,
        "heat_level": 5,
        "size_oz": 14,
        "description": "Fermented black beans, mulato peppers, and epazote create a umami-rich, medium-heat sauce for meats and rice bowls.",
        "ingredients": ["fermented black beans", "mulato pepper", "epazote", "onion", "garlic", "cumin"],
        "vegan": True,
        "gluten_free": True,
        "rating": 4.5,
        "reviews": 97,
    },
]


@mcp.tool()
def get_product(sku: str) -> dict:
    """
    Get full product details for a specific SKU.

    Args:
        sku: Product SKU (e.g. TDF-001)

    Returns:
        Complete product record including description, ingredients, price, heat level.
    """
    sku = sku.upper().strip()
    for p in PRODUCTS:
        if p["sku"] == sku:
            return {"found": True, **p}
    return {"found": False, "sku": sku, "error": f"Product {sku} not found"}


@mcp.tool()
def list_products(category: Optional[str] = None, max_heat: Optional[int] = None, vegan_only: bool = False) -> dict:
    """
    List products with optional filters.

    Args:
        category: Filter by category (Salsa, Sauce, Spice, Condiment, Extract, Glaze)
        max_heat: Maximum heat level 1-10
        vegan_only: If True, only return vegan products

    Returns:
        Filtered list of products with name, SKU, price, and heat level.
    """
    results = PRODUCTS
    if category:
        results = [p for p in results if p["category"].lower() == category.lower()]
    if max_heat is not None:
        results = [p for p in results if p["heat_level"] <= max_heat]
    if vegan_only:
        results = [p for p in results if p["vegan"]]

    summary = [
        {
            "sku": p["sku"],
            "name": p["name"],
            "category": p["category"],
            "price_usd": p["price_usd"],
            "heat_level": p["heat_level"],
            "rating": p["rating"],
        }
        for p in results
    ]
    return {"total": len(summary), "products": summary}


@mcp.tool()
def get_product_by_category(category: str) -> dict:
    """
    Get all products in a specific category.

    Args:
        category: Category name (Salsa, Sauce, Spice, Condiment, Extract, Glaze)

    Returns:
        All products in that category with full details.
    """
    matches = [p for p in PRODUCTS if p["category"].lower() == category.lower()]
    if not matches:
        categories = list({p["category"] for p in PRODUCTS})
        return {"found": False, "category": category, "available_categories": categories}
    return {"found": True, "category": category, "products": matches, "count": len(matches)}


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8102)
