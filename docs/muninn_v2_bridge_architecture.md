# Muninn v2 Read-Only Bridge Architecture

## Purpose

Phase E introduces a local, opt-in Muninn v2 bridge that lets an external
consumer ask:

> Given this explicit v2 shadow DB, project scope, query, and budget, return
> explainable memory context.

The bridge is a controlled consumption layer. It is not production cutover, not
live Codex context replacement, and not a v1 MCP/API change.

## Gate Structure

Phase E is split into four gates:

1. E1 plan the bridge contract and safety boundary.
2. E2 validate the plan against existing v2 contracts and cross-project
   boundaries.
3. E3 build the read-only bridge harness.
4. E4 run local bridge validation and produce a pre-cutover report.

No gate authorizes live integration by itself.

## Contract Surface

The bridge accepts `BridgeRequestV1`:

- Schema: `docs/contracts/muninn_v2_bridge/v1/schemas/bridge-request.v1.schema.json`
- Capability: `read_only_context`
- Contract version: `1.0.0`

The bridge emits:

- `RehydrateResponseV1` JSON
- Markdown context preview
- bridge audit log

Consumers must treat `RehydrateResponseV1` as the stable agent-context payload.
The audit log is for safety review and replay evidence.

## Inputs

Required:

- explicit `v2_db`
- query text
- output directory
- read-only capability declaration
- safety flags denying writes, v1 access, reinforcement recording, adaptive
  retrieval defaults, and LLM dependency

Optional:

- `space_key`
- `project_path`
- limit and budget controls
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

The output envelope includes retrieval provenance, fallback/degradation markers,
budget usage, selected cards/events/evidence, uncertainty/context gaps, and
explanations.

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

## Rollback

Rollback is mechanical because Phase E does not touch live routes:

1. Stop using the `bridge-context` CLI.
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
