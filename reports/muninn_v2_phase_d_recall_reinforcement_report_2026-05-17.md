# Muninn v2 Phase D Recall/Reinforcement Report - 2026-05-17

## Executive Summary

Phase D initial offline recall/reinforcement mechanics are implemented.

The layer is v2-only, deterministic, replayable, and explainable. It records explicit offline recall events, replays them into derived retrieval state, and can optionally apply that state to v2 hybrid retrieval scoring without changing defaults.

No live v1 behavior, MCP route, Codex default, or canonical card truth was changed.

## What Was Added

- Derived state table: `v2_reinforcement_state`
- Offline event command: `recall-event-record`
- Offline replay command: `recall-reinforcement-replay`
- Deterministic replay model for boost, suppression, quiet-period decay, and durable preservation
- JSON/Markdown reports for event recording and replay
- Optional v2 hybrid retrieval scoring hook, disabled unless a reinforcement state map is explicitly passed
- Tests for dry-run behavior, explicit write flags, deterministic replay, no canonical card mutation, no v1 connector use, and optional scoring adjustment

## Mechanics

Recall events carry:

- query
- actor
- scope key
- recalled IDs
- accepted IDs
- suppressed IDs
- metadata
- timestamp

Replay computes one derived state per active card:

- `boosted`: accepted/useful recall history dominates
- `suppressed`: suppression outweighs accepted reinforcement and preservation
- `preserved`: durable project-state memory survives quiet-period decay
- `decayed`: quiet-period decay dominates non-durable memory
- `neutral`: no strong signal

The replay output explains each state with score components and notes. Derived state is rebuildable from v2 cards and v2 recall events.

## Lexi Smoke Run

I copied the Lexi Phase C shadow DB into:

`reports/pilots/phase_d_recall_reinforcement_2026-05-17/lexi_phase_d_shadow_v2.db`

Then I recorded one offline recall event:

- Accepted: Lexi production audit verdict, Phase 6 checkpoint, Phase 6 runtime preflight card
- Suppressed: older broad Lex end-to-end review card

Replay result:

- Eligible cards: 77
- Recall events: 1
- Boosted: 3
- Suppressed: 1
- Preserved: 73
- Decayed: 0
- Neutral: 0
- State rows written: 77

Interpretation: Phase D correctly boosted the current production-audit and Phase 6 runtime cards and suppressed the older broad review card. The high preserved count is expected for Lexi because most migrated cards are durable decision/constraint/runbook records. Do not tune that yet; future Phase D fixtures should decide whether preservation should be narrower.

## Safety Assessment

- Phase D command v1 DB access: no
- v1 writes: no
- Final v1 row counts: 516 cards, 1408 evidence refs, 1408 card/evidence links, 2 interaction events
- v1 note: row counts and latest records stayed unchanged from Phase C closeout; the DB mtime advanced during the broader session, so this report treats v1 content as not mutated by Phase D commands.
- live MCP/default changes: no
- live agent-context integration: no
- canonical v2 card mutation: no
- project repo edits: no
- LLM salience judgments: no
- generated DB committed: no

## Decision

- Phase D initial layer: implemented
- Offline recall/reinforcement fixture expansion: GO
- Live agent context: NO-GO
- Phase E cutover: NO-GO

Recommended next task: build multi-pilot Phase D reinforcement fixtures for Friday, ReadyPlayer1, SubSim, Sindri, and Lexi, then tune preservation/suppression thresholds only from offline audit evidence.
