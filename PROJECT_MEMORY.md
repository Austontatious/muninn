# Project Memory — Muninn (stateful)

## Mission
Build a standalone, pluggable memory harness for LLM agents that supports:

- durable canonical memory (facts/episodes/preferences) with provenance
- safe write-gating and auditability
- conceptual recall via compact memory cards
- clean integration interfaces (HTTP + provider adapters)

## Current Snapshot

- Repo scaffold created (FastAPI + SQLite)
- Schemas defined for core objects + memory cards
- Endpoints implemented:
  - health
  - write_candidates
  - retrieve
  - render_cards
  - rehydrate
  - upsert_embeddings
  - query_vector
  - memory/version
- Retrieval supports mode toggle:
  - `fts` (default)
  - `vector` (caller-provided query embedding)
  - `hybrid` (FTS + vector fused with RRF)
- Embeddings are caller-provided and stored in SQLite as normalized float32 blobs
- Optional sqlite-vec acceleration added with automatic fallback to brute-force
- Namespace isolation enforced in storage/query paths (v0.5)
- Admin reindex path added to rebuild sqlite-vec mappings from canonical embeddings
- Typed `MuninnClient` + OpenAI/Anthropic/local adapters added with contract tests (v0.6)
- Confirm-required lifecycle added: stage/list/confirm with durable pending queues (v0.7)
- Ops hardening added: cleanup endpoint, debug stats, readonly mode, optional API key middleware (v0.8)

## Key Constraints

- Avoid storing raw transcripts as “memory”
- Memory is facts/episodes/preferences with confidence + provenance
- “Instruction injection” never stored (firewall)
- Muninn stays model-agnostic (no built-in embedding model coupling)

## Next Steps (nearest)

- Add ANN backend behind existing vector store interface (sqlite-vec / pgvector)
- Add admin authz layer for `/v0/admin/*` endpoints
- Add background reindex flow for sqlite-vec mappings after long brute-force-only periods
- Add contradiction ledger + merge/dedupe policies
- Add sensitivity tiers + redaction filters
