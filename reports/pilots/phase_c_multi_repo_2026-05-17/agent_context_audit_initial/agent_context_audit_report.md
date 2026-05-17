# Muninn v2 Agent Context Audit

- Fixture: `SubSim and Sindri Phase C initial agent-context audit`
- Cases: 2
- GO cases: 2
- NO-GO cases: 0
- Average v2 coverage: `1.0`
- Same-good-decision supported: 2
- Missing required needs: 0
- Confusing flags: 2
- Over-included cards: 9

## Cases

### subsim-readyplayer1-campaign-integration

- Project: `SubSim`
- Decision: `go`
- V2 coverage: `1.0`
- Missing required: `[]`
- V1 comparison: `{'v1_context_provided': True, 'same_good_decision_supported': True, 'coverage_delta_v2_minus_v1': 0.4, 'regressions': []}`
- Stale flags: `[]`
- Confusing flags: `[{'term': 'Godot mobile controls', 'reason': 'Godot mobile UI work is unrelated to the ReadyPlayer1 campaign-integration task.', 'blocking': False}]`
- Over-included cards: 5

Over-included candidates:
- `b97c8e3f-2a41-4031-946f-2f57b87f2bc2` SubSim x ReadyPlayer1 preflight documented and Campaign 001 selected (primary_retrieval)
- `a4659ce9-bcf2-4615-9c37-4c09601943ab` Hydrophone corpus expansion v2 (recent_in_scope_supplement)
- `1fff427d-0f12-44cd-a002-56f1516745fb` Bounded hydrophone pipeline (recent_in_scope_supplement)
- `12583c95-c343-4350-bae7-0b882ed70d96` Campaign 001 sonar clutter readability producer behavior (recent_in_scope_supplement)
- `14d4b7a7-b338-4ede-bdad-36278a07392e` Godot mobile controls now include explicit Ping and gameplay-effective Fire (recent_in_scope_supplement)

### sindri-wrapper-lane-trust-calibration

- Project: `Sindri`
- Decision: `go`
- V2 coverage: `1.0`
- Missing required: `[]`
- V1 comparison: `{'v1_context_provided': True, 'same_good_decision_supported': True, 'coverage_delta_v2_minus_v1': 0.0, 'regressions': []}`
- Stale flags: `[]`
- Confusing flags: `[{'term': 'Phase 8.5 adopts harness discipline surfaces', 'reason': 'Phase 8.5 process-surface import is background context, not the current wrapper-lane trust state.', 'blocking': False}]`
- Over-included cards: 4

Over-included candidates:
- `0bc6cc14-39e3-4eb4-bbaf-8c90c8387f3c` Phase 8.5 adopts harness discipline surfaces without widening Sindri scope (recent_in_scope_supplement)
- `e7f21da8-5a23-46ce-ab62-f093960a7ff5` Phase 8 targeted-review calibration validation commands (recent_in_scope_supplement)
- `ebafdc59-b748-4df8-a9ee-1a8234741860` Phase 8 calibrates targeted-review overrides via disagreement-health and handoff fields (recent_in_scope_supplement)
- `47ce04d1-aa39-4341-be83-0ccc1b8658e4` Phase 7 validation and burden-eval command path (recent_in_scope_supplement)

## Safety

- Offline read-only harness only.
- Does not call live MCP or change Codex defaults.
- Does not write to v1 or project repositories.
