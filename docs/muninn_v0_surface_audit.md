# Muninn /v0 Surface Audit

Last updated: 2026-04-05

## Scope

This audit inventories all `/v0/*` HTTP routes in `src/muninn/api.py`, classifies each route by how it is backed, and notes compatibility risks.

## Classification legend

- **core-backed**: route is a thin wrapper over `core.v0_runtime.V0Runtime`.
- **human-memory direct**: route calls the human-memory subsystem directly (canonical, but not SDK-first core yet).
- **legacy direct**: route calls legacy modules directly without the v0 runtime adapter.

## Inventory

| Route | Status | Current path | Compatibility notes |
| --- | --- | --- | --- |
| `/v0/debug/vector_backend` | core-backed | `api.py -> V0Runtime.vector_backend_info -> vector_store` | Debug only. Keeps legacy vector backend probing. |
| `/v0/debug/stats` | legacy direct | `api.py -> ops.stats.collect_stats` | Not yet routed through `V0Runtime`; debug-only surface. |
| `/v0/memory/write_candidates` | core-backed | `api.py -> V0Runtime.write_candidates -> memory.writeback` | Legacy v0 write path preserved. |
| `/v0/memory/stage_candidates` | core-backed | `api.py -> V0Runtime.stage_candidates -> memory.pending` | Pending workflow preserved. |
| `/v0/memory/list_pending` | core-backed | `api.py -> V0Runtime.list_pending -> memory.pending` | Pending workflow preserved. |
| `/v0/memory/pending` (GET) | core-backed | `api.py -> V0Runtime.list_pending -> memory.pending` | Same as POST list. |
| `/v0/memory/confirm_candidates` | core-backed | `api.py -> V0Runtime.confirm_candidates -> memory.pending` | Confirm workflow preserved. |
| `/v0/memory/upsert_embeddings` | core-backed | `api.py -> V0Runtime.upsert_embeddings -> vector.store` | Legacy embedding upsert preserved. |
| `/v0/memory/query_vector` | core-backed | `api.py -> V0Runtime.query_vector -> vector.store` | Legacy vector query preserved. |
| `/v0/admin/reindex_vectors` | core-backed | `api.py -> V0Runtime.reindex_vectors -> vector.reindex` | Admin-only; backend compatibility preserved. |
| `/v0/admin/cleanup` | core-backed | `api.py -> V0Runtime.cleanup -> ops.cleanup` | Admin-only; retention semantics preserved. |
| `/v0/memory/retrieve` | core-backed | `api.py -> V0Runtime.retrieve -> memory.retrieval` | Legacy retrieval preserved. |
| `/v0/memory/render_cards` | core-backed | `api.py -> V0Runtime.render_cards -> memory.cards` | Legacy render path preserved. |
| `/v0/memory/rehydrate` | core-backed | `api.py -> V0Runtime.rehydrate -> memory.retrieval + memory.cards` | Legacy rehydrate preserved. |
| `/v0/memory/procedures/retrieve` | core-backed | `api.py -> core.procedures.ProcedureStore.query -> human_memory.procedures.query_procedure_cards` | Now routed through procedural core adapter. |
| `/v0/memory/procedures/reflect` | core-backed | `api.py -> core.procedures.ProcedureStore.reflect -> human_memory.procedures.ingest_procedure_reflection` | Now routed through procedural core adapter. |
| `/v0/memory/version` | legacy direct | `api.py -> service.memory_version` | Simple version surface; no core dependency. |

## Summary

- The `/v0/memory/*` and `/v0/admin/*` surfaces now flow through a single compatibility adapter (`core.v0_runtime.V0Runtime`).
- Procedure endpoints now flow through the core procedural adapter while preserving the same response shapes.
- Debug/stats endpoints are still direct legacy calls; they are non-critical and remain explicitly transitional.

## Follow-ups (non-blocking)

- Consider moving `collect_stats` behind `V0Runtime` if a stricter single-path rule is required for debug surfaces.
- Add SDK-level procedure primitives if `/v0/memory/procedures/*` needs to be deprecated in favor of SDK routes.
