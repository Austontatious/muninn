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

## Vector acceleration

Optional sqlite-vec acceleration can be toggled via env:
- `MUNINN_VEC_BACKEND=auto|bruteforce|sqlite_vec`
- `MUNINN_SQLITE_VEC_ENABLED=1|0`
- `MUNINN_SQLITE_VEC_PATH=/path/to/sqlite_vec.(so|dylib|dll)` (optional)

Debug current backend:
- `curl http://127.0.0.1:8000/v0/debug/vector_backend`

Troubleshooting:
- If `sqlite_vec_loaded=false`, Muninn automatically falls back to brute-force vector search.
- On macOS, extension loading may be disabled in system Python/SQLite builds.
