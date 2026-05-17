# Muninn v2 RehydrateResponseV1

`RehydrateResponseV1` is the stable JSON envelope for Muninn v2 shadow rehydration previews and future opt-in agent-context experiments.

It is not a v1 API contract, not a live MCP/Codex default, and not a production cutover mechanism.

## Contract Files

- JSON Schema: `docs/contracts/muninn_v2/v1/schemas/rehydrate-response.v1.schema.json`
- Valid example: `docs/contracts/muninn_v2/v1/examples/valid/rehydrate-response.shadow-preview.v1.json`
- Schema version: `muninn.v2.rehydrate_response.v1`
- Contract version: `1.0.0`

## Required Envelope Sections

Every `RehydrateResponseV1` payload includes:

- `schema`: schema name, contract version, schema version, and schema path.
- `request`: query text, explicit v2 source DB metadata, filters, retrieval mode, and budget controls.
- `composition`: deterministic preview composition stages.
- `selected_memory`: selected memory cards, events, and evidence refs.
- `explanations`: score/ranking details when requested, plus stable per-card selection reasons.
- `uncertainty`: context gaps, warnings, and usability marker.
- `budget`: limits, selected counts, budget usage, duplicate removal, and omitted counts.
- `retrieval_provenance`: retrieval mode, backend, result count, query profile, provider status, and retrieval paths.
- `fallbacks`: explicit fallback/degradation markers such as JSON-vector fallback or lexical fallback.
- `agent_briefing`: deterministic non-LLM briefing derived from selected card titles and summaries.

## Semantics

The selected memory is durable v2 memory projected into an agent-consumable envelope:

- Cards remain canonical v2 memory records.
- Evidence is attached only when present; the envelope never fabricates evidence.
- Events are reserved in the schema and currently emitted as an empty array by `shadow-rehydrate-preview`.
- Vectors remain optional derived indexes and appear only through retrieval provenance or fallback markers.
- Budgeting prefers primary retrieval results over recent supplements.
- Recent supplements are continuity context, not query hits.

## Boundary

Future APIs and agent-context experiments that consume v2 rehydration output must consume this envelope instead of relying on command-specific JSON fields. Changing the envelope requires a new version.

This contract is not Mimir cognition. It does not perform motif detection, salience propagation, spreading activation, hidden-link discovery, or autonomous reasoning.
