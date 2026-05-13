# Muninn Migration Options

Date: 2026-05-13

## Current Migration Surface

Muninn has at least four migration dimensions:

- human-memory cards/evidence/events/relations
- legacy v0 entity/fact/episode/preference memory
- Cardex cards/sources/chunks/artifacts/embeddings/signals
- API/MCP/CLI compatibility contracts

The migration should be designed as a controlled compatibility program, not a one-time table rewrite.

## Option A: Incremental Muninn v2 Evolution

### Description

Keep the current repo and schemas. Add missing primitives incrementally, slowly route more runtime paths through the SDK, and deprecate v0 over time.

### Advantages

- Lowest immediate disruption.
- Existing MCP/HTTP/CLI consumers continue working.
- Human-memory data can remain in place.
- Current tests and operational runbooks remain useful.
- Easier to land small compatibility-safe changes.

### Risks

- Split-brain schema can persist indefinitely.
- New v2 concepts may accrete around old overfit structures.
- Harder to enforce clean Mimir/Hrafnar boundaries.
- Runtime coupling may remain hidden because compatibility paths keep working.

### Complexity

Medium. Engineering work is steady but not conceptually clean.

### Migration Pain

Low to medium initially. Higher later if delayed consolidation keeps adding adapters.

### Long-Term Maintainability

Medium if aggressively disciplined. Low if treated as ordinary feature work.

### Conceptual Cleanliness

Medium-low.

## Option B: Hybrid Preserve And Re-Architect

### Description

Define Muninn v2 as a clean substrate contract and storage model. Preserve durable primitives from human-memory and Cardex. Build migration adapters from current schemas into the v2 contract. Keep existing runtime/API surfaces as compatibility adapters until consumers move.

### Advantages

- Preserves the real long-term assets.
- Gives v2 a coherent model instead of inheriting all history.
- Enables stable contracts before storage rewrite.
- Allows migration to happen in phases.
- Creates clean boundaries for Mimir and Hrafnar.

### Risks

- Requires more up-front architecture discipline.
- Must maintain adapters during transition.
- Data equivalence tests are required to avoid silent loss.
- Some current behavior may be hard to classify cleanly.

### Complexity

High, but bounded and controllable.

### Migration Pain

Medium. Card/evidence migration is straightforward; v0/Cardex and API compatibility are harder.

### Long-Term Maintainability

High if v2 contracts are enforced and compatibility layers are time-boxed.

### Conceptual Cleanliness

High.

## Option C: Clean Rewrite With Migration Adapters Only

### Description

Start a new substrate implementation. Treat current Muninn only as a source system for export/import and compatibility wrappers.

### Advantages

- Cleanest implementation surface.
- Avoids preserving accidental coupling.
- Allows storage and API contracts to be designed without repo history pressure.
- Strongest chance of pure Muninn/Mimir/Hrafnar separation.

### Risks

- Highest chance of losing proven operational behavior.
- Migration adapters still need to understand all legacy complexity.
- Existing reliability and tests may be discarded prematurely.
- Rehydration, evidence discipline, and space identity lessons may be re-learned.
- Long parallel-run period likely.

### Complexity

Very high.

### Migration Pain

High.

### Long-Term Maintainability

Potentially high, but only after a risky rebuild and migration period.

### Conceptual Cleanliness

Very high in design, uncertain in practice until migration pressure arrives.

## Migration Workstreams

### Schema Migration

Human-memory:

- Map `spaces` and `space_aliases` to v2 scopes.
- Map `cards` to v2 memory items.
- Map `evidence` and `card_evidence` to v2 evidence refs.
- Map `card_relations` to v2 associations with lineage edge types.
- Map `interaction_events` to v2 event log.
- Map `card_vectors` and `vector_index_state` to v2 vector index metadata.

v0:

- Map `entities` to v2 entities.
- Map `facts`, `episodes`, `preferences` to typed memory items or assertions/events/preferences.
- Map `audit_log` to append-only event stream.
- Map `pending_candidates` and `candidate_decisions` to proposal/review records.

Cardex:

- Map `sources`, `documents`, `chunks`, and `artifacts` to v2 assets/evidence.
- Map `card_refs` to associations/evidence refs.
- Map `signals` and `coaccess_edges` to recall/salience/association signals.
- Map `card_embeddings` to vector index rows.

### Metadata Migration

`context_json` needs profile-specific decoders for:

- policy state
- procedure payloads
- atlas records
- adaptation payloads
- provenance metadata

Do not bulk-copy opaque metadata into v2 without type labels and migration provenance.

### Retrieval Migration

Do not try to preserve exact ranking forever. Preserve:

- deterministic explainability
- stage names or stage lineage
- zero-result reasons
- strict/soft scope semantics as a profile
- vector modes and diagnostics
- compatibility output envelopes

Ranking can evolve behind a versioned `RecallEngine` contract.

### API Migration

Keep old surfaces as adapters:

- MCP tool names and payloads.
- `/v0/*` HTTP routes.
- ChatGPT bridge tools.
- CLI commands.

Introduce v2 APIs only after stable internal contracts exist.

### MCP Compatibility

MCP compatibility is a contract problem, not a storage problem. The current tool names should remain stable until a versioned replacement exists:

- `muninn.spaces.resolve`
- `muninn.cards.recent`
- `muninn.cards.search`
- `muninn.rehydrate.bundle`
- `muninn.session.start`
- `muninn.cards.upsert`
- `muninn.cards.supersede`
- `muninn.cards.merge`
- `muninn.policy.*`

## Recommended Sequence

1. Freeze v2 contract candidates in docs and tests.
2. Build read-only exporters for human-memory and v0/Cardex.
3. Define v2 canonical envelopes and migration ledger.
4. Write compatibility projections from current data to v2 envelopes.
5. Run parallel retrieval comparison.
6. Move new integrations to v2 SDK contracts.
7. Keep old API/MCP surfaces as adapters.
8. Deprecate direct v0 writes only after downstream adoption is complete.

## Recommendation

Choose Option B. A pure incremental path is too likely to preserve conceptual drift. A clean rewrite is unnecessary because the current system contains strong, hard-won primitives. Hybrid migration keeps the assets and removes the accidental architecture.
