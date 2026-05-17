# Muninn v2 Agent Context Audit

- Fixture: `Friday and ReadyPlayer1 Phase B agent-context audit`
- Cases: 2
- GO cases: 2
- NO-GO cases: 0
- Average v2 coverage: `1.0`
- Same-good-decision supported: 2
- Missing required needs: 0
- Confusing flags: 2
- Over-included cards: 12

## Cases

### friday-resume-current-state

- Project: `Friday`
- Decision: `go`
- V2 coverage: `1.0`
- Missing required: `[]`
- V1 comparison: `{'v1_context_provided': True, 'same_good_decision_supported': True, 'coverage_delta_v2_minus_v1': 0.0, 'regressions': []}`
- Stale flags: `[]`
- Confusing flags: `[{'term': 'web-wrapper', 'reason': 'Appears only as contrast in Android card; should not imply the current frontend is a web wrapper.', 'blocking': False}]`
- Over-included cards: 7

Over-included candidates:
- `17beee42-c7ec-4769-9b2b-d90b395c90d7` Run Friday analysis phase on gold_full_v1 with dry-run, heuristic-only, OpenAI smoke, and resume checks (primary_retrieval)
- `c1907668-82e4-4e07-908d-69250a58e825` Friday mobile client uses native Android Compose project under android/ (primary_retrieval)
- `da270af3-a737-4ad5-a652-92751cb57de2` Hard-gate trial for routing_001 traceback guard set to manual_review (recent_in_scope_supplement)
- `c9da15a8-7aa4-4471-a717-d7379249fa7f` Run Friday optimizer v1 with persisted splits and staged candidate trials (recent_in_scope_supplement)
- `d5f1c931-3233-46df-96f3-5c5645bfc86c` Friday now has a bounded synthetic optimizer harness v1 over safe policy surfaces (recent_in_scope_supplement)
- `ecc7842e-8058-4603-b3a0-633970ad4db5` V3 routing+prompt pass completed with targeted and full reruns (recent_in_scope_supplement)
- `7c366fc3-ec1f-455f-8c7a-3d2ea90ff178` Friday remediation v2 rerun and delta artifacts for failed/borderline and full corpus (recent_in_scope_supplement)

### readyplayer1-resume-current-campaign

- Project: `ReadyPlayer1`
- Decision: `go`
- V2 coverage: `1.0`
- Missing required: `[]`
- V1 comparison: `{'v1_context_provided': True, 'same_good_decision_supported': True, 'coverage_delta_v2_minus_v1': 0.0, 'regressions': []}`
- Stale flags: `[]`
- Confusing flags: `[{'term': 'Qwen3.6', 'reason': 'Unrelated model-serving trial appears as a recent supplement and should not steer ReadyPlayer1 campaign work.', 'blocking': False}]`
- Over-included cards: 5

Over-included candidates:
- `8db59c21-0224-4ef0-b628-f336867bf591` Campaign 003 acoustic clutter binding integrated (recent_in_scope_supplement)
- `2656c35f-79af-403d-9128-e98fc72663d6` Campaign 003 promoted for SubSim clutter binding (recent_in_scope_supplement)
- `4be809aa-731f-420c-8dc1-99cb5813c0ea` Campaign 002A promoted for SubSim sonar lifecycle diagnostics (recent_in_scope_supplement)
- `f5021943-807e-4015-a4d6-a24e1f8b8db4` Campaign 001 promoted on belief_baseline clutter evidence (recent_in_scope_supplement)
- `c7a9d5cf-187b-4d6d-9637-f6d191b512f3` Qwen3.6-27B isolated vLLM trial on V100 (sm_70) parses but fails to reach API-ready state (recent_in_scope_supplement)

## Safety

- Offline read-only harness only.
- Does not call live MCP or change Codex defaults.
- Does not write to v1 or project repositories.
