# Muninn v1 Compatibility Strategy

Date: 2026-05-13

## Compatibility Promise

Muninn v1 remains the live production memory system. The v2 foundation does not change:

- MCP tool names
- MCP payload contracts
- `/v0/*` HTTP routes
- Cardex routes
- CLI commands
- v1 schemas
- v1 production DB paths
- v1 startup and rehydration behavior

## Current Live Surfaces

Codex-facing human-memory MCP uses:

- `muninn.spaces.resolve`
- `muninn.cards.recent`
- `muninn.cards.search`
- `muninn.rehydrate.bundle`
- `muninn.session.start`
- `muninn.cards.upsert`
- `muninn.cards.supersede`
- `muninn.cards.merge`
- policy/adaptation tools

Legacy and bridge surfaces still include:

- `/v0/memory/*`
- `/v0/admin/*`
- `/cards`, `/sources`, `/retrieve`, `/propose`, `/confirm`, `/reject`
- ChatGPT bridge tools under `apps/muninn_mcp`

These remain v1/compatibility surfaces.

## Storage Isolation

v1 storage remains:

- `MUNINN_DB_PATH` or `~/.local/share/muninn/muninn.db`
- `MUNINN_HUMAN_MEMORY_DB_PATH` or `~/.local/share/muninn/human_memory.db`

v2 storage is only:

- an explicit path passed to `SQLiteMemoryStore`

No automatic v1-to-v2 migration exists.

## v1 To v2 Mapping

Current adapter support:

| v1 source | v2 target | Status |
| --- | --- | --- |
| `cards` | `MemoryCard` | implemented |
| `evidence` + `card_evidence` | nested `EvidenceRef` | implemented |
| `card_relations` | `MemoryAssociation` | implemented |
| `spaces` | `OntologyProfile` | implemented as profile projection |
| `interaction_events` | `MemoryEvent` | deferred |
| `card_vectors` | derived vector index | deferred |
| v0 `entities` | `MemoryEntity` | deferred |
| Cardex sources/chunks/artifacts | evidence/assets | deferred |
| Cardex signals/coaccess | recall/salience/associations | deferred |

## Unsupported In Phase 1

The v1 adapter does not yet map:

- v0 fact/episode/preference memory
- Cardex multimodal sources
- interaction events
- policy/adaptation projections
- vector rows
- pending candidate workflows
- audit log rows

Unsupported records remain safely in v1.

## Safety Rules

- Use `V1ReadAdapter` for read-only inspection.
- Use `V1ImportAdapter` only with an explicit v2 target store.
- Do not point v2 store at a v1 DB path.
- Do not route live Codex startup to v2.
- Do not delete v1 records after import.
- Treat v2 pilot exports as validation artifacts, not production source of truth.

## Rollback

Rollback is immediate because v1 is untouched:

1. Stop using the v2 pilot DB.
2. Delete the v2 pilot DB if desired.
3. Continue using existing v1 MCP/HTTP/CLI surfaces.

No v1 restoration step is required.
