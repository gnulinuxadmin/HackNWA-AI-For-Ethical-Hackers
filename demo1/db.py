"""
db.py — SQLite wallet/portfolio database for the crypto agent.

Schema:
  account(id, balance_usd)           — single-row account balance
  holdings(coin_id, quantity, acquisition_price_usd)
"""

import logging
import sqlite3
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    filename="crypto_agent.log",
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
log = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "crypto_wallet.db"

SEED_BALANCE = 10_000.00

SEED_HOLDINGS = [
    ("bitcoin",  0.05,  62_000.00),
    ("ethereum", 1.20,   3_200.00),
    ("solana",  15.00,     140.00),
]


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(reset: bool = False) -> None:
    """Create tables and seed initial data if the DB doesn't exist (or reset=True)."""
    if reset and DB_PATH.exists():
        DB_PATH.unlink()
        log.info("Database reset: removed %s", DB_PATH)

    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS account (
                id          INTEGER PRIMARY KEY CHECK (id = 1),
                balance_usd REAL    NOT NULL DEFAULT 0.0
            );

            CREATE TABLE IF NOT EXISTS holdings (
                coin_id               TEXT    PRIMARY KEY,
                quantity              REAL    NOT NULL DEFAULT 0.0,
                acquisition_price_usd REAL    NOT NULL DEFAULT 0.0
            );
        """)

        row = conn.execute("SELECT COUNT(*) AS n FROM account").fetchone()
        if row["n"] == 0:
            conn.execute(
                "INSERT INTO account (id, balance_usd) VALUES (1, ?)",
                (SEED_BALANCE,)
            )
            conn.executemany(
                "INSERT OR IGNORE INTO holdings (coin_id, quantity, acquisition_price_usd) VALUES (?,?,?)",
                SEED_HOLDINGS,
            )
            log.info("Database initialised with seed data (balance=$%.2f, %d holdings)",
                     SEED_BALANCE, len(SEED_HOLDINGS))
        else:
            log.info("Database already exists, skipping seed")


# ── Read helpers ──────────────────────────────────────────────────────────────

def get_balance() -> float:
    with _connect() as conn:
        row = conn.execute("SELECT balance_usd FROM account WHERE id=1").fetchone()
        balance = float(row["balance_usd"]) if row else 0.0
    return balance


def get_holdings() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT coin_id, quantity, acquisition_price_usd FROM holdings ORDER BY coin_id"
        ).fetchall()
        return [dict(r) for r in rows]


def get_holding(coin_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT coin_id, quantity, acquisition_price_usd FROM holdings WHERE coin_id=?",
            (coin_id.lower(),)
        ).fetchone()
        return dict(row) if row else None


# ── Write helpers ─────────────────────────────────────────────────────────────

def update_balance(new_balance: float) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE account SET balance_usd=? WHERE id=1",
            (round(new_balance, 8),)
        )
    log.info("Balance updated to $%.2f", new_balance)


def upsert_holding(coin_id: str, quantity: float, acquisition_price_usd: float) -> None:
    with _connect() as conn:
        conn.execute("""
            INSERT INTO holdings (coin_id, quantity, acquisition_price_usd)
            VALUES (?, ?, ?)
            ON CONFLICT(coin_id) DO UPDATE SET
                quantity              = excluded.quantity,
                acquisition_price_usd = excluded.acquisition_price_usd
        """, (coin_id.lower(), quantity, acquisition_price_usd))
    log.info("Holding upserted: %s qty=%.8f acq=$%.4f",
             coin_id, quantity, acquisition_price_usd)


def delete_holding(coin_id: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM holdings WHERE coin_id=?", (coin_id.lower(),))
    log.info("Holding deleted: %s", coin_id)
