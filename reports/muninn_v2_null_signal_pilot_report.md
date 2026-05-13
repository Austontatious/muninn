# Muninn v2 Null_Signal Pilot Report

Date: 2026-05-13

## Executive Summary

The first real single-project dry-run pilot completed safely for Null_Signal.

This was a dry-run only. It did not write the requested v2 DB and did not mutate v1. The command wrote reports, JSON/JSONL exports, and a scratch v2 DB under `reports/pilots/null_signal_v2_import/`.

## Command

```bash
PYTHONPATH=src python3 -m muninn.v2.cli pilot-import \
  --v1-db /home/unix/.local/share/muninn/human_memory.db \
  --v2-db /mnt/data/Muninn/reports/pilots/null_signal_v2_import/null_signal_v2.db \
  --space-key repo:8086caa7ff98deef \
  --project-path /mnt/data/Null_Signal \
  --out-dir /mnt/data/Muninn/reports/pilots/null_signal_v2_import \
  --dry-run \
  --strict
```

## Space Identity

- project path: `/mnt/data/Null_Signal`
- git remote: `https://github.com/Austontatious/Null_Signal.git`
- normalized remote: `https://github.com/austontatious/null_signal`
- canonical v1 space key: `repo:8086caa7ff98deef`
- v1 DB: `/home/unix/.local/share/muninn/human_memory.db`

The selector was unambiguous. `ambiguous_records.json` contains no records.

## Migration Counts

- scanned cards: 0
- migrated cards: 0
- migrated evidence refs: 0
- migrated associations: 0
- migrated events: 0
- created entities: 1
- created ontology profiles: 1
- unsupported records in selected space: 0

The Null_Signal v1 human-memory space exists but currently has no cards, evidence, card relations, interaction events, card vectors, or vector index records scoped to it.

## v1 Immutability Verification

All v1 row counts were unchanged.

Relevant counts:

- `spaces`: 33 before, 33 after
- `cards`: 506 before, 506 after
- `evidence`: 1369 before, 1369 after
- `card_relations`: 5 before, 5 after
- `interaction_events`: 2 before, 2 after
- `card_vectors`: 0 before, 0 after
- `vector_index_state`: 0 before, 0 after

## Output Artifacts

- `reports/pilots/null_signal_v2_import/pilot_import_report.md`
- `reports/pilots/null_signal_v2_import/pilot_import_report.json`
- `reports/pilots/null_signal_v2_import/v1_row_count_before_after.json`
- `reports/pilots/null_signal_v2_import/unsupported_records.json`
- `reports/pilots/null_signal_v2_import/ambiguous_records.json`
- `reports/pilots/null_signal_v2_import/migrated_cards.jsonl`
- `reports/pilots/null_signal_v2_import/migrated_events.jsonl`
- `reports/pilots/null_signal_v2_import/migrated_entities.jsonl`
- `reports/pilots/null_signal_v2_import/migrated_associations.jsonl`
- `reports/pilots/null_signal_v2_import/evidence_refs.jsonl`
- `reports/pilots/null_signal_v2_import/ontology_profile.json`
- `reports/pilots/null_signal_v2_import/v2_export_bundle.json`
- `reports/pilots/null_signal_v2_import/v2_export_bundle.jsonl`
- `reports/pilots/null_signal_v2_import/scratch_v2.db`

The requested v2 DB path `reports/pilots/null_signal_v2_import/null_signal_v2.db` was not created because the run was dry-run mode.

## Known Gaps

- This pilot did not exercise non-empty real project cards because Null_Signal currently has none.
- Interaction events are reported unsupported rather than mapped to `MemoryEvent`.
- v1 vector/index metadata is reported unsupported and remains derived, non-canonical state.
- No migration ledger/checksum manifest exists yet.
- No side-by-side recall comparison exists yet.

## Recommended Next Slice

Run the same dry-run importer against one low-risk project with existing cards/evidence/relations, then add a side-by-side v1/v2 recall comparison report before any consumer reads from v2.
