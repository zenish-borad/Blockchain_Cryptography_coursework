#!/usr/bin/env python3
"""
ingest.py - Keep a SQLite DB in sync with a running bitcoind node.
Handles pruned nodes automatically by starting from pruneheight.

Usage:
  python3 ingest.py --db /absolute/path/bitcoin.db --schema schema.sql
"""

import argparse
import json
import os
import sqlite3
import time
import requests

REORG_DEPTH = 10
RPC_TIMEOUT = 120

class RPC:
    def __init__(self, url, user, pw):
        self.url = url
        self.auth = (user, pw)
        self.session = requests.Session()

    def call(self, method, params=None):
        payload = {"jsonrpc": "1.0", "id": "hw3", "method": method,
                   "params": params or []}
        r = self.session.post(self.url, json=payload, auth=self.auth,
                              timeout=RPC_TIMEOUT)
        r.raise_for_status()
        out = r.json()
        if out.get("error"):
            raise RuntimeError(f"RPC {method} error: {out['error']}")
        return out["result"]

def open_db(path, schema_path):
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    if schema_path and os.path.exists(schema_path):
        with open(schema_path) as f:
            conn.executescript(f.read())
    return conn

def db_tip_height(conn):
    row = conn.execute("SELECT MAX(height) FROM blocks").fetchone()
    return row[0] if row and row[0] is not None else -1

def stored_hash_at(conn, height):
    row = conn.execute("SELECT hash FROM blocks WHERE height = ?",
                       (height,)).fetchone()
    return row[0] if row else None

def ingest_block(conn, block):
    h = block["hash"]
    height = block["height"]
    tx_rows, vin_rows, vout_rows = [], [], []

    for idx, tx in enumerate(block["tx"]):
        txid = tx["txid"]
        tx_rows.append((
            txid, tx.get("hash"), h, idx, tx.get("version"),
            tx.get("size"), tx.get("vsize"), tx.get("weight"),
            tx.get("locktime"), tx.get("fee"), tx.get("hex"),
        ))
        for vi, vin in enumerate(tx.get("vin", [])):
            ss = vin.get("scriptSig", {})
            witness = vin.get("txinwitness")
            vin_rows.append((
                txid, vi, vin.get("coinbase"),
                vin.get("txid"), vin.get("vout"),
                ss.get("asm"), ss.get("hex"),
                vin.get("sequence"),
                json.dumps(witness) if witness is not None else None,
            ))
        for vout in tx.get("vout", []):
            spk = vout.get("scriptPubKey", {})
            addr = spk.get("address")
            if addr is None and spk.get("addresses"):
                addr = spk["addresses"][0]
            vout_rows.append((
                txid, vout.get("n"), vout.get("value"),
                spk.get("asm"), spk.get("desc"), spk.get("hex"),
                spk.get("type"), addr,
            ))

    block_row = (
        h, block.get("confirmations"), height, block.get("version"),
        block.get("versionHex"), block.get("merkleroot"), block.get("time"),
        block.get("mediantime"), block.get("nonce"), block.get("bits"),
        block.get("difficulty"), block.get("chainwork"), block.get("nTx"),
        block.get("size"), block.get("strippedsize"), block.get("weight"),
        block.get("previousblockhash"), block.get("nextblockhash"),
    )

    with conn:
        conn.execute("DELETE FROM blocks WHERE height = ? OR hash = ?", (height, h))
        conn.execute(
            "INSERT INTO blocks (hash, confirmations, height, version, version_hex,"
            " merkleroot, time, mediantime, nonce, bits, difficulty, chainwork,"
            " n_tx, size, strippedsize, weight, previousblockhash, nextblockhash)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", block_row)
        conn.executemany(
            "INSERT INTO transactions (txid, wtxid, block_hash, tx_index, version,"
            " size, vsize, weight, locktime, fee, hex)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)", tx_rows)
        conn.executemany(
            "INSERT INTO tx_inputs (txid, vin_index, coinbase, prev_txid, prev_vout,"
            " script_sig_asm, script_sig_hex, sequence, txinwitness)"
            " VALUES (?,?,?,?,?,?,?,?,?)", vin_rows)
        conn.executemany(
            "INSERT INTO tx_outputs (txid, n, value, script_pubkey_asm,"
            " script_pubkey_desc, script_pubkey_hex, script_pubkey_type, address)"
            " VALUES (?,?,?,?,?,?,?,?)", vout_rows)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--schema", default="schema.sql")
    ap.add_argument("--rpc-url", default=os.environ.get("BITCOIN_RPC_URL", "http://127.0.0.1:8332"))
    ap.add_argument("--rpc-user", default=os.environ.get("BITCOIN_RPC_USER", "zenish"))
    ap.add_argument("--rpc-pass", default=os.environ.get("BITCOIN_RPC_PASS", "login@123"))
    ap.add_argument("--max-blocks", type=int, default=0)
    args = ap.parse_args()

    lock_path = args.db + ".lock"
    lock_fd = open(lock_path, "w")
    try:
        import fcntl
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (ImportError, OSError):
        print("another ingest run is in progress; exiting.")
        return

    rpc = RPC(args.rpc_url, args.rpc_user, args.rpc_pass)
    conn = open_db(args.db, args.schema)

    # get chain info - handles pruned nodes
    chain_info = rpc.call("getblockchaininfo")
    node_height = chain_info["blocks"]
    prune_height = chain_info.get("pruneheight", 0)
    db_height = db_tip_height(conn)

    # always start from pruneheight so we never request deleted blocks
    if db_height == -1:
        start = prune_height
    else:
        start = max(prune_height, db_height - REORG_DEPTH)

    print(f"node tip={node_height}  pruneheight={prune_height}  db tip={db_height}  starting at {start}")

    done = 0
    for height in range(start, node_height + 1):
        node_hash = rpc.call("getblockhash", [height])
        if stored_hash_at(conn, height) == node_hash:
            continue
        try:
            block = rpc.call("getblock", [node_hash, 2])
        except RuntimeError as e:
            print(f"  skipping block {height}: {e}")
            continue
        ingest_block(conn, block)
        done += 1
        if done % 100 == 0:
            print(f"  ...ingested up to height {height} ({done} blocks written)")
        if args.max_blocks and done >= args.max_blocks:
            print(f"hit --max-blocks={args.max_blocks}, stopping at {height}")
            break

    with conn:
        conn.execute("INSERT OR REPLACE INTO sync_state (k,v) VALUES ('last_height',?)",
                     (str(db_tip_height(conn)),))
        conn.execute("INSERT OR REPLACE INTO sync_state (k,v) VALUES ('last_run_ts',?)",
                     (str(int(time.time())),))

    print(f"done. wrote {done} block(s). db tip now {db_tip_height(conn)}")
    conn.close()

if __name__ == "__main__":
    main()
