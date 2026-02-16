from __future__ import annotations

from fastapi import FastAPI, Query

from . import db
from .config import max_vec_scan
from .memory.cards import render_cards
from .memory.retrieval import retrieve
from .memory.writeback import write_candidates
from .models import (
    QueryVectorRequest,
    QueryVectorResponse,
    RehydrateRequest,
    RehydrateResponse,
    RenderCardsRequest,
    RenderCardsResponse,
    RetrieveRequest,
    RetrieveResponse,
    UpsertEmbeddingsRequest,
    UpsertEmbeddingsResponse,
    WriteCandidatesRequest,
    WriteCandidatesResponse,
)
from .service import log_audit, memory_version
from .vector import store as vector_store

app = FastAPI(title="Muninn", version="0.3.0")


@app.on_event("startup")
def startup() -> None:
    conn = db.connect()
    db.init_db(conn)


@app.get("/health")
def health() -> dict[str, bool]:
    conn = db.connect()
    row = db.fetch_one(conn, "SELECT 1 as ok")
    return {"ok": bool(row and row["ok"] == 1)}


@app.post("/v0/memory/write_candidates", response_model=WriteCandidatesResponse)
def api_write_candidates(req: WriteCandidatesRequest) -> WriteCandidatesResponse:
    ids, reasons = write_candidates(req.namespace, req.candidates)
    log_audit(
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


@app.post("/v0/memory/upsert_embeddings", response_model=UpsertEmbeddingsResponse)
def api_upsert_embeddings(req: UpsertEmbeddingsRequest) -> UpsertEmbeddingsResponse:
    upserted, rejected, reasons = vector_store.upsert_embeddings(req.namespace, req.items)
    models = sorted({item.model for item in req.items})
    log_audit(
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
