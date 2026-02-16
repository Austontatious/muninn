# Runbook

## Local dev

- Init DB (+ migrations): `python scripts/init_db.py`
- Run: `./scripts/dev_run.sh`
- Tests: `pytest -q`

## DB location

- Default SQLite file: `./data/muninn.db`
- Config via env: `MUNINN_DB_PATH`

## Common issues

- DB missing: run `init_db.py`
- Port in use: set `MUNINN_PORT`

## Read-only mode

Set Muninn to write-blocking mode:
- `MUNINN_READONLY=1`

Behavior:
- Write/admin endpoints return `503` (`Muninn is in read-only mode`)
- Read endpoints continue to function

## API key protection (optional)

Disabled by default. Enable with:
- `MUNINN_REQUIRE_API_KEY=1`
- `MUNINN_API_KEY=<secret>`
- Optional header override: `MUNINN_API_KEY_HEADER=X-API-Key`

Allowlisted paths without key:
- `/health`
- `/docs`
- `/openapi.json`
- `/redoc`

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

## Admin reindex

Rebuild sqlite-vec index rows from canonical embeddings:

```bash
curl -X POST http://127.0.0.1:8000/v0/admin/reindex_vectors \
  -H 'content-type: application/json' \
  -d '{"namespace":"default","force_backend":"auto"}'
```

Notes:
- Endpoint is under `/v0/admin/*`; protect it with network/auth controls in production.
- If sqlite-vec is unavailable, response reports `backend_used=bruteforce` without failing.

## Admin cleanup

Endpoint:
- `POST /v0/admin/cleanup`

Example:
```bash
curl -X POST http://127.0.0.1:8000/v0/admin/cleanup \
  -H 'content-type: application/json' \
  -d '{"namespace":"default","targets":["pending","decisions","audit"],"dry_run":true}'
```

Retention defaults:
- `MUNINN_PENDING_RETENTION_DAYS=14`
- `MUNINN_AUDIT_RETENTION_DAYS=30`
- `MUNINN_CLEANUP_BATCH_LIMIT=2000`

For pending cleanup without explicit statuses, default statuses are:
- `accepted`
- `rejected`
- `expired`

`pending` status is preserved unless explicitly included in `statuses`.

## Confirm-required workflow ops notes

- Pending rows are durable in `pending_candidates` and namespace-scoped.
- `stage_candidates` can set `ttl_seconds`; expired rows transition to `expired` on list/confirm.
- Use `/v0/admin/cleanup` for retention pruning of pending/decision/audit rows.

## Debug stats

Endpoint:
- `GET /v0/debug/stats`
- Optional namespace scope: `GET /v0/debug/stats?namespace=lexi`

Returns app/api versions, safe config summary, migration status, and table counts.
