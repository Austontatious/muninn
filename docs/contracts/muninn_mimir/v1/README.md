# Muninn-Mimir Shared Contract Artifacts (v1)

This directory is the mechanical contract surface shared between Muninn and Mimir.

Rules:
- Contract artifacts are versioned via `versions.json`.
- Shape changes are interface changes and must update docs + tests in both repos.
- This is a build/test-time compatibility layer only. It does not create a runtime dependency between repos.
- Both repos validate these schemas and fixtures and check sibling parity when both repos are present.

Current contract version:
- `1.0.0`

Locked v1 surfaces:
- Card-like envelope projection
- Lifecycle/status semantics projection
- Provenance envelope
- Confidence/trust envelope
- Rehydration request/response projection
- Topology or binding reference envelope
- Mimir declared-world memory proposal batch projection

Golden example fixtures:
- valid: `examples/valid/*.v1.json`
- invalid: `examples/invalid/*.v1.json`

Authoritative locations:
- `/mnt/data/Mimir/docs/contracts/muninn_mimir/v1`
- `/mnt/data/Muninn/docs/contracts/muninn_mimir/v1`

These directories must remain byte-for-byte identical for the same contract version.
