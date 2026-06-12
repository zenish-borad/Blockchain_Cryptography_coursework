#!/usr/bin/env python3
"""
fetch_prices.py - Fetch Bitcoin price data from CoinGecko (free, no API key needed)
and store it in the SQLite database.

This enriches the database so you can answer questions like:
"What was the Bitcoin price when block 650000 was mined?"

Usage:
  python3 fetch_prices.py --db /Users/zenishborad/Assignment3/bitcoin.db

Schedule with cron every 5 minutes:
  */5 * * * * python3 /path/to/fetch_prices.py --db /path/to/bitcoin.db
"""

import argparse
import os
import sqlite3
import time
import requests

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"

def create_price_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS btc_prices (
            timestamp   INTEGER PRIMARY KEY,  -- unix epoch seconds
            price_usd   REAL,                 -- BTC price in USD
            fetched_at  INTEGER               -- when we fetched this
        )
    """)
    conn.commit()

def fetch_current_price():
    """Fetch current BTC price from CoinGecko free API (no key needed)."""
    resp = requests.get(COINGECKO_URL, params={
        "ids": "bitcoin",
        "vs_currencies": "usd"
    }, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data["bitcoin"]["usd"]

def store_price(conn, price):
    now = int(time.time())
    conn.execute(
        "INSERT OR REPLACE INTO btc_prices (timestamp, price_usd, fetched_at) VALUES (?,?,?)",
        (now, price, now)
    )
    conn.commit()
    return now

def get_price_at_block(conn, height):
    """Get the closest BTC price to when a block was mined."""
    row = conn.execute(
        "SELECT b.height, b.time, p.price_usd, p.timestamp "
        "FROM blocks b "
        "JOIN btc_prices p ON p.timestamp = ("
        "  SELECT timestamp FROM btc_prices "
        "  ORDER BY ABS(timestamp - b.time) ASC LIMIT 1"
        ") WHERE b.height = ?",
        (height,)
    ).fetchone()
    return row

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    args = ap.parse_args()

    if not os.path.exists(args.db):
        print(f"database not found: {args.db}")
        return

    conn = sqlite3.connect(args.db)
    create_price_table(conn)

    print("Fetching current BTC price from CoinGecko...")
    try:
        price = fetch_current_price()
        ts = store_price(conn, price)
        print(f"Stored: BTC = ${price:,.2f} USD at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))}")
    except Exception as e:
        print(f"Error fetching price: {e}")
        return

    # Show latest price
    row = conn.execute(
        "SELECT price_usd, timestamp FROM btc_prices ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    if row:
        print(f"\nLatest BTC price in DB: ${row[0]:,.2f} USD")

    # Show how many prices stored
    count = conn.execute("SELECT COUNT(*) FROM btc_prices").fetchone()[0]
    print(f"Total price records in DB: {count}")

    conn.close()

if __name__ == "__main__":
    main()
