# Cross-Project Compatibility (Muninn <-> Mimir)

## Purpose

Muninn and Mimir remain independently usable systems, but shared semantic surfaces must be mechanically locked to prevent silent drift.

## What Counts As Shared Contract Surface

A surface is shared if either repo emits, projects, or consumes it across project boundaries:
- card-like envelope projection
- lifecycle/status meanings
- provenance/source metadata envelope
- confidence/trust envelope
- rehydration request/response projection
- topology/binding reference projection

Internal models may differ. Shared projected contracts may not.

## Locked Surfaces (v1)

Locked by schemas + fixtures under `docs/contracts/muninn_mimir/v1`:
- `card-envelope.v1.schema.json`
- `lifecycle-state.v1.schema.json`
- `provenance-envelope.v1.schema.json`
- `confidence-trust.v1.schema.json`
- `rehydrate-request.v1.schema.json`
- `rehydrate-response.v1.schema.json`
- `topology-ref.v1.schema.json`

Examples:
- valid fixtures under `examples/valid/`
- invalid fixtures under `examples/invalid/`

## Current Deferred Surface

- Error/validation envelope harmonization is deferred in v1. The two repos currently expose different transport-level error formats (HTTP API vs MCP tool error payloads). This will be versioned as a dedicated shared envelope when we explicitly align semantics.

## Producer/Consumer View

- Muninn provides tool I/O envelopes, query envelopes, rehydration semantics, and memory-card projections used by cross-project integrations.
- Mimir provides repo-topology/rehydration projections and consumes shared envelope semantics when interfacing with Muninn-oriented workflows.

## Authoritative Artifact Locations

Both locations are canonical and must stay byte-identical for the same version:
- `/mnt/data/Muninn/docs/contracts/muninn_mimir/v1`
- `/mnt/data/Mimir/docs/contracts/muninn_mimir/v1`

## Versioning and Compatibility Policy

Version marker: `docs/contracts/muninn_mimir/v1/versions.json` (`current_version`).

Backward-compatible changes:
- add optional fields
- add safely ignorable enum values
- add tests/examples without changing existing required meaning

Breaking changes:
- remove/rename required fields
- narrow enums or alter existing semantics
- change envelope meaning without version bump

## Required Change Workflow

When shared contract shape/meaning changes:
1. Update schemas + fixtures in both repos.
2. Update this document and sibling repo copy.
3. Update compatibility tests in both repos.
4. Run validation in both repos.
5. If sibling compatibility is deferred, record an explicit deferred note in PR/task output.

## Deferred Gaps Log Policy

If a known compatibility gap is not fixed immediately, record:
- affected surface
- impacted repo(s)
- temporary behavior
- follow-up owner and expected fix window
