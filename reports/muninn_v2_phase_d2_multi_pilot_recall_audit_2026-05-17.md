# Muninn v2 Phase D2 Multi-Pilot Recall/Reinforcement Audit

## Executive Summary

Phase D2 replayed deterministic offline recall/reinforcement events across Friday, ReadyPlayer1, SubSim, Sindri, and Lexi using copied shadow v2 DBs only. The derived-state mechanics passed: accepted records were boosted, scoped negative records were suppressed, and no accepted record was falsely suppressed.

The optional adaptive hybrid scoring hook is still not enabled by default. After tightening explicit suppression handling, all suppressed fixture records dropped out of top-12 diagnostic retrieval. Residual unclassified results remain in several projects, so Phase D3 should focus on calibrated negative feedback coverage and context-sludge audits before any agent-context experiment uses adaptive state.

## Safety

- v1 DB access: false
- v1 mutation: false
- live MCP/Codex integration: false
- canonical v2 card mutation: false
- adaptive scoring default enabled: false
- generated shadow DBs committed: false

## Aggregate Counts

- Projects: 5
- Eligible cards: 216
- Recall events replayed: 5
- Boosted: 34
- Suppressed: 10
- Preserved: 166
- Decayed: 1
- Neutral: 5
- False suppressions: 0
- Suppression misses: 0
- Boosted but not accepted: 0
- Reinforced suppressed top-12 total: 0
- Reinforced unclassified top-12 total: 14

## Per-Pilot Results

### Friday

- Decision: `pass_with_watch`
- Eligible: 47; boosted: 5; suppressed: 3; preserved: 38; decayed: 1; neutral: 0
- Accepted boosted: 5 / 5
- False suppressions: 0; suppression misses: 0; boosted-not-accepted: 0
- Accepted top-12 baseline -> reinforced: 1 -> 2
- Suppressed top-12 baseline -> reinforced: 2 -> 0
- Reinforced unclassified top-12: 0
- Per-pilot report: `reports/pilots/phase_d2_recall_reinforcement_2026-05-17/friday/reinforcement_context_audit_report.md`

### ReadyPlayer1

- Decision: `pass_with_residual_context_risk`
- Eligible: 48; boosted: 7; suppressed: 3; preserved: 36; decayed: 0; neutral: 2
- Accepted boosted: 7 / 7
- False suppressions: 0; suppression misses: 0; boosted-not-accepted: 0
- Accepted top-12 baseline -> reinforced: 6 -> 7
- Suppressed top-12 baseline -> reinforced: 1 -> 0
- Reinforced unclassified top-12: 5
- Per-pilot report: `reports/pilots/phase_d2_recall_reinforcement_2026-05-17/readyplayer1/reinforcement_context_audit_report.md`

### SubSim

- Decision: `pass_with_residual_context_risk`
- Eligible: 18; boosted: 7; suppressed: 2; preserved: 6; decayed: 0; neutral: 3
- Accepted boosted: 7 / 7
- False suppressions: 0; suppression misses: 0; boosted-not-accepted: 0
- Accepted top-12 baseline -> reinforced: 6 -> 7
- Suppressed top-12 baseline -> reinforced: 1 -> 0
- Reinforced unclassified top-12: 1
- Per-pilot report: `reports/pilots/phase_d2_recall_reinforcement_2026-05-17/subsim/reinforcement_context_audit_report.md`

### Sindri

- Decision: `pass_with_residual_context_risk`
- Eligible: 26; boosted: 8; suppressed: 1; preserved: 17; decayed: 0; neutral: 0
- Accepted boosted: 8 / 8
- False suppressions: 0; suppression misses: 0; boosted-not-accepted: 0
- Accepted top-12 baseline -> reinforced: 3 -> 7
- Suppressed top-12 baseline -> reinforced: 1 -> 0
- Reinforced unclassified top-12: 3
- Per-pilot report: `reports/pilots/phase_d2_recall_reinforcement_2026-05-17/sindri/reinforcement_context_audit_report.md`

### Lexi

- Decision: `pass_with_residual_context_risk`
- Eligible: 77; boosted: 7; suppressed: 1; preserved: 69; decayed: 0; neutral: 0
- Accepted boosted: 7 / 7
- False suppressions: 0; suppression misses: 0; boosted-not-accepted: 0
- Accepted top-12 baseline -> reinforced: 4 -> 7
- Suppressed top-12 baseline -> reinforced: 0 -> 0
- Reinforced unclassified top-12: 5
- Per-pilot report: `reports/pilots/phase_d2_recall_reinforcement_2026-05-17/lexi/reinforcement_context_audit_report.md`

## Decision

- Phase D2 replay/state mechanics: GO
- Optional adaptive scoring experiment: GO with residual context-risk constraints
- Live agent context or default adaptive retrieval: NO-GO
- Phase D3: GO with a focus on calibrated negative feedback coverage, residual unclassified context, and replay histories longer than one event per project

## Recommended Next Task

Phase D3 should add multi-event replay fixtures per project and measure whether repeated accepted/suppressed events change context coverage without widening residual unclassified context. It should also add an explicit adaptive preview/eval flag rather than relying on ad hoc diagnostic scripts.
