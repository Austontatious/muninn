# Muninn v2 Bridge Consumer Evaluation

- Fixture: `Muninn v2 Phase F bridge shadow consumer evaluation`
- Cases: 3
- GO cases: 3
- NO-GO cases: 0
- Average v2 coverage: `1.0`
- Same-good-decision supported: 3
- Replay verified: 3
- Provenance sufficient: 3
- Missing required needs: 0
- Omissions: 0
- Confusing flags: 1
- Over-included cards: 4
- Adaptive-enabled cases: 0

## Cases

### friday-shadow-bridge-consumer

- Project: `Friday`
- Decision: `go`
- Bridge status: `ok` policy_allowed=`True` degraded=`True`
- Degradation reasons: `['sqlite_vec_unavailable_using_json_vector_fallback']`
- V2 coverage: `1.0`
- Missing required: `[]`
- V1 comparison: `{'v1_context_provided': True, 'coverage_delta_v2_minus_v1': 0.0, 'regressions': [], 'same_good_decision_supported': True}`
- Replay verified: `True` failed=`[]`
- Provenance: evidence_refs=`31` explanations=`True`
- Confusing flags: `[{'term': 'web-wrapper', 'reason': 'Appears only as contrast in Android card; should not imply the current frontend is a web wrapper.', 'blocking': False}]`
- Over-included cards: 3

Over-included candidates:
- `17beee42-c7ec-4769-9b2b-d90b395c90d7` Run Friday analysis phase on gold_full_v1 with dry-run, heuristic-only, OpenAI smoke, and resume checks (primary_retrieval)
- `c1907668-82e4-4e07-908d-69250a58e825` Friday mobile client uses native Android Compose project under android/ (primary_retrieval)
- `ecc7842e-8058-4603-b3a0-633970ad4db5` V3 routing+prompt pass completed with targeted and full reruns (recent_in_scope_supplement)

### readyplayer1-shadow-bridge-consumer

- Project: `ReadyPlayer1`
- Decision: `go`
- Bridge status: `ok` policy_allowed=`True` degraded=`True`
- Degradation reasons: `['sqlite_vec_unavailable_using_json_vector_fallback']`
- V2 coverage: `1.0`
- Missing required: `[]`
- V1 comparison: `{'v1_context_provided': True, 'coverage_delta_v2_minus_v1': 0.0, 'regressions': [], 'same_good_decision_supported': True}`
- Replay verified: `True` failed=`[]`
- Provenance: evidence_refs=`41` explanations=`True`
- Confusing flags: `[]`
- Over-included cards: 0

### lexi-shadow-bridge-consumer

- Project: `Lexi`
- Decision: `go`
- Bridge status: `ok` policy_allowed=`True` degraded=`True`
- Degradation reasons: `['sqlite_vec_unavailable_using_json_vector_fallback']`
- V2 coverage: `1.0`
- Missing required: `[]`
- V1 comparison: `{'v1_context_provided': True, 'coverage_delta_v2_minus_v1': 0.0, 'regressions': [], 'same_good_decision_supported': True}`
- Replay verified: `True` failed=`[]`
- Provenance: evidence_refs=`25` explanations=`True`
- Confusing flags: `[]`
- Over-included cards: 1

Over-included candidates:
- `df2b467b-c10b-4a2f-8c2c-e1f5e34d603f` Lex end-to-end review: prioritize auth hardening, side-effect removal, and real eval gating (recent_in_scope_supplement)

## Status

- BRIDGE SHADOW CONSUMPTION: GO
- LIVE CUTOVER: NO-GO
- WRITES: NO-GO
- ADAPTIVE DEFAULT: NO-GO

## Safety

- Offline bridge consumer evaluation only.
- Consumes BridgeResponseV1 artifacts and does not call live MCP.
- Does not write to v1, project repositories, or default context settings.
