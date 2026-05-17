# Muninn v2 Offline Recall Reinforcement

## Contract

Phase D introduces a v2-only, offline recall/reinforcement layer. It answers why one memory survives and another fades by replaying explicit recall events into derived retrieval state.

This is not production cutover, live agent context, Mimir cognition, or autonomous memory rewriting.

## Canonical vs Derived

Canonical v2 truth remains:

- cards
- events
- entities
- associations
- evidence
- ontology profiles
- explicit recall events

Derived Phase D state lives in `v2_reinforcement_state`. It is rebuildable from canonical cards plus `v2_recall_events`. Replaying reinforcement must not mutate canonical card JSON, evidence, associations, or ontology profiles.

## Inputs

Recall events are explicit and auditable:

- query text
- actor
- optional scope key
- recalled record IDs
- accepted/useful record IDs
- suppressed/confusing record IDs
- metadata
- deterministic timestamp when provided

Accepted IDs create stronger reinforcement. Recalled-only IDs receive a smaller exposure boost. Suppressed IDs receive deterministic suppression. Durable card kinds receive preservation against quiet-period decay.

## Replay Mechanics

`recall-reinforcement-replay` computes one derived state row per active v2 card:

- `boosted`: accepted or useful recall history dominates
- `suppressed`: suppression outweighs accepted reinforcement and preservation
- `preserved`: durable project-state memory survives quiet-period decay
- `decayed`: quiet-period decay dominates non-durable memory
- `neutral`: no strong signal

The replay is deterministic for the same cards, recall events, weights, and `--as-of` timestamp.

## CLI

Dry-run record event:

```bash
PYTHONPATH=src python3 -m muninn.v2.cli recall-event-record \
  --v2-db reports/pilots/example/example_shadow_v2.db \
  --query "resume project current state" \
  --out-dir reports/pilots/example/phase_d_event \
  --accepted-id CARD_ID \
  --suppressed-id OTHER_CARD_ID
```

Persist event into the explicit v2 DB:

```bash
PYTHONPATH=src python3 -m muninn.v2.cli recall-event-record \
  --v2-db reports/pilots/example/example_shadow_v2.db \
  --query "resume project current state" \
  --out-dir reports/pilots/example/phase_d_event \
  --accepted-id CARD_ID \
  --suppressed-id OTHER_CARD_ID \
  --write-event
```

Dry-run deterministic replay:

```bash
PYTHONPATH=src python3 -m muninn.v2.cli recall-reinforcement-replay \
  --v2-db reports/pilots/example/example_shadow_v2.db \
  --out-dir reports/pilots/example/phase_d_replay \
  --as-of 2026-05-17T00:00:00Z
```

Persist derived state into the explicit v2 DB:

```bash
PYTHONPATH=src python3 -m muninn.v2.cli recall-reinforcement-replay \
  --v2-db reports/pilots/example/example_shadow_v2.db \
  --out-dir reports/pilots/example/phase_d_replay \
  --as-of 2026-05-17T00:00:00Z \
  --write-state
```

## Reports

Both commands emit JSON and Markdown reports:

- `recall_event_record_report.json`
- `recall_event_record_report.md`
- `recall_reinforcement_replay_report.json`
- `recall_reinforcement_replay_report.md`

Reports include command mode, explicit source DB, counts, safety markers, derived statuses, score components, and explanations.

## Retrieval Application

Hybrid retrieval can accept a reinforcement state map in v2 code paths. The default remains unchanged. When state is supplied, boosted/preserved records receive transparent score components and suppressed records receive transparent penalties.

This hook is for offline experiments and evaluation only. It must not be wired into live MCP, live Codex context, or v1 retrieval defaults without a later explicit cutover plan.

## Safety

Phase D commands:

- require explicit `--v2-db`
- write nothing unless `--write-event` or `--write-state` is passed
- never open or mutate v1
- never mutate canonical v2 cards
- never require `sqlite_vec`
- never use LLM salience judgments
- produce replayable JSON/Markdown audit artifacts
