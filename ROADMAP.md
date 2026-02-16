# Roadmap

## v0 (Scaffold + Working Slice) ✅

- SQLite canonical store
- FastAPI endpoints
- Typed models + JSON schemas
- Memory card renderer
- Audit log for reads/writes

## v1 (Useful in production agents)

- Hybrid retrieval (lexical + vector)
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
