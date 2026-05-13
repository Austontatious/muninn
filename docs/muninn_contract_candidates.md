# Muninn Contract Candidates

Date: 2026-05-13

## Purpose

This document identifies interfaces that should remain stable regardless of whether Muninn v2 is implemented as an upgrade or a new substrate.

## Core Contracts

### MemoryItem

Stable durable memory envelope.

Required concepts:

- id
- type/kind
- title/summary/body or content payload
- typed payload
- lifecycle state
- space/scope
- created/updated timestamps
- confidence/trust
- salience
- tags
- evidence refs
- provenance

Current sources:

- `core.contracts.MemoryItem`
- human-memory `cards`
- Cardex `cards`

### EvidenceRef

Stable provenance reference.

Required concepts:

- type
- ref/URI/path
- excerpt
- metadata
- source identity
- capture time
- integrity hash where applicable

Current sources:

- `core.contracts.EvidenceRef`
- human-memory `evidence`
- Cardex `sources`, `documents`, `chunks`, `artifacts`

### MemoryStore

Stable storage interface.

Required operations:

- write item
- fetch item
- update lifecycle
- attach evidence
- add association
- record event
- query by id/type/scope
- export/import batch
- migration ledger access

Current source:

- `core.storage.HumanMemoryStore`

Required fix:

- Align lifecycle/status enums before this becomes authoritative.

### SpaceResolver

Stable identity resolution interface.

Required operations:

- resolve from explicit scope
- resolve from environment/context
- list aliases
- register alias
- explain resolution

Current source:

- `human_memory.spaces`

v2 change:

- Repo/path/git identities become one resolver profile, not the substrate identity model.

### EntityResolver

New stable contract.

Required operations:

- resolve entity by canonical id
- resolve aliases
- merge/split identity
- attach type labels
- attach evidence

Current sources:

- legacy v0 `entities`
- Cardex `card_refs` with `ref_type='entity'`
- JSON metadata conventions

### AssociationStore

New stable contract.

Required operations:

- add edge
- remove/deactivate edge
- query neighbors
- explain edge provenance
- store weight/confidence/salience
- store temporal validity

Current sources:

- human-memory `card_relations`
- Cardex `coaccess_edges`
- atlas relationship cards

### EventLog

Stable append-oriented event interface.

Required operations:

- append event
- query by actor/session/scope/time/signal
- link event to memory item
- export event stream

Current sources:

- human-memory `interaction_events`
- legacy `audit_log`
- telemetry JSONL

### RecallEngine

Stable retrieval interface.

Required operations:

- recall query
- return ranked items
- return stage decisions
- return suppressed/empty reasons
- return diagnostics
- support pluggable rankers

Current sources:

- `human_memory.rehydration.rehydrate_bundle`
- `core.bundle`
- Cardex retrieval
- legacy memory retrieval

Boundary:

- Muninn v2 should provide deterministic recall execution and explainability.
- Mimir should own advanced salience/reasoning strategies plugged into this interface.

### RehydrationProvider

Stable context-bundle interface.

Required operations:

- build bundle
- explain bundle
- project bundle to a target consumer profile
- preserve bundle fingerprints for compatibility testing

Current sources:

- `human_memory.session_start`
- `human_memory.rehydration`
- `core.contracts.BundleResult`

Boundary:

- Prompt rendering belongs in Hrafnar/runtime adapters.

### VectorIndex

Stable optional vector persistence/search interface.

Required operations:

- upsert vector
- delete vector
- rebuild/index status
- query by vector
- expose backend diagnostics
- support shadow/augment policy externally

Current sources:

- `human_memory.vector_store`
- legacy `vector.store`
- Cardex `card_embeddings`

### SalienceSignalSink

Stable signal ingestion interface.

Required operations:

- record access
- record coaccess
- record feedback/outcome
- record decay/reinforcement signal
- expose signals to processors

Current sources:

- Cardex `signals`
- Cardex `coaccess_edges`
- human-memory `interaction_events`
- `cards.salience`

Boundary:

- Muninn stores salience state and signals.
- Mimir computes propagation and associative weighting.

### ProposalReview

Stable guarded write-proposal interface.

Required operations:

- stage proposal
- validate proposal
- preview effects
- approve/reject
- record decision evidence
- map external proposal batches into memory writes

Current sources:

- legacy pending candidate workflow
- Cardex proposals
- `mimir_proposals.py`
- ChatGPT bridge staged confirmation

### MigrationAdapter

Stable migration interface.

Required operations:

- enumerate source records
- project to v2 envelopes
- validate loss/risk
- write migration ledger
- support dry run
- support rollback/export manifests

Current source:

- Not present as a first-class contract.

## Transport Contracts

These should remain stable as adapters but should not define substrate internals:

- MCP tool contracts.
- `/v0/*` HTTP route contracts.
- SDK public methods.
- CLI command outputs used by automation.
- ChatGPT bridge tool surface.

## Contract Stability Priority

Highest priority:

- `MemoryItem`
- `EvidenceRef`
- `MemoryStore`
- `SpaceResolver`
- `EventLog`
- `RecallEngine`
- `AssociationStore`

Second priority:

- `EntityResolver`
- `VectorIndex`
- `RehydrationProvider`
- `ProposalReview`
- `MigrationAdapter`
- `SalienceSignalSink`

Adapter priority:

- MCP tools.
- HTTP routes.
- CLI.
- ChatGPT bridge.

## Recommendation

Before implementation, define these contracts in a v2 ADR and executable compatibility tests. Storage can change behind them; transport adapters should depend on them rather than reaching into storage modules.
