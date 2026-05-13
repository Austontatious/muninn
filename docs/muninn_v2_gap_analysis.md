# Muninn v2 Gap Analysis

Date: 2026-05-13

## Baseline

Current Muninn already contains many memory-substrate ingredients, but they are split across human-memory, v0 memory, Cardex, SDK, and runtime adapters. Muninn v2 should consolidate the durable substrate model while allowing Mimir and Hrafnar to own higher-level cognition and protocol/runtime concerns.

## Strong Existing Foundations

### Durable Memory Envelopes

Human-memory `cards` provide a durable unit with:

- `kind`
- `status`
- `salience`
- `title`
- `summary`
- `body`
- `source_confidence`
- `context_json`
- tags
- evidence joins
- lineage relations

This is a credible kernel for generalized memory if `kind` and `context_json` become typed extension points instead of convention-only fields.

### Provenance

The separate `evidence` table and `card_evidence` join are strong. Evidence is not flattened into card text, which is the right substrate posture. The write-contract requirement for structured evidence is also worth preserving.

### Spaces

`spaces` and `space_aliases` solve a real identity problem. The current repo/path/git heuristics are project-overfit, but the abstraction of canonical scope plus aliases is durable.

### Events

`interaction_events` is the right place for raw behavior and recall/promotion signals. The current shape is not broad enough for generalized cognition, but the separation from cards is correct.

### Rehydration Explainability

`rehydrate_bundle` reports stage attempts, result counts, skip reasons, zero-result reasons, policy diagnostics, and vector diagnostics. This is a strong explainability baseline.

### Vector Caution

The vector layer is intentionally additive and gated. `off`, `shadow`, and `augment` modes are a good operational model for avoiding silent semantic drift.

## Missing Substrate Primitives

### General Entities

Current support is split:

- v0 has `entities`, `facts`, `episodes`, `preferences`.
- Cardex has `cards.type` values such as `contact`, `place`, `media`, `thread`.
- human-memory mostly encodes domain identity in `kind`, `tags`, and `context_json`.

Muninn v2 needs first-class generalized entities:

- person
- place
- organization
- device
- repository
- artifact
- concept
- task
- event
- custom

The entity model should not be synonymous with project spaces.

### Associations

Current association support:

- `card_relations`: lineage-like edges.
- Cardex `coaccess_edges`: recall/access co-occurrence.
- JSON metadata for atlas/boundary relations.

Missing:

- Typed many-to-many arbitrary association graph.
- Edge provenance.
- Edge confidence.
- Edge salience.
- Edge temporal validity.
- Directionality semantics beyond card lineage.

### Recall History

Human-memory rehydration emits diagnostics but does not persist recall events as first-class recall history. Cardex has `signals` and coaccess but this is not unified.

Muninn v2 should persist:

- query/session fingerprints
- recalled item ids
- accepted/injected item ids
- ignored/suppressed item ids
- user/agent feedback
- downstream outcome linkage

### Salience And Decay

`cards.salience` exists, but propagation and decay are not a stable substrate contract.

Muninn v2 needs:

- stored salience signals
- salience calculators as replaceable processors
- decay policy metadata
- provenance for salience changes
- explicit Mimir hook points

The substrate should store signals and resulting state. Mimir should own most propagation algorithms.

### Multimodal Assets

Cardex is ahead of human-memory here:

- `sources`
- `documents`
- `chunks`
- `artifacts`
- multimodal `card_embeddings`
- `card_refs`

Human-memory evidence supports `blob_path`, but multimodal assets are not first-class in the active substrate path.

Muninn v2 should preserve Cardex's asset/source/chunk/artifact direction, but unify it with cards/evidence instead of keeping it as a separate plane.

### Ontology Generalization

Current memory kinds are heavily workflow-shaped:

- `decision`
- `constraint`
- `interface`
- `runbook`
- `policy.*`
- `procedure.card`
- `atlas.*`

These are useful profiles, not substrate categories. Muninn v2 should make them app/profile-defined types using stable memory contracts.

## Overfit Areas

### Codex And Project Memory

Overfit indicators:

- default client `codex-vscode`
- repo/path/remote-based space identity as dominant resolution
- task-start protocol centered on Codex session rehydration
- audit gates for ordered start discipline
- default durable kinds tuned for software project continuity

Recommendation: keep as `ProjectMemoryProfile` or `CodexAdapter`, not substrate behavior.

### MCP Assumptions

The MCP layer has strong practical value, but it currently owns:

- input compatibility coercion
- slash aliases
- request telemetry
- rate limits
- card write warnings
- atlas context shaping
- rehydration output normalization

These belong in adapters or Hrafnar-like runtime layers.

### Retrieval Assumptions

Current rehydration assumes:

- lexical stage first
- strict/soft scope
- global fallback
- kind bonuses for `constraint`, `decision`, `runbook`, `interface`
- evidence count boosts

These are good profile defaults. They should not be hard-coded v2 substrate rules.

### Policy/Adaptation

Policy-state cards and interaction promotion are valuable, but the behavior learning loop belongs above the substrate. Muninn v2 should store policy memories and raw events, while Mimir or a policy processor owns promotion and salience.

## Technical Debt Gaps

### Split Storage Planes

The two schemas model overlapping concepts differently:

- human-memory: card/evidence/relation/event.
- v0/Cardex: entity/fact/episode/preference plus card/source/chunk/artifact/signals.

This is the largest architectural gap.

### Status Inconsistency

The SDK `LifecycleState` allows `revoked`, and `HumanMemoryStore.revoke_card` writes `revoked`, but the human-memory `cards.status` check allows only `active`, `superseded`, and `archived`. This is a concrete sign that contracts and storage are not aligned.

### JSON Metadata As Implicit Schema

Important structures live in `context_json`:

- provenance details
- policy state
- procedure payload
- atlas payload
- adaptation payload

These should become typed payload contracts or extension schemas.

### Runtime Coupling

The same runtime files currently handle transport, validation, telemetry, compatibility, and domain orchestration. This slows substrate evolution.

## v2 Required Additions

Muninn v2 should add or stabilize:

- `memory_items`
- `entities`
- `events`
- `evidence`
- `associations`
- `recall_events`
- `salience_signals`
- `asset_refs`
- `embeddings`
- `spaces`
- `type_registry`
- `migration_ledger`

This does not require all tables to be new. It requires one coherent contract.

## Gap Severity

High severity:

- split storage planes
- contract/storage enum mismatch
- missing association graph
- missing recall history
- JSON metadata carrying critical schema

Medium severity:

- overfit project/Codex kinds
- MCP/runtime coupling
- vector model split
- global fallback noise

Low severity:

- SQLite as initial storage
- FTS-first retrieval
- current deterministic hash embeddings for test/dev

## Bottom Line

Muninn v2 should preserve the human-memory kernel and selected Cardex capabilities, but it needs a clean substrate contract. The gap is architectural coherence, not absence of good primitives.
