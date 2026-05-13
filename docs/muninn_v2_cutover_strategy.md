# Muninn v2 Cutover Strategy

Date: 2026-05-13

## Current Status

There is no cutover in this phase. Muninn v2 is adjacent and opt-in.

## Cutover Principles

- v1 remains production source of truth until explicit promotion.
- v2 must prove a narrow single-project pilot before broader adoption.
- v2 imports must be reproducible and non-destructive.
- v1 and v2 outputs must be compared before any consumer switches.
- Rollback must be path-level, not data-repair-level.

## Single-Project Pilot

1. Select one non-critical v1 human-memory space.
2. Create a new v2 DB file for that pilot.
3. Read v1 records with `V1ReadAdapter`.
4. Import with `V1ImportAdapter`.
5. Export the v2 bundle.
6. Compare counts:
   - v1 cards vs v2 cards
   - v1 relations vs v2 associations
   - v1 evidence joins vs v2 nested evidence
7. Manually inspect v2 JSONL export.
8. Keep Codex startup on v1.

## Pilot Acceptance Criteria

A pilot is acceptable only if:

- v1 DB remains byte/row-count stable during read/import.
- v2 import is repeatable.
- v2 export is deterministic enough for review.
- unsupported v1 records are explicitly reported.
- no MCP/HTTP/CLI compatibility tests regress.

## Dry-Run Pilot Command

The first explicit pilot command is:

```bash
PYTHONPATH=src python3 -m muninn.v2.cli pilot-import \
  --v1-db /path/to/human_memory.db \
  --v2-db /path/to/pilot_v2.db \
  --space-key repo:example \
  --project-path /path/to/project \
  --out-dir /path/to/pilot_artifacts \
  --dry-run \
  --strict
```

The command defaults to dry-run behavior. It writes the requested `--v2-db` only when `--write-v2` is passed. In dry-run mode it writes reports, JSON/JSONL exports, and a scratch v2 DB inside `--out-dir`.

Each pilot also emits:

- `migration_ledger.jsonl` for per-record source-to-target mapping
- `migration_checksums.json` for deterministic source/target/bundle/ledger/fidelity checksums
- `record_fidelity_report.json` and `.md` for side-by-side v1/v2 field comparisons

For the initial Null_Signal pilot:

- v1 DB: `/home/unix/.local/share/muninn/human_memory.db`
- project path: `/mnt/data/Null_Signal`
- space key: `repo:8086caa7ff98deef`
- output directory: `/mnt/data/Muninn/reports/pilots/null_signal_v2_import`

For the first non-empty ReadyPlayer1 pilot:

- v1 DB: `/home/unix/.local/share/muninn/human_memory.db`
- project path: `/mnt/data/ReadyPlayer1`
- space key: `repo:5059f410815720ea`
- output directory: `/mnt/data/Muninn/reports/pilots/readyplayer1_v2_import`

## Future Slices Before Cutover

1. Add v1 interaction-event mapping to `MemoryEvent`.
2. Add v0 entity/fact/episode/preference mapping.
3. Add Cardex source/chunk/artifact mapping.
4. Add migration ledger with source checksums and import manifests.
5. Add side-by-side recall comparison for a single project.
6. Add read-only v2 MCP inspection tools behind explicit opt-in.
7. Define explicit promotion gate for one consumer.

## Rollback Strategy

Before any cutover:

- v1 remains unchanged and rollback is simply disabling v2 consumers.

After a future opt-in consumer cutover:

- Keep v1 read path available.
- Keep v1 DB untouched until a retention window closes.
- Keep v2 import manifest and export bundle for audit.
- Repoint consumer to v1 if parity checks fail.

## Hard Blocks To Cutover

Do not cut over while any of these are true:

- v2 lacks migration ledger.
- v2 lacks interaction-event mapping.
- v2 lacks side-by-side recall comparison.
- v2 import cannot report unsupported records.
- v2 contracts lack versioned compatibility tests.
- v1 MCP/Codex tests regress.

## Recommendation

The next cutover-related work should be side-by-side recall comparison against a non-empty project after at least one dry-run import report has been reviewed.
