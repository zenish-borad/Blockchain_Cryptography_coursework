#!/usr/bin/env python3
"""
test_cases.py - Task 5: 12 text-to-SQL test cases of varying difficulty.

Run (gold answers only):
  python3 test_cases.py --db /Users/zenishborad/Assignment3/bitcoin.db

Also compare against LLM:
  python3 test_cases.py --db /abs/path.db --with-llm
"""

import argparse
import os
import sqlite3
import sys
import time

TESTS = [
    ("easy", "How many blocks are stored in the database?",
     "SELECT COUNT(*) FROM blocks;"),
    ("easy", "What is the height of the latest block?",
     "SELECT MAX(height) FROM blocks;"),
    ("easy", "What is the hash of the block at the minimum height?",
     "SELECT hash FROM blocks WHERE height = (SELECT MIN(height) FROM blocks);"),
    ("easy", "How many transactions are stored in total?",
     "SELECT COUNT(*) FROM transactions;"),
    ("medium", "How many transactions are in the most recent block?",
     "SELECT n_tx FROM blocks WHERE height = (SELECT MAX(height) FROM blocks);"),
    ("medium", "Which block height has the most transactions?",
     "SELECT height, n_tx FROM blocks ORDER BY n_tx DESC LIMIT 1;"),
    ("medium", "List the 5 largest blocks by size in bytes with their heights.",
     "SELECT height, size FROM blocks ORDER BY size DESC LIMIT 5;"),
    ("medium", "What is the average number of transactions per block?",
     "SELECT AVG(n_tx) FROM blocks;"),
    ("hard", "What is the total number of transaction outputs in the database?",
     "SELECT COUNT(*) FROM tx_outputs;"),
    ("hard", "How many distinct output addresses appear in the database?",
     "SELECT COUNT(DISTINCT address) FROM tx_outputs WHERE address IS NOT NULL;"),
    ("hard", "What is the largest single transaction output value in BTC?",
     "SELECT MAX(value) FROM tx_outputs;"),
    ("hard", "Which block has the largest total output value across all its transactions?",
     "SELECT b.height, SUM(o.value) as total_value FROM tx_outputs o "
     "JOIN transactions t ON o.txid = t.txid "
     "JOIN blocks b ON t.block_hash = b.hash "
     "GROUP BY b.height ORDER BY total_value DESC LIMIT 1;"),
]


def run(db_path, sql):
    uri = f"file:{os.path.abspath(db_path)}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        rows = conn.execute(sql).fetchall()
        return rows, None
    except sqlite3.Error as e:
        return None, str(e)
    finally:
        conn.close()


def fmt(rows):
    if rows is None:
        return None
    if len(rows) == 1 and len(rows[0]) == 1:
        return rows[0][0]
    return rows


def generate_with_retry(gen_sql, q, schema, retries=5, delay=15):
    for attempt in range(retries):
        try:
            return gen_sql(q, schema)
        except Exception as e:
            err = str(e)
            if "503" in err or "UNAVAILABLE" in err or "429" in err or "EXHAUSTED" in err:
                wait = delay * (attempt + 1)
                print(f"  API busy, waiting {wait}s... (attempt {attempt+1}/{retries})")
                time.sleep(wait)
            else:
                raise
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--with-llm", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.db):
        sys.exit(f"database not found: {args.db}")

    gen_sql = None
    schema = None
    if args.with_llm:
        try:
            from text_to_sql import generate_sql, extract_schema
            gen_sql = generate_sql
            schema = extract_schema(args.db)
        except Exception as e:
            sys.exit(f"could not load text_to_sql.py: {e}")

    passed = 0
    failed = 0
    for i, (level, q, gold) in enumerate(TESTS, 1):
        gold_rows, gold_err = run(args.db, gold)
        gold_ans = fmt(gold_rows) if gold_err is None else f"ERROR: {gold_err}"

        print(f"\n=== Test {i} [{level}] ===")
        print(f"Q:    {q}")
        print(f"SQL:  {gold}")
        print(f"ANS:  {gold_ans}")

        if gen_sql:
            # wait 13 seconds between calls to stay under 5/min free tier limit
            if i > 1:
                print("  (waiting 13s for rate limit...)")
                time.sleep(13)

            llm = generate_with_retry(gen_sql, q, schema)
            if llm is None:
                print("LLM: FAILED after retries")
                failed += 1
                continue

            llm_rows, llm_err = run(args.db, llm)
            llm_ans = fmt(llm_rows) if llm_err is None else f"ERROR: {llm_err}"
            ok = (llm_err is None) and (llm_ans == gold_ans)
            if ok:
                passed += 1
            else:
                failed += 1
            print(f"LLM SQL: {llm}")
            print(f"LLM ANS: {llm_ans}")
            print(f"RESULT:  {'✅ PASS' if ok else '❌ FAIL'}")

    if gen_sql:
        total = passed + failed
        print(f"\n==== {passed}/{total} passed ====")


if __name__ == "__main__":
    main()
