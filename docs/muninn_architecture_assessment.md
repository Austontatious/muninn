# Muninn Architectural Assessment

> Status: HISTORICAL ASSESSMENT. This document is retained as evidence for the
> 2026-05-13 v2 direction. Current architecture truth lives in
> `../ARCHITECTURE_CHECKPOINT.md` and later ADRs/reports.

Date: 2026-05-13

## Executive Summary

Muninn is salvageable as the basis for Muninn v2, but not by treating the current repository as a single coherent substrate. The current codebase contains three overlapping memory architectures:

1. The legacy `/v0` plane backed by `src/muninn/schema.sql` and `data/muninn.db`.
2. The human-memory plane backed by `migrations/0001_init.sql` and `human_memory.db`.
3. The SDK-first overlay under `src/muninn/core`, which wraps the human-memory plane with app-defined contracts.

The strongest foundation is the human-memory plane: canonical spaces, durable cards, evidence refs, card relations, interaction events, deterministic staged rehydration, and explicit telemetry. These are close to generalized memory-substrate primitives.

The weakest foundation is the split-brain architecture. Muninn currently has two storage planes, multiple retrieval models, transport code with domain logic, and several concept families that belong in Mimir or Hrafnar rather than in a durable memory substrate.

Recommendation: Option B, a hybrid path. Preserve the durable primitives and migrate toward a v2 substrate around stable contracts, but treat the current architecture as a source of proven primitives and migration adapters rather than as the final v2 shape.

## Scope And Evidence

This assessment inspected:

- `ARCHITECTURE_CHECKPOINT.md`
- `migrations/0001_init.sql`
- `src/muninn/schema.sql`
- `src/muninn/human_memory/*`
- `src/muninn/core/*`
- `src/muninn/memory/*`
- `src/muninn/cardex/*`
- `src/muninn/api.py`
- `src/muninn/mcp_server.py`
- `apps/muninn_mcp/server.py`
- `docs/MUNINN_SURFACE_STATUS.md`
- `docs/SDK_CORE_CONTRACT.md`
- `docs/SDK_COMPATIBILITY_AND_MIGRATION.md`
- `docs/muninn_v0_surface_audit.md`
- Bifrost boundary records under `/mnt/data/Bifrost/atlas`

No implementation, schema change, data migration, or runtime refactor was performed.

## Current Architecture

The live human-memory path is:

```text
MCP / CLI / selected API paths
  -> runtime validation and telemetry
  -> canonical space resolution
  -> human-memory SQLite bootstrap
  -> cards, evidence, relations, interactions, policy, rehydration
  -> human_memory.db
```

The legacy v0 path is:

```text
FastAPI /v0/*
  -> core.v0_runtime.V0Runtime
  -> memory/cardex/vector modules
  -> muninn.db
```

The SDK path is:

```text
muninn.core.sdk.Muninn
  -> AppSpec / MemorySpec / BundleSpec
  -> HumanMemoryStore
  -> human-memory modules
```

The SDK-first overlay is directionally correct, but it is not yet the single source of truth. Important runtime paths still call human-memory modules directly, and v0 remains materially separate.

## Primary Findings

Muninn is already close to a generalized memory substrate in its durable primitives, not in its whole architecture.

Durable primitives that should survive:

- Canonical space identity and aliases.
- Card as durable memory envelope.
- Evidence as a separate provenance object.
- Card-to-evidence joins.
- Card relations for lineage and contradiction/refinement.
- Interaction events as raw behavioral trace.
- Deterministic staged rehydration with diagnostics.
- Explicit vector indexing as an optional rescue layer, not a silent default.
- SDK envelope direction: `MemoryItem`, `EvidenceRef`, `MemoryEvent`, bundle explanations, app specs.

Architectural baggage that should not define v2:

- Two SQLite planes with different conceptual models.
- Transport surfaces owning request shaping, business rules, telemetry, and compatibility at once.
- Legacy entity/fact/episode/preference APIs competing with card-centric memory.
- Project/Codex-specific lens semantics embedded in core workflows.
- Policy/adaptation promotion logic living inside the substrate rather than behind a separable salience/learning hook.
- ChatGPT bridge deployment concerns in the same repo as substrate code.

## Question Answers

### 1. Is the current schema/general architecture close to generalized memory?

Partly. The human-memory schema is a credible substrate kernel for durable memory. It has spaces, cards, evidence, relations, events, tags, FTS, salience, and vectors. The v0/Cardex schema also contains generalized concepts such as entities, facts, episodes, preferences, sources, chunks, artifacts, multimodal embeddings, signals, and coaccess edges.

The problem is that these concepts are split across planes. Current Muninn has many ingredients for a generalized substrate, but not one coherent substrate model.

### 2. Which parts should be preserved?

Preserve:

- Human-memory `cards`, `evidence`, `card_evidence`, `card_relations`.
- `spaces` and `space_aliases`.
- `interaction_events`.
- Deterministic rehydration stage reporting.
- Optional vector diagnostics and shadow/augment controls.
- Evidence discipline and object-shaped write contract.
- SDK contracts and app-pack direction, after tightening semantics.

### 3. Which parts are overfit?

Overfit areas:

- `repo:<sha(remote)>`, `path:<sha(root)>`, `cwd:*` identity as the dominant space model.
- Default kinds: `decision`, `constraint`, `interface`, `runbook`.
- Rehydration sections: `facts`, `constraints`, `lessons`, `preferences`.
- MCP startup discipline and Codex-first audit gates.
- Tool names and slash aliases.
- ChatGPT bridge routes and private path-prefix deployment.
- Policy kinds tied to agent workflow preferences.

These can remain as adapters/profiles, but they should not be v2 substrate primitives.

### 4. Is retrieval portable, explainable, extensible, ontology-generalizable?

Retrieval is explainable and deterministic. It is only moderately portable and not yet ontology-generalizable.

Strengths:

- Explicit stages.
- Per-stage diagnostics and zero-result reasons.
- Deterministic scoring inputs.
- Space-scope controls.
- Vector mode disabled by default and observable when used.

Weaknesses:

- Card-kind heuristics are hard-coded.
- Rehydration bundle labels assume project/agent workflows.
- Relation graph is not used as a first-class ranking/input surface.
- Recall history and coaccess are split between human-memory and Cardex, not unified.
- Vector rescue is narrow and tied to durable project-memory kinds.

### 5. Does storage support person/place/time/thing, event logs, recall history, reinforcement, association graphs, multimodal futures, vector rescue, salience propagation?

Support is uneven:

- Person/place/time/thing: partially in legacy `entities`, Cardex `type`, and JSON metadata; not unified in human-memory.
- Event logs: strong enough in `interaction_events` and legacy `audit_log`.
- Recall history: weak in human-memory, stronger in Cardex `signals` and `coaccess_edges`.
- Reinforcement: partial through policy promotion, confidence, salience, and interaction-derived policy.
- Association graphs: partial through `card_relations` and Cardex `coaccess_edges`; not generalized.
- Multimodal futures: stronger in Cardex `sources`, `documents`, `chunks`, `artifacts`, and multimodal `card_embeddings`; weak in human-memory.
- Vector rescue layers: present and carefully gated in human-memory; hybrid retrieval exists in Cardex.
- Salience propagation: not first-class. Salience exists as a field but propagation rules are not a substrate contract.

### 6. Is there hidden debt making rewrite cleaner?

Yes. The hidden debt is not one bug; it is architectural multiplicity:

- Duplicate schemas and concepts.
- Inconsistent status enums. Example: SDK `revoke_card` writes `revoked`, while human-memory schema allows `active`, `superseded`, `archived`.
- Runtime/domain logic coupling.
- Legacy v0 compatibility still uses a different model.
- JSON metadata conventions carry important schema without first-class validation.
- Policy/adaptation concerns mix substrate storage with cognitive learning behavior.

This debt argues against pure incremental cleanup, but not against preserving the data primitives.

### 7. Which abstractions should become contracts?

Minimum stable contracts:

- `MemoryStore`
- `MemoryItem`
- `EvidenceRef`
- `EventLog`
- `SpaceResolver`
- `EntityResolver`
- `AssociationStore`
- `RecallEngine`
- `RehydrationProvider`
- `VectorIndex`
- `SalienceSignalSink`
- `MigrationAdapter`

### 8. Which components become libraries/adapters/modules/deprecated?

Standalone libraries:

- Core contracts and app specs.
- Human-memory storage primitives.
- Rehydration planner/explainer.
- Vector index interface.
- Migration/export tools.

Adapters:

- FastAPI.
- MCP local tools.
- ChatGPT bridge.
- CLI.
- v0 compatibility.
- Codex project-memory profile.

Optional modules:

- Policy/adaptation learning.
- Procedural memory.
- Vector backends.
- Cardex multimodal ingestion.

Deprecated legacy layers:

- Direct `/v0` fact/episode/preference mutation as a primary model.
- Transport-specific slash aliases.
- Compatibility-only pending candidate workflow if replaced by a general proposal contract.

### 9. How difficult is migration?

Moderate to high, depending on whether v2 unifies storage.

Human-memory card migration is straightforward. v0/Cardex migration is harder because it contains richer but differently shaped concepts: entities/facts/episodes/preferences, sources/documents/chunks/artifacts, proposals, signals, coaccess edges, and embeddings.

API and MCP migration is the most compatibility-sensitive area. Existing consumers rely on tool names, envelopes, route shapes, and startup behavior.

### 10. What belongs in Mimir, Hrafnar, or Muninn v2?

Muninn v2:

- Durable memory records.
- Evidence/provenance.
- Event log.
- Association graph persistence.
- Recall records.
- Vector index persistence.
- Salience signal storage and hooks.
- Migration/export/import contracts.

Mimir:

- Associative processing.
- Salience propagation algorithms.
- World-state/topology interpretation.
- Memory proposal generation.
- Recall strategy experimentation.
- Contradiction/cluster analysis.

Hrafnar:

- Runtime protocol translation.
- Human/LLM/device interaction protocols.
- MCP/HTTP/CLI bridges.
- Prompt-ready rendering.
- Session interpretation.
- Wearable/device context ingress adapters.

## Recommendation

Choose Option B: preserve durable primitives, but rewrite the architecture around them.

This means Muninn v2 should not be a from-scratch discard of all existing work. It should be a clean substrate boundary that imports or adapts current human-memory cards, evidence, events, and selected Cardex multimodal/association structures.

Current Muninn can evolve into v2 only if the v2 work explicitly separates substrate kernel, associative processing, and interpreter/runtime concerns. Without that separation, incremental evolution will continue accumulating concept drift.

## Confidence

Confidence: 0.78.

The evidence is strong for preserving primitives and avoiding a pure rewrite. Confidence is lower on migration cost because live production data volume and downstream consumer behavior were not exhaustively inspected.
