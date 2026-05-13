# Muninn v2 Recall Parity

Date: 2026-05-13

## Purpose

The recall parity command measures v1/v2 retrieval overlap for one explicit project space. It is opt-in, read-only, and measurement-only.

It does not tune retrieval, migrate data, change live MCP/Codex defaults, or make v2 the production recall path.

## Command

```bash
PYTHONPATH=src python3 -m muninn.v2.cli recall-parity \
  --v1-db /home/unix/.local/share/muninn/human_memory.db \
  --v2-db /mnt/data/Muninn/reports/pilots/readyplayer1_v2_import/scratch_v2.db \
  --space-key repo:5059f410815720ea \
  --project-path /mnt/data/ReadyPlayer1 \
  --out-dir /mnt/data/Muninn/reports/pilots/readyplayer1_v2_import/recall_parity \
  --query-file /mnt/data/Muninn/reports/pilots/readyplayer1_v2_import/readyplayer1_recall_queries.json \
  --limit 10 \
  --strict \
  --include-evidence \
  --include-ranking \
  --include-explanations
```

## Safety Contract

- `--v1-db` is required.
- `--v2-db` is required.
- `--space-key` is required.
- `--project-path` is required.
- `--out-dir` is required.
- v1 is opened with SQLite `mode=ro` and `PRAGMA query_only=ON`.
- v2 is opened with SQLite `mode=ro` and `PRAGMA query_only=ON`.
- v1 and v2 row counts are captured before and after parity.
- any row-count change fails the command.

## Retrieval Paths

v1 uses the existing human-memory card search path:

- `muninn.human_memory.cards.cards_search`
- FTS5 `cards_fts`
- BM25 scoring where lower scores are better

v2 uses a provisional lexical matcher over imported v2 `MemoryCard` records:

- title
- summary
- body
- tags
- evidence ref/excerpt text

The v2 matcher is intentionally simple and explainable. It is not a final recall engine and is not Mimir salience/cognition.

## Metrics

Per query:

- v1 result count
- v2 result count
- matched card IDs
- overlap count
- overlap ratio, defined as Jaccard overlap over returned card IDs
- missing-from-v2 records
- extra-from-v2 records
- rank deltas for overlapping records
- evidence availability comparison
- explanation notes

Aggregate:

- total queries
- average overlap ratio
- full/partial/zero-overlap query counts
- total missing-from-v2
- total extra-from-v2
- evidence mismatches
- likely mismatch causes

## Output Artifacts

The command writes:

- `recall_parity_report.md`
- `recall_parity_report.json`
- `recall_parity_results.jsonl`
- `missing_from_v2.json`
- `extra_from_v2.json`
- `ranking_deltas.json`
- `evidence_parity_report.json`
- `readyplayer1_recall_queries.json`

## Interpretation

Rank differences are expected and acceptable at this stage. Missing cards are the primary concern. Missing evidence on overlapping cards is more serious than rank deltas. Extra v2 cards indicate that the provisional v2 matcher is surfacing records that v1 FTS did not return in the same top-N window.

This command measures retrieval parity. It is distinct from record existence parity, which was covered by the pilot import ledger and fidelity reports.
