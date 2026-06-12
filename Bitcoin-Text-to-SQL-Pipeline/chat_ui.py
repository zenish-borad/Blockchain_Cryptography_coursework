#!/usr/bin/env python3
"""
chat_ui.py - Web-based Chat UI for Bitcoin Text-to-SQL Pipeline.

Features:
  - Clean white + blue modern chat interface
  - Auto-generates SQL and executes on bitcoin.db
  - Chart generation for numerical results
  - Bitcoin price display
  - LLM rejection for unanswerable questions

Usage:
  pip3 install flask google-genai requests
  export GEMINI_API_KEY=your_key
  python3 chat_ui.py --db /Users/zenishborad/Assignment3/bitcoin.db
  Open browser at http://localhost:5000
"""

import argparse
import os
import re
import sqlite3
import time

import requests
from flask import Flask, jsonify, render_template_string, request
from google import genai
from google.genai import types

app = Flask(__name__)
DB_PATH = None
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

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bitcoin Text-to-SQL</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #f0f4f8;
    height: 100vh;
    display: flex;
    flex-direction: column;
  }
  header {
    background: #ffffff;
    border-bottom: 1px solid #e2e8f0;
    padding: 14px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  }
  .header-left { display: flex; align-items: center; gap: 10px; }
  .logo {
    width: 32px; height: 32px; background: #2563eb;
    border-radius: 8px; display: flex; align-items: center;
    justify-content: center; color: white; font-weight: 700; font-size: 14px;
  }
  header h1 { font-size: 1.05em; font-weight: 600; color: #1e293b; }
  header p { font-size: 0.8em; color: #64748b; }
  .price-badge {
    background: #eff6ff; color: #1d4ed8;
    border: 1px solid #bfdbfe;
    padding: 6px 14px; border-radius: 20px;
    font-weight: 600; font-size: 0.88em;
  }
  #chat-container {
    flex: 1; overflow-y: auto;
    padding: 24px; display: flex;
    flex-direction: column; gap: 16px;
  }
  .message { display: flex; gap: 10px; max-width: 85%; }
  .message.user { align-self: flex-end; flex-direction: row-reverse; }
  .message.bot { align-self: flex-start; }
  .avatar {
    width: 32px; height: 32px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 13px; font-weight: 600; flex-shrink: 0;
  }
  .avatar.bot { background: #dbeafe; color: #1d4ed8; }
  .avatar.user { background: #2563eb; color: white; }
  .bubble {
    padding: 12px 16px; border-radius: 14px;
    font-size: 0.92em; line-height: 1.55;
  }
  .message.user .bubble {
    background: #2563eb; color: white;
    border-bottom-right-radius: 4px;
  }
  .message.bot .bubble {
    background: #ffffff; color: #1e293b;
    border: 1px solid #e2e8f0;
    border-bottom-left-radius: 4px;
  }
  .sql-box {
    background: #f8fafc; border: 1px solid #e2e8f0;
    border-left: 3px solid #2563eb;
    border-radius: 6px; padding: 10px 12px;
    font-family: 'SF Mono', 'Monaco', monospace;
    font-size: 0.82em; color: #334155;
    margin-top: 8px; overflow-x: auto;
    white-space: pre-wrap; word-break: break-all;
  }
  .answer-value {
    font-size: 1.4em; font-weight: 700;
    color: #2563eb; margin-top: 8px;
  }
  table { border-collapse: collapse; width: 100%; margin-top: 10px; font-size: 0.85em; }
  th { background: #eff6ff; color: #1e40af; padding: 7px 10px; text-align: left; font-weight: 600; }
  td { padding: 7px 10px; border-bottom: 1px solid #f1f5f9; color: #334155; }
  tr:last-child td { border-bottom: none; }
  .chart-wrap { margin-top: 12px; max-height: 220px; }
  .reject { color: #dc2626; font-weight: 600; }
  .sql-label {
    font-size: 0.75em; font-weight: 600; color: #64748b;
    text-transform: uppercase; letter-spacing: 0.05em;
    margin-top: 8px;
  }
  .examples {
    display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px;
  }
  .ex-btn {
    background: #f8fafc; border: 1px solid #e2e8f0;
    color: #2563eb; padding: 6px 12px; border-radius: 20px;
    font-size: 0.82em; cursor: pointer; font-weight: 500;
    transition: all 0.15s;
  }
  .ex-btn:hover { background: #eff6ff; border-color: #bfdbfe; }
  .loading { color: #94a3b8; font-style: italic; }
  #input-area {
    padding: 16px 24px; background: #ffffff;
    border-top: 1px solid #e2e8f0;
    display: flex; gap: 10px; align-items: center;
  }
  #question-input {
    flex: 1; padding: 11px 18px; border-radius: 24px;
    border: 1px solid #e2e8f0; background: #f8fafc;
    color: #1e293b; font-size: 0.95em; outline: none;
    transition: border 0.15s;
  }
  #question-input:focus { border-color: #2563eb; background: #fff; }
  #send-btn {
    background: #2563eb; color: white; border: none;
    padding: 11px 22px; border-radius: 24px;
    font-weight: 600; cursor: pointer; font-size: 0.95em;
    transition: background 0.15s;
  }
  #send-btn:hover { background: #1d4ed8; }
</style>
</head>
<body>
<header>
  <div class="header-left">
    <div class="logo">₿</div>
    <div>
      <h1>Bitcoin Text-to-SQL</h1>
      <p>Ask questions about the blockchain in plain English</p>
    </div>
  </div>
  <div class="price-badge" id="price-badge">Loading...</div>
</header>

<div id="chat-container">
  <div class="message bot">
    <div class="avatar bot">₿</div>
    <div class="bubble">
      <strong>Welcome!</strong> Ask me anything about the Bitcoin blockchain database.
      <div class="examples">
        <button class="ex-btn" onclick="ask('How many blocks are there?')">How many blocks?</button>
        <button class="ex-btn" onclick="ask('What is the highest block height?')">Highest block?</button>
        <button class="ex-btn" onclick="ask('How many transactions are there?')">Total transactions?</button>
        <button class="ex-btn" onclick="ask('Which block has the most transactions?')">Busiest block?</button>
        <button class="ex-btn" onclick="ask('What is the largest output value in BTC?')">Largest output?</button>
        <button class="ex-btn" onclick="ask('What is the weather today?')">Weather? (test rejection)</button>
      </div>
    </div>
  </div>
</div>

<div id="input-area">
  <input type="text" id="question-input" placeholder="Ask a question about Bitcoin..."
    onkeypress="if(event.key==='Enter') sendMessage()">
  <button id="send-btn" onclick="sendMessage()">Ask</button>
</div>

<script>
  fetch('/price').then(r=>r.json()).then(d=>{
    document.getElementById('price-badge').textContent = d.price
      ? 'BTC $' + Number(d.price).toLocaleString()
      : 'Price unavailable';
  }).catch(()=>{ document.getElementById('price-badge').textContent = 'Price unavailable'; });

  function ask(q) {
    document.getElementById('question-input').value = q;
    sendMessage();
  }

  function sendMessage() {
    const inp = document.getElementById('question-input');
    const q = inp.value.trim();
    if (!q) return;
    inp.value = '';
    addMsg(q, 'user');
    const lid = 'l' + Date.now();
    addMsg('Thinking...', 'bot', lid, true);
    fetch('/ask', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({question: q})
    }).then(r=>r.json()).then(d=>{
      document.getElementById(lid)?.remove();
      renderBot(d);
    }).catch(e=>{
      document.getElementById(lid)?.remove();
      addMsg('Error: ' + e.message, 'bot');
    });
  }

  function addMsg(text, type, id, loading) {
    const c = document.getElementById('chat-container');
    const wrap = document.createElement('div');
    wrap.className = 'message ' + type;
    if (id) wrap.id = id;
    const av = document.createElement('div');
    av.className = 'avatar ' + type;
    av.textContent = type === 'user' ? 'You' : '₿';
    const bub = document.createElement('div');
    bub.className = 'bubble' + (loading ? ' loading' : '');
    bub.textContent = text;
    wrap.appendChild(av);
    wrap.appendChild(bub);
    c.appendChild(wrap);
    c.scrollTop = c.scrollHeight;
  }

  function renderBot(data) {
    const c = document.getElementById('chat-container');
    const wrap = document.createElement('div');
    wrap.className = 'message bot';
    const av = document.createElement('div');
    av.className = 'avatar bot';
    av.textContent = '₿';
    const bub = document.createElement('div');
    bub.className = 'bubble';

    if (data.cannot_answer) {
      bub.innerHTML = '<span class="reject">This question cannot be answered from the Bitcoin database.</span>';
    } else if (data.error) {
      bub.innerHTML = '<span class="reject">Error: ' + esc(data.error) + '</span>';
    } else {
      let h = '';
      if (data.sql) {
        h += '<div class="sql-label">Generated SQL</div>';
        h += '<div class="sql-box">' + esc(data.sql) + '</div>';
      }
      if (data.rows && data.rows.length > 0) {
        if (data.rows.length === 1 && data.cols.length === 1) {
          h += '<div class="answer-value">' + esc(String(data.rows[0][0])) + '</div>';
        } else {
          h += '<table><tr>' + data.cols.map(c=>'<th>'+esc(c)+'</th>').join('') + '</tr>';
          data.rows.slice(0,10).forEach(row=>{
            h += '<tr>' + row.map(cell=>'<td>'+esc(String(cell))+'</td>').join('') + '</tr>';
          });
          h += '</table>';
          if (data.chart) {
            const cid = 'chart' + Date.now();
            h += '<div class="chart-wrap"><canvas id="' + cid + '"></canvas></div>';
            setTimeout(()=>makeChart(cid, data.chart), 100);
          }
        }
      } else {
        h += '<div style="color:#94a3b8; margin-top:6px; font-size:0.9em;">No results found.</div>';
      }
      bub.innerHTML = h;
    }
    wrap.appendChild(av);
    wrap.appendChild(bub);
    c.appendChild(wrap);
    c.scrollTop = c.scrollHeight;
  }

  function makeChart(id, cd) {
    const el = document.getElementById(id);
    if (!el) return;
    new Chart(el, {
      type: 'bar',
      data: {
        labels: cd.labels,
        datasets: [{
          label: cd.dataset_label,
          data: cd.values,
          backgroundColor: '#bfdbfe',
          borderColor: '#2563eb',
          borderWidth: 1.5,
          borderRadius: 4
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { labels: { color: '#334155', font: { size: 12 } } } },
        scales: {
          x: { ticks: { color: '#64748b' }, grid: { color: '#f1f5f9' } },
          y: { ticks: { color: '#64748b' }, grid: { color: '#f1f5f9' } }
        }
      }
    });
  }

  function esc(t) {
    return String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }
</script>
</body>
</html>
"""

def extract_schema(db_path):
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY type DESC"
    ).fetchall()
    conn.close()
    return "\n".join(r[0].strip() + ";" for r in rows)

def clean_sql(text):
    text = text.strip()
    if "CANNOT_ANSWER" in text.upper():
        return "CANNOT_ANSWER"
    text = re.sub(r"```(?:sql)?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```", "", text).strip()
    text = re.sub(r"^(sqlite|sql|here\s+is.*?:|answer:)\s*", "", text, flags=re.IGNORECASE).strip()
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line.strip().upper().startswith(("SELECT","WITH","INSERT","UPDATE","DELETE","CREATE","DROP")):
            text = "\n".join(lines[i:])
            break
    return text.strip()

def generate_sql(question):
    schema = extract_schema(DB_PATH)
    client = genai.Client()
    resp = client.models.generate_content(
        model=MODEL,
        contents=f"Database schema:\n{schema}\n\nQuestion: {question}\n\nReturn only raw SQLite SQL or CANNOT_ANSWER.",
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0),
    )
    return clean_sql(resp.text)

def run_query(sql):
    uri = f"file:{os.path.abspath(DB_PATH)}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        cur = conn.execute(sql)
        cols = [c[0] for c in cur.description] if cur.description else []
        rows = cur.fetchall()
        return cols, rows, None
    except sqlite3.Error as e:
        return [], [], str(e)
    finally:
        conn.close()

def should_chart(cols, rows):
    if len(rows) < 2 or len(cols) < 2:
        return None
    try:
        labels = [str(r[0]) for r in rows[:10]]
        values = [float(r[1]) for r in rows[:10]]
        return {"labels": labels, "values": values, "dataset_label": cols[1]}
    except (ValueError, TypeError):
        return None

def get_btc_price():
    try:
        resp = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd"}, timeout=5
        )
        return resp.json()["bitcoin"]["usd"]
    except:
        return None

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/price")
def price():
    return jsonify({"price": get_btc_price()})

@app.route("/ask", methods=["POST"])
def ask():
    question = request.json.get("question", "").strip()
    if not question:
        return jsonify({"error": "empty question"})
    try:
        sql = generate_sql(question)
        if sql == "CANNOT_ANSWER":
            return jsonify({"cannot_answer": True})
        cols, rows, err = run_query(sql)
        if err:
            return jsonify({"sql": sql, "error": err})
        return jsonify({
            "sql": sql, "cols": cols,
            "rows": [list(r) for r in rows],
            "chart": should_chart(cols, rows)
        })
    except Exception as e:
        return jsonify({"error": str(e)})

def main():
    global DB_PATH
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--port", type=int, default=5000)
    args = ap.parse_args()
    DB_PATH = args.db
    print(f"Starting Bitcoin Text-to-SQL Chat UI...")
    print(f"Open http://localhost:{args.port} in your browser")
    app.run(debug=False, port=args.port)

if __name__ == "__main__":
    main()
