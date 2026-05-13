# Muninn Component Inventory

Date: 2026-05-13

## Classification Legend

- A: Durable Memory Substrate, candidate for Muninn v2.
- B: Associative Processor, candidate for Mimir or Mimir-adjacent modules.
- C: Interpreter/Runtime, candidate for Hrafnar or runtime adapters.
- D: Legacy, tightly coupled, or deprecated compatibility layer.

## Storage And Schema

| Component | Classification | Notes |
| --- | --- | --- |
| `migrations/0001_init.sql` | A | Best current substrate schema: spaces, cards, evidence, relations, events, vectors. |
| `src/muninn/schema.sql` entity/fact/episode/preference tables | A/D | Useful primitives, but legacy plane conflicts with human-memory model. |
| `src/muninn/schema.sql` Cardex tables | A/B | Sources/chunks/artifacts/embeddings/signals/coaccess are valuable, but should be unified. |
| `data/muninn.db` | D | Legacy local DB instance; migration source, not v2 source of truth. |
| `human_memory.db` default path | A | Current active human-memory storage target, though not present in repo data directory. |

## Core Human-Memory Modules

| Component | Classification | Notes |
| --- | --- | --- |
| `human_memory/bootstrap.py` | A | Idempotent schema/bootstrap path with compatibility repair. |
| `human_memory/spaces.py` | A | Canonical scope/alias primitive; project heuristics should become adapter/profile logic. |
| `human_memory/cards.py` | A | Durable card/evidence/lineage operations. |
| `human_memory/rehydration.py` | A/B | Deterministic recall planner belongs in substrate as a contract; ranking policy may move to Mimir. |
| `human_memory/vector_store.py` | A/B | Vector persistence and diagnostics are substrate; recall policy belongs above it. |
| `human_memory/interactions.py` | A | Raw event capture is substrate. |
| `human_memory/policy.py` | B | Promotion and behavior learning are associative/learning concerns; stored cards remain substrate. |
| `human_memory/adaptation.py` | B | Behavior adaptation projection belongs above substrate. |
| `human_memory/procedures.py` | A/B | Procedure records can be durable memory; reflection-driven update policy belongs above substrate. |
| `human_memory/session_start.py` | C | Prompt-ready bootstrap shaping is runtime/interpreter behavior. |
| `human_memory/retrieval_eval.py` | A/B | Evaluation harness should remain, but tied to retrieval policy experiments. |
| `human_memory/heal.py` | A/C | Operator repair utility, not core model. |

## SDK Core

| Component | Classification | Notes |
| --- | --- | --- |
| `core/contracts.py` | A | Good contract seed: `MemoryItem`, `EvidenceRef`, `MemoryEvent`, bundle explanation. |
| `core/specs.py` | A | App-defined memory and bundle specs are the right v2 extensibility direction. |
| `core/storage.py` | A | Useful adapter around human-memory DB, but has contract/storage mismatch on `revoked`. |
| `core/sdk.py` | A/C | SDK orchestration is a stable integration surface; some bundle rendering is runtime-adjacent. |
| `core/bundle.py` | A/B | Staged bundle construction; ranking strategy should be pluggable. |
| `core/procedures.py` | A/B | Typed procedure contract is valuable; learning/reflection policy should be separate. |
| `core/v0_runtime.py` | D | Compatibility adapter for old v0 plane. |
| `core/registry.py` | A | Registry concept belongs in v2. |

## Legacy v0 And Cardex

| Component | Classification | Notes |
| --- | --- | --- |
| `memory/retrieval.py` | D/B | Legacy fact/episode/preference retrieval; useful migration reference. |
| `memory/writeback.py` | D | Legacy write path. |
| `memory/pending.py` | D/A | Pending review concepts are valuable, implementation is compatibility-layer. |
| `memory/policy.py` | D | Old write policy heuristics. |
| `memory/provenance.py` | D/A | Provenance normalization concept survives. |
| `cardex/store.py` | A/D | Rich multimodal storage operations, but separate plane. |
| `cardex/retrieval.py` | B/D | Hybrid retrieval and redaction are useful, but current implementation is Cardex-specific. |
| `cardex/index_jobs.py` | A/C | Index-job pattern useful for v2 vector/artifact processing. |
| `cardex/embeddings.py` | A | Deterministic local embeddings are useful for tests/dev. |
| `cardex/signals.py` | B | Coaccess and access signals belong to salience/associative processing. |
| `cardex/proposals.py` | A/C | Proposal records should survive as a stable review contract. |

## Runtime And Transport

| Component | Classification | Notes |
| --- | --- | --- |
| `mcp_server.py` | C | Local MCP runtime, validation, telemetry, compatibility, tool orchestration. Hrafnar candidate. |
| `api.py` | C/D | FastAPI runtime plus v0 compatibility. |
| `cli.py` | C | Operator runtime. |
| `runtime/http.py`, `runtime/mcp.py`, `runtime/cli.py` | C | Runtime wrappers. |
| `apps/muninn_mcp/server.py` | C | Narrow ChatGPT bridge; should remain adapter, not substrate. |
| `middleware/auth.py` | C | Runtime auth. |
| `telemetry.py` | C/A | Runtime emission, but event schema should inform substrate observability contracts. |
| `client/http.py` | C | Client adapter. |

## Cross-Project Boundary Components

| Component | Classification | Notes |
| --- | --- | --- |
| `mimir_proposals.py` | B/C | Proposal validation/preview belongs at Mimir-Muninn boundary, not core storage. |
| `docs/contracts/muninn_mimir/v1` | A/C | Stable shared contract artifacts should remain versioned. |
| Atlas card conventions | A/C | Atlas records can be stored as memory, but Bifrost owns boundary vocabulary. |

## Documentation Assets

| Component | Classification | Notes |
| --- | --- | --- |
| `ARCHITECTURE_CHECKPOINT.md` | C | Current map, not v2 contract. |
| `docs/SDK_CORE_CONTRACT.md` | A | Strong basis for v2 contracts. |
| `docs/SDK_COMPATIBILITY_AND_MIGRATION.md` | C | Useful migration policy. |
| `docs/MUNINN_SURFACE_STATUS.md` | C | Useful surface classification. |
| ADRs for vector stages | A/B | Good record of vector safety posture. |

## Summary

The reusable assets cluster around human-memory schema, SDK contracts, evidence discipline, deterministic rehydration, and Cardex multimodal pieces. The components most likely to move out of core Muninn are policy promotion, adaptation projection, retrieval experimentation, and all protocol/runtime bridges.
