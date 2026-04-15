#!/usr/bin/env python3
"""
reset_wallet.py — Reset the portfolio database to its initial seed state.

Usage:
    python reset_wallet.py          # prompts for confirmation
    python reset_wallet.py --yes    # skips confirmation
"""

import sys
import db

def main():
    skip_confirm = "--yes" in sys.argv

    if not skip_confirm:
        print("This will reset your wallet to the initial seed state:")
        print(f"  Cash balance : ${db.SEED_BALANCE:,.2f}")
        for cid, qty, acq in db.SEED_HOLDINGS:
            print(f"  {cid:<12}: {qty} units @ ${acq:,.2f}")
        answer = input("\nProceed? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.")
            return

    db.init_db(reset=True)
    print("\n✅ Wallet reset complete.")
    print(f"  Cash: ${db.get_balance():,.2f}")
    for h in db.get_holdings():
        print(f"  {h['coin_id']:<12}: {h['quantity']} @ ${h['acquisition_price_usd']:,.2f}")


if __name__ == "__main__":
    main()
