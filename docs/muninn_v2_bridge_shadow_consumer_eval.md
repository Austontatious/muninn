# Muninn v2 Bridge Shadow Consumer Evaluation

Phase F validates the read-only v2 bridge as a shadow context provider before
any live integration.

The harness consumes `BridgeResponseV1` artifacts from the Phase E bridge,
extracts the embedded `RehydrateResponseV1`, renders the deterministic context
block an agent would receive, and scores that block against controlled
Codex-style task fixtures.

It is offline and read-only. It does not call live MCP, mutate v1 databases,
change Codex defaults, record reinforcement events, or create memory.

## Command

```bash
PYTHONPATH=src python3 -m muninn.v2.cli bridge-consumer-eval \
  --fixture reports/pilots/phase_f_shadow_bridge_consumer_2026-05-17/bridge_consumer_phase_f_fixture.json \
  --out-dir reports/pilots/phase_f_shadow_bridge_consumer_2026-05-17/audit
```

Optional schema overrides:

```bash
--bridge-schema docs/contracts/muninn_v2_bridge/v1/schemas/bridge-response.v1.schema.json
--rehydrate-schema docs/contracts/muninn_v2/v1/schemas/rehydrate-response.v1.schema.json
```

## Fixture Contract

The fixture is a JSON object:

```json
{
  "schema_version": "muninn.v2.bridge_consumer_eval_fixture.v1",
  "name": "Phase F bridge shadow consumer evaluation",
  "version": 1,
  "defaults": {
    "min_coverage": 0.85,
    "require_all_required": true
  },
  "cases": [
    {
      "id": "friday-shadow-consumption",
      "project": "Friday",
      "task": "resume Friday project current state and next steps",
      "bridge_response_path": "friday/rehydrate/bridge_response_friday-rehydrate.json",
      "bridge_audit_path": "friday/rehydrate/bridge_audit_friday-rehydrate.json",
      "bridge_request_path": "requests/friday_rehydrate.json",
      "bridge_policy_path": "policies/friday_policy.json",
      "v2_db_path": "../friday_v2_shadow_2026-05-17/friday_shadow_v2.db",
      "v1_context": "Optional v1-style baseline context text.",
      "expected_needs": [
        {
          "id": "current-state",
          "description": "Agent has the durable project-state facts needed for the task.",
          "all_terms": ["current state"],
          "any_terms": ["next steps", "checkpoint"]
        }
      ]
    }
  ]
}
```

## Evaluation

For each case, the harness checks:

- `BridgeResponseV1` schema validity
- embedded `RehydrateResponseV1` schema validity
- bridge status, policy allow decision, and adaptive scoring disabled
- bridge audit replay metadata and response/request/policy hashes
- DB unchanged markers from the bridge audit
- deterministic rendered agent context
- expected need coverage
- v1-style baseline comparison and regressions
- omissions, stale/confusing flags, and over-included cards
- provenance, evidence, explanations, degradation markers, and trace IDs

The output is:

- `bridge_consumer_eval_report.json`
- `bridge_consumer_eval_report.md`
- `rendered_context_blocks/<case-id>.md`

## Status Semantics

The report always includes:

- `BRIDGE SHADOW CONSUMPTION`: `GO` only when every case passes coverage,
  replay, provenance, policy, and no-regression checks.
- `LIVE CUTOVER`: always `NO-GO` for Phase F.
- `WRITES`: always `NO-GO` for Phase F.
- `ADAPTIVE DEFAULT`: always `NO-GO` for Phase F.

Phase F proves only that bridge responses are good enough for controlled shadow
consumption. It does not authorize live agent-context replacement.
