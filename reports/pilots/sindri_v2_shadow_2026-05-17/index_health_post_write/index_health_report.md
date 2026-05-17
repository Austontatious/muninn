# Muninn v2 Derived Index Health

- v2 DB: `reports/pilots/sindri_v2_shadow_2026-05-17/sindri_shadow_v2.db`
- Backend: `json_vector_fallback`
- Backend available: `true`
- Eligible records: 26
- Indexed records: 26
- Missing records: 0
- Stale records: 0
- Degraded: `true`

## Reasons

- `sqlite_vec_unavailable_using_json_vector_fallback`

## Contract

- Vectors are optional derived indexes, not canonical truth.
- Rebuilds are explicit and scoped to the provided v2 DB path.
- sqlite_vec absence is allowed; fallback status must be reported.
