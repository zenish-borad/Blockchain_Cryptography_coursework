# Blockchain & Cryptography Coursework

## Blockchain Explorer Foundation (HW2)
Setting up the core tools needed to build an AI-powered Blockchain Explorer.

### Tools
- **Docker** — Containerized a Python solution
- **Bitcoin Core** — Built and ran a Bitcoin node from source
- **AI Text-to-SQL** — Used Gemini API to convert natural language to SQL queries

### Structure
Blockchain-Explorer-Foundation/
├── Dockerfile          # Docker container for Two Sum solution
├── solution.py         # Two Sum algorithm
├── text_to_sql.py      # Gemini AI Text-to-SQL script
├── debug.log           # Bitcoin node sync log
└── blockchaind.png     # Bitcoin RPC commands screenshot

---

## Bitcoin Text-to-SQL Pipeline (HW3)
A full Bitcoin blockchain data pipeline with natural language querying.

### What it does
- Syncs Bitcoin blockchain data from a running bitcoind node into SQLite
- Accepts natural language questions and returns answers from the database
- Uses Gemini AI to convert questions into SQL queries automatically

### Tools
- **Bitcoin Core** — Full node for blockchain data via RPC
- **SQLite** — Stores blocks, transactions, inputs, outputs
- **Gemini API** — Converts natural language to SQL

### Structure
Bitcoin-Text-to-SQL-Pipeline/
├── schema.sql           # SQLite schema for blocks/transactions
├── ingest.py            # Pulls blocks from bitcoind RPC into SQLite
├── text_to_sql.py       # Natural language -> SQL -> answer
├── test_cases.py        # 12 test cases (easy/medium/hard)
├── hard_test_cases.py   # 3 failing cases showing system limits
└── hard_cases_slide.pptx # Slide presenting the 3 hard cases

### Usage
python3 ingest.py --db bitcoin.db --schema schema.sql
python3 text_to_sql.py "how many blocks are there?" --db bitcoin.db
python3 test_cases.py --db bitcoin.db

### Scheduling the ingester (every 5 minutes)
