# Muninn v2 Agent Context Consumer Harness

The Phase B consumer harness proves whether a `RehydrateResponseV1` artifact can feed an agent safely and usefully before any live integration.

It is offline, read-only, and v2-only. It does not call live MCP tools, mutate v1 databases, change Codex defaults, or touch project repositories.

## Command

```bash
PYTHONPATH=src python3 -m muninn.v2.cli agent-context-audit \
  --fixture PATH \
  --out-dir PATH
```

Optional:

```bash
--schema docs/contracts/muninn_v2/v1/schemas/rehydrate-response.v1.schema.json
```

## Inputs

The fixture is a JSON object with cases. Each case points at a real `RehydrateResponseV1` JSON artifact and declares known project-state needs.

```json
{
  "schema_version": "muninn.v2.agent_context_audit_fixture.v1",
  "name": "phase b pilot fixture",
  "version": 1,
  "defaults": {
    "min_coverage": 0.85,
    "require_all_required": true
  },
  "cases": [
    {
      "id": "friday-resume",
      "project": "Friday",
      "task": "resume Friday project current state and next steps",
      "response_path": "reports/pilots/friday_v2_shadow_2026-05-17/shadow_rehydrate_preview_phase_a/shadow_rehydrate_preview.json",
      "v1_context": "Optional v1-style baseline context text.",
      "expected_needs": [
        {
          "id": "direct-coder-route",
          "description": "Agent knows Friday direct chat routes code prompts to coder.",
          "all_terms": ["direct chat", "coder"],
          "any_terms": ["repo file context", "file context"]
        }
      ]
    }
  ]
}
```

## Outputs

The command writes:

- `agent_context_audit_report.json`
- `agent_context_audit_report.md`
- `agent_context_blocks/<case-id>.md`

The context block is the exact deterministic text an offline agent experiment would receive. It includes:

- schema and contract metadata
- task/query
- v2 source DB metadata
- retrieval backend and degradation markers
- budget usage
- primary memory
- continuity supplements
- evidence refs
- uncertainty/context gaps
- deterministic briefing

## Scoring

For each case, the harness evaluates:

- required expected needs covered by the v2 context
- optional needs covered by the v2 context
- optional v1-style baseline context coverage
- v1-to-v2 regressions where the baseline covered a need but v2 missed it
- stale terms
- confusing terms
- over-included cards that do not match expected need terms

The main question is:

> If Codex consumed this v2 context instead of v1 memory, would it have made the same good decisions?

The harness answers `go` only when the v2 context passes the fixture coverage gate and does not regress against the provided v1-style baseline.

## Boundary

This harness is an offline evaluation consumer. It is not a bridge, live context source, MCP route, cutover mechanism, or retrieval optimizer.

Phase ordering remains:

1. Phase B: offline consumer harness
2. Phase C: multi-repo pilots using this harness
3. Phase D: recall/reinforcement mechanics
4. Phase E: cutover/rollback plan
5. Then, and only then, consider bridge/live integration
