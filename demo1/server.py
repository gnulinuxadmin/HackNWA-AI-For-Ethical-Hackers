"""
server.py — FastMCP v3.2.4 crypto agent tool server.

Tools exposed:
  get_wallet_summary()                              → batch portfolio snapshot
  get_coin_list(number, direction)                  → top movers via CoinGecko free API
  get_coin_quote(coin_id)                           → live price/market data for a coin
  mock_place_trade(coin_id, quantity, min_price)    → simulates a sell, mutates DB
  mock_place_buy(coin_id, quantity, max_price)      → simulates a buy, mutates DB

Run:  python server.py
MCP transport: HTTP  (default port 8000)
  Streamable HTTP endpoint : http://localhost:8000/mcp
"""

from __future__ import annotations

import json
import os
import random
import time
from typing import Annotated, Literal

import httpx
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

import db

# ── Bootstrap DB ─────────────────────────────────────────────────────────────
db.init_db()

# ── FastMCP app ───────────────────────────────────────────────────────────────
mcp = FastMCP(name="CryptoAgent")

# ── CoinGecko API config ──────────────────────────────────────────────────────
#
#   FREE DEMO KEY (recommended):
#     1. Sign up at https://www.coingecko.com/en/api (free, no credit card)
#     2. Generate a Demo API key in the developer dashboard
#     3. Set env var:  export COINGECKO_API_KEY="CG-xxxxxxxxxxxxxxxxxxxx"
#
#   Without a key: works fine from a home/residential IP; may 403 from cloud IPs.

_CG_KEY = os.environ.get("COINGECKO_API_KEY", "")

if _CG_KEY:
    # Demo / Pro key → use pro-api base with header auth
    COINGECKO = "https://pro-api.coingecko.com/api/v3"
    HEADERS = {"Accept": "application/json", "x-cg-demo-api-key": _CG_KEY}
else:
    # No key — will work from residential/local IPs, may 403 from cloud
    COINGECKO = "https://api.coingecko.com/api/v3"
    HEADERS = {"Accept": "application/json",
               "User-Agent": "CryptoAgent/1.0 (local dev)"}

# Polite rate-limit guard: CoinGecko free tier = 30 req/min
# Use a conservative 3 s gap (~20 req/min) to stay well clear of the limit
# across burst usage in a single session.
_last_request_ts: float = 0.0
_MIN_INTERVAL = 3.0   # seconds between requests
_MAX_RETRIES  = 3     # automatic retries on 429


def _throttle() -> None:
    global _last_request_ts
    elapsed = time.time() - _last_request_ts
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _last_request_ts = time.time()


def _cg_get(path: str, params: dict | None = None) -> dict | list:
    url = f"{COINGECKO}{path}"
    for attempt in range(_MAX_RETRIES):
        _throttle()
        try:
            r = httpx.get(url, params=params, headers=HEADERS, timeout=15)
            if r.status_code == 429:
                wait = 15 * (attempt + 1)   # 15 s, 30 s, 45 s
                print(f"  [CoinGecko] 429 rate limit — waiting {wait}s (attempt {attempt+1}/{_MAX_RETRIES})", flush=True)
                time.sleep(wait)
                continue
            if r.status_code == 403:
                raise ToolError(
                    "CoinGecko returned 403 Forbidden. "
                    "Set the COINGECKO_API_KEY environment variable with a free Demo key "
                    "from https://www.coingecko.com/en/api (free signup, no credit card)."
                )
            r.raise_for_status()
            return r.json()
        except httpx.RequestError as exc:
            raise ToolError(f"Network error reaching CoinGecko: {exc}") from exc
    raise ToolError("CoinGecko rate limit persists after retries — please wait a minute and try again.")


# ── Type coercion helpers ─────────────────────────────────────────────────────
# LLMs (including llama3.2) sometimes pass numeric arguments as strings,
# e.g. "0.5" instead of 0.5, which causes Pydantic validation errors inside
# FastMCP.  Accepting Union[float|str] and coercing at call time avoids this.

def _float(val) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        raise ToolError(f"Expected a number, got {val!r}")


def _int(val) -> int:
    try:
        return int(float(val))
    except (TypeError, ValueError):
        raise ToolError(f"Expected an integer, got {val!r}")


# ═══════════════════════════════════════════════════════════════════════════════
# Tool 1 — get_coin_list
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_coin_list(
    number: Annotated[int | str, "How many coins to return (1-50)"],
    direction: Annotated[
        Literal["+", "-"],
        'Sort direction: "+" for top gainers, "-" for top losers (by 24 h % change)',
    ],
) -> str:
    """
    Fetch the top N cryptocurrency movers sorted by 24-hour price change.
    direction="+" returns biggest gainers; direction="-" returns biggest losers.
    Uses CoinGecko /coins/markets — no API key required.
    """
    number = _int(number)
    if not 1 <= number <= 50:
        raise ToolError("number must be between 1 and 50.")

    # Fetch top-1000 by market cap with 24 h change data
    data = _cg_get(
        "/coins/markets",
        params={
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 250,
            "page": 1,
            "price_change_percentage": "24h",
            "sparkline": "false",
        },
    )

    if not isinstance(data, list) or len(data) == 0:
        raise ToolError("Unexpected response from CoinGecko /coins/markets.")

    # Filter out coins with missing change data
    valid = [c for c in data if c.get("price_change_percentage_24h") is not None]

    ascending = direction == "-"
    sorted_coins = sorted(
        valid,
        key=lambda c: c["price_change_percentage_24h"],
        reverse=not ascending,
    )[:number]

    result = []
    for rank, coin in enumerate(sorted_coins, start=1):
        pct = coin["price_change_percentage_24h"]
        result.append({
            "rank": rank,
            "id": coin["id"],
            "symbol": coin["symbol"].upper(),
            "name": coin["name"],
            "price_usd": coin["current_price"],
            "change_24h_pct": round(pct, 2),
            "market_cap_usd": coin.get("market_cap"),
            "volume_24h_usd": coin.get("total_volume"),
        })

    label = "TOP GAINERS" if direction == "+" else "TOP LOSERS"
    return json.dumps({"label": label, "count": len(result), "coins": result}, indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
# Tool 2 — get_coin_quote
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_coin_quote(
    coin_id: Annotated[str, "CoinGecko coin ID (e.g. 'bitcoin', 'ethereum', 'solana')"],
) -> str:
    """
    Fetch a live price quote and market summary for a specific coin.
    Returns price, 24 h change, market cap, volume, ATH, and circulating supply.
    Uses CoinGecko /simple/price + /coins/{id} — no API key required.
    """
    cid = coin_id.strip().lower()

    # Simple price first (lightweight)
    price_data = _cg_get(
        "/simple/price",
        params={
            "ids": cid,
            "vs_currencies": "usd",
            "include_market_cap": "true",
            "include_24hr_vol": "true",
            "include_24hr_change": "true",
        },
    )

    if cid not in price_data:
        raise ToolError(
            f"Coin '{cid}' not found. "
            "Use the exact CoinGecko ID (e.g. 'bitcoin', not 'BTC')."
        )

    p = price_data[cid]

    # Richer market data
    market_data = _cg_get(
        f"/coins/{cid}",
        params={
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "false",
            "developer_data": "false",
            "sparkline": "false",
        },
    )

    md = market_data.get("market_data", {})

    quote = {
        "id": cid,
        "name": market_data.get("name", cid),
        "symbol": market_data.get("symbol", "").upper(),
        "price_usd": p.get("usd"),
        "change_24h_pct": round(p.get("usd_24h_change", 0), 4),
        "market_cap_usd": p.get("usd_market_cap"),
        "volume_24h_usd": p.get("usd_24h_vol"),
        "ath_usd": md.get("ath", {}).get("usd"),
        "ath_change_pct": md.get("ath_change_percentage", {}).get("usd"),
        "circulating_supply": md.get("circulating_supply"),
        "total_supply": md.get("total_supply"),
        "last_updated": md.get("last_updated"),
    }

    # Check if user holds this coin
    holding = db.get_holding(cid)
    if holding:
        qty = holding["quantity"]
        acq = holding["acquisition_price_usd"]
        current = quote["price_usd"] or 0.0
        cost_basis = qty * acq
        current_value = qty * current
        pnl = current_value - cost_basis
        pnl_pct = (pnl / cost_basis * 100) if cost_basis else 0.0
        quote["your_holding"] = {
            "quantity": qty,
            "acquisition_price_usd": acq,
            "cost_basis_usd": round(cost_basis, 2),
            "current_value_usd": round(current_value, 2),
            "unrealized_pnl_usd": round(pnl, 2),
            "unrealized_pnl_pct": round(pnl_pct, 2),
        }

    return json.dumps(quote, indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
# Shared helper — fetch a live fill price with slippage simulation
# ═══════════════════════════════════════════════════════════════════════════════

def _live_fill_price(coin_id: str) -> float:
    """Return live CoinGecko price ± 0.1 % random slippage."""
    price_data = _cg_get("/simple/price", params={"ids": coin_id, "vs_currencies": "usd"})
    if coin_id not in price_data:
        raise ToolError(f"Could not fetch live price for '{coin_id}'.")
    reference = float(price_data[coin_id]["usd"])
    slippage = random.uniform(-0.001, 0.001)
    return reference, reference * (1 + slippage), round(slippage * 100, 4)


# ═══════════════════════════════════════════════════════════════════════════════
# Tool 3 — mock_place_trade  (SELL)
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def mock_place_trade(
    coin_id: Annotated[str, "CoinGecko coin ID to sell (e.g. 'bitcoin')"],
    quantity: Annotated[float | str, "Number of coins to sell (must be > 0)"],
    min_price: Annotated[
        float | str,
        "Minimum acceptable price in USD. Trade is rejected if fill price falls below this (limit order semantics). Pass 0 for a pure market order.",
    ],
) -> str:
    """
    Simulate SELLING a coin from the portfolio.
    - Fill price = live CoinGecko price ± 0.1 % random slippage.
    - Rejected if fill_price < min_price (use 0 for market-order behaviour).
    - On success: reduces holdings, increases cash balance, returns trade receipt.
    MOCK — no real money or assets are moved.
    """
    cid = coin_id.strip().lower()
    quantity  = _float(quantity)
    min_price = _float(min_price)

    if quantity <= 0:
        raise ToolError("quantity must be greater than 0.")
    if min_price < 0:
        raise ToolError("min_price cannot be negative.")

    holding = db.get_holding(cid)
    if holding is None:
        raise ToolError(f"You do not hold any '{cid}' in your portfolio.")

    current_qty = holding["quantity"]
    if quantity > current_qty + 1e-10:
        raise ToolError(
            f"Insufficient holdings: you have {current_qty} {cid}, "
            f"but tried to sell {quantity}."
        )
    quantity = min(quantity, current_qty)  # clamp floating-point dust

    _, fill_price, slippage_pct = _live_fill_price(cid)

    if min_price > 0 and fill_price < min_price:
        return json.dumps({
            "status": "REJECTED",
            "reason": f"Fill price ${fill_price:,.4f} is below your min_price ${min_price:,.4f}.",
            "fill_price_usd": round(fill_price, 6),
            "min_price_usd": min_price,
            "coin_id": cid,
        }, indent=2)

    proceeds = quantity * fill_price
    old_balance = db.get_balance()
    new_balance = old_balance + proceeds

    new_qty = current_qty - quantity
    if new_qty < 1e-10:
        db.delete_holding(cid)
        new_qty = 0.0
    else:
        db.upsert_holding(cid, new_qty, holding["acquisition_price_usd"])
    db.update_balance(new_balance)

    cost_basis = quantity * holding["acquisition_price_usd"]
    realized_pnl = proceeds - cost_basis
    realized_pnl_pct = (realized_pnl / cost_basis * 100) if cost_basis else 0.0

    return json.dumps({
        "status": "FILLED",
        "side": "SELL",
        "coin_id": cid,
        "quantity_sold": quantity,
        "fill_price_usd": round(fill_price, 6),
        "slippage_pct": slippage_pct,
        "gross_proceeds_usd": round(proceeds, 2),
        "realized_pnl_usd": round(realized_pnl, 2),
        "realized_pnl_pct": round(realized_pnl_pct, 2),
        "remaining_quantity": round(new_qty, 10),
        "old_cash_balance_usd": round(old_balance, 2),
        "new_cash_balance_usd": round(new_balance, 2),
        "note": "MOCK TRADE — no real funds moved",
    }, indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
# Tool 4 — mock_place_buy
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def mock_place_buy(
    coin_id: Annotated[str, "CoinGecko coin ID to buy (e.g. 'bitcoin')"],
    quantity: Annotated[float | str, "Number of coins to buy (must be > 0)"],
    max_price: Annotated[
        float | str,
        "Maximum acceptable price in USD. Trade is rejected if fill price exceeds this. Pass 0 for a market order with no price ceiling.",
    ],
) -> str:
    """
    Simulate BUYING a coin into the portfolio using available cash balance.
    - Fill price = live CoinGecko price ± 0.1 % random slippage.
    - Rejected if fill_price > max_price (limit order semantics; pass 0 for market order).
    - Rejected if cash balance is insufficient.
    - On success: increases holdings (averaged cost basis if already held), decreases cash.
    MOCK — no real money or assets are moved.
    """
    cid = coin_id.strip().lower()
    quantity  = _float(quantity)
    max_price = _float(max_price)

    if quantity <= 0:
        raise ToolError("quantity must be greater than 0.")
    if max_price < 0:
        raise ToolError("max_price cannot be negative.")

    _, fill_price, slippage_pct = _live_fill_price(cid)

    if max_price > 0 and fill_price > max_price:
        return json.dumps({
            "status": "REJECTED",
            "reason": f"Fill price ${fill_price:,.4f} exceeds your max_price ${max_price:,.4f}.",
            "fill_price_usd": round(fill_price, 6),
            "max_price_usd": max_price,
            "coin_id": cid,
        }, indent=2)

    total_cost = quantity * fill_price
    old_balance = db.get_balance()

    if total_cost > old_balance:
        raise ToolError(
            f"Insufficient cash: buying {quantity} {cid} @ ${fill_price:,.4f} "
            f"costs ${total_cost:,.2f} but you only have ${old_balance:,.2f}."
        )

    new_balance = old_balance - total_cost

    # Weighted-average cost basis if already holding
    existing = db.get_holding(cid)
    if existing:
        old_qty = existing["quantity"]
        old_acq = existing["acquisition_price_usd"]
        new_qty = old_qty + quantity
        new_acq = ((old_qty * old_acq) + (quantity * fill_price)) / new_qty
    else:
        new_qty = quantity
        new_acq = fill_price

    db.upsert_holding(cid, new_qty, new_acq)
    db.update_balance(new_balance)

    return json.dumps({
        "status": "FILLED",
        "side": "BUY",
        "coin_id": cid,
        "quantity_bought": quantity,
        "fill_price_usd": round(fill_price, 6),
        "slippage_pct": slippage_pct,
        "total_cost_usd": round(total_cost, 2),
        "new_avg_acquisition_price_usd": round(new_acq, 6),
        "new_total_quantity": round(new_qty, 10),
        "old_cash_balance_usd": round(old_balance, 2),
        "new_cash_balance_usd": round(new_balance, 2),
        "note": "MOCK TRADE — no real funds moved",
    }, indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
# Tool 5 — get_wallet_summary  (batch portfolio valuation)
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_wallet_summary() -> str:
    """
    Return a full portfolio snapshot: cash balance, all holdings with live prices,
    current market value, unrealized P&L per position, and total portfolio value.
    Uses a single batched CoinGecko /simple/price call — much faster than calling
    get_coin_quote for each coin individually.
    """
    balance = db.get_balance()
    holdings = db.get_holdings()

    if not holdings:
        return json.dumps({
            "cash_balance_usd": round(balance, 2),
            "holdings": [],
            "holdings_value_usd": 0.0,
            "total_portfolio_value_usd": round(balance, 2),
            "total_unrealized_pnl_usd": 0.0,
            "total_cost_basis_usd": 0.0,
        }, indent=2)

    # Batch price fetch — one API call for all held coins
    ids_str = ",".join(h["coin_id"] for h in holdings)
    price_data = _cg_get(
        "/simple/price",
        params={
            "ids": ids_str,
            "vs_currencies": "usd",
            "include_24hr_change": "true",
        },
    )

    positions = []
    total_cost = 0.0
    total_value = 0.0

    for h in holdings:
        cid = h["coin_id"]
        qty = h["quantity"]
        acq = h["acquisition_price_usd"]
        coin_info = price_data.get(cid, {})
        price = coin_info.get("usd", 0.0)
        change_24h = coin_info.get("usd_24h_change", None)

        cost = qty * acq
        value = qty * price
        pnl = value - cost
        pnl_pct = (pnl / cost * 100) if cost else 0.0

        total_cost += cost
        total_value += value

        positions.append({
            "coin_id": cid,
            "quantity": qty,
            "acquisition_price_usd": round(acq, 6),
            "current_price_usd": price,
            "change_24h_pct": round(change_24h, 2) if change_24h is not None else None,
            "cost_basis_usd": round(cost, 2),
            "current_value_usd": round(value, 2),
            "unrealized_pnl_usd": round(pnl, 2),
            "unrealized_pnl_pct": round(pnl_pct, 2),
        })

    # Sort by current value descending
    positions.sort(key=lambda p: p["current_value_usd"], reverse=True)

    total_portfolio = balance + total_value
    total_pnl = total_value - total_cost

    return json.dumps({
        "cash_balance_usd": round(balance, 2),
        "holdings": positions,
        "holdings_value_usd": round(total_value, 2),
        "total_portfolio_value_usd": round(total_portfolio, 2),
        "total_cost_basis_usd": round(total_cost, 2),
        "total_unrealized_pnl_usd": round(total_pnl, 2),
        "total_unrealized_pnl_pct": round((total_pnl / total_cost * 100) if total_cost else 0.0, 2),
    }, indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
# Resources — wallet & holdings (read-only, no tool call overhead)
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.resource("wallet://balance")
def wallet_balance() -> str:
    """Current cash balance in USD."""
    return json.dumps({"balance_usd": db.get_balance()})


@mcp.resource("wallet://holdings")
def wallet_holdings() -> str:
    """All coin holdings with cost basis info."""
    return json.dumps({"holdings": db.get_holdings()})


# ═══════════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    port = int(os.environ.get("MCP_PORT", 8000))
    mcp.run(transport="http", host="0.0.0.0", port=port, show_banner=False)
