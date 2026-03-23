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

---

# Muninn Step 7 Local MCP Wrapper Plan

## Objective
Add a local-only MCP server wrapper (`muninn mcp up`) that forwards a small fixed tool set to Muninn HTTP endpoints.

## Checklist
- [x] Add MCP dependency and wrapper server module
- [x] Expose only rehydrate/stage/list/confirm tools
- [x] Wire `muninn mcp up` CLI command with host/port/base-url options
- [x] Forward `MUNINN_API_KEY` when set
- [x] Update README/PROJECT_MEMORY with MCP local mode notes
- [x] Verify local MCP endpoint reachability and end-to-end tool calls

---

# Muninn v0.9 Cardex v1 Plan

## Objective
Add a card-centric multimodal-ready memory slice (Cardex v1) while keeping all existing `/v0/memory/*` APIs backward compatible.

## Scope
In:
- Additive schema/migration for card-oriented tables (`cards`, `sources`, `documents`, `chunks`, `card_refs`, `artifacts`, `card_embeddings`, `proposals`)
- New Cardex endpoints for card/source/ref CRUD, retrieval context packs, and propose/confirm/reject workflow
- Retrieval pipeline using FTS over cards + artifacts with ref-based evidence expansion and sensitivity/redaction policy
- Docs/tool spec/test updates

Out:
- Raw media storage pipeline implementation
- Production multimodal embedding generation (stub interface only)

## Checklist
- [x] Add `0003_cardex_v1.sql` migration in both migrations locations
- [x] Extend `schema.sql` for fresh installs with Cardex tables + FTS triggers
- [x] Add Cardex models and storage/retrieval/proposal modules
- [x] Add endpoints: `/cards`, `/cards/{id}`, `/sources`, `/cards/{id}/refs`, `/retrieve`, `/propose`, `/confirm/{id}`, `/reject/{id}`
- [x] Wire audit logging for Cardex operations and return retrieval `audit_id`
- [x] Update `docs/INTEGRATION.md`, `schemas/tooling/muninn_tool_spec.json`, and packaged tool spec
- [x] Update `PROJECT_MEMORY.md` with Cardex architecture notes
- [x] Add tests for Cardex create/propose/confirm/retrieve and migration apply
- [x] Run `ruff check .` and `pytest -q`

---

# Muninn v0.10 Ingestion v1 Plan

## Objective
Add a deterministic ingestion pipeline that produces stable source/doc/chunk/artifact identities and searchable text artifacts without requiring embeddings.

## Checklist
- [x] Add ingestion request/response models for deterministic text/url/file/media-stub intake
- [x] Implement ingestion module with normalization, structure-first chunking, overlap, stable IDs, and heuristic tagging
- [x] Add `POST /ingest` endpoint and audit wiring
- [x] Add pending artifact stubs for media and fetch-later source modes
- [x] Add optional card hooks (`card_mode=none|propose|trusted`) with ref suggestions
- [x] Update tool specs/adapters/client/docs for new ingestion endpoint
- [x] Add ingestion tests for determinism, fallback retrieval, media stubs, and card hooks
- [x] Run `ruff check .` and `pytest -q`

---

# Muninn v0.11 Meaningful Memory Plan

## Objective
Add meaningful-memory mechanics on top of Cardex by introducing evidence lifecycle states, access signals, deterministic promotion proposals, and indexing hooks while preserving `/v0/memory/*` compatibility.

## Checklist
- [x] Add `0004_meaningful_memory.sql` migration in both migrations locations
- [x] Extend `schema.sql` with `evidence_state`, `signals`, `coaccess_edges`, and `index_jobs` tables + invariants
- [x] Add models for promotion endpoint request/response and new proposal type support
- [x] Add `cardex/signals.py` and wire access tracking into `POST /retrieve`
- [x] Add `cardex/promotion.py` with deterministic implicit trigger policy + cooldown handling
- [x] Add `POST /promote` endpoint (propose/trusted modes), write-gated behavior, and audit events
- [x] Extend proposals apply path for promotion payload confirmation
- [x] Enqueue index jobs for `cards.status='active'` and promoted evidence
- [x] Update tool specs/adapters/client for `muninn_cardex_promote`
- [x] Add tests: schema invariants, signals, trigger promotion, cooldown, promote endpoint, index jobs, and keep existing contracts green
- [x] Update docs (`README.md`, `docs/INTEGRATION.md`, `PROJECT_MEMORY.md`)
- [x] Add `Makefile` with idempotent `init-db` and `install` targets
- [x] Run `ruff check .` and `pytest -q`

---

# Muninn Human-Memory Core v1 (Standalone) Plan

## Objective
Land a user/space/card/evidence-first schema and helper layer that is system-agnostic, deterministic, and easy to bootstrap on any machine without changing existing Cardex/v0 APIs.

## Checklist
- [x] Add standalone canonical schema at `migrations/0001_init.sql`
- [x] Include v1 invariants: global space row model, summary/body split, enum/range checks, and uniqueness constraints
- [x] Add FTS5 index + triggers for `cards.title|summary|body`
- [x] Add deterministic bootstrap defaults (`ent_local_user`, `codex-vscode`, `global` space)
- [x] Add deterministic `resolve_space_from_cwd()` and `get_or_create_space()` helpers
- [x] Add minimal card APIs (`cards_recent`, `cards_search`, `card_upsert`) with optional evidence linking
- [x] Add MCP lens tool surface (`muninn.spaces.resolve`, `muninn.cards.recent`, `muninn.cards.search`, `muninn.cards.upsert`) mapped directly to human-memory helpers
- [x] Set MCP transport defaults: Streamable HTTP primary, STDIO compatibility shim, non-loopback bind guardrails with explicit auth
- [x] Add init script `scripts/init_human_memory_db.py`
- [x] Add focused tests for bootstrap, space resolution, and card/evidence flows
- [x] Update docs (`README.md`, `docs/INTEGRATION.md`, `PROJECT_MEMORY.md`, `RUNBOOK.md`)
- [x] Run lint and targeted tests for the standalone slice

---

# Muninn LAILA Adaptation Memory Support Plan

## Objective
Add deterministic, typed adaptation-memory storage and retrieval contracts for LAILA on top of the human-memory card substrate, without embedding adaptation policy in Muninn.

## Checklist
- [x] Formalize adaptation memory types/tags/metadata conventions (direct/inferred preferences, scoped overrides, corrections, outcomes)
- [x] Add adaptation write/query helpers with deterministic filtering by subject, scope, persistence, category, tags, and recency
- [x] Add MCP retrieval affordance(s) for durable preferences, recent overrides, corrections, outcomes, and prompt-state grouping
- [x] Harden query reliability (cards search query normalization + invalid-shape fail-safe behavior)
- [x] Add targeted tests for adaptation create/retrieve flows and lens/query reliability
- [x] Add docs for adaptation schema/tags and stable query contracts (`docs/laila_adaptation_memory.md`, `docs/query_contracts.md`)

---

# Muninn Hardening + Next-State Adaptation Plan

## Objective
Harden the human-memory/MCP path so retrieval contracts, telemetry, space identity, provenance, fallback recall, and session rehydration are reliable under real Codex usage, then add a minimal memory-native next-state adaptation loop that captures evaluative/directive feedback as scoped policy memory.

## Checklist
- [ ] Audit current MCP retrieval contracts, telemetry payloads, space resolution, evidence policy, and rehydration call graph
- [ ] Add backward-compatible lens/query parsing for legacy retrieval payload shapes with actionable validation errors
- [ ] Canonicalize project space identity and add alias/migration support for prior `path:*` / `repo:*` fragmentation
- [ ] Expand structured telemetry for read/write operations with redacted request summaries, resolved space context, DB target, and failure diagnostics
- [ ] Add evidence-discipline policy helpers and warnings for engineering/project memory writes without provenance
- [ ] Refactor retrieval into deterministic staged fallback with scoring across strict, recent, alias, evidence-backed, and soft/global paths
- [ ] Add explicit rehydration orchestration for task start / resume with stage tracing and policy-track retrieval
- [ ] Add minimal interaction capture + interpretation pipeline for evaluative/directive signals
- [ ] Persist scoped policy-state cards and retrieve them alongside project memory during rehydration
- [ ] Add inspection surfaces/tests/docs for hardening + next-state adaptation behavior

## Rollback plan
- Revert the hardening commit series if compatibility or retrieval quality regresses
- Human-memory schema changes must remain additive and self-healing for existing local DBs
- Keep legacy retrieval tool usage working throughout the transition

## Test plan
- `PYTHONPATH=src /home/unix/.local/share/uv/python/cpython-3.11.14-linux-x86_64-gnu/bin/python3.11 -m pytest -q`
- Focused suites while iterating:
  - `tests/test_human_memory_cards.py`
  - `tests/test_human_memory_spaces.py`
  - `tests/test_mcp_telemetry_sink.py`
  - `tests/test_cli_audit.py`
  - new hardening/rehydration/policy tests added in this pass
