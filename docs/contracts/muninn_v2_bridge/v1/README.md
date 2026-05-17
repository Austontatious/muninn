# Muninn v2 Bridge Contracts

These contracts define the first controlled bridge for read-only Muninn v2
context consumption. They are not live v1 API, MCP, or Codex defaults.

## BridgeRequestV1

- Schema: `schemas/bridge-request.v1.schema.json`
- Valid example: `examples/valid/bridge-request.read-only-context.v1.json`
- Capability policy: `capabilities/read-only-context.v1.json`
- Contract version: `1.0.0`
- Schema version: `muninn.v2.bridge_request.v1`

`BridgeRequestV1` is intentionally capability-scoped. The only v1 capability is
`read_only_context`, which reads an explicit v2 shadow DB and emits a
`RehydrateResponseV1` plus a bridge audit log.

The request must explicitly deny writes, v1 access, reinforcement recording,
adaptive retrieval defaults, and LLM-dependent context generation. The bridge
rejects requests that do not carry those safety flags.

## Response

The bridge emits the existing Muninn v2 `RehydrateResponseV1` contract:

- `docs/contracts/muninn_v2/v1/schemas/rehydrate-response.v1.schema.json`

Consumers must treat `RehydrateResponseV1` as the agent-facing payload. The
bridge audit log is operational evidence for safety review, not replacement
memory context.

## Boundary

The bridge is local/offline and v2-only. It does not change v1 runtime,
production schemas, MCP routes, Codex defaults, or project repositories.
