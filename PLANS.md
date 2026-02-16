# Muninn v0.3 Hybrid Retrieval Plan

## Objective
Add caller-provided vector retrieval and hybrid FTS+vector retrieval with RRF fusion, while keeping all existing v0.2 APIs backward compatible.

## Scope
In:
- Embeddings storage table and vector query/upsert APIs
- Retrieval mode toggles (`fts`, `vector`, `hybrid`)
- Hybrid fusion via RRF
- Optional embedding fields in retrieve/rehydrate
- Version hash optionally including embedding model state
- Docs/tool spec/tests updates

Out:
- ANN indexing backends (`sqlite-vec`, `pgvector`) implementation
- Automatic embedding generation inside Muninn

## Checklist
- [x] Add config toggles for retrieval mode, RRF, and vector scan cap
- [x] Add embeddings table/indexes to schema
- [x] Add vector utilities and vector storage/query module
- [x] Extend models for embedding upsert/query and optional retrieve fields
- [x] Refactor retrieval into FTS/vector/hybrid pathways with recency fill
- [x] Add API endpoints for upsert/query vector and embed-aware rehydrate/retrieve
- [x] Update memory version endpoint for optional embedding model contribution
- [x] Update integration docs, tool spec, roadmap bullet
- [x] Add tests for vector query, hybrid RRF, and version with embeddings
- [x] Run ruff/pytest and smoke-test server endpoints

## Rollback plan
- Revert commit to return to v0.2 behavior
- Schema change is additive and non-destructive; old endpoints remain usable

## Test plan
- `ruff check .`
- `pytest -q`
- `./scripts/dev_run.sh` smoke test for `/docs`, `/v0/memory/upsert_embeddings`, and `/v0/memory/rehydrate` with `query_embedding`
