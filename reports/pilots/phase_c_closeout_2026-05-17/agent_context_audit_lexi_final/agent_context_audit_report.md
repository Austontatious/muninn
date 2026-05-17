# Muninn v2 Agent Context Audit

- Fixture: `phase c final independent Lexi pilot`
- Cases: 1
- GO cases: 1
- NO-GO cases: 0
- Average v2 coverage: `1.0`
- Same-good-decision supported: 1
- Missing required needs: 0
- Confusing flags: 0
- Over-included cards: 1

## Cases

### lexi-runtime-modernization-resume

- Project: `Lexi`
- Decision: `go`
- V2 coverage: `1.0`
- Missing required: `[]`
- V1 comparison: `{'v1_context_provided': True, 'same_good_decision_supported': True, 'coverage_delta_v2_minus_v1': 0.0, 'regressions': []}`
- Stale flags: `[]`
- Confusing flags: `[]`
- Over-included cards: 1

Over-included candidates:
- `df2b467b-c10b-4a2f-8c2c-e1f5e34d603f` Lex end-to-end review: prioritize auth hardening, side-effect removal, and real eval gating (recent_in_scope_supplement)

## Safety

- Offline read-only harness only.
- Does not call live MCP or change Codex defaults.
- Does not write to v1 or project repositories.
