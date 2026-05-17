# Muninn v2 Phase E Read-Only Bridge Report

Date: 2026-05-17

## Executive Summary

Phase E now has an operation-oriented, policy-scoped, local/offline read-only bridge harness. It accepts BridgeRequestV1, enforces BridgeCapabilityPolicyV1 before retrieval, emits BridgeResponseV1, embeds RehydrateResponseV1 for rehydrate, and writes request-id scoped audit artifacts.

Cutover remains blocked. Bridge is GO for shadow read-only use only.

## Contracts Implemented

- BridgeRequestV1
- BridgeResponseV1
- BridgeCapabilityPolicyV1
- BridgeAuditV1 artifact shape

## Policy Model

deny_by_default_consumer_operation_space_project_budget_evidence_explanation_adaptive_policy

## Operations Implemented

- health
- search
- rehydrate
- explain

## Per-Pilot Results

### friday

- health: status=`ok`, allowed=`true`, degraded=`true`, reasons=`sqlite_vec_unavailable_using_json_vector_fallback`
- search: status=`ok`, allowed=`true`, degraded=`true`, reasons=`sqlite_vec_unavailable_using_json_vector_fallback`, results=3
- rehydrate: status=`ok`, allowed=`true`, degraded=`true`, reasons=`sqlite_vec_unavailable_using_json_vector_fallback`, selected=8 (3 primary, 5 supplements)
- explain: status=`ok`, allowed=`true`, degraded=`true`, reasons=`sqlite_vec_unavailable_using_json_vector_fallback`
- deny_wrong_project: status=`denied`, allowed=`false`, degraded=`false`, reasons=`none`
- deny_adaptive: status=`denied`, allowed=`false`, degraded=`false`, reasons=`none`

### lexi

- health: status=`ok`, allowed=`true`, degraded=`true`, reasons=`sqlite_vec_unavailable_using_json_vector_fallback`
- search: status=`ok`, allowed=`true`, degraded=`true`, reasons=`sqlite_vec_unavailable_using_json_vector_fallback,evidence_required_but_unavailable`, results=5
- rehydrate: status=`ok`, allowed=`true`, degraded=`true`, reasons=`sqlite_vec_unavailable_using_json_vector_fallback`, selected=8 (3 primary, 5 supplements)
- explain: status=`ok`, allowed=`true`, degraded=`true`, reasons=`sqlite_vec_unavailable_using_json_vector_fallback`
- deny_wrong_project: status=`denied`, allowed=`false`, degraded=`false`, reasons=`none`
- deny_adaptive: status=`denied`, allowed=`false`, degraded=`false`, reasons=`none`

### readyplayer1

- health: status=`ok`, allowed=`true`, degraded=`true`, reasons=`sqlite_vec_unavailable_using_json_vector_fallback`
- search: status=`ok`, allowed=`true`, degraded=`true`, reasons=`sqlite_vec_unavailable_using_json_vector_fallback`, results=10
- rehydrate: status=`ok`, allowed=`true`, degraded=`true`, reasons=`sqlite_vec_unavailable_using_json_vector_fallback`, selected=9 (3 primary, 6 supplements)
- explain: status=`ok`, allowed=`true`, degraded=`true`, reasons=`sqlite_vec_unavailable_using_json_vector_fallback`
- deny_wrong_project: status=`denied`, allowed=`false`, degraded=`false`, reasons=`none`
- deny_adaptive: status=`denied`, allowed=`false`, degraded=`false`, reasons=`none`

### sindri

- health: status=`ok`, allowed=`true`, degraded=`true`, reasons=`sqlite_vec_unavailable_using_json_vector_fallback`
- search: status=`ok`, allowed=`true`, degraded=`true`, reasons=`sqlite_vec_unavailable_using_json_vector_fallback`, results=7
- rehydrate: status=`ok`, allowed=`true`, degraded=`true`, reasons=`sqlite_vec_unavailable_using_json_vector_fallback`, selected=8 (3 primary, 5 supplements)
- explain: status=`ok`, allowed=`true`, degraded=`true`, reasons=`sqlite_vec_unavailable_using_json_vector_fallback`
- deny_wrong_project: status=`denied`, allowed=`false`, degraded=`false`, reasons=`none`
- deny_adaptive: status=`denied`, allowed=`false`, degraded=`false`, reasons=`none`

### subsim

- health: status=`ok`, allowed=`true`, degraded=`true`, reasons=`sqlite_vec_unavailable_using_json_vector_fallback`
- search: status=`ok`, allowed=`true`, degraded=`true`, reasons=`sqlite_vec_unavailable_using_json_vector_fallback`, results=1
- rehydrate: status=`ok`, allowed=`true`, degraded=`true`, reasons=`sqlite_vec_unavailable_using_json_vector_fallback`, selected=4 (1 primary, 3 supplements)
- explain: status=`ok`, allowed=`true`, degraded=`true`, reasons=`sqlite_vec_unavailable_using_json_vector_fallback`
- deny_wrong_project: status=`denied`, allowed=`false`, degraded=`false`, reasons=`none`
- deny_adaptive: status=`denied`, allowed=`false`, degraded=`false`, reasons=`none`

## Denial / Security Tests

- Wrong-project requests denied for all five pilots.
- Adaptive-scoring requests denied for all five pilots.
- Unit tests cover unknown operation, wrong project, adaptive scoring, omitted evidence, and invalid schema.

## Audit / Replay Status

response and audit artifacts include request hash, policy hash, response hash, DB path/hash, operation, policy decision, degradation, retrieval config, adaptive config, and trace id

## Adaptive Retrieval Status

disabled by default; denied unless policy explicitly allows it; no reinforcement writes are supported

## v1 Safety Status

- v1 row counts changed: `false`
- v1 runtime/schema/MCP/defaults changed: `false`
- bridge v1 access: `false`

## Known Limitations

- local CLI only; no production network auth/rate limiting
- sqlite_vec unavailable so derived vector status is degraded to JSON/hash fallback
- Lexi search includes evidence_required_but_unavailable degradation for some selected search hits
- SubSim has sparse search coverage for the generic resume query but rehydrate still returns scoped context
- no live integration, no cutover, no autonomous writes

## Cutover GO/NO-GO

- CUTOVER: NO-GO
- BRIDGE: GO FOR SHADOW READ-ONLY USE
- ADAPTIVE DEFAULT RETRIEVAL: NO-GO
- WRITES: NO-GO
