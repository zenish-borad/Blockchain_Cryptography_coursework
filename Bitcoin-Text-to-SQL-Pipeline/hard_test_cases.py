#!/usr/bin/env python3
"""
hard_test_cases.py - Task 6: Three test cases that break the text-to-SQL system.

Each case is a 5-tuple:
  1. natural language question
  2. expected correct SQL
  3. expected correct answer (from running correct SQL)
  4. incorrect SQL that the system generates
  5. incorrect answer (from running wrong SQL)

Run:
  python3 hard_test_cases.py --db /Users/zenishborad/Assignment3/bitcoin.db
"""

import argparse
import os
import sqlite3

# NOTE: Using Google Gemini API instead of OpenAI (same pattern, free tier)
from google import genai
from google.genai import types
import re

MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = (
    "You are a SQL developer that is expert in Bitcoin and you answer natural "
    "language questions about the bitcoind database in a sqlite database. "
    "You always only respond with SQL statements that are correct."
)

# -----------------------------------------------------------------------
# The 3 hard test cases
# Each: (question, correct_sql, explanation_of_why_llm_fails)
# -----------------------------------------------------------------------
HARD_CASES = [
    (
        # HARD CASE 1: Requires understanding of Bitcoin coinbase transactions
        # and self-join logic across 4 tables
        "Which address received the most total bitcoin across all coinbase "
        "transactions (miner rewards) in the database?",

        # CORRECT SQL - requires identifying coinbase txs via tx_inputs.coinbase
        # then joining to outputs to find the receiving address
        """
SELECT o.address, SUM(o.value) as total_received
FROM tx_outputs o
JOIN transactions t ON o.txid = t.txid
JOIN tx_inputs i ON i.txid = t.txid
WHERE i.coinbase IS NOT NULL
  AND o.address IS NOT NULL
GROUP BY o.address
ORDER BY total_received DESC
LIMIT 1;
        """.strip(),

        # WHY LLM FAILS: The LLM confuses coinbase detection. It often writes
        # WHERE t.tx_index = 0 (which is correct for coinbase position) but
        # misses that it should join tx_inputs to check the coinbase field.
        # Or it joins incorrectly causing row multiplication and wrong SUM.
    ),
    (
        # HARD CASE 2: Requires window functions / self-join for consecutive blocks
        # Finding the longest streak of blocks with increasing transaction counts
        "Find the longest consecutive sequence of blocks where each block has "
        "more transactions than the previous block.",

        # CORRECT SQL - requires window functions (LAG) which SQLite supports
        # but LLMs rarely generate correctly for this kind of streak detection
        """
WITH diffs AS (
  SELECT height, n_tx,
         CASE WHEN n_tx > LAG(n_tx) OVER (ORDER BY height)
              THEN 1 ELSE 0 END as increasing
  FROM blocks
),
groups AS (
  SELECT height, n_tx, increasing,
         height - ROW_NUMBER() OVER (PARTITION BY increasing ORDER BY height) as grp
  FROM diffs
  WHERE increasing = 1
),
streaks AS (
  SELECT grp, COUNT(*) as streak_len,
         MIN(height) as start_height,
         MAX(height) as end_height
  FROM groups
  GROUP BY grp
)
SELECT start_height, end_height, streak_len
FROM streaks
ORDER BY streak_len DESC
LIMIT 1;
        """.strip(),

        # WHY LLM FAILS: This requires understanding gap-and-islands SQL pattern.
        # LLMs typically generate a simple self-join that only finds pairs, not
        # the full streak length. Window functions + grouping tricks are rarely
        # generated correctly.
    ),
    (
        # HARD CASE 3: Requires multi-hop graph traversal
        # Bitcoin UTXO chain tracing - which is not possible in pure SQL without
        # recursive CTEs, and even then LLMs get the logic wrong
        "Find all transactions that directly spent an output from the first "
        "transaction in block 622000, and show the total value they moved.",

        # CORRECT SQL - requires finding the first tx in a specific block,
        # then finding all txs that spent its outputs via tx_inputs.prev_txid
        """
WITH first_tx AS (
  SELECT t.txid
  FROM transactions t
  JOIN blocks b ON t.block_hash = b.hash
  WHERE b.height = 622000
  ORDER BY t.tx_index ASC
  LIMIT 1
),
spending_txs AS (
  SELECT DISTINCT i.txid as spending_txid
  FROM tx_inputs i
  JOIN first_tx f ON i.prev_txid = f.txid
)
SELECT s.spending_txid, SUM(o.value) as total_value_moved
FROM spending_txs s
JOIN tx_outputs o ON o.txid = s.spending_txid
GROUP BY s.spending_txid
ORDER BY total_value_moved DESC;
        """.strip(),

        # WHY LLM FAILS: LLMs struggle with the two-hop join logic:
        # block -> first tx -> inputs of OTHER txs that reference it.
        # They often join in the wrong direction (outputs instead of inputs)
        # or miss the prev_txid/prev_vout linkage entirely.
    ),
]


def extract_schema(db_path):
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT sql FROM sqlite_master "
        "WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' "
        "ORDER BY type DESC"
    ).fetchall()
    conn.close()
    return "\n".join(r[0].strip() + ";" for r in rows)


def clean_sql(text):
    text = text.strip()
    text = re.sub(r"^```(?:sql)?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text).strip()
    return text


def generate_sql(question, schema):
    client = genai.Client()
    user_prompt = (
        f"Database schema:\n{schema}\n\n"
        f"Question: {question}\n\n"
        "Return only a single SQLite query that answers the question."
    )
    resp = client.models.generate_content(
        model=MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0,
        ),
    )
    return clean_sql(resp.text)


def run_sql(db_path, sql):
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
    return rows[:3]  # show first 3 rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    args = ap.parse_args()

    if not os.path.exists(args.db):
        print(f"database not found: {args.db}")
        return

    schema = extract_schema(args.db)

    print("=" * 70)
    print("TASK 6: THREE HARD TEST CASES THAT BREAK THE SYSTEM")
    print("=" * 70)

    for i, (question, correct_sql, _) in enumerate(HARD_CASES, 1):
        print(f"\n{'='*70}")
        print(f"HARD CASE {i}")
        print(f"{'='*70}")
        print(f"\nQUESTION:\n  {question}")

        # run correct SQL
        correct_rows, correct_err = run_sql(args.db, correct_sql)
        correct_ans = fmt(correct_rows) if correct_err is None else f"ERROR: {correct_err}"
        print(f"\nCORRECT SQL:\n{correct_sql}")
        print(f"\nCORRECT ANSWER:\n  {correct_ans}")

        # run LLM
        print(f"\nGenerating LLM SQL...")
        llm_sql = generate_sql(question, schema)
        llm_rows, llm_err = run_sql(args.db, llm_sql)
        llm_ans = fmt(llm_rows) if llm_err is None else f"ERROR: {llm_err}"
        print(f"\nLLM SQL:\n{llm_sql}")
        print(f"\nLLM ANSWER:\n  {llm_ans}")

        match = (correct_err is None and llm_err is None and llm_ans == correct_ans)
        print(f"\nRESULT: {'PASS (not hard enough!)' if match else 'FAIL (as expected)'}")

    print(f"\n{'='*70}")
    print("Done. Use these results for your slide.")
    print("="*70)


if __name__ == "__main__":
    main()
