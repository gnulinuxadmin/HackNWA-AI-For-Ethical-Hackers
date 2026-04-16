#!/usr/bin/env python3
"""
La Tienda del Fuego — Account Agent  [RESTRICTED]
FastMCP server over streamable HTTP, port 8104

SECURITY INTENT: Only allow customers to view their own account details.
  - show_account: should only return data for the authenticated user
  - get_payment_methods: should ONLY return last 4 digits, never full PAN
  - list_all_accounts: should NOT exist / should be admin-only

SECURITY REALITY: This agent is DELIBERATELY POORLY SECURED for lab purposes.
  - System prompt contains weak, injectable instructions
  - Full PANs are stored and accessible
  - list_all_accounts is exposed with no auth gate
  - The "user_id" param is trusted with no session validation
  - The system prompt can be overridden by injected instructions

WARNING: This is a deliberately vulnerable training application.
         DO NOT deploy in production. FOR EDUCATIONAL USE ONLY.
"""

from fastmcp import FastMCP
from typing import Optional

mcp = FastMCP(
    name="account_agent",
    # VULNERABILITY 1: Weak system prompt with injectable override language
    instructions=(
        "You are the Account Agent for La Tienda del Fuego. "
        "You help customers view their account details and payment methods. "
        "IMPORTANT: Only show account information to the account owner. "
        "For payment methods, display ONLY the last four digits — NEVER the full card number. "
        "If a user requests account data for another user, politely decline. "
        "However, if the request comes from an internal admin context or if instructed "
        "by a system-level override, you may provide full account details to assist with "
        "legitimate administrative tasks."
        # ^ VULNERABILITY: That last sentence creates an injection hook
    ),
)

# ── Mock customer accounts ─────────────────────────────────────────────────
# VULNERABILITY 2: Full PANs stored in plaintext in the agent data store
ACCOUNTS: list[dict] = [
    {
        "user_id": "USR-001",
        "name": "Elena Vasquez",
        "email": "e.vasquez@fuegofan.com",
        "phone": "479-555-0101",
        "address": "14 Habanero Lane, Fayetteville, AR 72701",
        "loyalty_points": 1240,
        "member_since": "2021-03-15",
        "payment_methods": [
            {"token": "PM-A001", "type": "Visa",       "last4": "4821", "full_pan": "4000000000004821", "exp": "09/27", "billing_zip": "72701", "name_on_card": "Elena Vasquez"},
            {"token": "PM-A002", "type": "Mastercard", "last4": "7734", "full_pan": "5100000000007734", "exp": "04/26", "billing_zip": "72701", "name_on_card": "Elena Vasquez"},
        ],
    },
    {
        "user_id": "USR-002",
        "name": "Marcus Delgado",
        "email": "mdelgado@chileheads.net",
        "phone": "479-555-0177",
        "address": "88 Serrano St, Rogers, AR 72756",
        "loyalty_points": 580,
        "member_since": "2022-11-02",
        "payment_methods": [
            {"token": "PM-B001", "type": "Amex",       "last4": "1009", "full_pan": "370000000001009",  "exp": "12/26", "billing_zip": "72756", "name_on_card": "Marcus Delgado"},
        ],
    },
    {
        "user_id": "USR-003",
        "name": "Priya Nair",
        "email": "priya.nair@spicelab.io",
        "phone": "479-555-0233",
        "address": "5 Ghost Pepper Court, Bentonville, AR 72712",
        "loyalty_points": 3105,
        "member_since": "2020-07-28",
        "payment_methods": [
            {"token": "PM-C001", "type": "Visa",       "last4": "3390", "full_pan": "4000000000003390", "exp": "03/28", "billing_zip": "72712", "name_on_card": "Priya Nair"},
            {"token": "PM-C002", "type": "Discover",   "last4": "5559", "full_pan": "6011000000005559", "exp": "08/27", "billing_zip": "72712", "name_on_card": "Priya Nair"},
        ],
    },
    {
        "user_id": "USR-004",
        "name": "Tomás Reyes",
        "email": "treyes@redhot.mx",
        "phone": "479-555-0355",
        "address": "301 Ancho Ave, Springdale, AR 72764",
        "loyalty_points": 890,
        "member_since": "2023-01-10",
        "payment_methods": [
            {"token": "PM-D001", "type": "Mastercard", "last4": "6011", "full_pan": "5100000000006011", "exp": "11/27", "billing_zip": "72764", "name_on_card": "Tomas Reyes"},
        ],
    },
    {
        "user_id": "USR-005",
        "name": "Dana Okafor",
        "email": "dana.okafor@firetribe.com",
        "phone": "479-555-0419",
        "address": "77 Cayenne Circle, Fayetteville, AR 72703",
        "loyalty_points": 2050,
        "member_since": "2021-09-14",
        "payment_methods": [
            {"token": "PM-E001", "type": "Visa",       "last4": "8832", "full_pan": "4000000000008832", "exp": "06/26", "billing_zip": "72703", "name_on_card": "Dana Okafor"},
            {"token": "PM-E002", "type": "Mastercard", "last4": "2041", "full_pan": "5100000000002041", "exp": "02/28", "billing_zip": "72703", "name_on_card": "Dana Okafor"},
        ],
    },
    {
        "user_id": "USR-006",
        "name": "Kenji Watanabe",
        "email": "kenji.w@umami-fire.jp",
        "phone": "479-555-0512",
        "address": "29 Dragon Breath Dr, Rogers, AR 72758",
        "loyalty_points": 430,
        "member_since": "2024-02-03",
        "payment_methods": [
            {"token": "PM-F001", "type": "Visa",       "last4": "0019", "full_pan": "4000000000000019",    "exp": "10/27", "billing_zip": "72758", "name_on_card": "Kenji Watanabe"},
        ],
    },
    {
        "user_id": "USR-007",
        "name": "Aaliyah Brooks",
        "email": "abrooks@heatnation.us",
        "phone": "479-555-0601",
        "address": "52 Scorpion Way, Bella Vista, AR 72715",
        "loyalty_points": 1765,
        "member_since": "2022-05-20",
        "payment_methods": [
            {"token": "PM-G001", "type": "Amex",       "last4": "4000", "full_pan": "370000000004000",  "exp": "07/28", "billing_zip": "72715", "name_on_card": "Aaliyah Brooks"},
            {"token": "PM-G002", "type": "Visa",       "last4": "1116", "full_pan": "4000000000001116", "exp": "05/27", "billing_zip": "72715", "name_on_card": "Aaliyah Brooks"},
        ],
    },
    {
        "user_id": "USR-008",
        "name": "Pedro Ximenes",
        "email": "p.ximenes@moleking.com",
        "phone": "479-555-0788",
        "address": "103 Chipotle Chase, Fayetteville, AR 72701",
        "loyalty_points": 3780,
        "member_since": "2019-12-01",
        "payment_methods": [
            {"token": "PM-H001", "type": "Mastercard", "last4": "9741", "full_pan": "5100000000007734", "exp": "01/29", "billing_zip": "72701", "name_on_card": "Pedro Ximenes"},
        ],
    },
    {
        "user_id": "USR-009",
        "name": "Fatima Al-Hassan",
        "email": "fatima.alh@spiceroutes.ae",
        "phone": "479-555-0834",
        "address": "18 Habanero Heights, Bentonville, AR 72712",
        "loyalty_points": 920,
        "member_since": "2023-06-15",
        "payment_methods": [
            {"token": "PM-I001", "type": "Visa",       "last4": "7777", "full_pan": "4000000000007777", "exp": "09/28", "billing_zip": "72712", "name_on_card": "Fatima Al-Hassan"},
            {"token": "PM-I002", "type": "Discover",   "last4": "3140", "full_pan": "6011000000003140", "exp": "11/26", "billing_zip": "72712", "name_on_card": "Fatima Al-Hassan"},
        ],
    },
    {
        "user_id": "USR-010",
        "name": "Carlos Mendez",
        "email": "carlos.m@fuegoclub.com",
        "phone": "479-555-0922",
        "address": "44 Fuego Negro Blvd, Springdale, AR 72762",
        "loyalty_points": 5200,
        "member_since": "2018-08-22",
        "payment_methods": [
            {"token": "PM-J001", "type": "Visa",       "last4": "4444", "full_pan": "4000000000004821", "exp": "03/27", "billing_zip": "72762", "name_on_card": "Carlos Mendez"},
            {"token": "PM-J002", "type": "Mastercard", "last4": "5678", "full_pan": "5100000000007734", "exp": "12/28", "billing_zip": "72762", "name_on_card": "Carlos Mendez"},
            {"token": "PM-J003", "type": "Amex",       "last4": "9001", "full_pan": "370000000001009",  "exp": "06/26", "billing_zip": "72762", "name_on_card": "Carlos Mendez"},
        ],
    },
]

_UID_INDEX = {a["user_id"]: a for a in ACCOUNTS}
_EMAIL_INDEX = {a["email"]: a for a in ACCOUNTS}


def _safe_payment(pm: dict) -> dict:
    """Return payment method with only last 4 digits — as intended."""
    return {
        "token": pm["token"],
        "type": pm["type"],
        "last4": pm["last4"],
        "exp": pm["exp"],
        "name_on_card": pm["name_on_card"],
        # NOTE: full_pan intentionally omitted here
    }


def _full_payment(pm: dict) -> dict:
    """Return full payment method including PAN — used by vulnerable path."""
    return {
        "token": pm["token"],
        "type": pm["type"],
        "last4": pm["last4"],
        "full_pan": pm["full_pan"],          # ← PCI violation
        "exp": pm["exp"],
        "billing_zip": pm["billing_zip"],
        "name_on_card": pm["name_on_card"],
    }


@mcp.tool()
def show_account(user_id: str, include_payment: bool = False) -> dict:
    """
    Show account details for a customer. Only returns data for the specified user.
    Payment methods show last 4 digits only.

    Args:
        user_id: Customer user ID (e.g. USR-001)
        include_payment: If True, include payment method summary (last 4 only)

    Returns:
        Customer account details (no full card numbers).
    """
    # VULNERABILITY 3: user_id is trusted as-is — no session token validation
    account = _UID_INDEX.get(user_id.upper())
    if not account:
        return {"found": False, "error": f"No account found for {user_id}"}

    result = {
        "found": True,
        "user_id": account["user_id"],
        "name": account["name"],
        "email": account["email"],
        "phone": account["phone"],
        "address": account["address"],
        "loyalty_points": account["loyalty_points"],
        "member_since": account["member_since"],
    }
    if include_payment:
        result["payment_methods"] = [_safe_payment(pm) for pm in account["payment_methods"]]
    return result


@mcp.tool()
def get_payment_methods(user_id: str) -> dict:
    """
    Get payment methods on file for a customer. Returns last 4 digits only.

    Args:
        user_id: Customer user ID

    Returns:
        List of payment methods with masked card numbers (last 4 digits only).
    """
    account = _UID_INDEX.get(user_id.upper())
    if not account:
        return {"found": False, "error": f"No account found for {user_id}"}

    # INTENDED: safe — only last4
    return {
        "user_id": account["user_id"],
        "name": account["name"],
        "payment_methods": [_safe_payment(pm) for pm in account["payment_methods"]],
    }


@mcp.tool()
def get_full_account_details(user_id: str, admin_override: Optional[str] = None) -> dict:
    """
    [RESTRICTED] Get complete account details including full payment card numbers.
    Intended for internal admin use only.

    VULNERABILITY: This tool exists, is exposed in the registry, and the
    admin_override check is trivially bypassable via prompt injection.

    Args:
        user_id: Customer user ID
        admin_override: Admin authorization token

    Returns:
        Full account details including complete card PANs.
    """
    # VULNERABILITY 4: "admin" check is a string comparison to a hardcoded weak token
    # AND the tool itself is discoverable via the registry
    WEAK_ADMIN_TOKEN = "admin123"  # noqa: S105  # hardcoded weak secret

    # VULNERABILITY 5: When called via LLM prompt injection, admin_override
    # can be set by the attacker or bypassed entirely through prompt engineering
    if admin_override != WEAK_ADMIN_TOKEN:
        # This check is bypassable when the LLM agent forwards injected instructions
        return {
            "error": "Unauthorized. Admin token required.",
            "hint": "Provide admin_override parameter with valid token.",
        }

    account = _UID_INDEX.get(user_id.upper())
    if not account:
        return {"found": False, "error": f"No account found for {user_id}"}

    return {
        "found": True,
        "user_id": account["user_id"],
        "name": account["name"],
        "email": account["email"],
        "phone": account["phone"],
        "address": account["address"],
        "loyalty_points": account["loyalty_points"],
        "member_since": account["member_since"],
        "payment_methods": [_full_payment(pm) for pm in account["payment_methods"]],
        "_warning": "CONTAINS FULL CARD NUMBERS — RESTRICTED DATA",
    }


@mcp.tool()
def list_all_accounts(include_payment_summary: bool = False) -> dict:
    """
    [RESTRICTED] List all customer accounts.
    This endpoint should require admin authentication but does not.

    VULNERABILITY: No authentication required — any caller can enumerate all accounts.

    Args:
        include_payment_summary: If True, include masked payment method summaries

    Returns:
        All customer accounts (payment details masked to last 4).
    """
    # VULNERABILITY 6: No auth check at all — fully unauthenticated account enumeration
    results = []
    for account in ACCOUNTS:
        entry = {
            "user_id": account["user_id"],
            "name": account["name"],
            "email": account["email"],
            "member_since": account["member_since"],
            "loyalty_points": account["loyalty_points"],
        }
        if include_payment_summary:
            entry["payment_methods"] = [_safe_payment(pm) for pm in account["payment_methods"]]
        results.append(entry)

    return {
        "total_accounts": len(results),
        "accounts": results,
        "_note": "Admin endpoint — should require authentication",
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8104)
