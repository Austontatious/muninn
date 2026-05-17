# Muninn v2 Pilot Import Report

- Mode: `write_v2`
- v1 DB: `/home/unix/.local/share/muninn/human_memory.db`
- Requested v2 DB: `reports/pilots/lexi_v2_shadow_2026-05-17_final/lexi_shadow_v2.db`
- Written v2 DB: `reports/pilots/lexi_v2_shadow_2026-05-17_final/lexi_shadow_v2.db`
- Space key: `repo:0c321b2a6f183a95`
- Project path: `/mnt/data/Lex`
- v1 row counts changed: `no`

## Counts

- Scanned cards: 79
- Migrated cards: 79
- Evidence refs: 155
- Associations: 2
- Entities: 1
- Ontology profiles: 1
- Unsupported records: 0
- Ledger entries: 238
- Fidelity records checked: 238
- Fidelity failures: 0

## Safety

The v1 database was opened using SQLite read-only mode and `PRAGMA query_only=ON`.
The requested v2 DB is written only when `--write-v2` is passed.

## Unsupported Records

- `interaction_events`: 0 (present=true)
- `card_vectors`: 0 (present=true)
- `vector_index_state`: 0 (present=true)
