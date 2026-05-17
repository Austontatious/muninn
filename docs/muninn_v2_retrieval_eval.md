# Muninn v2 Retrieval Eval

Muninn v2 retrieval eval is diagnostic infrastructure. It measures behavior; it does not tune retrieval, change live routing, or alter v1 defaults.

## Contract

- v1 live retrieval remains unchanged.
- v2 retrieval eval requires an explicit `--v2-db`.
- eval fixtures are fixed query sets.
- reports distinguish canonical record existence from retrieval mismatch.
- vector indexes are optional derived inputs.
- eval supports `hybrid`, `lexical`, and `vector` diagnostic modes.
- default eval mode is `hybrid`.
- if no healthy derived vector index is available in vector mode, eval uses labeled lexical fallback.

## Command

```bash
PYTHONPATH=src python3 -m muninn.v2.cli retrieval-eval \
  --v2-db /path/to/v2.db \
  --fixture /path/to/retrieval_fixture.json \
  --out-dir /path/to/reports \
  --retrieval-mode hybrid
```

The command writes:
- `retrieval_eval_report.json`
- `retrieval_eval_report.md`

## Fixture Shape

```json
{
  "version": 1,
  "name": "example",
  "defaults": {"limit": 10},
  "cases": [
    {
      "id": "example-case",
      "query": "derived index diagnostics",
      "space_key": "repo:example",
      "expected_card_ids": ["card-1"]
    }
  ]
}
```

## Metrics

Reports include:
- case count
- expected record count
- hit count
- mean recall at limit
- record-absent count
- retrieval-mismatch count
- extra result count
- per-case ranking deltas
- compact top-result explanations with score components when provided by the retrieval mode

`record_absent` means an expected card ID is not present in canonical v2 records. `retrieval_mismatch` means the expected card exists in canonical v2 records but did not appear in the retrieval result window.

Hybrid mode uses deterministic, explainable score components documented in `docs/muninn_v2_retrieval_contract.md`. It is still diagnostic only and is not a production route.

## Non-Goals

This eval layer does not implement cognition, salience propagation, spreading activation, motif detection, or hidden-link discovery. Those are Mimir-adjacent concerns if they become necessary.
