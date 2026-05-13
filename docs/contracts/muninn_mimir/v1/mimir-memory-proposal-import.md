# Mimir Memory Proposal Import Contract

Mimir proposes. Muninn remembers.

This contract defines the guarded Muninn-side path for Mimir declared-world memory proposal batches. Validation and preview are read-only. Durable memory writes require a future explicit approval/write path and must never happen from validation alone.

## Proposal Artifact

Mimir emits `mimir.muninn_memory_proposal_batch.v1` JSON. Muninn accepts that batch as an external proposal artifact when it can validate:

- source system is Mimir, or the legacy provisional Mimir schema makes that source inferable
- world id and task are present
- generated command is present or inferable from the Mimir schema version
- all proposals are `review_required: true`
- batch write behavior claims `writes_to_muninn: false`
- batch write behavior claims `writes_durable_memory: false`
- every proposal has evidence and source paths
- every proposal has a known proposal type and valid confidence

The schema is:

- `schemas/mimir-memory-proposal-batch.v1.schema.json`

## Validation

Validation checks shape and safety. It does not write.

```bash
PYTHONPATH=src python3 -m muninn.cli proposals validate \
  --proposal-batch /tmp/local_ai_ecosystem_memory_proposals.json
```

Validation fails for:

- non-Mimir source system
- missing review requirement
- missing evidence
- missing source paths
- unknown proposal type
- invalid confidence
- proposal artifact claiming it already wrote to Muninn
- proposal artifact claiming it wrote durable memory
- malformed batch JSON
- ambiguous-signal proposals without explicit review metadata

## Preview

Preview maps validated proposals to Muninn-compatible card envelope projections. It does not create cards or write proposals to the database.

```bash
PYTHONPATH=src python3 -m muninn.cli proposals preview \
  --proposal-batch /tmp/local_ai_ecosystem_memory_proposals.json
```

Preview preserves:

- title and summary
- proposal id
- world id and task
- project id or scope
- memory type
- tags and suggested namespace
- confidence
- source evidence and source paths
- review metadata

## Approval

Approval currently supports dry-run mapping for selected proposals or all proposals. It remains read-only in this slice.

```bash
PYTHONPATH=src python3 -m muninn.cli proposals approve \
  --proposal-batch /tmp/local_ai_ecosystem_memory_proposals.json \
  --proposal-id mem-proposal-001-example \
  --namespace default
```

Approving all proposals requires an explicit flag:

```bash
PYTHONPATH=src python3 -m muninn.cli proposals approve \
  --proposal-batch /tmp/local_ai_ecosystem_memory_proposals.json \
  --all \
  --namespace default
```

The `--write` flag is intentionally rejected until a later slice implements audited durable writes.

## Current Limitations

- This contract validates and previews proposal batches; it does not persist cards.
- Legacy provisional Mimir batches without `source_system`, `batch_id`, or `generated_by_command` are normalized with warnings.
- Card envelope previews are candidate projections, not stored memories.
- The actual write path should be implemented only after an explicit audit/approval design is accepted.
