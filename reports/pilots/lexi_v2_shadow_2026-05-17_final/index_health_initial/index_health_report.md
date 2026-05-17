# Muninn v2 Derived Index Health

- v2 DB: `reports/pilots/lexi_v2_shadow_2026-05-17_final/lexi_shadow_v2.db`
- Backend: `json_vector_fallback`
- Backend available: `true`
- Eligible records: 77
- Indexed records: 0
- Missing records: 77
- Stale records: 0
- Degraded: `true`

## Reasons

- `sqlite_vec_unavailable_using_json_vector_fallback`
- `index_table_missing`
- `rebuild_required`

## Contract

- Vectors are optional derived indexes, not canonical truth.
- Rebuilds are explicit and scoped to the provided v2 DB path.
- sqlite_vec absence is allowed; fallback status must be reported.
