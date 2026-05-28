# Project Memory — Muninn (stateful)

> Status: REVIEW_NEEDED / HISTORICAL. This file is retained as a project
> memory log and may contain useful stable-edge records, but it is not the
> current architecture or operating-policy source of truth. Confirm current
> state against `AGENTS.md`, `ARCHITECTURE_CHECKPOINT.md`, `RUNBOOK.md`, and
> `docs/CODEX_STANDARDS.md`.

## Mission
Build a standalone, pluggable memory harness for LLM agents that supports:

- durable canonical memory (facts/episodes/preferences) with provenance
- safe write-gating and auditability
- conceptual recall via compact memory cards
- clean integration interfaces (HTTP + provider adapters)

## PROJECT_MEMORY Maintenance Rules (updated 2026-02-24)

- Treat this file as a single source of truth, not a terminal/log transcript.
- Prefer editing existing statements over appending duplicates.
- Append only for stable-edge outcomes: new decisions, constraints, contracts, interfaces, incidents, or milestones.
- Every durable entry must use this fixed schema:
  - Context
  - Decision / Change
  - Why
  - Evidence (file/symbol/test pointers; no raw output)
  - Impact
  - Date (`YYYY-MM-DD`)
- Write only at stable edges (checkpoint completion, contract change, invariant established, regression-fixed bug, finalized migration/schema).
- Hard bans:
  - no raw transcripts or long terminal output
  - no plans/checklists
  - no "how to think" instructions (those belong in `AGENTS.md`/`README.md`)
- Scope discipline:
  - default scope is this repo
  - cross-repo references only when contract/integration surfaces changed
- Supersedes rule: when a new change modifies an older statement, edit the existing line and mark it `(updated YYYY-MM-DD)`.

## Human Overview

### What it is
Muninn is an HTTP memory service for LLM applications. It sits beside your agent/orchestrator and provides durable memory operations without coupling to any specific model provider.

### What it does
- Stores canonical memory objects (facts, episodes, preferences) with provenance.
- Stores card-centric memory objects (Cardex) with source/artifact references for multimodal growth.
- Retrieves relevant memories for the current turn (lexical, vector, or hybrid).
- Renders compact memory cards for prompt context.
- Applies safety gates for writes, including a confirm-required queue for sensitive candidates.
- Exposes operational controls: migrations, debug stats, cleanup, readonly mode, optional API key protection.

### How it is done
- FastAPI service layer (`api.py`) exposes stable endpoints.
- SQLite canonical store with additive migrations (`schema.sql` + `scripts/migrations`).
- Retrieval pipeline combines FTS5, vector similarity, and RRF fusion.
- Policy + writeback pipeline enforces guardrails and dedupe/merge behavior.
- Pending workflow tables (`pending_candidates`, `candidate_decisions`) close the write lifecycle loop.
- Ops modules provide cleanup and observability endpoints.

## Architecture Map

- Ingress/API:
  - `src/muninn/api.py`
- Domain models:
  - `src/muninn/models.py`
- Memory pipeline:
  - `src/muninn/memory/policy.py`
  - `src/muninn/memory/writeback.py`
  - `src/muninn/memory/pending.py`
  - `src/muninn/memory/retrieval.py`
  - `src/muninn/memory/cards.py`
- Cardex pipeline:
  - `src/muninn/cardex/store.py`
  - `src/muninn/cardex/retrieval.py`
  - `src/muninn/cardex/proposals.py`
  - `src/muninn/cardex/signals.py`
  - `src/muninn/cardex/promotion.py`
- Human-memory v1 standalone helpers:
  - `src/muninn/human_memory/bootstrap.py`
  - `src/muninn/human_memory/spaces.py`
  - `src/muninn/human_memory/cards.py`
- Vector subsystem:
  - `src/muninn/vector/store.py`
  - `src/muninn/vector/sqlite_vec_backend.py`
  - `src/muninn/vector/reindex.py`
- Ops/security:
  - `src/muninn/ops/stats.py`
  - `src/muninn/ops/cleanup.py`
  - `src/muninn/middleware/auth.py`
- Persistence:
  - `src/muninn/schema.sql`
  - `scripts/migrations/*.sql`
  - `scripts/init_db.py`

## Turn Lifecycle (high-level)

1) Rehydrate: retrieve relevant memory and render cards for prompt injection.
2) Respond: agent answers user.
3) Stage: agent submits memory candidates.
4) Decide:
   - benign -> written to canonical tables
   - sensitive -> queued pending confirmation
   - unsafe/instruction-like -> rejected
5) Confirm/reject pending candidates.
6) Observe and maintain with debug stats and cleanup.

## Current Snapshot

- Repo scaffold created (FastAPI + SQLite)
- Schemas defined for core objects + memory cards
- Endpoints implemented:
  - health
  - write_candidates
  - retrieve
  - render_cards
  - rehydrate
  - upsert_embeddings
  - query_vector
  - memory/version
- Retrieval supports mode toggle:
  - `fts` (default)
  - `vector` (caller-provided query embedding)
  - `hybrid` (FTS + vector fused with RRF)
- Core `/v0/memory` embeddings are caller-provided and stored in SQLite as normalized float32 blobs; Cardex retrieval now also supports local deterministic embeddings via index jobs (updated 2026-02-24)
- Optional sqlite-vec acceleration added with automatic fallback to brute-force
- Namespace isolation enforced in storage/query paths (v0.5) and hardened to server-assigned namespaces with fail-closed invalid API key mappings plus explicit unauth override flag (updated 2026-02-24)
- Admin reindex path added to rebuild sqlite-vec mappings from canonical embeddings
- Typed `MuninnClient` + OpenAI/Anthropic/local adapters added with contract tests (v0.6)
- Confirm-required lifecycle added: stage/list/confirm with durable pending queues (v0.7)
- Ops hardening added: cleanup endpoint, debug stats, readonly mode, optional API key middleware (v0.8)
- Cardex v1 added (v0.9): cards/sources/refs/artifacts/proposals schema + retrieval context pack endpoint + propose/confirm/reject state machine + multimodal embedding status stubs
- Cardex retrieval now emits explicit `redactions[]` metadata and tier-block stubs for least-privilege evidence delivery
- Audit trail hardened to append-only DB behavior with request-level audit middleware (success and failure paths)
- Ingestion v1 added (v0.10): deterministic `/ingest` flow with stable source/doc/chunk/artifact IDs, heuristic tags, searchable `extracted_text` artifacts, and media/url/file pending artifact stubs
- Meaningful memory added (v0.11): evidence lifecycle state (`captured|candidate|promoted`), access signals/co-access edges, deterministic implicit promotion proposals, `POST /promote`, and `index_jobs` hooks for active cards/promoted evidence; Checkpoint B adds a real index worker plus hybrid lexical+vector Cardex retrieval (updated 2026-02-24)
- Human-memory v1 standalone core added: `migrations/0001_init.sql` plus deterministic bootstrap/space-resolution/card helpers for user/space/card/evidence lens testing on fresh machines
- CLI baseline added for installability (`muninn up`, `muninn doctor`, `muninn status`)
- Universal local run hardened: `muninn up` now auto-creates config/data dirs, initializes DB+migrations, prints startup banner, and reports actionable port conflicts
- Local MCP wrapper added (`muninn mcp up`) with HTTP forwarding for core memory tools
- MCP human-memory lens tools added: `muninn.spaces.resolve`, `muninn.cards.recent`, `muninn.cards.search`, `muninn.cards.upsert` (backed by `src/muninn/human_memory/*`, with temporary slash aliases for backcompat)
- MCP transport policy hardened: Streamable HTTP is the default, `muninn mcp stdio` is a compatibility shim, and non-loopback binds require explicit auth tokens
- ChatGPT connector prep added: `muninn enable-chatgpt` provisions API key config, ensures API+MCP background services, and prints local MCP endpoint/header/key
- ChatGPT connector tunnel automation added: `enable-chatgpt` can download/use `cloudflared`, start quick tunnel, and print HTTPS `/mcp` URL

## Key Constraints

- Avoid storing raw transcripts as “memory”
- Memory is facts/episodes/preferences with confidence + provenance
- Cardex writes should default to proposal/confirmation (except trusted mode)
- “Instruction injection” never stored (firewall)
- Muninn stays model-agnostic (no built-in embedding model coupling)

## Compatibility Contract

- `/v0/memory/*` is a stable API surface.
- Cardex is additive: `/cards`, `/sources`, `/ingest`, `/retrieve`, `/promote`, `/propose`, `/confirm/{id}`, `/reject/{id}`.
- Tool spec is mirrored and must stay byte-identical in:
  - `schemas/tooling/muninn_tool_spec.json`
  - `src/muninn/resources/muninn_tool_spec.json`

## Operator Knobs (stable)

### `MUNINN_API_KEYS`
- Context: Auth and namespace isolation (`middleware/auth.py`, `api.py`).
- Decision / Change: API keys map to server-resolved namespaces using `key:namespace` pairs (or equivalent JSON); if env is present but invalid/empty after parse, fail closed.
- Why: Prevent silent auth bypass and cross-namespace writes/reads from malformed key configuration.
- Evidence:
  - `src/muninn/middleware/auth.py:_parse_api_key_namespaces`
  - `src/muninn/api.py:_resolve_namespace`
  - `tests/test_api_key_middleware.py::test_api_keys_env_invalid_fails_closed`
  - `tests/test_namespace_auth_isolation.py::test_namespace_override_is_rejected`
- Impact: Protected requests are namespace-bound by server auth context; invalid key map denies protected access.
- Date: 2026-02-24

### `MUNINN_ALLOW_UNAUTH_NAMESPACE_OVERRIDE`
- Context: Unauthenticated/dev namespace behavior in middleware + API namespace resolution.
- Decision / Change: Default is `false`; unauthenticated client namespace overrides are ignored unless explicitly enabled for dev.
- Why: Avoid accidental "no auth + arbitrary namespace" behavior in production-like setups.
- Evidence:
  - `src/muninn/middleware/auth.py:_allow_unauth_namespace_override`
  - `src/muninn/api.py:_resolve_namespace`
  - `tests/test_namespace_auth_isolation.py::test_unauthed_mode_ignores_namespace_override_by_default`
  - `tests/test_namespace_auth_isolation.py::test_unauthed_mode_can_allow_namespace_override_with_flag`
- Impact: Safer default in unauth mode; opt-in dev flexibility remains available.
- Date: 2026-02-24

## Stable Edge Records

### Checkpoint A — Namespace Isolation MVP
- Context: Auth middleware, request namespace resolution, API contract enforcement.
- Decision / Change: Namespace is server-assigned from auth mapping; mismatched client namespace overrides are rejected when auth is enforced; invalid `MUNINN_API_KEYS` mapping fails closed.
- Why: Enforce tenant isolation invariants at ingress and prevent bypass from malformed configuration.
- Evidence:
  - `src/muninn/middleware/auth.py:_parse_api_key_namespaces`
  - `src/muninn/api.py:_resolve_namespace`
  - `tests/test_namespace_auth_isolation.py::test_same_identifier_isolated_by_server_namespace`
  - `tests/test_namespace_auth_isolation.py::test_index_jobs_are_written_with_resolved_namespace`
  - `tests/test_api_key_middleware.py::test_api_keys_env_invalid_fails_closed`
- Impact: All reads/writes/index job rows are tied to resolved server namespace; cross-namespace override attempts are blocked.
- Date: 2026-02-24

### Checkpoint B — Real Cardex Semantic Retrieval v1
- Context: Cardex indexing and retrieval (`cardex/store.py`, `cardex/retrieval.py`, index jobs).
- Decision / Change: Cardex now has real deterministic embedding generation, background index job processing, idempotent embedding upserts, and deterministic hybrid lexical+vector ranking; retrieval no longer uses stub vector paths.
- Why: Replace stub retrieval with queryable semantic behavior while preserving namespace-clean filtering and deterministic outputs.
- Evidence:
  - `src/muninn/cardex/embeddings.py::embed_text`
  - `src/muninn/cardex/index_jobs.py::process_pending_index_jobs`
  - `src/muninn/cardex/retrieval.py::_search_cards`
  - `src/muninn/cardex/store.py::upsert_card_embedding`
  - `tests/test_cardex_semantic_retrieval.py::test_index_worker_builds_embeddings_and_vector_search_is_queryable`
  - `tests/test_cardex_semantic_retrieval.py::test_cardex_retrieval_is_namespace_clean_for_vector_and_lexical`
  - `tests/test_cardex_semantic_retrieval.py::test_hybrid_ranking_can_outrank_lexical_trap`
- Impact: `POST /retrieve` returns semantically ranked Cardex results with real hybrid/debug stats, and index jobs produce queryable embeddings.
- Date: 2026-02-24

## Next Steps (nearest)

- Add ANN backend behind existing vector store interface (sqlite-vec / pgvector)
- Add admin authz layer for `/v0/admin/*` endpoints
- Add background reindex flow for sqlite-vec mappings after long brute-force-only periods
- Add contradiction ledger + merge/dedupe policies
- Improve redaction policy beyond v1 basic email/phone masking
