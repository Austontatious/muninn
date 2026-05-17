# Muninn v2 Phase E Bridge Pre-Cutover Report

Date: 2026-05-17

## Executive Summary

Phase E built a local/offline v2 read-only bridge harness. It accepts a versioned `BridgeRequestV1`, rejects unsafe capabilities, reads only an explicit v2 shadow DB, and emits `RehydrateResponseV1` JSON, Markdown context, and a bridge audit log.

GO for local/offline read-only bridge validation. NO-GO remains for live Codex context replacement, v1 cutover, default adaptive retrieval, and autonomous writes.

## What Was Built

- BridgeRequestV1 schema and valid request fixture
- read_only_context capability policy
- v2 bridge-context CLI command
- read-only immutable SQLite bridge reads
- bridge audit log with DB and sidecar before/after snapshots
- tests for schema stability, unsafe request rejection, read-only CLI output, no v1 call, and no recall event write

## Pilot Results

### Friday

- Decision: `go_read_only_bridge`
- Read-only OK: `true`
- Selected cards: 8 (3 primary, 5 supplements)
- Retrieval mode: `hybrid`
- Degraded: `true`
- v1 accessed: `false`
- v1 mutated: `false`
- v2 canonical memory mutated: `false`
- v2 storage sidecar changed: `false`
- Context gaps: Derived index backend is degraded: sqlite_vec_unavailable_using_json_vector_fallback

### ReadyPlayer1

- Decision: `go_read_only_bridge`
- Read-only OK: `true`
- Selected cards: 9 (3 primary, 6 supplements)
- Retrieval mode: `hybrid`
- Degraded: `true`
- v1 accessed: `false`
- v1 mutated: `false`
- v2 canonical memory mutated: `false`
- v2 storage sidecar changed: `false`
- Context gaps: Derived index backend is degraded: sqlite_vec_unavailable_using_json_vector_fallback

## Validation

- `PYTHONPATH=src python3 -m pytest -q tests/test_v2_*.py`: 72 passed
- `python3 -m py_compile $(find src/muninn/v2 -name '*.py' | sort)`: passed
- `PYTHONPATH=src python3 -m pytest -q`: 259 passed, 2 skipped

## Safety Assessment

- v1 runtime/schema/MCP/default files were not changed.
- The bridge does not open v1 DBs; tests monkeypatch the v1 read connector to fail if called.
- The bridge records no recall/reinforcement events.
- The bridge uses immutable SQLite read-only connections and rejects non-empty WAL files to avoid silent sidecar writes or stale reads.
- Adaptive retrieval remains opt-in and disabled by default.
- Context generation is deterministic and non-LLM.

## Remaining Unsafe Areas

- No production network bridge/auth/rate limiting has been implemented.
- No live MCP or Codex integration has been reviewed or approved.
- No cutover or rollback runbook for production defaults exists yet.
- Bridge currently uses local CLI request files and local report output only.
- sqlite_vec remains unavailable, so vector-derived retrieval is degraded to the JSON/hash fallback.

## GO/NO-GO

- GO: local/offline read-only bridge validation.
- GO with review: future API or agent-context experiment that consumes `RehydrateResponseV1` without changing defaults.
- NO-GO: live Codex context replacement.
- NO-GO: v1 production cutover.
- NO-GO: default adaptive retrieval.
- NO-GO: autonomous writes.

## Recommended Next Task

Draft Phase E cutover-readiness plan for a read-only experimental API/adapter, including auth, operator controls, rollback, and explicit non-default wiring.
