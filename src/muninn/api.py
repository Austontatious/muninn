from __future__ import annotations

from fastapi import FastAPI

from . import db
from .memory.cards import render_cards
from .memory.retrieval import retrieve
from .memory.writeback import write_candidates
from .models import (
    RehydrateRequest,
    RehydrateResponse,
    RenderCardsRequest,
    RenderCardsResponse,
    RetrieveRequest,
    RetrieveResponse,
    WriteCandidatesRequest,
    WriteCandidatesResponse,
)
from .service import log_audit

app = FastAPI(title="Muninn", version="0.1.0")


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


@app.post("/v0/memory/retrieve", response_model=RetrieveResponse)
def api_retrieve(req: RetrieveRequest) -> RetrieveResponse:
    items = retrieve(req.namespace, req.query, req.entity_id, req.k)
    log_audit(
        "retrieve",
        {
            "namespace": req.namespace,
            "query": req.query,
            "entity_id": req.entity_id,
            "k": req.k,
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
    items = retrieve(req.namespace, req.query, req.entity_id, req.k)
    cards = render_cards(items, req.profile)
    log_audit(
        "rehydrate",
        {
            "namespace": req.namespace,
            "query": req.query,
            "profile": req.profile,
            "k": req.k,
        },
    )
    return RehydrateResponse(cards=cards, items=items)
