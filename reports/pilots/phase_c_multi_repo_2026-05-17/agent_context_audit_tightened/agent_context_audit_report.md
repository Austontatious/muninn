# Muninn v2 Agent Context Audit

- Fixture: `SubSim and Sindri Phase C tightened agent-context audit`
- Cases: 2
- GO cases: 2
- NO-GO cases: 0
- Average v2 coverage: `1.0`
- Same-good-decision supported: 2
- Missing required needs: 0
- Confusing flags: 0
- Over-included cards: 1

## Cases

### subsim-readyplayer1-campaign-integration

- Project: `SubSim`
- Decision: `go`
- V2 coverage: `1.0`
- Missing required: `[]`
- V1 comparison: `{'v1_context_provided': True, 'same_good_decision_supported': True, 'coverage_delta_v2_minus_v1': 0.4, 'regressions': []}`
- Stale flags: `[]`
- Confusing flags: `[]`
- Over-included cards: 1

Over-included candidates:
- `b97c8e3f-2a41-4031-946f-2f57b87f2bc2` SubSim x ReadyPlayer1 preflight documented and Campaign 001 selected (primary_retrieval)

### sindri-wrapper-lane-trust-calibration

- Project: `Sindri`
- Decision: `go`
- V2 coverage: `1.0`
- Missing required: `[]`
- V1 comparison: `{'v1_context_provided': True, 'same_good_decision_supported': True, 'coverage_delta_v2_minus_v1': 0.0, 'regressions': []}`
- Stale flags: `[]`
- Confusing flags: `[]`
- Over-included cards: 0

## Safety

- Offline read-only harness only.
- Does not call live MCP or change Codex defaults.
- Does not write to v1 or project repositories.
