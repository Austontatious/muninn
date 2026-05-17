# Muninn v2 Agent Context Audit

- Fixture: `Friday and ReadyPlayer1 Phase C tightened regression audit`
- Cases: 2
- GO cases: 2
- NO-GO cases: 0
- Average v2 coverage: `1.0`
- Same-good-decision supported: 2
- Missing required needs: 0
- Confusing flags: 1
- Over-included cards: 5

## Cases

### friday-resume-current-state

- Project: `Friday`
- Decision: `go`
- V2 coverage: `1.0`
- Missing required: `[]`
- V1 comparison: `{'v1_context_provided': True, 'same_good_decision_supported': True, 'coverage_delta_v2_minus_v1': 0.0, 'regressions': []}`
- Stale flags: `[]`
- Confusing flags: `[{'term': 'web-wrapper', 'reason': 'Appears only as contrast in Android card; should not imply the current frontend is a web wrapper.', 'blocking': False}]`
- Over-included cards: 3

Over-included candidates:
- `17beee42-c7ec-4769-9b2b-d90b395c90d7` Run Friday analysis phase on gold_full_v1 with dry-run, heuristic-only, OpenAI smoke, and resume checks (primary_retrieval)
- `c1907668-82e4-4e07-908d-69250a58e825` Friday mobile client uses native Android Compose project under android/ (primary_retrieval)
- `ecc7842e-8058-4603-b3a0-633970ad4db5` V3 routing+prompt pass completed with targeted and full reruns (recent_in_scope_supplement)

### readyplayer1-resume-current-campaign

- Project: `ReadyPlayer1`
- Decision: `go`
- V2 coverage: `1.0`
- Missing required: `[]`
- V1 comparison: `{'v1_context_provided': True, 'same_good_decision_supported': True, 'coverage_delta_v2_minus_v1': 0.0, 'regressions': []}`
- Stale flags: `[]`
- Confusing flags: `[]`
- Over-included cards: 2

Over-included candidates:
- `8db59c21-0224-4ef0-b628-f336867bf591` Campaign 003 acoustic clutter binding integrated (recent_in_scope_supplement)
- `2656c35f-79af-403d-9128-e98fc72663d6` Campaign 003 promoted for SubSim clutter binding (recent_in_scope_supplement)

## Safety

- Offline read-only harness only.
- Does not call live MCP or change Codex defaults.
- Does not write to v1 or project repositories.
