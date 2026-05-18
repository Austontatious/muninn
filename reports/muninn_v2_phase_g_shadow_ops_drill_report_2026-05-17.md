# Muninn v2 Phase G Shadow Operations Drill Report

## Executive Summary

Phase G is GO for continued bridge shadow consumption. The read-only v2 bridge completed replayable multi-task shadow drills for Friday, ReadyPlayer1, and Lexi with adaptive-off, budget-pressure, and explicit adaptive-on modes. No live cutover, writes, or adaptive default behavior were introduced.

## Drill Results

- Pilots: 3
- Tasks: 6
- Mode runs: 18
- GO tasks: 6
- NO-GO tasks: 0
- Missing required context: 0
- Audit replay failures: 0
- Contamination denied: 3 / 3
- Budget-pressure GO: 6 / 6
- Adaptive-on enabled: 6 / 6
- Adaptive default enabled: 0
- Stale flags: 0
- Confusing flags: 1
- Over-included cards: 11

## Per-Pilot Metrics

### Friday

- Tasks: 2 / 2 GO
- Adaptive-off GO: 2
- Budget-pressure GO: 2; min coverage `1.0`; omitted-for-budget `2`
- Adaptive-on enabled: 2
- Missing required: 0
- Stale flags: 0
- Confusing flags: 1
- Over-included cards: 7

### Lexi

- Tasks: 2 / 2 GO
- Adaptive-off GO: 2
- Budget-pressure GO: 2; min coverage `0.857143`; omitted-for-budget `3`
- Adaptive-on enabled: 2
- Missing required: 0
- Stale flags: 0
- Confusing flags: 0
- Over-included cards: 4

### ReadyPlayer1

- Tasks: 2 / 2 GO
- Adaptive-off GO: 2
- Budget-pressure GO: 2; min coverage `0.8`; omitted-for-budget `7`
- Adaptive-on enabled: 2
- Missing required: 0
- Stale flags: 0
- Confusing flags: 0
- Over-included cards: 0

## Failure-Mode Findings

- Replayability: all bridge response/request/policy/audit hashes verified.
- Stale context: no blocking stale terms appeared.
- Contamination: all cross-project access attempts were denied by policy with space/project reason codes.
- Budget pressure: every run stayed GO, but omitted context under 6500-char budgets shows production budgets still need review.
- Adaptive comparison: adaptive-on read derived reinforcement state only when request and policy allowed it; adaptive-off never enabled adaptive scoring.
- Noise: Friday retained one non-blocking contrast term and over-inclusion remains measurable, but neither blocked task coverage.

## v1 Safety

- v1 row counts changed: `false`
- v1 DB size changed: `false`
- v1 DB mtime changed: `false`
- cards before/after: `521` / `521`

## Artifacts

- Fixture: `/mnt/data/Muninn/reports/pilots/phase_g_shadow_ops_drill_2026-05-17/bridge_ops_phase_g_fixture.json`
- Drill JSON: `/mnt/data/Muninn/reports/pilots/phase_g_shadow_ops_drill_2026-05-17/drill/bridge_ops_drill_report.json`
- Drill Markdown: `/mnt/data/Muninn/reports/pilots/phase_g_shadow_ops_drill_2026-05-17/drill/bridge_ops_drill_report.md`
- Operator review: `/mnt/data/Muninn/reports/pilots/phase_g_shadow_ops_drill_2026-05-17/drill/operator_review_notes.md`
- Rendered context blocks: `/mnt/data/Muninn/reports/pilots/phase_g_shadow_ops_drill_2026-05-17/drill/rendered_context_blocks`
- v1 safety report: `/mnt/data/Muninn/reports/pilots/phase_g_shadow_ops_drill_2026-05-17/safety/v1_row_counts_before_after.json`

## Status

- BRIDGE SHADOW CONSUMPTION: GO
- LIVE CUTOVER: NO-GO
- WRITES: NO-GO
- ADAPTIVE DEFAULT: NO-GO

## Recommended Next Task

Phase H should be an operator-reviewed shadow runbook and replay gate, or a deeper Phase G follow-up with human-reviewed context blocks before any live bridge integration.
