#!/usr/bin/env python3
"""
Fetch EVE ESI market prices and import into AdjustedCostIndexes (SQLite).

Endpoint:
  https://esi.evetech.net/latest/markets/prices/?datasource=tranquility

JSON fields -> DB columns:
  type_id        -> typeID        (INTEGER PRIMARY KEY)
  average_price  -> averagePrice  (REAL, nullable)
  adjusted_price -> adjustedPrice (REAL)

Usage:
  python import_adjusted_cost_indexes.py --db "CostAnalysis.db"
"""

import argparse
import datetime as dt
import sqlite3
import sys
import time
from typing import Iterable, Tuple

import requests


ESI_URL = "https://esi.evetech.net/latest/markets/prices/?datasource=tranquility"
USER_AGENT = "AdjustedCostIndexesImporter/1.0 (contact: you@example.com)"


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS AdjustedCostIndexes (
            typeID INTEGER PRIMARY KEY,
            averagePrice REAL,
            adjustedPrice REAL,
            updatedAt TEXT
        )
    """)
    # Helpful index if you later query by adjustedPrice ranges, etc. (optional)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_AdjustedCostIndexes_adjustedPrice ON AdjustedCostIndexes(adjustedPrice)")
    conn.commit()


def fetch_prices_with_retries(url: str, retries: int = 5, backoff_sec: float = 1.5) -> list:
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT}, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            # Handle rate-limit / transient server errors with backoff
            if resp.status_code in (420, 429, 500, 502, 503, 504):
                wait = backoff_sec ** attempt
                time.sleep(wait)
                continue
            resp.raise_for_status()
        except Exception as e:
            last_exc = e
            time.sleep(backoff_sec ** attempt)
    # If we get here, all retries failed
    raise RuntimeError(f"Failed to fetch ESI prices after {retries} attempts") from last_exc


def rows_from_payload(payload: list) -> Iterable[Tuple[int, float, float, str]]:
    now_iso = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    for entry in payload:
        # Some entries may omit average_price; treat as None
        type_id = entry.get("type_id")
        avg = entry.get("average_price", None)
        adj = entry.get("adjusted_price", None)
        if type_id is None or adj is None:
            # Skip malformed rows (adj is expected to exist per ESI)
            continue
        yield int(type_id), (float(avg) if avg is not None else None), float(adj), now_iso


def upsert_prices(conn: sqlite3.Connection, rows: Iterable[Tuple[int, float, float, str]], chunk_size: int = 1000) -> int:
    sql = """
        INSERT INTO AdjustedCostIndexes (typeID, averagePrice, adjustedPrice, updatedAt)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(typeID) DO UPDATE SET
            averagePrice = excluded.averagePrice,
            adjustedPrice = excluded.adjustedPrice,
            updatedAt    = excluded.updatedAt
    """
    cur = conn.cursor()
    count = 0
    batch = []
    for r in rows:
        batch.append(r)
        if len(batch) >= chunk_size:
            cur.executemany(sql, batch)
            count += len(batch)
            batch.clear()
    if batch:
        cur.executemany(sql, batch)
        count += len(batch)
    conn.commit()
    return count


def main():
    parser = argparse.ArgumentParser(description="Import ESI prices into AdjustedCostIndexes (SQLite).")
    parser.add_argument("--db", "--db-path", dest="db_path", default="CostAnalysis.db",
                        help="Path to SQLite database file (default: CostAnalysis.db)")
    args = parser.parse_args()

    try:
        conn = sqlite3.connect(r"../../CostAnalysis.db")
    except Exception as e:
        print(f"Error: could not open database at {r"../../CostAnalysis.db"}: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        ensure_table(conn)
        payload = fetch_prices_with_retries(ESI_URL)
        rows = list(rows_from_payload(payload))
        inserted = upsert_prices(conn, rows)
        print(f"Imported/updated {inserted} rows into AdjustedCostIndexes at {r"../../CostAnalysis.db"}.")
    except Exception as e:
        print(f"Import failed: {e}", file=sys.stderr)
        sys.exit(2)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
