-- Schema auto-generated using Gemini AI (gemini-2.5-flash).
-- Approach: fed a sample getblock verbosity=2 JSON to Gemini and asked it to
-- "Write code to auto-generate a SQL schema from this JSON object".
-- Output was 99% correct with minor manual adjustments to foreign keys.

-- ============================================================
-- Bitcoin Core  getblock <blockhash> 2  ->  SQLite schema
-- Captures every element returned by getblock at verbosity=2.
-- Normalized into 4 tables: blocks, transactions, tx_inputs, tx_outputs
-- Target: Bitcoin Core v25+ (modern scriptPubKey shape)
-- ============================================================

PRAGMA foreign_keys = ON;

-- ---------- BLOCK-LEVEL FIELDS (same as verbosity=1) ----------
CREATE TABLE IF NOT EXISTS blocks (
    hash              TEXT PRIMARY KEY,        -- block hash
    confirmations     INTEGER,                 -- SNAPSHOT value; changes as chain grows
    height            INTEGER UNIQUE NOT NULL,
    version           INTEGER,
    version_hex       TEXT,                    -- "versionHex"
    merkleroot        TEXT,
    time              INTEGER,                 -- unix epoch seconds
    mediantime        INTEGER,
    nonce             INTEGER,
    bits              TEXT,                    -- hex-encoded difficulty target
    difficulty        REAL,
    chainwork         TEXT,                    -- hex
    n_tx              INTEGER,                 -- "nTx"
    size              INTEGER,
    strippedsize      INTEGER,
    weight            INTEGER,
    previousblockhash TEXT,
    nextblockhash     TEXT                     -- NULL for the chain tip
);

-- ---------- TRANSACTIONS (getrawtransaction format) ----------
CREATE TABLE IF NOT EXISTS transactions (
    txid        TEXT PRIMARY KEY,
    wtxid       TEXT,        -- the tx "hash" field (witness txid; == txid if no witness)
    block_hash  TEXT NOT NULL REFERENCES blocks(hash) ON DELETE CASCADE,
    tx_index    INTEGER,     -- position within the block (0 = coinbase)
    version     INTEGER,
    size        INTEGER,
    vsize       INTEGER,
    weight      INTEGER,
    locktime    INTEGER,
    fee         REAL,        -- BTC; NULL if block undo data unavailable (e.g. pruned)
    hex         TEXT         -- raw serialized tx
);
CREATE INDEX IF NOT EXISTS idx_tx_block ON transactions(block_hash);

-- ---------- INPUTS (vin) ----------
CREATE TABLE IF NOT EXISTS tx_inputs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    txid            TEXT NOT NULL REFERENCES transactions(txid) ON DELETE CASCADE,
    vin_index       INTEGER NOT NULL,   -- order of this input within the tx
    coinbase        TEXT,               -- set ONLY for the coinbase input; else NULL
    prev_txid       TEXT,               -- "txid" of the output being spent (NULL for coinbase)
    prev_vout       INTEGER,            -- "vout" index of the output being spent
    script_sig_asm  TEXT,               -- scriptSig.asm
    script_sig_hex  TEXT,               -- scriptSig.hex
    sequence        INTEGER,
    txinwitness     TEXT,               -- JSON array of witness hex strings (NULL if none)
    UNIQUE(txid, vin_index)
);
CREATE INDEX IF NOT EXISTS idx_vin_txid ON tx_inputs(txid);
CREATE INDEX IF NOT EXISTS idx_vin_prev ON tx_inputs(prev_txid, prev_vout);

-- ---------- OUTPUTS (vout) ----------
CREATE TABLE IF NOT EXISTS tx_outputs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    txid                TEXT NOT NULL REFERENCES transactions(txid) ON DELETE CASCADE,
    n                   INTEGER NOT NULL,   -- vout index
    value               REAL,               -- BTC (see note on satoshis below)
    script_pubkey_asm   TEXT,
    script_pubkey_desc  TEXT,               -- inferred output descriptor
    script_pubkey_hex   TEXT,
    script_pubkey_type  TEXT,               -- pubkeyhash, scripthash, witness_v0_*, nulldata, ...
    address             TEXT,               -- single address (modern Core); NULL if none
    UNIQUE(txid, n)
);
CREATE INDEX IF NOT EXISTS idx_vout_txid ON tx_outputs(txid);
CREATE INDEX IF NOT EXISTS idx_vout_addr ON tx_outputs(address);

-- A bookmark table so the ingester knows where it left off / stays consistent.
CREATE TABLE IF NOT EXISTS sync_state (
    k TEXT PRIMARY KEY,
    v TEXT
);
