# Muninn Rewrite vs Upgrade

Date: 2026-05-13

## Recommendation

Choose Option B: hybrid preserve-and-re-architect.

Muninn should evolve into Muninn v2 around a clean substrate contract, but that v2 should preserve current durable primitives and provide migration adapters from existing schemas. A pure upgrade is too likely to preserve split-brain architecture. A pure rewrite is too likely to discard proven memory primitives and operational lessons.

## Why Not Pure Incremental Upgrade

Incremental upgrade is attractive because current Muninn works and has meaningful tests, tools, and runtime behavior. The problem is that the architectural debt is structural:

- two storage planes
- competing memory models
- transport/domain coupling
- project/Codex assumptions in core paths
- retrieval policy embedded in substrate code
- policy/adaptation logic mixed with durable storage
- implicit schemas inside JSON metadata

These cannot be cleaned up safely by ordinary feature work unless v2 contracts are defined first.

## Why Not Clean Rewrite

A clean rewrite would produce the cleanest design surface, but current Muninn has real long-term assets:

- evidence discipline
- canonical space aliases
- durable cards
- lineage relations
- interaction events
- deterministic rehydration
- vector safety posture
- SDK app-spec direction
- compatibility tests and docs

Discarding these would add risk without enough benefit. The existing codebase has learned several hard lessons that a rewrite would have to re-learn.

## Option Comparison

| Option | Advantages | Risks | Complexity | Migration Pain | Maintainability | Cleanliness |
| --- | --- | --- | --- | --- | --- | --- |
| A: Incremental evolution | Lowest disruption, preserves consumers | May preserve split-brain model | Medium | Low now, higher later | Medium | Medium-low |
| B: Hybrid | Preserves primitives, enables clean v2 | Requires disciplined contracts and adapters | High | Medium | High | High |
| C: Clean rewrite | Cleanest blank slate | Highest migration and regression risk | Very high | High | Potentially high | Very high |

## Strongest Reusable Primitives

1. `cards` as durable memory units.
2. `evidence` plus `card_evidence`.
3. `card_relations`.
4. `spaces` and `space_aliases`.
5. `interaction_events`.
6. Staged rehydration diagnostics.
7. Optional vector index with explicit safety modes.
8. SDK envelope models and app-defined memory specs.
9. Cardex sources/artifacts/chunks for multimodal futures.
10. Cardex signals/coaccess edges as seeds for recall history and salience signals.

## Biggest Technical Debt Risks

1. Split human-memory and v0/Cardex storage planes.
2. Contract/storage mismatch around lifecycle states such as `revoked`.
3. Runtime surfaces directly owning core behavior.
4. JSON metadata acting as unversioned schema.
5. Multiple retrieval implementations with different assumptions.
6. Compatibility paths that may become permanent.
7. Lack of first-class migration ledger.

## Biggest Conceptual Mismatch Risks

1. Muninn absorbing Mimir responsibilities such as salience propagation and associative cognition.
2. Muninn absorbing Hrafnar responsibilities such as protocol interpretation, prompt rendering, and session runtime.
3. Treating project/Codex memory as the substrate model rather than one profile.
4. Treating MCP tool shape as storage architecture.
5. Treating topology/world-state records as Muninn-owned cognition rather than durable memory about external structures.

## Recommended Architecture Direction

Muninn v2 should be:

- durable memory storage
- provenance and evidence system
- event and recall ledger
- association persistence
- salience signal storage
- vector and asset persistence
- stable storage/retrieval contracts

Muninn v2 should not be:

- repo topology engine
- salience reasoning engine
- agent orchestrator
- prompt/runtime interpreter
- device protocol layer
- MCP-first architecture

## Most Important Next Decision

Decide the v2 canonical memory model before writing code.

Specifically, decide whether the v2 primitive is:

1. card-first with typed payloads and entities/associations as attached primitives, or
2. entity/event/assertion-first with cards as projections.

The current evidence favors card-first with typed payloads plus first-class entities, events, evidence, associations, and recall history. This preserves the strongest current primitive while avoiding project-memory overfit.

## Proposed Next Step

Write a v2 substrate ADR that defines:

- canonical objects
- lifecycle states
- association model
- recall event model
- evidence model
- migration ledger
- Mimir hook points
- Hrafnar adapter boundary
- compatibility contract policy

No implementation should start until that ADR and executable contract tests exist.

## Confidence

Confidence: 0.78.

The recommendation is well supported by the inspected schema and runtime structure. The main uncertainty is migration complexity from real local/production data and downstream consumers not inspected in full.
