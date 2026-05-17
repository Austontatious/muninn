# Muninn v2 Bridge Contracts

These contracts define the Phase E read-only Muninn v2 bridge. They are not
live v1 API, MCP, or Codex defaults.

## Contracts

### BridgeRequestV1

- Schema: `schemas/bridge-request.v1.schema.json`
- Contract version: `1.0.0`
- Schema version: `BridgeRequestV1`
- Operations: `health`, `search`, `rehydrate`, `explain`

Requests are operation-oriented and must include `consumer_id`. Search,
rehydrate, and explain operations must include explicit project scope.

### BridgeResponseV1

- Schema: `schemas/bridge-response.v1.schema.json`
- Contract version: `1.0.0`
- Schema version: `BridgeResponseV1`

Responses carry structured status, policy decision, degradation markers, result
payload, optional structured error, and replay audit metadata. Rehydrate results
embed the existing `RehydrateResponseV1` envelope.

### BridgeCapabilityPolicyV1

- Schema: `schemas/bridge-capability-policy.v1.schema.json`
- Schema version: `BridgeCapabilityPolicyV1`
- Template: `capabilities/read-only-context.v1.json`

Policy is deny-by-default. A request is allowed only when the consumer,
operation, space key, project path, result budget, adaptive setting, evidence
requirements, and explanation requirements all satisfy the policy.

## Boundary

The bridge may read explicit v2 canonical and derived state. It may not write
canonical memory, create cards, record reinforcement events, read or write v1,
or perform live Codex/MCP cutover.
