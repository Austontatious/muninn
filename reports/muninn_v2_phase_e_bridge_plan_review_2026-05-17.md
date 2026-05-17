# Muninn v2 Phase E Bridge Plan Review

Date: 2026-05-17

## Decision

GO for v2-only local/offline read-only bridge implementation.

NO-GO remains for live Codex context replacement, v1 cutover, default adaptive
retrieval, autonomous writes, or hidden memory mutation.

## Validation Questions

| Check | Result | Notes |
| --- | --- | --- |
| Preserve v1 safety? | PASS | Bridge reads explicit v2 DBs only and does not change v1 runtime/schema/MCP/defaults. |
| Prevent uncontrolled writes? | PASS | Capability policy denies writes; bridge writes only response/audit artifacts to caller output directory. |
| Prevent cross-project leakage? | PASS | Policy requires allowed `space_key` and `project_path`; missing or mismatched scope is denied. |
| Expose provenance? | PASS | Search/explain include score components and evidence when requested/required; rehydrate embeds `RehydrateResponseV1`. |
| Support replay? | PASS | Audit includes request hash, policy hash, response hash, DB hash/path, trace id, retrieval config, and adaptive config. |
| Keep adaptive scoring opt-in? | PASS | Adaptive scoring is disabled by default and denied unless policy explicitly allows it. |
| Keep Mimir out of Muninn? | PASS | Bridge is retrieval/context plumbing only; no motif detection, spreading activation, or hidden cognition. |
| Provide rollback/cutover gates? | PASS | Architecture doc lists rollback and cutover preconditions; cutover remains blocked. |

## Required Contract Corrections

The first Phase E bridge slice implemented a narrow `bridge-context` command.
The expanded instruction sheet requires an operation-based `BridgeRequestV1`,
`BridgeResponseV1`, and deny-by-default `BridgeCapabilityPolicyV1`. The plan is
valid after adding those operation contracts and keeping the narrow command as a
compatibility path.

## Approved Build Scope

- Add `bridge-request` CLI.
- Add `health`, `search`, `rehydrate`, and `explain` operations.
- Add policy file validation and enforcement before retrieval.
- Add structured denial/error responses.
- Add request-id scoped response and audit artifacts.
- Keep v1 untouched.

## Blocked Scope

- network daemon
- live MCP route
- Codex default context replacement
- v1 production DB access
- adaptive retrieval defaults
- autonomous memory creation or reinforcement writeback
