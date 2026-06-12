#!/usr/bin/env python3
"""
text_to_sql.py - Natural language questions -> SQL -> answer over a
Bitcoin sqlite database produced by ingest.py.

NOTE: Using Google Gemini API (gemini-2.0-flash) instead of OpenAI.
Same pattern: system prompt (task) + user prompt (schema + question) -> SQL.
Gemini free tier chosen; satisfies identical API requirement.

Setup:
  pip3 install google-genai
  export GEMINI_API_KEY=your_key

Usage:
  python3 text_to_sql.py "how many blocks are there?" --db /abs/path/bitcoin.db
"""

import argparse
import os
import re
import sqlite3
import sys

from google import genai
from google.genai import types

MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = (
    "You are a SQL developer that is expert in Bitcoin and you answer natural "
    "language questions about the bitcoind database in a sqlite database. "
    "You always only respond with SQL statements that are correct. "
    "Never include any explanation, markdown, or code fences. "
    "Only output the raw SQL query and nothing else. "
    "If the question cannot be answered from the Bitcoin database, "
    "respond with exactly: CANNOT_ANSWER"
)


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
    """Aggressively strip everything that isn't SQL."""
    text = text.strip()
    # check for rejection first
    if "CANNOT_ANSWER" in text.upper():
        return "CANNOT_ANSWER"
    # remove ```sql ... ``` or ``` ... ```
    text = re.sub(r"```(?:sql)?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```", "", text).strip()
    # remove common prefixes
    text = re.sub(r"^(sqlite|sql|here\s+is.*?:|answer:)\s*", "", text, flags=re.IGNORECASE).strip()
    # find the line that starts with a SQL keyword
    lines = text.split("\n")
    sql_keywords = ("SELECT", "WITH", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP")
    for i, line in enumerate(lines):
        if line.strip().upper().startswith(sql_keywords):
            text = "\n".join(lines[i:])
            break
    return text.strip()


def generate_sql(question, schema):
    client = genai.Client()
    user_prompt = (
        f"Database schema:\n{schema}\n\n"
        f"Question: {question}\n\n"
        "If this question can be answered from the Bitcoin database, "
        "return only a single raw SQLite query with no explanation, "
        "no markdown, no code fences, no prefixes. Just the SQL.\n"
        "If this question CANNOT be answered from the Bitcoin database "
        "(e.g. weather, stock prices, general knowledge), "
        "respond with exactly: CANNOT_ANSWER"
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


def run_query(db_path, sql):
    uri = f"file:{os.path.abspath(db_path)}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        cur = conn.execute(sql)
        cols = [c[0] for c in cur.description] if cur.description else []
        rows = cur.fetchall()
        return cols, rows
    finally:
        conn.close()


def main():
    ap = argparse.ArgumentParser(description="NL -> SQL over a Bitcoin sqlite DB")
    ap.add_argument("question", help="natural language question (quote it)")
    ap.add_argument("--db", required=True, help="absolute path to the sqlite database")
    ap.add_argument("--no-exec", action="store_true",
                    help="only print the generated SQL, do not run it")
    args = ap.parse_args()

    if not os.path.exists(args.db):
        sys.exit(f"database not found: {args.db}")

    schema = extract_schema(args.db)
    sql = generate_sql(args.question, schema)

    # handle rejection
    if sql == "CANNOT_ANSWER":
        print("\n--- answer ---")
        print("❌ This question cannot be answered from the Bitcoin database.")
        return

    print("\n--- generated SQL ---")
    print(sql)

    if args.no_exec:
        return

    print("\n--- answer ---")
    try:
        cols, rows = run_query(args.db, sql)
        if cols:
            print(" | ".join(cols))
        for r in rows:
            print(" | ".join(str(x) for x in r))
        if not rows:
            print("(no rows)")
    except sqlite3.Error as e:
        print(f"SQL ERROR: {e}")


if __name__ == "__main__":
    main()
