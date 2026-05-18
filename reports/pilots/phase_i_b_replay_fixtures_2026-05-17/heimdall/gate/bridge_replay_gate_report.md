# Muninn v2 Bridge Replay Gate

## Summary

- Technical replay gate: `GO`
- Live shadow trial: `NO-GO`
- Bridge shadow consumption: `GO`
- Live cutover: `NO-GO`
- Writes: `NO-GO`
- Adaptive default: `NO-GO`
- Gates passed: 12 / 12

## Gates

- `status_boundaries`: `pass`
- `task_outcomes`: `pass`
- `required_context_retention`: `pass`
- `budget_pressure_retention`: `pass`
- `cross_project_contamination_denied`: `pass`
- `adaptive_state_opt_in`: `pass`
- `degradation_markers_visible`: `pass`
- `operator_review`: `pass`
- `audit_trace_replay`: `pass`
- `evidence_required_when_policy_requires_it`: `pass`
- `v1_untouched`: `pass`
- `failure_drills_detect_expected_failures`: `pass`

## Failure Drills

- `corrupted_adaptive_state` detected=`true` mutation=`adaptive state enabled without version/count`
- `contamination_attempt` detected=`true` mutation=`cross-project request allowed`
- `stale_replay_artifact` detected=`true` mutation=`audit trace no longer matches response`
- `denied_policy_bypass` detected=`true` mutation=`denied response reports policy allowed`
- `degraded_index_marker_missing` detected=`true` mutation=`degraded run omitted reason codes`
- `missing_evidence` detected=`true` mutation=`policy requires evidence but payload has none`
- `replay_hash_mismatch` detected=`true` mutation=`response hash mismatch`

## Safety

- Offline replay gate only.
- Does not call live MCP.
- Does not write v1 or v2 canonical memory.
- Does not authorize live cutover.
