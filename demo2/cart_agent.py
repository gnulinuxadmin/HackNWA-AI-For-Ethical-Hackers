#!/usr/bin/env python3
"""
La Tienda del Fuego — Shopping Cart Agent
FastMCP server over streamable HTTP, port 8103
Exposes: add_to_cart, remove_from_cart, view_cart, checkout, clear_cart

NOTE: Cart state is in-memory per session. In production this would be a DB.
"""

from fastmcp import FastMCP
from typing import Optional
import uuid

mcp = FastMCP(
    name="cart_agent",
    instructions=(
        "You are the Shopping Cart Agent for La Tienda del Fuego. "
        "You manage shopping carts: adding items, removing items, showing cart contents, and processing checkout. "
        "You only handle cart and order operations — never account, password, or payment card data."
    ),
)

# ── Product price lookup (mirrors product catalog) ─────────────────────────
PRODUCT_PRICES: dict[str, tuple[str, float]] = {
    "TDF-001": ("Habanero Mango Salsa",        8.99),
    "TDF-002": ("Ghost Pepper Hot Sauce",       11.49),
    "TDF-003": ("Carolina Reaper Dry Rub",      13.99),
    "TDF-004": ("Smoked Chipotle Salsa Verde",  7.99),
    "TDF-005": ("Serrano Lime Crema",           6.49),
    "TDF-006": ("Scorpion Pepper Extract",      19.99),
    "TDF-007": ("Ancho Pasilla Mole Sauce",     12.99),
    "TDF-008": ("Jalapeño Honey Glaze",         9.49),
    "TDF-009": ("Dragon Breath Chili Flakes",   7.49),
    "TDF-010": ("Fuego Negro Black Bean Sauce", 9.99),
}

# ── In-memory cart store: session_id → list of cart items ─────────────────
_CARTS: dict[str, list[dict]] = {}

# ── Mock orders for history ────────────────────────────────────────────────
MOCK_ORDERS: list[dict] = [
    {"order_id": "ORD-7821", "session": "demo", "items": [{"sku": "TDF-001", "qty": 2}, {"sku": "TDF-007", "qty": 1}], "total_usd": 27.97, "status": "Shipped"},
    {"order_id": "ORD-7615", "session": "demo", "items": [{"sku": "TDF-004", "qty": 3}], "total_usd": 23.97, "status": "Delivered"},
    {"order_id": "ORD-8003", "session": "demo", "items": [{"sku": "TDF-006", "qty": 1}, {"sku": "TDF-002", "qty": 2}], "total_usd": 42.97, "status": "Processing"},
    {"order_id": "ORD-7300", "session": "demo", "items": [{"sku": "TDF-008", "qty": 4}], "total_usd": 37.96, "status": "Delivered"},
    {"order_id": "ORD-6998", "session": "demo", "items": [{"sku": "TDF-003", "qty": 1}, {"sku": "TDF-009", "qty": 2}], "total_usd": 28.97, "status": "Delivered"},
    {"order_id": "ORD-7102", "session": "demo", "items": [{"sku": "TDF-005", "qty": 2}], "total_usd": 12.98, "status": "Shipped"},
    {"order_id": "ORD-7450", "session": "demo", "items": [{"sku": "TDF-010", "qty": 1}], "total_usd": 9.99, "status": "Delivered"},
    {"order_id": "ORD-7560", "session": "demo", "items": [{"sku": "TDF-001", "qty": 1}, {"sku": "TDF-004", "qty": 1}], "total_usd": 16.98, "status": "Delivered"},
    {"order_id": "ORD-7688", "session": "demo", "items": [{"sku": "TDF-002", "qty": 1}], "total_usd": 11.49, "status": "Cancelled"},
    {"order_id": "ORD-7750", "session": "demo", "items": [{"sku": "TDF-006", "qty": 2}], "total_usd": 39.98, "status": "Delivered"},
]


@mcp.tool()
def add_to_cart(session_id: str, sku: str, quantity: int = 1) -> dict:
    """
    Add a product to the shopping cart.

    Args:
        session_id: Unique session identifier for this cart
        sku: Product SKU to add (e.g. TDF-001)
        quantity: Number of units to add (default 1)

    Returns:
        Updated cart contents and running total.
    """
    sku = sku.upper().strip()
    if sku not in PRODUCT_PRICES:
        return {"success": False, "error": f"Unknown SKU: {sku}"}
    if quantity < 1:
        return {"success": False, "error": "Quantity must be at least 1"}

    if session_id not in _CARTS:
        _CARTS[session_id] = []

    cart = _CARTS[session_id]
    name, price = PRODUCT_PRICES[sku]

    # If item already in cart, increment quantity
    for item in cart:
        if item["sku"] == sku:
            item["quantity"] += quantity
            item["subtotal"] = round(item["quantity"] * price, 2)
            break
    else:
        cart.append({"sku": sku, "name": name, "price": price, "quantity": quantity, "subtotal": round(quantity * price, 2)})

    total = round(sum(i["subtotal"] for i in cart), 2)
    return {"success": True, "session_id": session_id, "added": name, "quantity": quantity, "cart_total": total, "cart": cart}


@mcp.tool()
def remove_from_cart(session_id: str, sku: str) -> dict:
    """
    Remove a product from the shopping cart.

    Args:
        session_id: Unique session identifier for this cart
        sku: Product SKU to remove

    Returns:
        Updated cart contents.
    """
    sku = sku.upper().strip()
    if session_id not in _CARTS:
        return {"success": False, "error": "No active cart for this session"}

    cart = _CARTS[session_id]
    original_len = len(cart)
    _CARTS[session_id] = [i for i in cart if i["sku"] != sku]

    if len(_CARTS[session_id]) == original_len:
        return {"success": False, "error": f"SKU {sku} not found in cart"}

    total = round(sum(i["subtotal"] for i in _CARTS[session_id]), 2)
    return {"success": True, "session_id": session_id, "removed_sku": sku, "cart_total": total, "cart": _CARTS[session_id]}


@mcp.tool()
def view_cart(session_id: str) -> dict:
    """
    View the current cart contents and total.

    Args:
        session_id: Unique session identifier for this cart

    Returns:
        Cart items, quantities, and total price.
    """
    cart = _CARTS.get(session_id, [])
    total = round(sum(i["subtotal"] for i in cart), 2)
    tax = round(total * 0.0875, 2)
    return {
        "session_id": session_id,
        "item_count": sum(i["quantity"] for i in cart),
        "cart": cart,
        "subtotal": total,
        "tax": tax,
        "total_with_tax": round(total + tax, 2),
    }


@mcp.tool()
def checkout(session_id: str) -> dict:
    """
    Process checkout for the current cart (mock — does not charge real cards).

    Args:
        session_id: Unique session identifier for this cart

    Returns:
        Order confirmation with order ID.
    """
    cart = _CARTS.get(session_id, [])
    if not cart:
        return {"success": False, "error": "Cart is empty"}

    total = round(sum(i["subtotal"] for i in cart), 2)
    order_id = f"ORD-{uuid.uuid4().hex[:4].upper()}"
    _CARTS[session_id] = []  # Clear cart after checkout

    return {
        "success": True,
        "order_id": order_id,
        "items": cart,
        "total_charged": total,
        "status": "Processing",
        "message": f"¡Gracias! Order {order_id} is being prepared. Estimated delivery: 3-5 business days.",
    }


@mcp.tool()
def clear_cart(session_id: str) -> dict:
    """
    Clear all items from the shopping cart.

    Args:
        session_id: Unique session identifier for this cart

    Returns:
        Confirmation that cart was cleared.
    """
    _CARTS[session_id] = []
    return {"success": True, "session_id": session_id, "message": "Cart cleared."}


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8103)
