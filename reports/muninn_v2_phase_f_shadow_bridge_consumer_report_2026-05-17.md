# Muninn v2 Phase F Shadow Bridge Consumer Evaluation

## Executive Summary

Phase F is GO for bridge shadow consumption. The read-only Phase E bridge was used as a shadow context provider for Friday, ReadyPlayer1, and Lexi controlled Codex-style tasks. All three cases validated `BridgeResponseV1`, extracted valid `RehydrateResponseV1`, rendered deterministic context blocks, verified bridge audit replay metadata, and matched the v1-style expected project-state needs with no omissions.

Muninn itself was not used as the third pilot because this repo was under active modification during the evaluation. Lexi was used as the safer completed Phase C alternative pilot.

## Pilot Results

| Pilot | Decision | Coverage | Omissions | Over-Included | Replay Verified | Evidence Refs | Degradation |
|---|---:|---:|---:|---:|---:|---:|---|
| Friday | GO | 1.0 | 0 | 3 | True | 31 | sqlite_vec_unavailable_using_json_vector_fallback |
| ReadyPlayer1 | GO | 1.0 | 0 | 0 | True | 41 | sqlite_vec_unavailable_using_json_vector_fallback |
| Lexi | GO | 1.0 | 0 | 1 | True | 25 | sqlite_vec_unavailable_using_json_vector_fallback |

## V1 vs V2 Context Comparison

- Cases with v1-style baseline comparison: 3
- Same-good-decision supported: 3
- Average v2 coverage: 1.0
- Missing required needs: 0
- Omissions: 0

## Omission And Noise Analysis

- Required context omissions: 0.
- Stale blocking flags: 0.
- Confusing flags: 1 non-blocking Friday `web-wrapper` contrast marker.
- Over-included cards: 4 total. Friday had 3 and Lexi had 1; none blocked the task decision.

## Audit Replay

- Replay verified cases: 3 / 3.
- Request, policy, response, trace, and DB unchanged markers were verified from bridge artifacts.
- Bridge responses remained policy-allowed, rehydrate-only, and adaptive scoring disabled.

## Safety

- v1 row counts changed: False
- v1 DB size changed: False
- v1 DB mtime changed: False
- Live MCP/Codex defaults changed: false.
- Writes/autonomous memory creation: false.
- Adaptive retrieval default enabled: false.

## Artifacts

- Fixture: `reports/pilots/phase_f_shadow_bridge_consumer_2026-05-17/bridge_consumer_phase_f_fixture.json`
- Bridge requests: `reports/pilots/phase_f_shadow_bridge_consumer_2026-05-17/requests`
- Bridge policies: `reports/pilots/phase_f_shadow_bridge_consumer_2026-05-17/policies`
- Bridge responses/audits: `reports/pilots/phase_f_shadow_bridge_consumer_2026-05-17`
- Rendered context blocks: `reports/pilots/phase_f_shadow_bridge_consumer_2026-05-17/audit/rendered_context_blocks`
- Consumer audit report: `reports/pilots/phase_f_shadow_bridge_consumer_2026-05-17/audit/bridge_consumer_eval_report.json`
- v1 safety report: `reports/pilots/phase_f_shadow_bridge_consumer_2026-05-17/safety/v1_row_counts_before_after.json`

## Final Status

- BRIDGE SHADOW CONSUMPTION: GO
- LIVE CUTOVER: NO-GO
- WRITES: NO-GO
- ADAPTIVE DEFAULT: NO-GO

## Remaining Gaps

- The Friday context still contains one non-blocking confusing contrast marker and three over-included cards.
- Lexi includes one over-included supplement.
- sqlite_vec is still unavailable, so all pilots report the expected json-vector fallback degradation.

## Recommended Next Task

Run a replayable shadow bridge drill against a fresh task set with operator review of rendered context blocks before any live integration design is reopened.
