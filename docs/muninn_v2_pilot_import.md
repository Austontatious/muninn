# Muninn v2 Pilot Import

Date: 2026-05-13

## Purpose

The v2 pilot importer is a safe, explicit, single-project dry-run path from Muninn v1 human-memory records into adjacent Muninn v2 artifacts.

It is not a cutover, not an automatic migration, and not part of live Codex/MCP startup.

## Command

Run the pilot with:

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

Default behavior is dry-run. The requested `--v2-db` is not written unless `--write-v2` is passed.

## Safety Contract

- `--v1-db` is required.
- `--v2-db` is required even in dry-run mode.
- `--space-key` is required.
- `--project-path` is required.
- `--out-dir` is required.
- v1 is opened through SQLite `mode=ro`.
- v1 connections set `PRAGMA query_only=ON`.
- v1 row counts are captured before and after the run.
- any v1 row-count change fails the command.
- no production DB path is selected by default.
- no migration runs on import/startup.

Dry-run writes only reports, exports, and a scratch v2 DB under `--out-dir`.

## Current Mapping

| v1 source | v2 target | Status |
| --- | --- | --- |
| `cards` | `MemoryCard` | mapped |
| `evidence` + `card_evidence` | `EvidenceRef` nested under cards and exported separately | mapped |
| `card_relations` | `MemoryAssociation` | mapped when both cards are in the selected space |
| `spaces` | `OntologyProfile` | mapped |
| selected project path/repo identity | `MemoryEntity` | mapped as a project entity |
| `interaction_events` | `MemoryEvent` | reported unsupported in this slice |
| `card_vectors` | derived vector layer | reported unsupported |
| `vector_index_state` | store-local operational metadata | reported unsupported |

## Output Artifacts

The pilot writes:

- `pilot_import_report.md`
- `pilot_import_report.json`
- `v1_row_count_before_after.json`
- `unsupported_records.json`
- `ambiguous_records.json`
- `migrated_cards.jsonl`
- `migrated_events.jsonl`
- `migrated_entities.jsonl`
- `migrated_associations.jsonl`
- `evidence_refs.jsonl`
- `ontology_profile.json`
- `v2_export_bundle.json`
- `v2_export_bundle.jsonl`
- `scratch_v2.db` in dry-run mode
- `migration_ledger.jsonl`
- `migration_checksums.json`
- `record_fidelity_report.json`
- `record_fidelity_report.md`

## Interpreting Reports

Use `pilot_import_report.json` for machine-readable counts. The important fields are:

- `mode`
- `space_key_canonical`
- `counts`
- `v1_row_counts_changed`
- `unsupported_records`
- `ambiguous_records`
- `artifacts`

`v1_row_count_before_after.json` is the safety gate artifact. Every row should have `"changed": false`.

`migration_ledger.jsonl` is a deterministic per-record mapping ledger. Each entry includes source table/id, target record type/id, source checksum, target checksum, and fidelity status.

`migration_checksums.json` records SHA-256 checksums over canonical JSON payloads for source groups, target groups, the exported bundle, the migration ledger, and the fidelity report.

`record_fidelity_report.json` compares source-side v1 rows with target-side v2 records for cards, evidence refs, associations, ontology profiles, and project entities. A pilot intended to prove mapping quality should have `summary.fidelity_passed = true`.

## Null_Signal Pilot

Null_Signal was chosen as the first sacrificial pilot because it is a low-risk project space and has an unambiguous v1 human-memory identity:

- project path: `/mnt/data/Null_Signal`
- git remote: `https://github.com/Austontatious/Null_Signal.git`
- normalized remote: `https://github.com/austontatious/null_signal`
- v1 space key: `repo:8086caa7ff98deef`

At the time this pilot command was added, the v1 human-memory space existed but contained no cards or interaction events.

## ReadyPlayer1 Pilot

ReadyPlayer1 is the first non-empty dry-run target:

- project path: `/mnt/data/ReadyPlayer1`
- git remote: `https://github.com/Austontatious/ReadyPlayer1.git`
- normalized remote: `https://github.com/austontatious/readyplayer1`
- v1 space key: `repo:5059f410815720ea`

At the time this document was updated, the ReadyPlayer1 v1 space contained 48 cards and 197 distinct evidence refs.

## No-Op Guarantee

Rollback is deletion of the pilot output directory. v1 remains the production source of truth and is never written by the pilot importer.

## Next Step

The next migration slice should compare v1 and v2 recall outputs side by side for a project with non-empty cards before any consumer reads from v2.
