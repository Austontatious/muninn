# Runbook

## Local dev

- Init DB (+ migrations): `python scripts/init_db.py`
- Init DB via Makefile (idempotent): `make init-db`
- Init standalone human-memory v1 DB: `PYTHONPATH=src python scripts/init_human_memory_db.py --db ~/.local/share/muninn/human_memory.db`
- Run: `./scripts/dev_run.sh`
- Tests: `pytest -q`
- Install + init in one step: `make install`

## DB location

- Default SQLite file: `~/.local/share/muninn/muninn.db`
- Config via env: `MUNINN_DB_PATH`

## Common issues

- DB missing: run `init_db.py`
- Port in use: set `MUNINN_PORT`

## MCP transport & auth

- Primary transport: Streamable HTTP (`muninn mcp up`) on loopback by default.
- Compatibility transport: STDIO (`muninn mcp stdio`).
- Default bind is safe: `--host 127.0.0.1`.
- Non-loopback binds (e.g. `--host 0.0.0.0`) require auth and are refused otherwise.
- Example non-loopback run:
  - `MUNINN_MCP_REQUIRE_API_KEY=1 MUNINN_MCP_BEARER_TOKEN=<token> muninn mcp up --host 0.0.0.0 --port 8765`
- HTTP MCP auth options:
  - `MUNINN_API_KEY` with `MUNINN_API_KEY_HEADER` (default `X-API-Key`)
  - `MUNINN_MCP_BEARER_TOKEN` via `Authorization: Bearer <token>`
- Slash alias controls (temporary migration window):
  - `MUNINN_MCP_ENABLE_SLASH_ALIASES=1|0` (default `1`)
  - `MUNINN_MCP_SUPPRESS_ALIAS_WARNINGS=1|0` (default `1`)
- Soft write-rate limiter for `muninn.cards.upsert`:
  - `MUNINN_MCP_CARD_WRITE_LIMIT_PER_HOUR` (default `20`, set `0` to disable)
  - `MUNINN_MCP_CARD_WRITE_WINDOW_SECONDS` (default `3600`)
- Adaptation memory contracts:
  - `docs/laila_adaptation_memory.md`
  - `docs/query_contracts.md`

## Telemetry rotation and inspection

- MCP/CLI structured telemetry sink:
  - `MUNINN_MCP_TELEMETRY_PATH` (example: `~/.local/share/muninn/mcp_telemetry.jsonl`)
- Rotation policy (size-based):
  - `MUNINN_MCP_TELEMETRY_MAX_BYTES` (default `5242880`)
  - `MUNINN_MCP_TELEMETRY_BACKUP_COUNT` (default `5`)
- Flush behavior:
  - `MUNINN_MCP_TELEMETRY_FLUSH=1` for immediate write-through
- Failure handling:
  - telemetry init/write errors emit visible warnings and fall back to console/journal events.

Quick checks:
- `ls -lh ~/.local/share/muninn/mcp_telemetry.jsonl*`
- `tail -n 20 ~/.local/share/muninn/mcp_telemetry.jsonl`
- `rg -n '\"event\":\"(request_ingress|space_resolution|rehydration_stage|tool_call|tool_error|cli_command|api_startup|human_memory_)\"' ~/.local/share/muninn/mcp_telemetry.jsonl`

## Policy inspection CLI (read-only)

- List policy cards by canonical space:
  - `muninn policy list --cwd /path/to/repo --limit 20 --json`
- Show one policy card:
  - `muninn policy show <card_id> --json`
- List recent interaction events:
  - `muninn policy events --cwd /path/to/repo --limit 50 --json`
- Optional filters:
  - `--space-key <space>`
  - `--promoted all|promoted|unpromoted`
  - `--event-type policy_signal`
  - `--query`, `--tool-name`, `--task-type` (policy list)

## Continuous availability (systemd user)

- Core services should be enabled with restart policy:
  - `systemctl --user enable --now muninn-api.service muninn-mcp.service`
  - `systemctl --user status muninn-api.service muninn-mcp.service`
- Ensure user lingering is enabled for reboot persistence:
  - `loginctl show-user \"$USER\" -p Linger`
- Optional auto-restart on local code/config changes can be implemented with a user timer that watches Muninn source/config signatures and restarts both services when changed.

## VS Code memory usage smoke (10 minutes)

1) Start MCP service:
- `muninn mcp up --host 127.0.0.1 --port 8765`

2) Verify connectivity:
- Call `muninn.system.ping` from any MCP client (or confirm startup + request logs).

3) Open your repo in VS Code and confirm Codex config:
- `~/.codex/config.toml` contains:
  - `[mcp_servers.muninn]`
  - `url = "http://127.0.0.1:8765/mcp"`
  - `enabled = true`

4) Run a prompt that forces memory reads and writeback:
- Example:
  - `Before you start, load recent decisions and constraints from Muninn and summarize them in 5 bullets, then implement X.`

5) Pass criteria in MCP logs (order matters):
- `muninn.spaces.resolve`
- `muninn.cards.recent` with `scope="strict"`
- `muninn.cards.search` with `scope="soft"`
- Later: `muninn.cards.upsert` (typically 1-3 calls)

If this sequence appears in one real task run, Codex memory usage is validated.

## Codex instruction discovery

- Keep `AGENTS.md` at repo root (`/mnt/data/Muninn/AGENTS.md`) so repo-scoped instructions are discoverable.
- If a client surface ignores repo instructions, mirror a minimal memory-contract snippet in that surface's global Codex instructions/config and reload the client session.

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

## Meaningful memory ops notes (v0.11)

- Evidence lifecycle is tracked in `evidence_state`:
  - `captured`
  - `candidate`
  - `promoted`
- Each `POST /retrieve` now:
  - Updates `signals` counters and `coaccess_edges`.
  - Runs deterministic implicit-promotion triggers.
  - Writes audit events (`cardex_retrieve`, `cardex_promotion_trigger` when triggered).
- Manual promotion endpoint:
  - `POST /promote`
  - `mode=propose` (default) keeps write-gating.
  - `mode=trusted` may auto-confirm, but sensitive evidence is downgraded to proposal mode.
- Indexing hooks are queue-only in v0.11:
  - `index_jobs` rows are enqueued for `cards.active` and promoted evidence.
  - No required vector backend coupling for this stage.

## Debug stats

Endpoint:
- `GET /v0/debug/stats`
- Optional namespace scope: `GET /v0/debug/stats?namespace=lexi`

Returns app/api versions, safe config summary, migration status, and table counts.
