# Muninn v2 Read-Only Bridge Architecture

## Purpose

Phase E introduces a local, opt-in Muninn v2 bridge that lets an external
consumer ask:

> Given this explicit v2 shadow DB, project scope, query, and budget, return
> explainable memory context.

The bridge is a controlled read-only consumption layer between external
agents/tools and Muninn v2. It is not production cutover, not live Codex context
replacement, and not a v1 MCP/API change.

It exposes:

- `health`: bridge/DB/index status
- `search`: scoped v2 retrieval
- `rehydrate`: bridge-wrapped `RehydrateResponseV1`
- `explain`: card/query provenance and score explanations
- recent context through the rehydrate composition stage
- audit replay metadata

It does not expose:

- autonomous write
- memory rewrite
- live reinforcement writeback
- unscoped global memory access
- Mimir cognition

## Gate Structure

Phase E is split into four gates:

1. E1 plan the bridge contract and safety boundary.
2. E2 validate the plan against existing v2 contracts and cross-project
   boundaries.
3. E3 build the read-only bridge harness.
4. E4 run local bridge validation and produce a pre-cutover report.

No gate authorizes live integration by itself.

## Trust Boundaries

External consumers submit request envelopes and policy-scoped identity. The
bridge validates policy before retrieval. Muninn v2 retrieval reads explicit
v2 canonical cards and optional derived indexes. Derived reinforcement state can
be read only in a future explicitly allowed mode; Phase E leaves adaptive
scoring disabled. v1 production Muninn remains outside the bridge boundary.

Rules:

- bridge may read v2 canonical state and derived index state
- bridge may not write canonical memory
- bridge may not access v1 unless a future explicit read-only safety-check mode
  is designed and approved
- bridge may not create memory cards
- bridge may not mutate reinforcement state unless a future explicit mode allows
  it
- future Mimir salience/cognition remains outside Muninn v2 bridge behavior

## Capability Scope Model

Bridge policy is deny-by-default. A policy object looks like:

```json
{
  "schema_version": "BridgeCapabilityPolicyV1",
  "consumer_id": "codex-shadow",
  "allowed_operations": ["health", "search", "rehydrate", "explain"],
  "allowed_space_keys": ["repo:f8cc7f64d3636a4e"],
  "allowed_project_paths": ["/mnt/data/friday"],
  "max_results": 12,
  "max_context_chars": 12000,
  "allow_adaptive_scoring": false,
  "allow_reinforcement_read": true,
  "allow_reinforcement_write": false,
  "allow_cross_project": false,
  "require_evidence": true,
  "require_explanations": true,
  "audit_log_required": true
}
```

Unknown consumers, unknown operations, missing project scope, wrong project,
wrong space, adaptive scoring without permission, and reinforcement writes are
denied before retrieval.

## Contract Surface

The operation bridge accepts `BridgeRequestV1`:

- Schema: `docs/contracts/muninn_v2_bridge/v1/schemas/bridge-request.v1.schema.json`
- Policy: `docs/contracts/muninn_v2_bridge/v1/schemas/bridge-capability-policy.v1.schema.json`
- Contract version: `1.0.0`

The bridge emits:

- `BridgeResponseV1`
- `RehydrateResponseV1` inside rehydrate results
- request-id scoped bridge audit log

Consumers must treat `BridgeResponseV1.result.rehydrate_response` as the stable
agent-context payload for rehydrate operations. The audit log is for safety
review and replay evidence.

Example health request:

```json
{
  "schema_version": "BridgeRequestV1",
  "operation": "health",
  "consumer_id": "codex-shadow",
  "request_id": "health-1"
}
```

Example search request:

```json
{
  "schema_version": "BridgeRequestV1",
  "operation": "search",
  "consumer_id": "codex-shadow",
  "request_id": "search-1",
  "query": "current Friday project state",
  "space_key": "repo:f8cc7f64d3636a4e",
  "project_path": "/mnt/data/friday",
  "limit": 10,
  "include_explanations": true
}
```

Example rehydrate request:

```json
{
  "schema_version": "BridgeRequestV1",
  "operation": "rehydrate",
  "consumer_id": "codex-shadow",
  "request_id": "rehydrate-1",
  "query": "resume Friday project",
  "space_key": "repo:f8cc7f64d3636a4e",
  "project_path": "/mnt/data/friday",
  "max_context_chars": 12000,
  "include_evidence": true,
  "include_explanations": true,
  "allow_adaptive_scoring": false
}
```

Bridge response shape:

```json
{
  "schema_version": "BridgeResponseV1",
  "request_id": "rehydrate-1",
  "operation": "rehydrate",
  "consumer_id": "codex-shadow",
  "status": "ok",
  "policy_decision": {"allowed": true, "reason_codes": [], "clamps": {}},
  "degradation": {"degraded": false, "reason_codes": []},
  "result": {},
  "audit": {
    "trace_id": "bridge_...",
    "created_at": "2026-05-17T00:00:00Z",
    "replayable": true,
    "input_hash": "...",
    "response_hash": "..."
  }
}
```

## Inputs

Required:

- explicit `v2_db` CLI argument
- explicit policy JSON
- explicit request JSON
- explicit output directory

Optional:

- `space_key`
- `project_path`
- operation-specific query, card id, limit, and budget controls
- retrieval mode: `hybrid`, `lexical`, or `vector`
- evidence and explanation inclusion flags

## Composition

The bridge reuses the v2 shadow rehydration preview composition:

1. Primary retrieval from the explicit v2 DB.
2. Recent in-scope supplements when enabled.
3. Evidence attachment when requested.
4. Explanation attachment when requested.
5. Budget accounting and omission metadata.
6. Deterministic non-LLM agent briefing.

The rehydrate output embeds the existing envelope with retrieval provenance,
fallback/degradation markers, budget usage, selected cards/events/evidence,
uncertainty/context gaps, and explanations.

## Adaptive Retrieval Visibility

Phase E leaves adaptive scoring disabled by default. If a future request enables
adaptive scoring, the bridge response must disclose:

- whether adaptive scoring was enabled
- reinforcement state version
- boosted cards
- suppressed cards
- reason codes
- scoring deltas
- fallback/degradation markers

Requests that ask for adaptive scoring are denied unless policy explicitly
allows it.

## Audit / Replay

Every `bridge-request` call writes:

- `bridge_response_<request_id>.json`
- `bridge_audit_<request_id>.json`

Audit records include request hash, policy hash, response hash, operation,
policy decision, degradation, v2 DB path/hash, retrieval config, adaptive config,
trace id, timestamp, and DB before/after metadata. Audit records avoid copying
giant context bodies; the response artifact is the replayable context payload.

## Read-Only Guarantees

The bridge:

- opens v2 card/index reads using SQLite read-only connections
- refuses missing explicit v2 DB paths
- refuses unsafe capability flags
- refuses persistent derived-index rebuild writes
- does not open v1 DBs
- does not record recall or reinforcement events
- does not mutate canonical v2 cards/events/evidence
- does not use an LLM to generate context
- emits before/after DB and sidecar snapshots in the audit log

If the DB or SQLite sidecar files change during the bridge read, the audit
decision becomes `no_go_review_required`.

## Boundary

Muninn owns durable memory and deterministic context envelopes. Bifrost remains
the source of cross-project topology/governance review, and Mimir remains the
future home for cognition-like salience propagation or hidden-link discovery.

The Phase E bridge deliberately does not implement:

- live MCP route replacement
- Codex default context replacement
- auth/rate-limited network service exposure
- autonomous writes
- adaptive retrieval by default
- Mimir-style cognition

## Failure Modes

The bridge fails closed when:

- request schema/version is unsupported
- capability is not `read_only_context`
- safety flags permit writes, v1 access, reinforcement events, adaptive
  defaults, or LLM dependency
- v2 DB is missing
- query is empty
- retrieval mode or limits are invalid
- strict v2 preview rules fail
- project not allowed
- context budget over policy max, which is clamped with a reason code
- adaptive scoring requested but not allowed
- evidence or explanations required by policy but omitted in the request

Failures return structured `BridgeResponseV1` JSON with `status` set to
`denied` or `error`.

## Rollback

Rollback is mechanical because Phase E does not touch live routes:

1. Stop using the `bridge-request` or `bridge-context` CLI.
2. Ignore or delete generated Phase E reports.
3. Revert v2 bridge source/docs if needed.
4. Keep v1 MCP/API/Codex configuration unchanged.

## GO/NO-GO

GO for local/offline bridge validation requires:

- `BridgeRequestV1` schema and example validate
- bridge emits valid `RehydrateResponseV1`
- bridge emits audit logs
- no v1 access or mutation
- no v2 canonical mutation
- tests pass

NO-GO remains for live agent context until an explicit cutover plan, rollback
plan, production auth/policy review, and operator approval exist.

Cutover preconditions:

- bridge contract stable
- read-only bridge tested across five pilots
- audit logs replayable
- policy denial tests pass
- no v1 mutation
- adaptive retrieval still opt-in
- rollback plan documented
- shadow comparison against v1 completed
- human approval for cutover
