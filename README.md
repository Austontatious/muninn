# Muninn

> Current status (2026-05-28): Muninn v1 remains the live Codex/MCP memory
> path. Muninn v2 is adjacent, opt-in substrate work with a personal/local
> read-only Phase J trial in this repo only. Current operating truth is in
> `AGENTS.md`, `ARCHITECTURE_CHECKPOINT.md`, and `RUNBOOK.md`.

Muninn is a **pluggable memory harness** for LLM agents.

It provides:
- A durable **core memory store** (entities, facts, episodes, preferences)
- An **audit log** for every read/write decision
- A **memory card renderer** to rehydrate retrieved records into compact, structured "conceptual recall"
- A stable **HTTP API** so any orchestrator (ChatGPT, Claude, local agent) can plug in

The current repository includes:
- SQLite-backed store
- FastAPI service
- Typed schemas and a minimal card pipeline
- retrieval backends, vector safety fallback paths, and provider adapters
- Namespace isolation enforced at the DB/query layer (v0.5.0)
- human-memory MCP tools and deterministic rehydration
- adjacent v2 shadow/pilot tooling under `src/muninn/v2`

## Canonical References

- `AGENTS.md`: repo policy for agents and current v1/v2 posture.
- `ARCHITECTURE_CHECKPOINT.md`: concise current architecture truth.
- `RUNBOOK.md`: local operations, MCP, systemd, and Phase J trial procedures.
- `docs/CODEX_STANDARDS.md`: repo-local standards contract and validation commands.
- `docs/README.md`: documentation map for current, historical, and generated evidence docs.
- `reports/README.md`: generated report and pilot-evidence index.

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

5) Meaningful-memory layer
- Captured evidence is tracked as `captured | candidate | promoted`.
- `/retrieve` updates access signals (`signals`, `coaccess_edges`) and can auto-propose promotions deterministically.
- `/promote` creates write-gated promotion proposals (or trusted auto-confirm where allowed).
- Index hooks enqueue `index_jobs` for `cards.active` and promoted evidence.

6) Ops and safety layer
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

## The Muninn Memory Discipline

Muninn provides a durable, scoped memory substrate. It does not enforce behavior. It enables it.

Agents integrating with Muninn should follow a consistent memory discipline so long-term memory remains high-signal, sparse, and reliable.

### 1) Read Before Acting

Before generating substantial output, an agent should:
- Resolve the active space (repo / cwd / global).
- Load recent durable cards (for example: decisions, constraints, runbooks).
- Search memory for task-relevant prior knowledge.

Long-term memory should inform reasoning before new decisions are made.

### 2) Persist Only Durable Knowledge

Write to memory only when knowledge is expected to remain useful beyond the current session.

Examples of durable knowledge:
- Finalized design decisions
- Discovered invariants or constraints
- Root causes of defects
- Stable interface contracts
- Reusable operational runbooks

Do not persist:
- Draft reasoning
- Exploratory thoughts
- Transient discussion
- Partial solutions

### 3) Write at Stable Boundaries

Memory writes should occur at natural completion points:
- After a feature is completed
- After a bug is resolved
- After an interface contract is defined
- After a workflow stabilizes

Avoid mid-task writes.

### 4) Keep Cards Atomic

Each card should represent one durable concept.

The summary must:
- Stand alone
- Be understandable without conversation context
- Describe a single decision, constraint, or reusable idea

The body may include additional detail, evidence references, or rationale.

### 5) Prefer Superseding Over Duplicating

When prior memory exists:
- Update or supersede the existing card.
- Avoid creating parallel or conflicting truths.

Memory should converge, not fragment.

### 6) Scope Memory Deliberately

Default retrieval scope should be strict (current space only).

Soft scope (including global space) may be used when work spans multiple projects.

Cross-space writes should be intentional.

Muninn does not enforce this discipline. It provides the primitives required to implement it.

Agents that adopt a consistent memory discipline produce memory that compounds in value over time.

## Human-Memory Model

Muninn now separates four concerns explicitly in the local human-memory layer:

- `cards`: durable factual/project memory such as decisions, constraints, interfaces, and runbooks
- `evidence`: auditable support such as files, diffs, commits, tests, logs, URLs, and user messages
- `policy-state`: scoped behavioral guidance such as directives, preferences, anti-patterns, and tooling heuristics
- `interaction_events`: raw evaluative/directive traces that can later promote into policy-state

Canonical project identity prefers repo-root remote identity when available:

- git repo with remote: `repo:<sha(remote_norm)>`
- git repo without remote: `path:<sha(repo_root)>`
- non-git path: `path:<sha(abs_cwd)>`

Legacy `path:*` and `cwd:*` keys are preserved as aliases so old memories remain retrievable while the canonical key settles.

## Sample AGENTS.md Section

The following section is intentionally concise and operational for repo-root `AGENTS.md` files:

```text
Muninn Memory Protocol

This repository integrates with Muninn (MCP memory service).

Follow this protocol:

On Task Start

Call muninn.spaces.resolve with current cwd.

Call muninn.cards.recent with:

scope: strict

kinds: decision, constraint, runbook, interface

Call muninn.cards.search with:

scope: soft

query: short, concrete noun-heavy summary of the task

Use retrieved cards to inform reasoning before making changes.

Optional one-call equivalent:

Call muninn.rehydrate.bundle with the same lens and a short, concrete task query when the client supports the newer rehydration tool.

On Meaningful Completion

When durable knowledge is created, write 1–3 cards maximum via muninn.cards.upsert.

A write is appropriate when:

A decision is finalized.

A constraint is discovered.

A reusable workflow is established.

A root cause is identified.

Each card must include:

A clear, atomic summary

A durable body

Evidence references when available (commit, file path, test)

If the card is a decision, constraint, interface, or runbook and there is no evidence yet, surface a warning rather than silently pretending the provenance is strong.

Do not write transient reasoning.

Memory Hygiene Rules

Do not create duplicate cards.

Supersede outdated decisions rather than fragmenting memory.

Prefer strict scope unless cross-project knowledge is intentional.
```

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
  - `docs/laila_adaptation_memory.md`: adaptation memory type/tag/metadata contract for LAILA
  - `docs/query_contracts.md`: stable lens and adaptation query contracts
  - `docs/CROSS_PROJECT_COMPATIBILITY.md`: Muninn/Mimir shared contract discipline and change flow
  - `docs/contracts/muninn_mimir/v1/`: versioned shared schemas + fixtures

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
# or (idempotent helper target)
make init-db
```

Human-memory v1 core (standalone schema for cross-machine lens testing):
```bash
PYTHONPATH=src python scripts/init_human_memory_db.py --db ~/.local/share/muninn/human_memory.db
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
- Creates/initializes the core API DB (`~/.local/share/muninn/muninn.db`) and applies migrations
- Starts API on `127.0.0.1:8000` by default
- Prints startup banner with API URL, DB path, namespace default, and readonly state
- Exits with an actionable message if port is already in use

### MCP Quickstart (No systemd)

This is the blessed cross-platform path (Linux/macOS/Windows terminal shells):

1) Start API:
```bash
muninn up
```

2) Start MCP (separate terminal):
```bash
muninn mcp up --host 127.0.0.1 --port 8765
```

3) Optional Codex config (`~/.codex/config.toml`):
```toml
[mcp_servers.muninn]
url = "http://127.0.0.1:8765/mcp"
enabled = true
tool_timeout_sec = 60
```

4) Verify end-to-end:
```bash
muninn status
muninn audit --last 2h
```
`muninn status` checks API `/health`, MCP `muninn.system.ping`, and prints active DB paths.
`muninn audit` summarizes tool usage and memory-discipline adherence from telemetry JSONL or systemd journal fallback.

DB split:
- `~/.local/share/muninn/muninn.db` backs the core API/Cardex runtime started by `muninn up`.
- `~/.local/share/muninn/human_memory.db` backs the MCP human-memory tool surface and the human-memory procedure routes.
- When debugging `muninn.rehydrate.bundle`, `muninn.cards.*`, `muninn.policy.*`, or `muninn.spaces.resolve`, inspect `human_memory.db`.
- Use `muninn status` to confirm the active core and human-memory DB paths when env vars override defaults.

### Codex (Optional)

Muninn is MCP-native and works with many clients. Codex is one supported integration.

- Keep a repo-root `AGENTS.md` with your memory protocol (sample in this README).
- Verification steps:
  - Confirm `muninn.system.ping` succeeds (via `muninn status` or MCP client call).
  - Confirm task-start tool logs include either `muninn.spaces.resolve` -> `muninn.cards.recent` (optionally `muninn.cards.search`) or a single `muninn.rehydrate.bundle`.
  - Confirm completion writes 1-3 `muninn.cards.upsert` calls for durable outcomes.

### Advanced Linux (systemd)

For persistent auto-restart background services, use the Linux systemd user-service flow in `RUNBOOK.md`.

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
muninn audit --last 2h
muninn heal --window-days 30
muninn doctor
muninn up
muninn mcp up
muninn enable-chatgpt
```

- `muninn up` initializes schema/migrations and starts the API server.
- `muninn status` checks API health + MCP ping and prints DB paths.
- `muninn audit` reports MCP tool usage discipline (`resolve -> recent strict [-> search soft]` or `rehydrate.bundle`, then upsert hygiene).
  Reads `MUNINN_MCP_TELEMETRY_PATH` JSONL when present, else falls back to `journalctl --user -u muninn-mcp.service`.
  It also reports successful upserts that carried missing-evidence warnings.
- `muninn heal` runs self-healing maintenance for human-memory cards:
  detects duplicate/contradictory/stale patterns and can apply merge/supersede actions with `--apply`.
- `muninn doctor` runs environment checks and prints PASS/FAIL with fixes.
- `muninn mcp up` starts the primary Streamable HTTP MCP server (default `127.0.0.1:8765`).
- `muninn mcp stdio` starts a compatibility STDIO MCP shim for clients that cannot use HTTP.
- Human-memory MCP tools:
  `muninn.spaces.resolve`, `muninn.cards.recent`, `muninn.cards.search`, `muninn.rehydrate.bundle`,
  `muninn.policy.learn`, `muninn.policy.inspect`, `muninn.cards.upsert`,
  `muninn.cards.supersede`, `muninn.cards.merge`, `muninn.cards.adaptation.query`.
  Diagnostic tool: `muninn.system.ping`.
  Dot names are canonical.
  Deprecated slash aliases (`muninn/...`) remain available temporarily and are removable after `v0.12`.
  Alias toggles: `MUNINN_MCP_ENABLE_SLASH_ALIASES=1|0`, `MUNINN_MCP_SUPPRESS_ALIAS_WARNINGS=1|0`.
  Set `MUNINN_MCP_ENABLE_SLASH_ALIASES=0` now to test forward compatibility.
  These use `MUNINN_HUMAN_MEMORY_DB_PATH` (default `~/.local/share/muninn/human_memory.db`).
  This is separate from the core API DB path `MUNINN_DB_PATH` (default `~/.local/share/muninn/muninn.db`).
- `muninn.cards.upsert` soft limits new-card writes per client/space window (default `20` per `3600` seconds).
  Tune with `MUNINN_MCP_CARD_WRITE_LIMIT_PER_HOUR` and `MUNINN_MCP_CARD_WRITE_WINDOW_SECONDS`.
- JSONL telemetry sink (optional):
  - `MUNINN_MCP_TELEMETRY_PATH=~/.local/share/muninn/mcp_telemetry.jsonl`
  - `MUNINN_MCP_TELEMETRY_FLUSH=1` to flush every line
  - `MUNINN_MCP_TELEMETRY_MAX_BYTES` optional rotation threshold in bytes
  - `MUNINN_MCP_TELEMETRY_BACKUP_COUNT` retained rotated files (default `5`)
  - when the active file crosses the threshold, it rotates to `.1` and older backups shift upward; `backup_count=0` truncates instead of retaining backups
  - records canonicalized space identity, summarized queries/lenses, result counts, warnings, DB target, and latency
- For HTTP MCP auth, set either `MUNINN_API_KEY` (custom header) or `MUNINN_MCP_BEARER_TOKEN` (`Authorization: Bearer ...`).
- Non-loopback binds (`0.0.0.0` or LAN IP) are blocked unless auth is explicitly configured.
- `muninn enable-chatgpt` provisions a local connector key, ensures API+MCP are running, and prints copy/paste connector values.
  By default it also starts a Cloudflare quick tunnel and prints an HTTPS MCP endpoint.

## MCP Security Notes

- Loopback default (`127.0.0.1`) is unauthenticated by design for local-only use.
- LAN/non-loopback bind requires explicit auth token configuration.
- Never expose Muninn directly to the public internet; use a reverse proxy and strong auth controls.

## API (v0)

- `GET /health`
- `POST /cards` — create card directly (`trusted_mode=true`) or propose creation by default
- `GET /cards/{card_id}` — fetch a card
- `POST /ingest` — deterministic ingestion pipeline for stable chunks/artifacts/tags
- `POST /sources` — create a source (optionally with document/chunks/artifacts)
- `POST /sources/{source_id}/artifacts` — add derived artifacts to an existing source
- `POST /cards/{card_id}/refs` — link refs from a card to source/doc/chunk/entity/external ids
- `POST /embeddings` — upsert multimodal embedding status rows for card/source/chunk owners
- `POST /retrieve` — card-centric retrieval context pack (cards + evidence + audit id)
- `POST /promote` — promote artifact/chunk evidence into meaningful memory via proposal/trusted mode
- `POST /propose` — create proposal (`create_card|update_card|link_refs|add_source`)
- `POST /confirm/{proposal_id}` — confirm and apply proposal
- `POST /reject/{proposal_id}` — reject proposal
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
- Audit log is append-only (DB triggers block update/delete).
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
