# Muninn Vector / Session / Retrieval Drift Review

Date: 2026-05-13
Branch: `muninn-v2-adjacent-core-pilot-recall-parity`

## Decision

Salvage the useful vector/session/retrieval concepts into Muninn v2 only.

Do not bless the drift as live v1 behavior. The v1 schema, bootstrap, CLI, MCP, and rehydration changes were reverted or discarded after the inventory was captured.

## Root Cause Of Vector Health Warning

The reported vector health issue is expected for the experimental drift:

- sqlite_vec is unavailable in this environment.
- the experimental v1 vector tables were not part of committed production v1 schema.
- no committed v1 vector rebuild job has populated vectors.
- live v1 does not depend on vector health; API/MCP health remains OK.

The correct response is not to auto-create v1 vector tables. The safe path is v2 optional derived-index diagnostics.

## Salvaged Concepts

- deterministic local hash embeddings for offline diagnostics
- explicit index health with eligible/indexed/missing/stale counts
- dry-run rebuild by default
- explicit `--write-index` before persistence
- fallback lexical recall when no vector index is available
- fixture-based retrieval eval
- record-absence vs retrieval-mismatch classification
- optional session-shaped retrieval report helper

## Discarded Or Deferred Concepts

- v1 `card_vectors` and `vector_index_state` schema additions
- v1 bootstrap self-healing table creation
- v1 CLI `vectors`, `start-session`, and retrieval-eval commands
- v1 MCP `muninn.session.start` registration
- v1 `rehydrate.bundle` vector `shadow`/`augment` behavior
- vector graduation and shadow-promotion gates
- Mimir-adjacent cognition behavior such as salience propagation or hidden-link discovery

## Resulting Placement

The salvage lives under:

- `src/muninn/v2/indexes/`
- `src/muninn/v2/retrieval/`
- `src/muninn/v2/eval/`
- `src/muninn/v2/diagnostics/`
- `src/muninn/v2/session/`

All new commands require explicit v2 DB paths. None use production v1 defaults.
