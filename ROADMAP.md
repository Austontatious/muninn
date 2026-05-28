# Roadmap

> Status: HISTORICAL. This roadmap reflects early product planning. Confirm
> current v1/v2 posture against `ARCHITECTURE_CHECKPOINT.md`,
> `docs/decisions/`, and the latest Phase J reports before treating any item
> here as active direction.

## v0 (Scaffold + Working Slice) ✅

- SQLite canonical store
- FastAPI endpoints
- Typed models + JSON schemas
- Memory card renderer
- Audit log for reads/writes

## v1 (Useful in production agents)

- Hybrid retrieval (lexical + vector)
- Lexical FTS5 retrieval done in v0.2; vector retrieval next
- Hybrid retrieval (FTS + vectors) with RRF fusion (SQLite brute-force v0; backend pluggable).
- Entity linking + dedupe/merge
- Contradiction ledger (coexist w/ confidence + provenance)
- Sensitivity tiers + redaction rules
- “Write gate” policies (auto vs user-confirmed)

## v2 (Performance + multi-tenant)

- Postgres option (and pgvector)
- Memory version hashing
- KV-prefix cache integration hooks (for inference servers)
- Per-user + per-project namespaces
- Background consolidation jobs

## v3 (Research-grade)

- Learned card compression (LoRA dataset logging)
- Episodic memory replay experiments
- Attention-native memory slots (model-dependent)

## Developer Experience (Future Infrastructure)

- Ambient Muninn integration when local service is healthy:
  - Detect local Muninn availability in the developer environment.
  - Default agent workflows to Muninn memory protocol without per-repo prompt drift.
  - Enforce repo bootstrap of canonical `AGENTS.md` memory block at repo creation/normalization time.
  - Add service-aware middleware/hooks so memory usage is default-on when `muninn.system.ping` succeeds.
