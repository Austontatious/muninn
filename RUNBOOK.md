# Runbook

## Local dev

- Init DB: `python scripts/init_db.py`
- Run: `./scripts/dev_run.sh`
- Tests: `pytest -q`

## DB location

- Default SQLite file: `./data/muninn.db`
- Config via env: `MUNINN_DB_PATH`

## Common issues

- DB missing: run `init_db.py`
- Port in use: set `MUNINN_PORT`
