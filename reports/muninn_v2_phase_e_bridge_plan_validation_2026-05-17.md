# Muninn v2 Phase E Bridge Plan Validation

Date: 2026-05-17

## Gate

E2 validation: GO to build a local/offline read-only v2 bridge.

## Inputs Reviewed

- `AGENTS.md`
- `/home/unix/codex-standards/BASELINE.md`
- `ARCHITECTURE_CHECKPOINT.md`
- `docs/contracts/muninn_v2/v1/schemas/rehydrate-response.v1.schema.json`
- Phase A-D reports and current v2 CLI surfaces
- Bifrost cross-project boundary docs under `/mnt/data/Bifrost`

## Validation Result

The bridge can be implemented safely if it is limited to a local CLI harness
that accepts a versioned request contract, reads only an explicit v2 DB, emits
the existing `RehydrateResponseV1` envelope, and writes only local report/audit
artifacts.

## Accepted Scope

- Add `BridgeRequestV1`.
- Add read-only capability policy for `read_only_context`.
- Add v2-only `bridge-context` CLI command.
- Emit `RehydrateResponseV1`, Markdown context, and bridge audit log.
- Snapshot v2 DB and sidecar files before/after bridge reads.
- Reject unsafe request flags before bridge execution.

## Rejected Scope

- live MCP route changes
- v1 runtime/schema/default changes
- v1 DB access
- live Codex context replacement
- adaptive retrieval by default
- recall/reinforcement event recording from bridge reads
- LLM-dependent context generation
- Bifrost topology or Mimir cognition inside Muninn

## Cross-Project Boundary

Bifrost remains the governance/topology boundary. Muninn owns durable memory,
retrieval, and rehydration response contracts. The Phase E bridge is a Muninn
context-consumption adapter only; it does not own atlas topology or orchestration.

## Risk Decision

Primary risk: SQLite read-only connections can still create WAL/SHM sidecar
files. Mitigation required before GO: use immutable read-only connections for
bridge reads and reject non-empty WAL files so the bridge does not ignore
uncheckpointed data.

## GO/NO-GO

- GO: local/offline bridge build and fixture tests.
- NO-GO: live agent integration, production API deployment, v1 cutover, default
  adaptive retrieval, or autonomous writes.
