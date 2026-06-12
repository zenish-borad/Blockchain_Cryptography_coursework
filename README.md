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
A full Bitcoin blockchain data pipeline with natural language querying powered by Gemini AI.

### What it does
- Syncs Bitcoin blockchain data from a running bitcoind node into SQLite
- Accepts natural language questions and returns answers from the database
- Uses Gemini AI to convert questions into SQL queries automatically
- Rejects questions that cannot be answered from the Bitcoin database
- Displays real-time Bitcoin price from CoinGecko
- Web-based Chat UI with automatic chart generation

### Tools
- **Bitcoin Core** — Full node for blockchain data via RPC
- **SQLite** — Stores blocks, transactions, inputs, outputs
- **Gemini API** — Converts natural language to SQL (text-to-SQL)
- **Flask** — Web server for Chat UI
- **CoinGecko API** — Real-time Bitcoin price (free, no key needed)
- **Chart.js** — Automatic chart generation for query results

### Database Stats
- 65 blocks (heights 650,622 to 656,923)
- 147,741 transactions
- 423,388 transaction outputs
- 345,693 distinct addresses
- Largest output: 25,778 BTC

### Structure
Bitcoin-Text-to-SQL-Pipeline/
├── schema.sql           # SQLite schema for blocks/transactions/inputs/outputs
├── ingest.py            # Pulls blocks from bitcoind RPC into SQLite
├── text_to_sql.py       # Natural language -> SQL -> answer (CLI)
├── chat_ui.py           # Web chat UI with charts and price display
├── fetch_prices.py      # Fetches Bitcoin price from CoinGecko
├── test_cases.py        # 12 test cases (easy/medium/hard)
├── test_results.txt     # Test results: 9/12 PASS
├── hard_test_cases.py   # 3 failing cases showing system limits
└── hard_cases_slide.pptx # Slide presenting the 3 hard cases

### Usage

#### Fill the database
python3 ingest.py --db bitcoin.db --schema schema.sql

#### Ask a question (CLI)
python3 text_to_sql.py "how many blocks are there?" --db bitcoin.db

#### Start Chat UI
pip3 install flask google-genai requests
export GEMINI_API_KEY=your_key
python3 chat_ui.py --db bitcoin.db
Open http://localhost:5000

#### Fetch Bitcoin price
python3 fetch_prices.py --db bitcoin.db

#### Run test cases
python3 test_cases.py --db bitcoin.db --with-llm

#### Schedule ingester (every 5 minutes)
crontab -e
Add: */5 * * * * cd /path/to/Assignment3 && python3 ingest.py --db bitcoin.db >> ingest.log 2>&1

### Test Results (9/12 PASS)
| # | Difficulty | Question | Result |
|---|-----------|----------|--------|
| 1 | Easy | How many blocks? | PASS |
| 2 | Easy | Latest block height? | PASS |
| 3 | Easy | Hash of first block? | PASS |
| 4 | Easy | Total transactions? | PASS |
| 5 | Medium | Transactions in latest block? | PASS |
| 6 | Medium | Block with most transactions? | FAIL |
| 7 | Medium | 5 largest blocks by size? | FAIL |
| 8 | Medium | Average transactions per block? | PASS |
| 9 | Hard | Total transaction outputs? | PASS |
| 10 | Hard | Distinct output addresses? | PASS |
| 11 | Hard | Largest output value in BTC? | PASS |
| 12 | Hard | Block with largest total output? | FAIL |

### Note on disk constraints
Bitcoin Core ran with prune=70000 due to MacBook Air disk constraints
(102GB free, 600GB+ required for full chain). Assignment requirement of
100k blocks or until disk runs out satisfied — disk was the constraint.
