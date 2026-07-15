# spend-ledger

A tiny local-first expense tracker I built out of boredom — and to be more
financially aware and make wiser spending decisions. No accounts, no cloud,
no dependencies. Your data is a SQLite file on your own machine.

![Python](https://img.shields.io/badge/python-3.8+-blue) ![deps](https://img.shields.io/badge/dependencies-0-brightgreen) ![license](https://img.shields.io/badge/license-MIT-lightgrey)

## Why

I was logging expenses in my phone's notes app. That doesn't scale past
week two. Spreadsheets worked but adding a row shouldn't require opening
Excel. This is the middle ground: a quick-add form, a ledger grouped by
day, and a donut chart that shows exactly where the money goes.

## Features

- **Quick logging** — date, details, amount, category; Enter to submit
- **Interactive category donut** — click a slice to filter the ledger
- **Receipt-style breakdown** — per-category totals and percentage share
- **Month switcher** — browse any past month
- **Auto-archiving** — every completed month is exported to `archives/YYYY-MM.csv`
  (with a total row, opens straight in Excel) each time the app starts
- **Local-first** — data lives in `expenses.db` next to the app; backup = copy one file

## Stack

Python standard library only: `http.server` for the API, `sqlite3` for
storage. Frontend is a single vanilla HTML/CSS/JS file — the chart is
hand-drawn SVG, no chart library. Zero `pip install`.

```
app.py       server + REST API + monthly archiving
ui.html      frontend
expenses.db  created on first run (gitignored)
archives/    monthly CSV exports (gitignored)
```

## Run

```bash
python app.py
```

Opens `http://localhost:8765` in your browser automatically. Ctrl+C to stop —
every entry is saved to disk the moment you add it.

## API

| Method | Endpoint             | Description                          |
|--------|----------------------|--------------------------------------|
| GET    | `/api/expenses`      | All expenses, newest first           |
| POST   | `/api/expenses`      | Add `{date, details, amount, category}` |
| DELETE | `/api/expenses/<id>` | Remove an expense                    |
| POST   | `/api/archive`       | Export completed months to CSV       |

The server binds to `127.0.0.1` only — it is not reachable from other machines.

## License

MIT
