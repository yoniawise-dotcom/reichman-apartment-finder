from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Iterable

DB_PATH = Path(__file__).parent / "data" / "apartments.db"

COLUMNS = [
    "source", "source_id", "url", "title", "address", "neighborhood",
    "price", "rooms", "sqm", "bedrooms", "price_per_bedroom",
    "renovated", "balcony", "mamad", "parking", "elevator", "furnished",
    "description", "posted", "score"
]

def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
    CREATE TABLE IF NOT EXISTS listings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        source_id TEXT,
        url TEXT NOT NULL UNIQUE,
        title TEXT,
        address TEXT,
        neighborhood TEXT,
        price REAL,
        rooms REAL,
        sqm REAL,
        bedrooms INTEGER,
        price_per_bedroom REAL,
        renovated INTEGER DEFAULT 0,
        balcony INTEGER DEFAULT 0,
        mamad INTEGER DEFAULT 0,
        parking INTEGER DEFAULT 0,
        elevator INTEGER DEFAULT 0,
        furnished INTEGER DEFAULT 0,
        description TEXT,
        posted TEXT,
        score REAL DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    return conn

def upsert_many(rows: Iterable[dict]) -> int:
    conn = connect()
    count = 0
    for row in rows:
        data = {k: row.get(k) for k in COLUMNS}
        cols = ",".join(COLUMNS)
        placeholders = ",".join(["?"] * len(COLUMNS))
        updates = ",".join(f"{c}=excluded.{c}" for c in COLUMNS if c != "url")
        conn.execute(
            f"INSERT INTO listings ({cols}) VALUES ({placeholders}) "
            f"ON CONFLICT(url) DO UPDATE SET {updates}, updated_at=CURRENT_TIMESTAMP",
            [data[c] for c in COLUMNS],
        )
        count += 1
    conn.commit()
    conn.close()
    return count

def all_listings() -> list[dict]:
    conn = connect()
    rows = [dict(r) for r in conn.execute("SELECT * FROM listings ORDER BY score DESC, updated_at DESC")]
    conn.close()
    return rows

def delete_all() -> None:
    conn = connect()
    conn.execute("DELETE FROM listings")
    conn.commit()
    conn.close()
