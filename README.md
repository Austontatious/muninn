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

## Vector Backend

Muninn uses portable brute-force vector search by default.
Optional sqlite-vec acceleration is available with fallback safety:
- `MUNINN_VEC_BACKEND=auto|bruteforce|sqlite_vec`
- `MUNINN_SQLITE_VEC_ENABLED=1|0`
- `MUNINN_SQLITE_VEC_PATH=/path/to/sqlite_vec.(so|dylib|dll)` (optional)

## Design Notes

Muninn’s core idea:
- Keep truth + provenance in a canonical store
- Retrieve candidates via hybrid search
- Inject compact "memory cards" into the agent prompt
- Optionally KV-cache the injected prefix in the inference server (outside Muninn)

See: `ROADMAP.md`
