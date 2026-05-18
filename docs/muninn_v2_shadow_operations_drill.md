# Muninn v2 Replayable Shadow Operations Drill

Phase G tests whether the v2 read-only bridge survives realistic shadow
workflows, not just isolated context fixtures.

The drill is offline and v2-only. It does not call live MCP, replace Codex
defaults, write v1, create memory, or enable adaptive retrieval by default.

## Command

```bash
PYTHONPATH=src python3 -m muninn.v2.cli bridge-ops-drill \
  --fixture reports/pilots/phase_g_shadow_ops_drill_2026-05-17/bridge_ops_phase_g_fixture.json \
  --out-dir reports/pilots/phase_g_shadow_ops_drill_2026-05-17/drill
```

## Fixture Contract

The fixture is a JSON object:

```json
{
  "schema_version": "muninn.v2.bridge_ops_drill_fixture.v1",
  "name": "Phase G replayable shadow operations drill",
  "version": 1,
  "defaults": {
    "min_coverage": 1.0,
    "require_all_required": true,
    "budget_max_context_chars": 6500,
    "budget_min_coverage": 0.5
  },
  "pilots": [
    {
      "id": "friday",
      "project": "Friday",
      "v2_db": "/path/to/shadow_v2.db",
      "space_key": "repo:f8cc7f64d3636a4e",
      "project_path": "/mnt/data/friday",
      "consumer_id": "codex-shadow",
      "policy": {},
      "request_defaults": {},
      "sessions": [
        {
          "id": "friday-shadow-continuity",
          "continuity_needs": [],
          "tasks": [
            {
              "id": "resume-current-state",
              "query": "resume Friday project current state and next steps",
              "v1_context": "Optional v1-style baseline text.",
              "expected_needs": []
            }
          ]
        }
      ]
    }
  ]
}
```

Each task is run in three modes:

- `adaptive_off`: normal shadow bridge consumption; adaptive scoring remains
  disabled.
- `budget_pressure`: the same request under a smaller context budget.
- `adaptive_on`: explicit request plus explicit policy permission to read
  derived reinforcement state.

## Checks

The harness verifies:

- bridge and embedded rehydrate response validity
- request, policy, response, and audit hashes
- bridge audit DB unchanged markers
- v1-style context coverage comparison
- longitudinal continuity needs across tasks
- stale and confusing context flags
- budget clipping behavior
- adaptive-off versus explicit adaptive-on behavior
- cross-project contamination denial
- rendered context blocks for operator review

## Output

The output directory contains:

- `bridge_ops_drill_report.json`
- `bridge_ops_drill_report.md`
- `operator_review_notes.md`
- `rendered_context_blocks/*.md`
- per-task `bridge_request.json`, `bridge_policy.json`,
  `bridge_response_<request>.json`, and `bridge_audit_<request>.json`

## Status Semantics

The report always preserves the Phase G status boundary:

- `BRIDGE SHADOW CONSUMPTION`: `GO` only when every longitudinal task passes
  coverage, replay, contamination, and adaptive-default checks.
- `LIVE CUTOVER`: always `NO-GO`.
- `WRITES`: always `NO-GO`.
- `ADAPTIVE DEFAULT`: always `NO-GO`.

Phase G authorizes only continued shadow operations. It does not authorize live
agent-context replacement, live writes, autonomous reinforcement, or cutover.
