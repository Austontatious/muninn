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
- Minimal endpoints implemented:
  - health
  - write_candidates
  - retrieve
  - render_cards
  - rehydrate

## Key Constraints

- Avoid storing raw transcripts as “memory”
- Memory is facts/episodes/preferences with confidence + provenance
- “Instruction injection” never stored (firewall)

## Next Steps (nearest)

- Add hybrid retrieval (BM25 + vector) behind interface
- Add contradiction ledger + merge/dedupe policies
- Add sensitivity tiers + redaction filters
- Add provider adapter examples (OpenAI/Anthropic tool schemas)
