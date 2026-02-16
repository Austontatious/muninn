# Muninn v0.3 Hybrid Retrieval Plan

## Objective
Add caller-provided vector retrieval and hybrid FTS+vector retrieval with RRF fusion, while keeping all existing v0.2 APIs backward compatible.

## Scope
In:
- Embeddings storage table and vector query/upsert APIs
- Retrieval mode toggles (`fts`, `vector`, `hybrid`)
- Hybrid fusion via RRF
- Optional embedding fields in retrieve/rehydrate
- Version hash optionally including embedding model state
- Docs/tool spec/tests updates

Out:
- ANN indexing backends (`sqlite-vec`, `pgvector`) implementation
- Automatic embedding generation inside Muninn

## Checklist
- [x] Add config toggles for retrieval mode, RRF, and vector scan cap
- [x] Add embeddings table/indexes to schema
- [x] Add vector utilities and vector storage/query module
- [x] Extend models for embedding upsert/query and optional retrieve fields
- [x] Refactor retrieval into FTS/vector/hybrid pathways with recency fill
- [x] Add API endpoints for upsert/query vector and embed-aware rehydrate/retrieve
- [x] Update memory version endpoint for optional embedding model contribution
- [x] Update integration docs, tool spec, roadmap bullet
- [x] Add tests for vector query, hybrid RRF, and version with embeddings
- [x] Run ruff/pytest and smoke-test server endpoints

## Rollback plan
- Revert commit to return to v0.2 behavior
- Schema change is additive and non-destructive; old endpoints remain usable

## Test plan
- `ruff check .`
- `pytest -q`
- `./scripts/dev_run.sh` smoke test for `/docs`, `/v0/memory/upsert_embeddings`, and `/v0/memory/rehydrate` with `query_embedding`

---

# Muninn v0.4 Optional sqlite-vec Plan

## Objective
Add an optional sqlite-vec accelerator for vector search while preserving fallback-safe brute-force behavior on all platforms.

## Scope
In:
- Optional sqlite-vec loading and backend selection
- Per-model vec0 table management with rowid mapping
- Fallback-safe query/upsert behavior and debug endpoint
- Docs/tooling/test updates for optional acceleration

Out:
- Mandatory sqlite-vec dependency
- Breaking API changes

## Checklist
- [x] Add vec backend config toggles
- [x] Add sqlite-vec best-effort loader and DB integration
- [x] Add embeddings vec-index mapping schema
- [x] Implement sqlite-vec backend module (table ensure/upsert/query)
- [x] Integrate backend selection into vector store upsert/query
- [x] Add `/v0/debug/vector_backend` endpoint
- [x] Update docs/runbook/readme/tool spec for optional accel
- [x] Add portable tests (skip if sqlite-vec unavailable + fallback behavior)
- [x] Run `ruff check .`, `pytest -q`, and smoke test endpoints

## Rollback plan
- Revert commit to keep brute-force-only backend
- Existing canonical embeddings table remains authoritative

## Test plan
- `ruff check .`
- `pytest -q`
- `./scripts/dev_run.sh` smoke test for `/v0/debug/vector_backend`, `/v0/memory/upsert_embeddings`, `/v0/memory/query_vector`

---

# Muninn v0.5 Namespace Isolation Plan

## Objective
Enforce namespace isolation at storage/query layers, add a lightweight migration runner, and add admin vector reindex support.

## Scope
In:
- Migration framework and namespace migration
- Namespace columns and query enforcement across write/retrieve/vector/audit/version
- Admin endpoint for vector reindex from canonical embeddings
- Tests proving namespace isolation and reindex behavior

Out:
- Full authz layer for admin operations
- Pending-candidate confirmation lifecycle

## Checklist
- [x] Add migration runner and integrate into `scripts/init_db.py`
- [x] Add `0001_add_namespace.sql` migration
- [x] Update `schema.sql` to include namespace columns/indexes for new installs
- [x] Enforce namespace in writeback/retrieval/vector/service queries
- [x] Add vector reindex module + admin endpoint + models
- [x] Update docs and runbook ops notes
- [x] Add namespace isolation + vector namespace + reindex tests
- [x] Bump package/API versions to 0.5.0
- [x] Run `ruff check .`, `pytest -q`, and smoke tests

---

# Muninn v0.6 Adapter/Client Plan

## Objective
Add typed client and provider adapter glue so Muninn can be consumed as a plugin/tool contract without provider SDK dependencies.

## Checklist
- [x] Add `MuninnClient` typed HTTP client
- [x] Replace local/openai/anthropic adapter stubs with real tool-spec + dispatch helpers
- [x] Package tool spec as runtime resource
- [x] Add runnable integration examples
- [x] Add tool contract and client roundtrip tests (ASGI transport)
- [x] Update integration docs with provider adapter guidance
- [x] Bump package/API versions to 0.6.0
- [x] Run `ruff check .` and `pytest -q`

---

# Muninn v0.7 Confirm Workflow Plan

## Objective
Add a confirm-required memory workflow: stage candidates, list pending items, and confirm/reject decisions that control writeback.

## Checklist
- [x] Add pending workflow tables to `schema.sql` and add migration `0002_confirm_workflow.sql`
- [x] Extend policy decision with machine-readable `action`
- [x] Add pending workflow module (`stage_candidates`, `list_pending`, `confirm_candidates`)
- [x] Add API endpoints for stage/list/confirm and keep `write_candidates` unchanged
- [x] Update typed client/adapters/tool spec resources for new workflow tools
- [x] Update integration/runbook/project-memory docs
- [x] Add tests for stage/list/confirm accept/reject/ttl expiration
- [x] Bump package/API versions to 0.7.0 and run lint/tests

---

# Muninn v0.8 Ops Hardening Plan

## Objective
Add operational hardening: retention cleanup, debug stats, readonly write kill-switch, and optional API key middleware.

## Checklist
- [x] Add config toggles for readonly/auth/retention defaults
- [x] Add optional API key middleware and wire into FastAPI app
- [x] Enforce readonly mode on write/admin endpoints
- [x] Add `/v0/debug/stats` endpoint with migration/config/count summaries
- [x] Add `/v0/admin/cleanup` endpoint with pending/decisions/audit cleanup support
- [x] Extend typed client with `debug_stats` and `admin_cleanup`
- [x] Update docs (README/RUNBOOK/PROJECT_MEMORY)
- [x] Add tests for readonly, API key, stats, and cleanup behavior
- [x] Bump versions to 0.8.0 and run lint/tests/smoke
