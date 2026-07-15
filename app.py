#!/usr/bin/env python3
"""
Expense Tracker — local app.

Run:      python app.py            (then visit http://localhost:8765 — opens automatically)
Data:     expenses.db  (SQLite, lives next to this file)
Archives: archives/YYYY-MM.csv  (written automatically for every completed month)

Python 3.8+ standard library only. No pip installs.
"""
import csv
import json
import sqlite3
import threading
import webbrowser
from datetime import date
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "expenses.db"
ARCHIVE_DIR = APP_DIR / "archives"
UI_PATH = APP_DIR / "ui.html"
PORT = 8765

SEED = [
    # Optional: add starter rows here as ("YYYY-MM-DD", "details", amount, "Category")
]


# ---------------------------------------------------------------- database
def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with get_db() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS expenses (
                   id       INTEGER PRIMARY KEY AUTOINCREMENT,
                   date     TEXT NOT NULL,          -- YYYY-MM-DD
                   details  TEXT NOT NULL,
                   amount   REAL NOT NULL CHECK (amount > 0),
                   category TEXT NOT NULL
               )"""
        )
        cols = [r[1] for r in con.execute("PRAGMA table_info(expenses)")]
        if "currency" not in cols:
            con.execute(
                "ALTER TABLE expenses ADD COLUMN currency TEXT NOT NULL DEFAULT 'CAD'"
            )
        if SEED and con.execute("SELECT COUNT(*) FROM expenses").fetchone()[0] == 0:
            con.executemany(
                "INSERT INTO expenses (date, details, amount, category) VALUES (?,?,?,?)",
                SEED,
            )


# ---------------------------------------------------------------- archiving
def archive_completed_months():
    """Write archives/YYYY-MM.csv for every month before the current one."""
    ARCHIVE_DIR.mkdir(exist_ok=True)
    current = date.today().strftime("%Y-%m")
    with get_db() as con:
        months = [
            r[0]
            for r in con.execute(
                "SELECT DISTINCT substr(date,1,7) FROM expenses ORDER BY 1"
            )
        ]
        written = []
        for m in months:
            if m >= current:
                continue  # only completed months
            rows = con.execute(
                "SELECT date, details, amount, category, currency FROM expenses "
                "WHERE substr(date,1,7)=? ORDER BY date, id",
                (m,),
            ).fetchall()
            out = ARCHIVE_DIR / f"{m}.csv"
            with out.open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["Date", "Details", "Amount", "Currency", "Category"])
                for r in rows:
                    w.writerow([r["date"], r["details"], f"{r['amount']:.2f}", r["currency"], r["category"]])
                w.writerow([])
                totals = {}
                for r in rows:
                    totals[r["currency"]] = totals.get(r["currency"], 0) + r["amount"]
                for cur_code, tot in sorted(totals.items()):
                    w.writerow(["", f"Total ({cur_code})", f"{tot:.2f}", cur_code, ""])
            written.append(out.name)
        if written:
            print(f"Archived: {', '.join(written)}  ->  {ARCHIVE_DIR}/")
        return written


# ---------------------------------------------------------------- http server
class Handler(BaseHTTPRequestHandler):
    # ---- helpers
    def send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def log_message(self, fmt, *args):  # quieter console
        pass

    # ---- routes
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send(200, UI_PATH.read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/expenses":
            with get_db() as con:
                rows = [
                    dict(r)
                    for r in con.execute(
                        "SELECT * FROM expenses ORDER BY date DESC, id DESC"
                    )
                ]
            self.send(200, rows)
        else:
            self.send(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/api/expenses":
            try:
                b = self.read_json()
                d, det, amt, cat = (
                    str(b["date"]),
                    str(b["details"]).strip(),
                    round(float(b["amount"]), 2),
                    str(b["category"]),
                )
                cur_code = str(b.get("currency", "CAD")).upper()
                date.fromisoformat(d)  # validates format
                assert det and amt > 0
                assert len(cur_code) == 3 and cur_code.isalpha()
            except Exception:
                self.send(400, {"error": "invalid expense: need date (YYYY-MM-DD), details, amount > 0, category"})
                return
            with get_db() as con:
                cur = con.execute(
                    "INSERT INTO expenses (date, details, amount, category, currency) VALUES (?,?,?,?,?)",
                    (d, det, amt, cat, cur_code),
                )
            self.send(201, {"id": cur.lastrowid, "date": d, "details": det, "amount": amt, "category": cat, "currency": cur_code})
        elif self.path == "/api/archive":
            self.send(200, {"written": archive_completed_months()})
        else:
            self.send(404, {"error": "not found"})

    def do_PUT(self):
        parts = self.path.strip("/").split("/")
        if len(parts) == 3 and parts[:2] == ["api", "expenses"] and parts[2].isdigit():
            try:
                b = self.read_json()
                d, det, amt, cat = (
                    str(b["date"]),
                    str(b["details"]).strip(),
                    round(float(b["amount"]), 2),
                    str(b["category"]),
                )
                cur_code = str(b.get("currency", "CAD")).upper()
                date.fromisoformat(d)
                assert det and amt > 0
                assert len(cur_code) == 3 and cur_code.isalpha()
            except Exception:
                self.send(400, {"error": "invalid expense: need date (YYYY-MM-DD), details, amount > 0, category"})
                return
            with get_db() as con:
                cur = con.execute(
                    "UPDATE expenses SET date=?, details=?, amount=?, category=?, currency=? WHERE id=?",
                    (d, det, amt, cat, cur_code, int(parts[2])),
                )
            if cur.rowcount:
                self.send(200, {"id": int(parts[2]), "date": d, "details": det, "amount": amt, "category": cat, "currency": cur_code})
            else:
                self.send(404, {"error": "no such expense"})
        else:
            self.send(404, {"error": "not found"})

    def do_DELETE(self):
        parts = self.path.strip("/").split("/")
        if len(parts) == 3 and parts[:2] == ["api", "expenses"] and parts[2].isdigit():
            with get_db() as con:
                cur = con.execute("DELETE FROM expenses WHERE id=?", (int(parts[2]),))
            if cur.rowcount:
                self.send(200, {"deleted": int(parts[2])})
            else:
                self.send(404, {"error": "no such expense"})
        else:
            self.send(404, {"error": "not found"})


# ---------------------------------------------------------------- main
def main():
    init_db()
    archive_completed_months()
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"Expense tracker running at {url}   (Ctrl+C to stop)")
    print(f"Database: {DB_PATH}")
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped. Your data is safe in expenses.db")


if __name__ == "__main__":
    main()
