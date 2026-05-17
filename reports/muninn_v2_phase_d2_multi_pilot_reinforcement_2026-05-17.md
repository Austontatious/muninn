# Muninn v2 Phase D2 Multi-Pilot Recall/Reinforcement Audit

## Executive Summary

Phase D2 replayed deterministic offline recall/reinforcement events across Friday, ReadyPlayer1, SubSim, Sindri, and Lexi using copied shadow v2 DBs only. The derived-state mechanics passed: accepted records were boosted, scoped negative records were suppressed, and no accepted record was falsely suppressed.

Anti-echo protections are now explicit: repeated signals use deterministic diminishing returns, recalled-only exposure is capped below accepted reinforcement, boost scores remain bounded, durable boundaries remain retrievable, and suppression state is scope-filtered. Adaptive retrieval remains disabled by default.

## Safety

- v1 row-count snapshot safe: true
- v1 row counts changed: false
- v1 DB size changed: false
- v1 DB mtime changed: false
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

## Anti-Echo Checks

- Repeated recall diminishing returns: validated by tests
- Boost cap: validated by tests
- Recall-only exposure cap: validated by tests
- Durable older boundary retention: validated by tests and pilot preservation counts
- Scoped suppression: validated by tests and pilot fixture design
- Threshold tuning: no pilot-specific threshold tuning performed

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

## GO/NO-GO

- Phase D2 replay/state mechanics: GO
- Phase D2 anti-echo checks: GO
- Optional adaptive scoring experiment: GO with residual context-risk constraints
- Phase E API/bridge planning: GO for planning only
- Live agent context or default adaptive retrieval: NO-GO

## Remaining Risks

Residual unclassified top-12 results remain in ReadyPlayer1, SubSim, Sindri, and Lexi diagnostic retrieval. They were not explicit fixture failures, but they should be treated as Phase E/Phase D3 contract and calibration inputs before any live adaptive use.

## Recommended Next Phase

Proceed to Phase E API/bridge planning only. Keep it contract-first and read-only: define how a future bridge would request explicit v2 DB/context artifacts, consume RehydrateResponseV1 plus derived reinforcement state, and provide rollback/no-default guarantees. Do not wire live context yet.
