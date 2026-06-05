"""
Text-to-SQL using Google Gemini API
Blockchain Course — HW2 Deliverable 3
Author: Zenish Borad
"""

import os
from google import genai


# -----------------------------------------------------------
# 1. Load the API key from environment variable
# -----------------------------------------------------------
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY not set. Run: export GEMINI_API_KEY='your-key-here'"
    )

client = genai.Client(api_key=api_key)


# -----------------------------------------------------------
# 2. Define the SQL schema we'll be asking questions about
# -----------------------------------------------------------
SCHEMA = """
CREATE TABLE blocks (
    block_height   INTEGER PRIMARY KEY,
    block_hash     TEXT NOT NULL,
    timestamp      INTEGER NOT NULL,
    num_tx         INTEGER NOT NULL,
    size_bytes     INTEGER NOT NULL,
    miner          TEXT
);

CREATE TABLE transactions (
    txid                   TEXT PRIMARY KEY,
    block_height           INTEGER REFERENCES blocks(block_height),
    fee_satoshis           INTEGER NOT NULL,
    num_inputs             INTEGER NOT NULL,
    num_outputs            INTEGER NOT NULL,
    total_output_satoshis  INTEGER NOT NULL
);
"""


# -----------------------------------------------------------
# 3. The text-to-SQL function
# -----------------------------------------------------------
def text_to_sql(question: str, schema: str = SCHEMA) -> str:
    """
    Send a schema + natural language question to Gemini,
    and return the generated SQL query.
    """
    prompt = f"""You are an expert SQL writer. Given the schema below,
generate ONLY the SQL query that answers the user's question.
Do not include explanations, markdown formatting, or backticks.
Output the raw SQL only.

SCHEMA:
{schema}

QUESTION:
{question}

SQL:"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text.strip()


# -----------------------------------------------------------
# 4. Test it with a few blockchain-themed questions
# -----------------------------------------------------------
def main():
    questions = [
        "What is the total number of blocks?",
        "Find the 5 blocks with the most transactions.",
        "What is the average fee per transaction for blocks mined by 'Foundry USA'?",
        "Show the block height and timestamp for blocks larger than 1 MB.",
    ]

    print("=" * 70)
    print("Text-to-SQL using Google Gemini — Blockchain HW2")
    print("=" * 70)

    for q in questions:
        print(f"\nQ: {q}")
        sql = text_to_sql(q)
        print(f"A:\n{sql}")
        print("-" * 70)


if __name__ == "__main__":
    main()
