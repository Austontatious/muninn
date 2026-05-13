from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request

from . import db
from .cardex import ingestion as cardex_ingestion
from .cardex import promotion as cardex_promotion
from .cardex import proposals as cardex_proposals
from .cardex import retrieval as cardex_retrieval
from .cardex import signals as cardex_signals
from .cardex import store as cardex_store
from .config import readonly
from .middleware import ApiKeyMiddleware
from .migrations import apply_migrations
from .models import (
    CardCreateRequest,
    CardCreateResponse,
    CardEmbeddingUpsertRequest,
    CardEmbeddingUpsertResponse,
    CardexRetrieveRequest,
    CardexRetrieveResponse,
    CardRecord,
    CleanupRequest,
    CleanupResponse,
    ConfirmCandidatesRequest,
    ConfirmCandidatesResponse,
    DecideProposalRequest,
    DecideProposalResponse,
    IngestRequest,
    IngestResponse,
    LinkCardRefsRequest,
    LinkCardRefsResponse,
    ListPendingRequest,
    ListPendingResponse,
    PromoteRequest,
    PromoteResponse,
    ProcedureReflectionRequest,
    ProcedureReflectionResponse,
    ProcedureRetrieveRequest,
    ProcedureRetrieveResponse,
    ProposeRequest,
    ProposeResponse,
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
    SourceArtifactsRequest,
    SourceArtifactsResponse,
    SourceCreateRequest,
    SourceCreateResponse,
    StageCandidatesRequest,
    StageCandidatesResponse,
    UpsertEmbeddingsRequest,
    UpsertEmbeddingsResponse,
    WriteCandidatesRequest,
    WriteCandidatesResponse,
)
from .ops.stats import collect_stats
from .service import begin_audit_buffer, end_audit_buffer, flush_audit_buffer, log_audit, memory_version
from .telemetry import emit_event as emit_telemetry_event, telemetry_context
from .core.config import MuninnConfig
from .core.procedures import ProcedureReflection, ProcedureStore
from .core.storage import HumanMemoryStore
from .core.v0_runtime import V0Runtime
from .human_memory.bootstrap import DEFAULT_USER_ID

app = FastAPI(title="Muninn", version="0.11.0")
app.add_middleware(ApiKeyMiddleware)


def _resolve_human_memory_db_path() -> Path:
    configured = os.getenv("MUNINN_HUMAN_MEMORY_DB_PATH", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return Path("~/.local/share/muninn/human_memory.db").expanduser().resolve()


def _human_store() -> HumanMemoryStore:
    return HumanMemoryStore(
        MuninnConfig(
            db_path=str(_resolve_human_memory_db_path()),
            user_id=DEFAULT_USER_ID,
        )
    )


_HUMAN_STORE = _human_store()
_V0_RUNTIME = V0Runtime()


def _procedure_store() -> ProcedureStore:
    return ProcedureStore(_human_store(), MuninnConfig())


@contextmanager
def _human_memory_conn() -> sqlite3.Connection:
    with _HUMAN_STORE.connect() as conn:
        yield conn


def _ensure_human_space(conn: sqlite3.Connection, *, space_key: str) -> str:
    normalized = str(space_key or "").strip() or "global"
    return _HUMAN_STORE.ensure_space_key(conn, space_key=normalized, cwd=None)


def require_writable() -> None:
    if readonly():
        raise HTTPException(status_code=503, detail="Muninn is in read-only mode")


def _stable_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def _request_namespace(request: Request) -> str:
    namespace = getattr(request.state, "namespace", None)
    if isinstance(namespace, str) and namespace.strip():
        return namespace.strip()
    return "default"


def _resolve_namespace(request: Request, provided_namespace: str | None) -> str:
    resolved_namespace = _request_namespace(request)
    enforce = bool(getattr(request.state, "namespace_enforced", False))
    allow_override = bool(getattr(request.state, "allow_namespace_override", False))
    if provided_namespace is None:
        return resolved_namespace

    candidate = provided_namespace.strip()
    if not candidate:
        return resolved_namespace

    if enforce and candidate != resolved_namespace:
        raise HTTPException(status_code=403, detail="Namespace override is not allowed")
    if allow_override:
        return candidate
    return resolved_namespace


def _extract_namespace(payload: dict[str, Any], request: Request) -> str:
    return _request_namespace(request)


def _api_db_target(conn: sqlite3.Connection) -> str:
    row = conn.execute("PRAGMA database_list;").fetchone()
    if row is None:
        return "<unknown>"
    path = str(row["file"] if isinstance(row, sqlite3.Row) else row[2] or "").strip()
    return path or ":memory:"


def _schema_migration_state(conn: sqlite3.Connection) -> dict[str, Any]:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id TEXT PRIMARY KEY,
            applied_at REAL NOT NULL
        )
        """
    )
    rows = conn.execute(
        "SELECT id FROM schema_migrations ORDER BY id ASC"
    ).fetchall()
    migration_ids = [str(row["id"] if isinstance(row, sqlite3.Row) else row[0]) for row in rows]
    return {
        "applied_count": len(migration_ids),
        "last_applied": migration_ids[-1] if migration_ids else None,
    }


def _emit_api_startup_event(stage: str, **payload: Any) -> None:
    emit_telemetry_event(
        {
            "event": "api_startup",
            "module": "muninn.api",
            "stage": stage,
            "config_source": "env_and_defaults",
            **telemetry_context(),
            **payload,
        },
        stream_prefix="MUNINN_EVENT",
        stream="stderr",
    )


@app.middleware("http")
async def audit_http_requests(request: Request, call_next):
    audit_token = begin_audit_buffer()
    body_payload: dict[str, Any] = {}
    raw_body = await request.body()
    if raw_body:
        try:
            parsed = json.loads(raw_body.decode("utf-8"))
            if isinstance(parsed, dict):
                body_payload = parsed
        except Exception:
            body_payload = {}

    actor = (
        body_payload.get("requested_by")
        or body_payload.get("decided_by")
        or request.headers.get("X-Actor")
        or "local"
    )
    scope = body_payload.get("scope")
    modalities = body_payload.get("modalities")
    purpose = body_payload.get("purpose")
    namespace = _extract_namespace(body_payload, request)
    action = f"{request.method} {request.url.path}"

    input_hash = _stable_hash(
        {
            "path": request.url.path,
            "method": request.method,
            "query": dict(request.query_params.items()),
            "body": body_payload,
        }
    )
    result_status = "success"
    output_hash: str | None = None
    error_detail: str | None = None
    status_code = 500

    try:
        response = await call_next(request)
        status_code = int(getattr(response, "status_code", 500))
        result_status = "success" if status_code < 400 else "error"
        response_body = getattr(response, "body", None)
        if isinstance(response_body, (bytes, bytearray)):
            output_hash = hashlib.sha256(bytes(response_body)).hexdigest()
        return response
    except Exception as exc:
        result_status = "error"
        error_detail = type(exc).__name__
        raise
    finally:
        try:
            log_audit(
                namespace,
                "http_request",
                {
                    "action": action,
                    "actor": actor,
                    "purpose": purpose,
                    "scope": scope if isinstance(scope, list) else None,
                    "modalities": modalities if isinstance(modalities, list) else None,
                    "input_hash": input_hash,
                    "output_hash": output_hash,
                    "result_status": result_status,
                    "http_status": status_code,
                    "error": error_detail,
                },
            )
        except Exception:
            # Never break request handling because audit write failed.
            pass
        finally:
            try:
                flush_audit_buffer()
            except Exception:
                # Never break request handling because audit flush failed.
                pass
            end_audit_buffer(audit_token)


@app.on_event("startup")
def startup() -> None:
    conn = db.connect()
    db_target = _api_db_target(conn)
    before_state = _schema_migration_state(conn)
    _emit_api_startup_event(
        "start",
        db_target=db_target,
        migration_applied_count=before_state["applied_count"],
        migration_last_applied=before_state["last_applied"],
    )
    try:
        db.init_db(conn)
    except sqlite3.OperationalError as exc:
        # Existing pre-v0.5 DBs may fail schema apply before namespace migration.
        if "no such column: namespace" not in str(exc).lower():
            _emit_api_startup_event(
                "failure",
                db_target=db_target,
                error_class=type(exc).__name__,
                error_text=str(exc),
            )
            raise
        conn.rollback()
    try:
        applied_now = apply_migrations(conn)
        db.init_db(conn)
        after_state = _schema_migration_state(conn)
        _emit_api_startup_event(
            "finish",
            db_target=db_target,
            migration_started=True,
            migration_applied_now=applied_now,
            migration_applied_now_count=len(applied_now),
            migration_applied_count=after_state["applied_count"],
            migration_last_applied=after_state["last_applied"],
            startup_result="ok",
        )
    except Exception as exc:
        _emit_api_startup_event(
            "failure",
            db_target=db_target,
            migration_started=True,
            error_class=type(exc).__name__,
            error_text=str(exc),
            startup_result="error",
        )
        raise
    finally:
        conn.close()


@app.get("/health")
def health() -> dict[str, bool]:
    conn = db.connect()
    row = db.fetch_one(conn, "SELECT 1 as ok")
    conn.close()
    return {"ok": bool(row and row["ok"] == 1)}


@app.get("/v0/debug/vector_backend")
def api_debug_vector_backend() -> dict[str, str | bool]:
    backend_config, sqlite_loaded, effective = _V0_RUNTIME.vector_backend_info()
    return {
        "vec_backend_config": backend_config,
        "sqlite_vec_loaded": sqlite_loaded,
        "effective_backend": effective,
    }


@app.get("/v0/debug/stats")
def api_debug_stats(request: Request, namespace: str | None = Query(default=None)) -> dict:
    resolved_namespace = _resolve_namespace(request, namespace)
    return collect_stats(namespace=resolved_namespace, api_version=app.version)


@app.post("/cards", response_model=CardCreateResponse)
def api_create_card(req: CardCreateRequest, request: Request) -> CardCreateResponse:
    require_writable()
    namespace = _resolve_namespace(request, req.namespace)
    payload = {
        "type": req.type,
        "title": req.title,
        "summary": req.summary,
        "details_json": req.details_json,
        "tags_json": req.tags_json,
        "salience": req.salience,
        "confidence": req.confidence,
        "sensitivity_tier": req.sensitivity_tier,
        "status": req.status,
    }

    if req.trusted_mode:
        card = cardex_store.create_card(
            namespace=namespace,
            card_type=req.type,
            title=req.title,
            summary=req.summary,
            details_json=req.details_json,
            tags_json=req.tags_json,
            salience=req.salience,
            confidence=req.confidence,
            sensitivity_tier=req.sensitivity_tier,
            status=req.status,
        )
        log_audit(
            namespace,
            "cardex_create_card",
            {
                "namespace": namespace,
                "card_id": card.card_id,
                "trusted_mode": True,
                "requested_by": req.requested_by,
            },
        )
        return CardCreateResponse(status="created", card_id=card.card_id)

    proposal = cardex_proposals.create_proposal(
        ProposeRequest(
            namespace=namespace,
            proposal_type="create_card",
            payload_json=payload,
            requested_by=req.requested_by,
            reason="create_card_request",
        )
    )
    log_audit(
        namespace,
        "cardex_propose_create_card",
        {
            "namespace": namespace,
            "proposal_id": proposal.proposal_id,
            "requested_by": req.requested_by,
        },
    )
    return CardCreateResponse(status="proposed", proposal_id=proposal.proposal_id)


@app.get("/cards/{card_id}", response_model=CardRecord)
def api_get_card(
    card_id: str,
    request: Request,
    namespace: str | None = Query(default=None),
) -> CardRecord:
    resolved_namespace = _resolve_namespace(request, namespace)
    card = cardex_store.get_card(namespace=resolved_namespace, card_id=card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return card


@app.post("/sources", response_model=SourceCreateResponse)
def api_create_source(req: SourceCreateRequest, request: Request) -> SourceCreateResponse:
    require_writable()
    namespace = _resolve_namespace(request, req.namespace)
    req.namespace = namespace
    out = cardex_store.create_source(req)
    log_audit(
        namespace,
        "cardex_create_source",
        {
            "namespace": namespace,
            "source_id": out.source.source_id,
            "doc_id": out.doc_id,
            "chunk_count": len(out.chunk_ids),
            "artifact_count": len(out.artifact_ids),
            "requested_by": req.requested_by,
        },
    )
    return out


@app.post("/ingest", response_model=IngestResponse)
def api_ingest(req: IngestRequest, request: Request) -> IngestResponse:
    require_writable()
    namespace = _resolve_namespace(request, req.namespace)
    req.namespace = namespace
    out = cardex_ingestion.ingest(req)
    log_audit(
        namespace,
        "cardex_ingest",
        {
            "namespace": namespace,
            "source_id": out.source.source_id,
            "source_type": req.source_type,
            "content_hash": out.content_hash,
            "tags": out.tags,
            "doc_id": out.doc_id,
            "chunk_count": len(out.chunk_ids),
            "artifact_types": out.artifact_types,
            "card_mode": req.card_mode,
            "card_id": out.card_id,
            "proposal_id": out.proposal_id,
            "requested_by": req.requested_by,
        },
    )
    return out


@app.post("/sources/{source_id}/artifacts", response_model=SourceArtifactsResponse)
def api_add_source_artifacts(
    source_id: str,
    req: SourceArtifactsRequest,
    request: Request,
) -> SourceArtifactsResponse:
    require_writable()
    namespace = _resolve_namespace(request, req.namespace)
    try:
        out = cardex_store.add_source_artifacts(
            namespace=namespace,
            source_id=source_id,
            artifacts=req.artifacts,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    log_audit(
        namespace,
        "cardex_add_source_artifacts",
        {
            "namespace": namespace,
            "source_id": source_id,
            "artifact_count": len(out.artifact_ids),
            "requested_by": req.requested_by,
        },
    )
    return out


@app.post("/cards/{card_id}/refs", response_model=LinkCardRefsResponse)
def api_link_card_refs(card_id: str, req: LinkCardRefsRequest, request: Request) -> LinkCardRefsResponse:
    require_writable()
    namespace = _resolve_namespace(request, req.namespace)
    try:
        linked = cardex_store.link_card_refs(namespace=namespace, card_id=card_id, refs=req.refs)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    log_audit(
        namespace,
        "cardex_link_refs",
        {
            "namespace": namespace,
            "card_id": card_id,
            "linked": linked,
            "requested_by": req.requested_by,
        },
    )
    return LinkCardRefsResponse(card_id=card_id, linked=linked)


@app.post("/embeddings", response_model=CardEmbeddingUpsertResponse)
def api_upsert_card_embedding(
    req: CardEmbeddingUpsertRequest,
    request: Request,
) -> CardEmbeddingUpsertResponse:
    require_writable()
    namespace = _resolve_namespace(request, req.namespace)
    req.namespace = namespace
    out = cardex_store.upsert_card_embedding(req)
    log_audit(
        namespace,
        "cardex_upsert_embedding",
        {
            "namespace": namespace,
            "embedding_id": out.embedding_id,
            "owner_type": req.owner_type,
            "owner_id": req.owner_id,
            "modality": req.modality,
            "status": out.embed_status,
            "requested_by": req.requested_by,
        },
    )
    return out


@app.post("/retrieve", response_model=CardexRetrieveResponse)
def api_cardex_retrieve(req: CardexRetrieveRequest, request: Request) -> CardexRetrieveResponse:
    namespace = _resolve_namespace(request, req.namespace)
    req.namespace = namespace
    query_hash = _stable_hash(
        {
            "namespace": namespace,
            "query": req.query,
            "purpose": req.purpose,
            "scope": req.scope,
            "modalities": req.modalities,
            "sensitivity_ceiling": req.sensitivity_ceiling,
        }
    )
    cards, evidence, notes, redactions = cardex_retrieval.retrieve_context_pack(req)
    signal_updates = {"signals_touched": 0, "coaccess_edges_touched": 0}
    promotion_actions: list[dict[str, Any]] = []
    signal_error: str | None = None
    promotion_error: str | None = None
    try:
        signal_updates = cardex_signals.record_access(
            namespace=namespace,
            cards=cards,
            evidence=evidence,
            query_hash=query_hash,
        )
    except Exception as exc:  # pragma: no cover - defensive
        signal_error = type(exc).__name__
    try:
        promotion_actions = cardex_promotion.evaluate_implicit_triggers(
            namespace=namespace,
            evidence=evidence,
            query_hash=query_hash,
        )
    except Exception as exc:  # pragma: no cover - defensive
        promotion_error = type(exc).__name__

    notes = dict(notes)
    notes["query_hash"] = query_hash
    notes["signal_updates"] = signal_updates
    notes["promotion_actions"] = len(promotion_actions)
    if signal_error:
        notes["signal_error"] = signal_error
    if promotion_error:
        notes["promotion_error"] = promotion_error

    for action in promotion_actions:
        log_audit(
            namespace,
            "cardex_promotion_trigger",
            {
                "namespace": namespace,
                "query_hash": query_hash,
                "owner_type": action.get("owner_type"),
                "owner_id": action.get("owner_id"),
                "status": action.get("status"),
                "proposal_id": action.get("proposal_id"),
                "card_id": action.get("card_id"),
                "trigger_reasons": action.get("trigger_reasons"),
                "notes": action.get("notes"),
            },
        )

    audit_id = log_audit(
        namespace,
        "cardex_retrieve",
        {
            "namespace": namespace,
            "query": req.query,
            "query_hash": query_hash,
            "purpose": req.purpose,
            "scope": req.scope,
            "modalities": req.modalities,
            "sensitivity_ceiling": req.sensitivity_ceiling,
            "k_cards": req.k_cards,
            "k_evidence": req.k_evidence,
            "cards": len(cards),
            "evidence": len(evidence),
            "redactions": len(redactions),
            "signals_touched": signal_updates.get("signals_touched"),
            "coaccess_edges_touched": signal_updates.get("coaccess_edges_touched"),
            "promotion_actions": len(promotion_actions),
            "notes": notes,
        },
    )
    return CardexRetrieveResponse(
        cards=cards,
        evidence=evidence,
        audit_id=audit_id,
        redactions=redactions,
        notes=notes,
    )


@app.post("/promote", response_model=PromoteResponse)
def api_promote(req: PromoteRequest, request: Request) -> PromoteResponse:
    require_writable()
    namespace = _resolve_namespace(request, req.namespace)
    try:
        out = cardex_promotion.promote_owner(
            namespace=namespace,
            owner_type=req.owner_type,
            owner_id=req.owner_id,
            mode=req.mode,
            card_type=req.card_type,
            card_title=req.card_title,
            card_summary=req.card_summary,
            tags=req.tags,
            refs=req.refs,
            requested_by=req.requested_by,
            reason="manual_promote",
        )
    except ValueError as exc:
        if str(exc) == "owner_not_found":
            raise HTTPException(status_code=404, detail="Evidence owner not found") from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    log_audit(
        namespace,
        "cardex_promote",
        {
            "namespace": namespace,
            "owner_type": req.owner_type,
            "owner_id": req.owner_id,
            "mode": req.mode,
            "requested_by": req.requested_by,
            "status": out.get("status"),
            "proposal_id": out.get("proposal_id"),
            "card_id": out.get("card_id"),
            "notes": out.get("notes", {}),
        },
    )
    return PromoteResponse(
        status=str(out.get("status") or "noop"),
        proposal_id=out.get("proposal_id"),
        card_id=out.get("card_id"),
        notes=dict(out.get("notes") or {}),
    )


@app.post("/propose", response_model=ProposeResponse)
def api_propose(req: ProposeRequest, request: Request) -> ProposeResponse:
    require_writable()
    namespace = _resolve_namespace(request, req.namespace)
    proposed = cardex_proposals.create_proposal(
        ProposeRequest(
            namespace=namespace,
            proposal_type=req.proposal_type,
            payload_json=req.payload_json,
            requested_by=req.requested_by,
            reason=req.reason,
        )
    )

    applied = None
    proposal = proposed
    if req.trusted_mode:
        proposal, applied = cardex_proposals.confirm_proposal(
            namespace=namespace,
            proposal_id=proposed.proposal_id,
            decided_by=req.requested_by or "trusted_mode",
            reason=req.reason or "trusted_mode_auto_confirm",
        )
        if proposal is None:
            raise HTTPException(status_code=500, detail="Failed to auto-confirm proposal")

    log_audit(
        namespace,
        "cardex_propose",
        {
            "namespace": namespace,
            "proposal_id": proposed.proposal_id,
            "proposal_type": req.proposal_type,
            "trusted_mode": req.trusted_mode,
            "status": proposal.status,
        },
    )
    return ProposeResponse(proposal=proposal, applied=applied)


@app.post("/confirm/{proposal_id}", response_model=DecideProposalResponse)
def api_confirm_proposal(
    proposal_id: str,
    req: DecideProposalRequest,
    request: Request,
) -> DecideProposalResponse:
    require_writable()
    namespace = _resolve_namespace(request, req.namespace)
    try:
        proposal, applied = cardex_proposals.confirm_proposal(
            namespace=namespace,
            proposal_id=proposal_id,
            decided_by=req.decided_by,
            reason=req.reason,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found or not proposed")

    log_audit(
        namespace,
        "cardex_confirm",
        {
            "namespace": namespace,
            "proposal_id": proposal_id,
            "decided_by": req.decided_by,
            "status": proposal.status,
        },
    )
    return DecideProposalResponse(proposal=proposal, applied=applied)


@app.post("/reject/{proposal_id}", response_model=DecideProposalResponse)
def api_reject_proposal(
    proposal_id: str,
    req: DecideProposalRequest,
    request: Request,
) -> DecideProposalResponse:
    require_writable()
    namespace = _resolve_namespace(request, req.namespace)
    proposal = cardex_proposals.reject_proposal(
        namespace=namespace,
        proposal_id=proposal_id,
        decided_by=req.decided_by,
        reason=req.reason,
    )
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found or not proposed")

    log_audit(
        namespace,
        "cardex_reject",
        {
            "namespace": namespace,
            "proposal_id": proposal_id,
            "decided_by": req.decided_by,
            "status": proposal.status,
        },
    )
    return DecideProposalResponse(proposal=proposal, applied=None)


@app.post("/v0/memory/write_candidates", response_model=WriteCandidatesResponse)
def api_write_candidates(req: WriteCandidatesRequest, request: Request) -> WriteCandidatesResponse:
    require_writable()
    namespace = _resolve_namespace(request, req.namespace)
    ids, reasons = _V0_RUNTIME.write_candidates(namespace, req.candidates)
    log_audit(
        namespace,
        "write_candidates",
        {
            "namespace": namespace,
            "accepted_ids": ids,
            "reasons": reasons,
        },
    )
    accepted = len(ids)
    rejected = max(0, len(req.candidates) - accepted)
    return WriteCandidatesResponse(accepted=accepted, rejected=rejected, ids=ids, reasons=reasons)


@app.post("/v0/memory/stage_candidates", response_model=StageCandidatesResponse)
def api_stage_candidates(req: StageCandidatesRequest, request: Request) -> StageCandidatesResponse:
    require_writable()
    namespace = _resolve_namespace(request, req.namespace)
    accepted_ids, pending_ids, rejected, pending_reasons = _V0_RUNTIME.stage_candidates(
        namespace=namespace,
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
        namespace,
        "stage_candidates",
        {
            "namespace": namespace,
            "accepted": out.accepted,
            "pending": out.pending,
            "rejected": out.rejected,
            "ttl_seconds": req.ttl_seconds,
        },
    )
    return out


@app.post("/v0/memory/list_pending", response_model=ListPendingResponse)
def api_list_pending(req: ListPendingRequest, request: Request) -> ListPendingResponse:
    namespace = _resolve_namespace(request, req.namespace)
    items = _V0_RUNTIME.list_pending(
        namespace=namespace,
        entity_id=req.entity_id,
        status=req.status,
        limit=req.limit,
    )
    log_audit(
        namespace,
        "list_pending",
        {
            "namespace": namespace,
            "entity_id": req.entity_id,
            "status": req.status,
            "limit": req.limit,
            "items": len(items),
        },
    )
    return ListPendingResponse(items=items)


@app.get("/v0/memory/pending", response_model=ListPendingResponse)
def api_list_pending_get(
    request: Request,
    namespace: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    status: str = Query(default="pending"),
    limit: int = Query(default=50),
) -> ListPendingResponse:
    resolved_namespace = _resolve_namespace(request, namespace)
    items = _V0_RUNTIME.list_pending(
        namespace=resolved_namespace,
        entity_id=entity_id,
        status=status,
        limit=limit,
    )
    return ListPendingResponse(items=items)


@app.post("/v0/memory/confirm_candidates", response_model=ConfirmCandidatesResponse)
def api_confirm_candidates(
    req: ConfirmCandidatesRequest,
    request: Request,
) -> ConfirmCandidatesResponse:
    require_writable()
    namespace = _resolve_namespace(request, req.namespace)
    out = _V0_RUNTIME.confirm_candidates(
        namespace=namespace,
        pending_ids=req.pending_ids,
        decision=req.decision,
        decided_by=req.decided_by,
        note=req.note,
    )
    log_audit(
        namespace,
        "confirm_candidates",
        {
            "namespace": namespace,
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
def api_upsert_embeddings(req: UpsertEmbeddingsRequest, request: Request) -> UpsertEmbeddingsResponse:
    require_writable()
    namespace = _resolve_namespace(request, req.namespace)
    upserted, rejected, reasons = _V0_RUNTIME.upsert_embeddings(namespace, req.items)
    models = sorted({item.model for item in req.items})
    log_audit(
        namespace,
        "upsert_embeddings",
        {
            "namespace": namespace,
            "upserted": upserted,
            "rejected": rejected,
            "models": models,
        },
    )
    return UpsertEmbeddingsResponse(upserted=upserted, rejected=rejected, reasons=reasons)


@app.post("/v0/memory/query_vector", response_model=QueryVectorResponse)
def api_query_vector(req: QueryVectorRequest, request: Request) -> QueryVectorResponse:
    namespace = _resolve_namespace(request, req.namespace)
    hits = _V0_RUNTIME.query_vector(
        namespace=namespace,
        model=req.model,
        query_vector=req.query_vector,
        entity_id=req.entity_id,
        kinds=req.kinds,
        k=req.k,
    )
    log_audit(
        namespace,
        "query_vector",
        {
            "namespace": namespace,
            "model": req.model,
            "entity_id": req.entity_id,
            "kinds": req.kinds,
            "k": req.k,
            "hits": len(hits),
        },
    )
    return QueryVectorResponse(hits=hits)


@app.post("/v0/admin/reindex_vectors", response_model=ReindexVectorsResponse)
def api_reindex_vectors(req: ReindexVectorsRequest, request: Request) -> ReindexVectorsResponse:
    require_writable()
    namespace = _resolve_namespace(request, req.namespace)
    out = _V0_RUNTIME.reindex_vectors(
        namespace=namespace,
        model=req.model,
        dim=req.dim,
        batch_size=req.batch_size,
        dry_run=req.dry_run,
        force_backend=req.force_backend,
    )
    log_audit(
        namespace,
        "reindex_vectors",
        {
            "namespace": namespace,
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


@app.post("/v0/admin/cleanup", response_model=CleanupResponse)
def api_admin_cleanup(req: CleanupRequest, request: Request) -> CleanupResponse:
    require_writable()
    namespace = _resolve_namespace(request, req.namespace)
    cleanup = _V0_RUNTIME.cleanup(
        namespace=namespace,
        targets=list(dict.fromkeys(req.targets)),
        statuses=req.statuses,
        older_than_seconds=req.older_than_seconds,
        limit=req.limit,
        dry_run=req.dry_run,
    )
    out = CleanupResponse(
        targets=cleanup["targets"],
        namespace=cleanup["namespace"],
        deleted_pending=cleanup["deleted_pending"],
        deleted_decisions=cleanup["deleted_decisions"],
        deleted_audit=cleanup["deleted_audit"],
        scanned=cleanup["scanned"],
        reasons=cleanup["reasons"],
    )
    log_audit(
        namespace,
        "admin_cleanup",
        {
            "namespace": namespace,
            "targets": out.targets,
            "statuses": req.statuses,
            "older_than_seconds": req.older_than_seconds,
            "limit": req.limit,
            "dry_run": req.dry_run,
            "deleted_pending": out.deleted_pending,
            "deleted_decisions": out.deleted_decisions,
            "deleted_audit": out.deleted_audit,
            "scanned": out.scanned,
            "reasons": out.reasons,
        },
    )
    return out


@app.post("/v0/memory/retrieve", response_model=RetrieveResponse)
def api_retrieve(req: RetrieveRequest, request: Request) -> RetrieveResponse:
    namespace = _resolve_namespace(request, req.namespace)
    items = _V0_RUNTIME.retrieve(
        namespace=namespace,
        query=req.query,
        entity_id=req.entity_id,
        k=req.k,
        query_embedding=req.query_embedding,
        embedding_model=req.embedding_model,
    )
    log_audit(
        namespace,
        "retrieve",
        {
            "namespace": namespace,
            "query": req.query,
            "entity_id": req.entity_id,
            "k": req.k,
            "embedding_model": req.embedding_model,
            "has_query_embedding": req.query_embedding is not None,
        },
    )
    return RetrieveResponse(items=items)


@app.post("/v0/memory/render_cards", response_model=RenderCardsResponse)
def api_render_cards(req: RenderCardsRequest, request: Request) -> RenderCardsResponse:
    namespace = _resolve_namespace(request, req.namespace)
    cards = _V0_RUNTIME.render_cards(req.items, req.profile)
    log_audit(
        namespace,
        "render_cards",
        {
            "namespace": namespace,
            "profile": req.profile,
            "n_items": len(req.items),
        },
    )
    return RenderCardsResponse(cards=cards)


@app.post("/v0/memory/rehydrate", response_model=RehydrateResponse)
def api_rehydrate(req: RehydrateRequest, request: Request) -> RehydrateResponse:
    namespace = _resolve_namespace(request, req.namespace)
    payload = _V0_RUNTIME.rehydrate(
        namespace=namespace,
        query=req.query,
        entity_id=req.entity_id,
        k=req.k,
        query_embedding=req.query_embedding,
        embedding_model=req.embedding_model,
        profile=req.profile,
    )
    items = payload["items"]
    cards = payload["cards"]
    log_audit(
        namespace,
        "rehydrate",
        {
            "namespace": namespace,
            "query": req.query,
            "profile": req.profile,
            "k": req.k,
            "embedding_model": req.embedding_model,
            "has_query_embedding": req.query_embedding is not None,
        },
    )
    return RehydrateResponse(cards=cards, items=items)


@app.post("/v0/memory/procedures/retrieve", response_model=ProcedureRetrieveResponse)
def api_retrieve_procedures(req: ProcedureRetrieveRequest, request: Request) -> ProcedureRetrieveResponse:
    namespace = _resolve_namespace(request, req.namespace)
    space_key = str(req.space_key or "").strip() or "global"
    procedure_store = _procedure_store()
    payload = procedure_store.query(
        space_key=space_key,
        task_label=req.task_label,
        context_summary=req.context_summary,
        task_type=req.task_type,
        tool_names=req.tool_names,
        limit=req.limit,
    )
    log_audit(
        namespace,
        "procedure_retrieve",
        {
            "namespace": namespace,
            "space_key": space_key,
            "task_label": req.task_label,
            "task_type": req.task_type,
            "tool_names": req.tool_names,
            "limit": req.limit,
            "returned": len(payload.procedures),
        },
    )
    return ProcedureRetrieveResponse(
        procedures=[item.model_dump() for item in payload.procedures],
        compact=list(payload.compact),
        diagnostics=dict(payload.diagnostics),
    )


@app.post("/v0/memory/procedures/reflect", response_model=ProcedureReflectionResponse)
def api_reflect_procedure(req: ProcedureReflectionRequest, request: Request) -> ProcedureReflectionResponse:
    require_writable()
    namespace = _resolve_namespace(request, req.namespace)
    space_key = str(req.space_key or "").strip() or "global"
    reflection = ProcedureReflection(
        task_label=req.task_label,
        context_summary=req.context_summary,
        actions_taken=list(req.actions_taken),
        outcome_status=req.outcome_status,
        what_worked=req.what_worked,
        what_failed=req.what_failed,
        changed_outcome=req.changed_outcome,
        reusable=bool(req.reusable),
        candidate_procedure_id=req.candidate_procedure_id,
        task_type=req.task_type,
        workflow_type=req.workflow_type,
        tool_requirements=list(req.tool_requirements),
        verification_checks=list(req.verification_checks),
        metadata=dict(req.metadata),
        actor=req.actor,
    )
    procedure_store = _procedure_store()
    result = procedure_store.reflect(
        reflection=reflection,
        space_key=space_key,
    )
    log_audit(
        namespace,
        "procedure_reflect",
        {
            "namespace": namespace,
            "space_key": space_key,
            "task_label": req.task_label,
            "outcome_status": req.outcome_status,
            "reusable": req.reusable,
            "action": result.action,
            "procedure_card_id": result.procedure_card_id,
        },
    )
    return ProcedureReflectionResponse(**result.model_dump())


@app.get("/v0/memory/version")
def api_memory_version(
    request: Request,
    namespace: str | None = Query(default=None),
    profile: str = Query(default="generic"),
    embedding_model: str | None = Query(default=None),
) -> dict[str, str | None]:
    resolved_namespace = _resolve_namespace(request, namespace)
    version = memory_version(
        namespace=resolved_namespace,
        profile=profile,
        embedding_model=embedding_model,
    )
    return {
        "namespace": resolved_namespace,
        "profile": profile,
        "embedding_model": embedding_model,
        "version": version,
    }
