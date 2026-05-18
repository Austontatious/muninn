# Muninn v2 Shadow Operations Runbook

This runbook governs Muninn v2 bridge shadow operations before any live agent
context integration.

Current status boundaries:

- BRIDGE SHADOW CONSUMPTION: GO
- LIVE CUTOVER: NO-GO
- WRITES: NO-GO
- ADAPTIVE DEFAULT: NO-GO

Do not use this runbook to replace live Codex/MCP context. Do not write v1. Do
not enable adaptive retrieval by default.

## Required Inputs

- A committed or reviewable Phase G drill fixture.
- A Phase G `bridge_ops_drill_report.json`.
- Per-request bridge audit/response/request/policy artifacts.
- Rendered context blocks for operator review.
- A v1 before/after safety report proving row counts, DB size, and DB mtime did
  not change.

## Run Shadow Drills

Use the v2-only bridge operations drill:

```bash
PYTHONPATH=src python3 -m muninn.v2.cli bridge-ops-drill \
  --fixture reports/pilots/phase_g_shadow_ops_drill_2026-05-17/bridge_ops_phase_g_fixture.json \
  --out-dir reports/pilots/phase_g_shadow_ops_drill_2026-05-17/drill
```

The drill runs each task in:

- `adaptive_off`: default shadow bridge behavior.
- `budget_pressure`: smaller context budget.
- `adaptive_on`: explicit request plus explicit policy permission to read
  derived reinforcement state.

Successful drill output includes:

- `bridge_ops_drill_report.json`
- `bridge_ops_drill_report.md`
- `operator_review_notes.md`
- `rendered_context_blocks/*.md`
- per-task `bridge_request.json`
- per-task `bridge_policy.json`
- per-task `bridge_response_<request_id>.json`
- per-task `bridge_audit_<request_id>.json`

## Run Replay Gate

Use the executable replay gate before any live shadow trial:

```bash
PYTHONPATH=src python3 -m muninn.v2.cli bridge-replay-gate \
  --drill-report reports/pilots/phase_g_shadow_ops_drill_2026-05-17/drill/bridge_ops_drill_report.json \
  --v1-safety reports/pilots/phase_g_shadow_ops_drill_2026-05-17/safety/v1_row_counts_before_after.json \
  --out-dir reports/pilots/phase_h_shadow_ops_gate_2026-05-17/gate \
  --run-failure-drills
```

For a live shadow trial readiness review, add:

```bash
--require-human-signoff
```

Only use `--require-human-signoff` after the operator review artifact records
`human_signoff_recorded=true` and the reviewer identity/evidence has been
recorded in the review packet.

## Replay Gate Checks

The replay gate verifies:

- bridge shadow consumption status is GO
- live cutover remains NO-GO
- writes remain NO-GO
- adaptive default remains NO-GO
- all tasks are GO
- required context retention meets threshold
- budget-pressure coverage meets threshold
- bridge audit replay hashes match request/policy/response artifacts
- bridge audit DB unchanged markers are clean
- policy denial checks catch cross-project access attempts
- adaptive state appears only in explicit adaptive-on mode
- degraded index markers are visible
- evidence is present when policy requires evidence
- v1 safety report shows row counts, size, and mtime unchanged

## Inspect Audit Traces

For each request directory, inspect:

```text
bridge_request.json
bridge_policy.json
bridge_response_<request_id>.json
bridge_audit_<request_id>.json
```

Check:

- `request_id` matches across files.
- `operation` is `rehydrate`.
- `policy_decision.allowed` is true for in-scope requests.
- `policy_decision.allowed` is false for contamination attempts.
- `audit.input_hash` matches the request hash.
- `audit.policy_hash` matches the policy hash.
- `audit.response_hash` matches the response hash.
- audit `db.changed` booleans are all false.
- `degradation.reason_codes` are populated when degraded behavior occurs.

## Verify Replay Hashes

Preferred path:

```bash
PYTHONPATH=src python3 -m muninn.v2.cli bridge-replay-gate \
  --drill-report <drill-report.json> \
  --v1-safety <v1-row-count-before-after.json> \
  --out-dir <gate-output> \
  --run-failure-drills
```

Manual rule:

- Recompute the canonical JSON hash for request, policy, and response.
- For response hashing, set `response.audit.response_hash` to null before
  hashing.
- Compare against `bridge_audit_<request_id>.json`.

Any mismatch blocks live shadow trials.

## Compare Context Blocks

Open `operator_review_notes.md`, then review each referenced rendered context
block.

For every context block, classify:

- sufficient: contains current project state, constraints, next-step context,
  and evidence.
- omission: required project state is absent or budget-clipped.
- stale: superseded state appears as current.
- noisy: background or contrast-only cards distract from the task.
- confusing: card wording could lead an agent to a wrong action.
- contaminated: cards from another project appear without explicit policy.

Operator review must compare:

- adaptive-off vs adaptive-on
- adaptive-off vs budget-pressure
- task 1 vs later tasks in the same session
- v2 rendered context vs known v1-assisted expectations

## Identify Contamination

Contamination is any unapproved cross-project memory access or context leak.

Indicators:

- `space_key` outside the allowed policy list.
- `project_path` outside the allowed policy list.
- contamination check response is not `denied`.
- denial lacks `space_not_allowed` or `project_path_not_allowed`.
- selected cards contain another project path, repo key, or project-specific
  terminology without an explicit cross-project policy.

Contamination blocks live shadow trials.

## Identify Suppression Regressions

Suppression regression means adaptive state hides valid context.

Check adaptive-on against adaptive-off:

- Required cards present in adaptive-off must remain present in adaptive-on.
- Durable boundary, safety, contract, runbook, and interface cards must not
  disappear because unrelated recent cards were boosted.
- Suppressed cards must have scoped reason codes.
- Global suppression is suspicious unless explicitly justified by the replay
  fixture.
- Adaptive-on may reorder context, but it must not reduce required-context
  coverage.

Suppression regression blocks live shadow trials.

## Verify Adaptive State

Adaptive state is allowed only when both request and policy explicitly enable
it.

Required adaptive-on markers:

- `adaptive_scoring.requested=true`
- `adaptive_scoring.enabled=true`
- `adaptive_scoring.default=false`
- `adaptive_scoring.state_version` is populated
- `adaptive_scoring.state_count > 0`
- boosted/suppressed card IDs are disclosed

Required adaptive-off markers:

- `adaptive_scoring.requested=false`
- `adaptive_scoring.enabled=false`
- `adaptive_scoring.default=false`

Any adaptive-off enabled state blocks live shadow trials.

## Validate v1 Untouched Status

Before and after a drill, collect read-only v1 safety state:

- row counts for every v1 table
- DB file size
- DB mtime

The before/after report must show:

- `row_counts_changed=false`
- `size_changed=false`
- `mtime_changed=false`

Any v1 mutation blocks live shadow trials and requires immediate rollback.

## Rollback / Shut Down Bridge Access

The bridge is currently CLI-only and opt-in. Rollback means:

1. Stop running `bridge-request`, `bridge-ops-drill`, and
   `bridge-replay-gate`.
2. Remove or quarantine the capability policy file used by the consumer.
3. Delete or archive unapproved generated artifacts from the current review
   packet.
4. Confirm no live MCP/Codex default references the v2 bridge.
5. Confirm v1 safety report still shows unchanged row counts, size, and mtime.
6. If bridge code was staged for deployment, revert that deployment plan before
   any live process starts.

Do not delete canonical v2 shadow DBs during rollback unless the rollback plan
explicitly calls for removing generated pilot state.

## Human Review Workflow

Approvers:

- repo owner or delegated Muninn operator
- implementing engineer may prepare evidence but should not be the only
  approver for live shadow trials

Required evidence:

- drill report JSON and Markdown
- replay gate report JSON and Markdown
- v1 safety report
- rendered context blocks
- operator review notes
- list of confusing/stale/over-included cards
- contamination denial artifacts
- adaptive-off vs adaptive-on comparison
- budget-pressure result
- rollback plan

Regression classes:

- P0 safety: v1 changed, writes occurred, live defaults changed, or
  cross-project contamination allowed.
- P1 context: required context absent, suppression regression, or stale context
  presented as current.
- P2 operability: audit replay mismatch, missing evidence, incomplete traces,
  or degraded state not labeled.
- P3 quality: non-blocking over-inclusion, confusing contrast-only context, or
  budget pressure that still passes minimum coverage.

Live shadow trial blockers:

- any P0
- any unresolved P1
- any failed replay gate
- missing human signoff
- missing rollback plan
- adaptive default enabled
- incomplete audit traces

## Failure Drills

Run:

```bash
PYTHONPATH=src python3 -m muninn.v2.cli bridge-replay-gate \
  --drill-report <drill-report.json> \
  --v1-safety <v1-row-count-before-after.json> \
  --out-dir <gate-output> \
  --run-failure-drills
```

The gate simulates and must detect:

- corrupted adaptive state
- contamination attempts
- stale replay artifacts
- denied policy bypass
- degraded indexes without markers
- missing evidence
- replay hash mismatch

If any failure drill is not detected, live shadow trials are blocked.

## Minimum Live Shadow Trial Preconditions

- technical replay gate is GO
- failure drills are all detected
- human review is signed off
- rollback plan is explicit
- v1 untouched status is verified
- adaptive default remains disabled
- writes remain disabled
- live cutover remains explicitly out of scope
