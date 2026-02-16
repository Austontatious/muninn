from __future__ import annotations

import sqlite3

from fastapi import FastAPI, Query

from . import db
from .config import max_vec_scan
from .memory import pending as pending_memory
from .memory.cards import render_cards
from .memory.retrieval import retrieve
from .memory.writeback import write_candidates
from .migrations import apply_migrations
from .models import (
    ConfirmCandidatesRequest,
    ConfirmCandidatesResponse,
    ListPendingRequest,
    ListPendingResponse,
    QueryVectorRequest,
    QueryVectorResponse,
    RehydrateRequest,
    RehydrateResponse,
    ReindexVectorsRequest,
    ReindexVectorsResponse,
    RenderCardsRequest,
    RenderCardsResponse,
    RetrieveRequest,
    RetrieveResponse,
    StageCandidatesRequest,
    StageCandidatesResponse,
    UpsertEmbeddingsRequest,
    UpsertEmbeddingsResponse,
    WriteCandidatesRequest,
    WriteCandidatesResponse,
)
from .service import log_audit, memory_version
from .vector import reindex as vector_reindex
from .vector import store as vector_store

app = FastAPI(title="Muninn", version="0.7.0")


@app.on_event("startup")
def startup() -> None:
    conn = db.connect()
    try:
        db.init_db(conn)
    except sqlite3.OperationalError as exc:
        # Existing pre-v0.5 DBs may fail schema apply before namespace migration.
        if "no such column: namespace" not in str(exc).lower():
            raise
        conn.rollback()
    apply_migrations(conn)
    db.init_db(conn)


@app.get("/health")
def health() -> dict[str, bool]:
    conn = db.connect()
    row = db.fetch_one(conn, "SELECT 1 as ok")
    return {"ok": bool(row and row["ok"] == 1)}


@app.get("/v0/debug/vector_backend")
def api_debug_vector_backend() -> dict[str, str | bool]:
    backend_config, sqlite_loaded, effective = vector_store.effective_backend()
    return {
        "vec_backend_config": backend_config,
        "sqlite_vec_loaded": sqlite_loaded,
        "effective_backend": effective,
    }


@app.post("/v0/memory/write_candidates", response_model=WriteCandidatesResponse)
def api_write_candidates(req: WriteCandidatesRequest) -> WriteCandidatesResponse:
    ids, reasons = write_candidates(req.namespace, req.candidates)
    log_audit(
        req.namespace,
        "write_candidates",
        {
            "namespace": req.namespace,
            "accepted_ids": ids,
            "reasons": reasons,
        },
    )
    accepted = len(ids)
    rejected = max(0, len(req.candidates) - accepted)
    return WriteCandidatesResponse(accepted=accepted, rejected=rejected, ids=ids, reasons=reasons)


@app.post("/v0/memory/stage_candidates", response_model=StageCandidatesResponse)
def api_stage_candidates(req: StageCandidatesRequest) -> StageCandidatesResponse:
    accepted_ids, pending_ids, rejected, pending_reasons = pending_memory.stage_candidates(
        namespace=req.namespace,
        candidates=req.candidates,
        ttl_seconds=req.ttl_seconds,
    )
    reject_reasons = [reason for _, reason in rejected]
    out = StageCandidatesResponse(
        accepted=len(accepted_ids),
        pending=len(pending_ids),
        rejected=len(reject_reasons),
        accepted_ids=accepted_ids,
        pending_ids=pending_ids,
        reject_reasons=reject_reasons,
        pending_reasons=pending_reasons,
    )
    log_audit(
        req.namespace,
        "stage_candidates",
        {
            "namespace": req.namespace,
            "accepted": out.accepted,
            "pending": out.pending,
            "rejected": out.rejected,
            "ttl_seconds": req.ttl_seconds,
        },
    )
    return out


@app.post("/v0/memory/list_pending", response_model=ListPendingResponse)
def api_list_pending(req: ListPendingRequest) -> ListPendingResponse:
    items = pending_memory.list_pending(
        namespace=req.namespace,
        entity_id=req.entity_id,
        status=req.status,
        limit=req.limit,
    )
    log_audit(
        req.namespace,
        "list_pending",
        {
            "namespace": req.namespace,
            "entity_id": req.entity_id,
            "status": req.status,
            "limit": req.limit,
            "items": len(items),
        },
    )
    return ListPendingResponse(items=items)


@app.get("/v0/memory/pending", response_model=ListPendingResponse)
def api_list_pending_get(
    namespace: str = Query(default="default"),
    entity_id: str | None = Query(default=None),
    status: str = Query(default="pending"),
    limit: int = Query(default=50),
) -> ListPendingResponse:
    items = pending_memory.list_pending(
        namespace=namespace,
        entity_id=entity_id,
        status=status,
        limit=limit,
    )
    return ListPendingResponse(items=items)


@app.post("/v0/memory/confirm_candidates", response_model=ConfirmCandidatesResponse)
def api_confirm_candidates(req: ConfirmCandidatesRequest) -> ConfirmCandidatesResponse:
    out = pending_memory.confirm_candidates(
        namespace=req.namespace,
        pending_ids=req.pending_ids,
        decision=req.decision,
        decided_by=req.decided_by,
        note=req.note,
    )
    log_audit(
        req.namespace,
        "confirm_candidates",
        {
            "namespace": req.namespace,
            "decision": req.decision,
            "pending_count": len(req.pending_ids),
            "processed": out.processed,
            "accepted_writes": out.accepted_writes,
            "rejected": out.rejected,
            "missing": out.missing,
            "expired": out.expired,
        },
    )
    return out


@app.post("/v0/memory/upsert_embeddings", response_model=UpsertEmbeddingsResponse)
def api_upsert_embeddings(req: UpsertEmbeddingsRequest) -> UpsertEmbeddingsResponse:
    upserted, rejected, reasons = vector_store.upsert_embeddings(req.namespace, req.items)
    models = sorted({item.model for item in req.items})
    log_audit(
        req.namespace,
        "upsert_embeddings",
        {
            "namespace": req.namespace,
            "upserted": upserted,
            "rejected": rejected,
            "models": models,
        },
    )
    return UpsertEmbeddingsResponse(upserted=upserted, rejected=rejected, reasons=reasons)


@app.post("/v0/memory/query_vector", response_model=QueryVectorResponse)
def api_query_vector(req: QueryVectorRequest) -> QueryVectorResponse:
    hits = vector_store.query_vector(
        namespace=req.namespace,
        model=req.model,
        query_vec=req.query_vector,
        entity_id=req.entity_id,
        kinds=req.kinds,
        k=req.k,
        max_scan=max_vec_scan(),
    )
    log_audit(
        req.namespace,
        "query_vector",
        {
            "namespace": req.namespace,
            "model": req.model,
            "entity_id": req.entity_id,
            "kinds": req.kinds,
            "k": req.k,
            "hits": len(hits),
        },
    )
    return QueryVectorResponse(hits=hits)


@app.post("/v0/admin/reindex_vectors", response_model=ReindexVectorsResponse)
def api_reindex_vectors(req: ReindexVectorsRequest) -> ReindexVectorsResponse:
    out = vector_reindex.reindex_vectors(
        namespace=req.namespace,
        model=req.model,
        dim=req.dim,
        batch_size=req.batch_size,
        dry_run=req.dry_run,
        force_backend=req.force_backend,
    )
    log_audit(
        req.namespace,
        "reindex_vectors",
        {
            "namespace": req.namespace,
            "model": req.model,
            "dim": req.dim,
            "batch_size": req.batch_size,
            "dry_run": req.dry_run,
            "force_backend": req.force_backend,
            "backend_used": out.backend_used,
            "scanned": out.scanned,
            "reindexed": out.reindexed,
            "skipped": out.skipped,
        },
    )
    return out


@app.post("/v0/memory/retrieve", response_model=RetrieveResponse)
def api_retrieve(req: RetrieveRequest) -> RetrieveResponse:
    items = retrieve(
        namespace=req.namespace,
        query=req.query,
        entity_id=req.entity_id,
        k=req.k,
        query_embedding=req.query_embedding,
        embedding_model=req.embedding_model,
    )
    log_audit(
        req.namespace,
        "retrieve",
        {
            "namespace": req.namespace,
            "query": req.query,
            "entity_id": req.entity_id,
            "k": req.k,
            "embedding_model": req.embedding_model,
            "has_query_embedding": req.query_embedding is not None,
        },
    )
    return RetrieveResponse(items=items)


@app.post("/v0/memory/render_cards", response_model=RenderCardsResponse)
def api_render_cards(req: RenderCardsRequest) -> RenderCardsResponse:
    cards = render_cards(req.items, req.profile)
    log_audit(
        req.namespace,
        "render_cards",
        {
            "namespace": req.namespace,
            "profile": req.profile,
            "n_items": len(req.items),
        },
    )
    return RenderCardsResponse(cards=cards)


@app.post("/v0/memory/rehydrate", response_model=RehydrateResponse)
def api_rehydrate(req: RehydrateRequest) -> RehydrateResponse:
    items = retrieve(
        namespace=req.namespace,
        query=req.query,
        entity_id=req.entity_id,
        k=req.k,
        query_embedding=req.query_embedding,
        embedding_model=req.embedding_model,
    )
    cards = render_cards(items, req.profile)
    log_audit(
        req.namespace,
        "rehydrate",
        {
            "namespace": req.namespace,
            "query": req.query,
            "profile": req.profile,
            "k": req.k,
            "embedding_model": req.embedding_model,
            "has_query_embedding": req.query_embedding is not None,
        },
    )
    return RehydrateResponse(cards=cards, items=items)


@app.get("/v0/memory/version")
def api_memory_version(
    namespace: str = Query(default="default"),
    profile: str = Query(default="generic"),
    embedding_model: str | None = Query(default=None),
) -> dict[str, str | None]:
    version = memory_version(namespace=namespace, profile=profile, embedding_model=embedding_model)
    return {
        "namespace": namespace,
        "profile": profile,
        "embedding_model": embedding_model,
        "version": version,
    }
