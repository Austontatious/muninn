# Muninn

Muninn is a **pluggable memory harness** for LLM agents.

It provides:
- A durable **core memory store** (entities, facts, episodes, preferences)
- An **audit log** for every read/write decision
- A **memory card renderer** to rehydrate retrieved records into compact, structured "conceptual recall"
- A stable **HTTP API** so any orchestrator (ChatGPT, Claude, local agent) can plug in

This repo scaffolds the first working slice:
- SQLite-backed store
- FastAPI service
- Typed schemas and a minimal card pipeline
- Stubs for retrieval backends (vector/hybrid) and provider adapters
- Namespace isolation enforced at the DB/query layer (v0.5.0)

## High-Level Structure

Muninn is organized as a small service with five layers:

1) Ingestion and policy layer
- Receives memory candidates from agents.
- Applies write policy (accept, reject, confirm-required).
- Supports staged confirmation workflow (`stage_candidates` -> `list_pending` -> `confirm_candidates`).

2) Canonical storage layer
- SQLite is the source of truth.
- Core tables: `entities`, `facts`, `episodes`, `preferences`.
- Supporting tables: `embeddings`, `pending_candidates`, `candidate_decisions`, `audit_log`.
- Namespace is enforced in storage/query paths to prevent cross-tenant leakage.

3) Retrieval layer
- Lexical retrieval via FTS5.
- Vector retrieval via caller-provided embeddings.
- Hybrid retrieval via FTS + vectors using RRF fusion.
- Recency fallback fills short result sets.

4) Prompt composition layer
- Retrieved items are transformed into compact memory cards.
- Cards are intended for prompt injection as `<SYSTEM_MEMORY>...</SYSTEM_MEMORY>`.

5) Ops and safety layer
- Read-only kill switch (`MUNINN_READONLY=1`).
- Optional API key middleware.
- Debug endpoints (`/v0/debug/*`) and retention cleanup endpoint (`/v0/admin/cleanup`).
- Migration runner and init scripts keep DBs up to date.

## How It Works End-to-End

Typical user-facing turn:

1) Agent calls `/v0/memory/rehydrate` with current user message and namespace.
2) Muninn retrieves relevant records (FTS/vector/hybrid) and returns cards + raw items.
3) Agent answers user using memory cards in prompt context.
4) Agent proposes candidate memories.
5) Agent calls `/v0/memory/stage_candidates` (preferred) instead of direct write.
6) Muninn writes benign candidates immediately and queues sensitive ones as pending.
7) Agent/user confirms pending items through `/v0/memory/confirm_candidates`.

Trusted internal flows can still call `/v0/memory/write_candidates` directly.

## Repository Map

- `src/muninn/api.py`: FastAPI routes and endpoint wiring
- `src/muninn/models.py`: Pydantic request/response and domain models
- `src/muninn/memory/`: write policy, writeback, pending workflow, retrieval, card rendering
- `src/muninn/vector/`: embedding storage/query, optional sqlite-vec backend, reindex logic
- `src/muninn/ops/`: debug stats and cleanup operations
- `src/muninn/middleware/`: optional API key middleware
- `src/muninn/schema.sql`: source-of-truth DB schema
- `scripts/migrations/`: additive SQL migrations for existing DBs
- `examples/`: local and provider-adapter integration demos
- `docs/`: integration and runbook documentation

## Quickstart

### 1) Create venv + install
```bash
cd /mnt/data/Muninn
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

### 2) Init DB
```bash
python scripts/init_db.py
```

### 3) Run service
```bash
./scripts/dev_run.sh
```

Service: http://127.0.0.1:8000  
Docs: http://127.0.0.1:8000/docs

### Drop-in Local Run (After Install)

Once installed (for example with `pipx install muninn`), one command starts a usable local service:

```bash
muninn up
curl -sS http://127.0.0.1:8000/health
```

`muninn up` handles first-run setup automatically:
- Creates config directory (`~/.config/muninn`) if missing
- Creates data directory (`~/.local/share/muninn`) if missing
- Creates/initializes DB (`~/.local/share/muninn/muninn.db`) and applies migrations
- Starts API on `127.0.0.1:8000` by default
- Prints startup banner with API URL, DB path, namespace default, and readonly state
- Exits with an actionable message if port is already in use

## Demo

```bash
python examples/cli_agent_demo.py
```

Provider adapter demos:
```bash
python examples/local_client_demo.py
python examples/openai_tools_demo.py
python examples/anthropic_tools_demo.py
```

## CLI

Muninn ships a console command:

```bash
muninn --help
muninn status
muninn doctor
muninn up
muninn mcp up
```

- `muninn up` initializes schema/migrations and starts the API server.
- `muninn doctor` runs environment checks and prints PASS/FAIL with fixes.
- `muninn mcp up` starts a local MCP wrapper at `http://127.0.0.1:8765/mcp` by default.

## API (v0)

- `GET /health`
- `GET /v0/memory/version` — lightweight memory hash for namespace/profile
- `POST /v0/memory/write_candidates` — write proposed memory candidates (gated by policy)
- `POST /v0/memory/stage_candidates` — write benign candidates + queue confirm-required ones
- `POST /v0/memory/list_pending` — list staged pending/accepted/rejected/expired candidates
- `POST /v0/memory/confirm_candidates` — accept/reject pending candidates
- `POST /v0/memory/retrieve` — retrieve relevant records for a query/context
- `POST /v0/memory/render_cards` — render retrieved records into memory cards
- `POST /v0/memory/rehydrate` — retrieve + render in one call
- `GET /v0/debug/vector_backend` — inspect effective vector backend (sqlite-vec vs brute-force)
- `GET /v0/debug/stats` — runtime/version/migration/count summary
- `POST /v0/admin/cleanup` — retention cleanup for pending/decisions/audit

## Vector Backend

Muninn uses portable brute-force vector search by default.
Optional sqlite-vec acceleration is available with fallback safety:
- `MUNINN_VEC_BACKEND=auto|bruteforce|sqlite_vec`
- `MUNINN_SQLITE_VEC_ENABLED=1|0`
- `MUNINN_SQLITE_VEC_PATH=/path/to/sqlite_vec.(so|dylib|dll)` (optional)

## Ops Guards

- Read-only kill switch: `MUNINN_READONLY=1`
- Optional API key protection:
  - `MUNINN_REQUIRE_API_KEY=1`
  - `MUNINN_API_KEY=<secret>`
  - `MUNINN_API_KEY_HEADER=X-API-Key` (optional override)

## Design Notes

Muninn’s core idea:
- Keep truth + provenance in a canonical store
- Retrieve candidates via hybrid search
- Inject compact "memory cards" into the agent prompt
- Optionally KV-cache the injected prefix in the inference server (outside Muninn)

See: `ROADMAP.md`
