# Muninn SDK Refactor Boundary Audit

Date: 2026-04-05

## Goal
Map what belongs in `muninn-core` versus `muninn-runtime`, and identify coupled areas that must be separated for an SDK-first contract.

## Current Boundary Snapshot

### Substrate / domain logic (core candidates)
- `src/muninn/human_memory/*`
  - cards, evidence joins, lineage, FTS retrieval
  - canonical space resolution and alias migration
  - staged rehydration bundle
  - interaction events + policy promotion
  - procedure memory with structured evidence normalization
- `src/muninn/cardex/*`
  - retrieval/index jobs/embeddings (legacy v0 plane)
- `src/muninn/memory/*`
  - legacy v0 memory write/retrieve pipeline
- `src/muninn/db.py`
  - storage primitives + transaction helpers
- `migrations/*` + `schema.sql`
  - base schema files for v0 plane and human-memory plane

### Runtime / transport logic (runtime candidates)
- `src/muninn/api.py`
  - FastAPI routes for v0 plane and selected human-memory endpoints
- `src/muninn/mcp_server.py`
  - MCP tool surface for human-memory runtime
- `src/muninn/cli.py`
  - daemon startup, audit, heal, and operator commands
- `src/muninn/middleware/*`
  - auth + request metadata
- `src/muninn/telemetry.py`
  - structured telemetry emission + rotation

## Current Coupling Points
- `api.py` calls directly into `human_memory.*` and `memory.*` modules.
- `mcp_server.py` owns request validation and directly calls human-memory functions.
- `cli.py` directly bootstraps and uses both v0 DB and human-memory DB paths.
- `human_memory` functions operate over raw SQLite connections and produce dict payloads; transport concerns are not injected but the models are not centralized into a core API boundary.

## Boundary Decisions For SDK-First Refactor

### Move to `muninn-core`
- Canonical envelope models (memory item, evidence, event, lifecycle, trust)
- App/bundle registration (`AppSpec`, `MemorySpec`, `BundleSpec`)
- Storage abstraction for human-memory DB (initial backend)
- SDK orchestration: write/query/rehydrate/attach evidence/supersede/revoke

### Move to `muninn-runtime`
- HTTP API surface and FastAPI app
- MCP server + tool definitions
- CLI entrypoints / daemon lifecycle
- Runtime auth / telemetry / operational helpers

## Compatibility Surfaces To Preserve
- HTTP endpoints under `/v0/*`
- MCP tool names and payloads (`muninn.spaces.resolve`, `muninn.rehydrate.bundle`, `muninn.cards.*`, `muninn.policy.*`)
- CLI commands (`muninn up`, `muninn mcp`, `muninn audit`, etc.)
- `muninn.client.http.MuninnClient` for existing HTTP consumers

## Immediate Separation Work (Phase 1-2)
- Introduce `muninn.core` with typed contracts + SDK orchestration, backed by the human-memory DB.
- Leave HTTP/MCP/CLI intact but add runtime wrappers that route through the new SDK where feasible.
- Preserve existing `/v0` path behavior via adapters, not via duplication.

## Known Risks
- Two DB planes remain (human-memory + v0) until a later consolidation.
- Some runtime logic (telemetry, audit gates) still lives outside the SDK and should be wrapped, not reimplemented.
- Cross-repo contracts (Muninn <-> Mimir) must remain stable; SDK changes must not alter MCP payloads without compatibility updates.

## Next Steps
- Implement core contract module + SDK surface.
- Add example app packs (Lexi + Friday) to prove app-defined memory contracts.
- Add compatibility doc for runtime adapters.
