from __future__ import annotations

import json
import re
import sqlite3
import time
from typing import Any

from .. import db
from ..config import max_vec_scan
from ..models import (
    CardexRetrieveRequest,
    EvidenceProvenance,
    EvidenceRef,
    RedactionEvent,
    RetrieveCardRef,
    RetrievedCard,
    RetrievedEvidence,
)
from . import embeddings, store

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(r"\b(?:\+?\d{1,2}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}\b")


def _safe_query(query: str) -> str:
    tokens = [token for token in query.strip().split() if token]
    if not tokens:
        return query
    return " OR ".join(tokens)


def _query_tokens(query: str) -> list[str]:
    return [token for token in re.findall(r"[A-Za-z0-9_]+", query.lower()) if len(token) >= 2]


def _score_text(tokens: list[str], text: str) -> int:
    lowered = text.lower()
    return sum(lowered.count(token) for token in tokens)


def _redact_text(text: str) -> tuple[str, list[str]]:
    redactions: list[str] = []

    def _replace_email(_match) -> str:
        redactions.append("email")
        return "[REDACTED_EMAIL]"

    def _replace_phone(_match) -> str:
        redactions.append("phone")
        return "[REDACTED_PHONE]"

    out = _EMAIL_RE.sub(_replace_email, text)
    out = _PHONE_RE.sub(_replace_phone, out)
    # Keep evidence snippets compact for prompt assembly.
    out = out.strip()
    if len(out) > 480:
        out = out[:477].rstrip() + "..."
    return out, redactions


_HYBRID_VEC_WEIGHT = 0.65
_HYBRID_LEX_WEIGHT = 0.35
_HYBRID_RECENCY_WEIGHT = 0.05


def _rank_score(rank: int | None, total: int) -> float:
    if rank is None or total <= 0:
        return 0.0
    if total == 1:
        return 1.0
    return max(0.0, 1.0 - ((rank - 1) / float(total - 1)))


def _lexical_card_candidates(
    req: CardexRetrieveRequest,
    conn,
    limit: int,
) -> list[dict[str, Any]]:
    if not req.query.strip():
        return []

    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    fts_query = _safe_query(req.query)
    try:
        fts_rows = db.fetch_all(
            conn,
            """
            SELECT c.*, bm25(cards_fts) AS rank
            FROM cards_fts
            JOIN cards c ON c.card_id = cards_fts.card_id
            WHERE c.namespace = ?
              AND c.status = 'active'
              AND c.sensitivity_tier <= ?
              AND cards_fts.namespace = ?
              AND cards_fts MATCH ?
            ORDER BY rank ASC, c.salience DESC, c.updated_at DESC
            LIMIT ?
            """,
            (req.namespace, req.sensitivity_ceiling, req.namespace, fts_query, limit),
        )
    except sqlite3.OperationalError:
        fts_rows = []

    for row in fts_rows:
        card_id = str(row["card_id"])
        if card_id in seen:
            continue
        seen.add(card_id)
        payload = dict(row)
        payload["_lex_rank"] = float(row["rank"]) if row["rank"] is not None else 0.0
        out.append(payload)
        if len(out) >= limit:
            return out

    tokens = _query_tokens(req.query)
    if not tokens:
        fallback = req.query.lower().strip()
        tokens = [fallback] if fallback else []
    if not tokens:
        return out

    token_clauses: list[str] = []
    params: list[Any] = [req.namespace, req.sensitivity_ceiling]
    for token in tokens:
        like = f"%{token}%"
        token_clauses.append(
            "(lower(title) LIKE ? OR lower(summary) LIKE ? OR lower(tags_json) LIKE ?)"
        )
        params.extend([like, like, like])

    where_tokens = " OR ".join(token_clauses) if token_clauses else "1=1"
    rows = db.fetch_all(
        conn,
        f"""
        SELECT *
        FROM cards
        WHERE namespace = ?
          AND status = 'active'
          AND sensitivity_tier <= ?
          AND ({where_tokens})
        ORDER BY salience DESC, updated_at DESC
        LIMIT ?
        """,
        tuple(params + [limit]),
    )

    for row in rows:
        card_id = str(row["card_id"])
        if card_id in seen:
            continue
        seen.add(card_id)
        payload = dict(row)
        payload["_lex_rank"] = float(limit + len(out) + 1)
        out.append(payload)
        if len(out) >= limit:
            break

    return out


def _vector_card_candidates(
    req: CardexRetrieveRequest,
    conn,
    limit: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if "text" not in req.modalities:
        return [], {"model": None, "scanned": 0}
    if not req.query.strip():
        return [], {"model": None, "scanned": 0}

    model = embeddings.default_card_embedding_model()
    query_vec = embeddings.embed_text(req.query)
    scan_limit = max(1, min(int(max_vec_scan()), max(limit, limit * 4)))
    rows = db.fetch_all(
        conn,
        """
        SELECT owner_id, dims, vector_blob
        FROM card_embeddings
        WHERE namespace = ?
          AND owner_type = 'card'
          AND modality = 'text'
          AND model = ?
          AND embed_status = 'ready'
          AND vector_blob IS NOT NULL
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (req.namespace, model, scan_limit),
    )
    scored: dict[str, float] = {}
    for row in rows:
        try:
            vector = embeddings.unpack_f32(row["vector_blob"])
        except Exception:
            continue
        if len(vector) != len(query_vec):
            continue
        score = embeddings.cosine_sim(query_vec, vector)
        owner_id = str(row["owner_id"])
        best = scored.get(owner_id)
        if best is None or score > best:
            scored[owner_id] = score

    ordered = sorted(scored.items(), key=lambda pair: (-pair[1], pair[0]))
    candidate_ids = [card_id for card_id, _ in ordered[:limit]]
    if not candidate_ids:
        return [], {"model": model, "scanned": len(rows)}

    placeholders = ", ".join(["?"] * len(candidate_ids))
    card_rows = db.fetch_all(
        conn,
        (
            "SELECT * FROM cards "
            "WHERE namespace = ? AND status = 'active' AND sensitivity_tier <= ? "
            f"AND card_id IN ({placeholders})"
        ),
        tuple([req.namespace, req.sensitivity_ceiling] + candidate_ids),
    )
    by_id = {str(row["card_id"]): dict(row) for row in card_rows}

    out: list[dict[str, Any]] = []
    for card_id, score in ordered[:limit]:
        row = by_id.get(card_id)
        if not row:
            continue
        row["_vec_score"] = float(score)
        out.append(row)
    return out, {"model": model, "scanned": len(rows)}


def _hybrid_rank_cards(
    lexical: list[dict[str, Any]],
    vector: list[dict[str, Any]],
    k_cards: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    lexical_ids: list[str] = []
    vector_ids: list[str] = []

    for row in lexical:
        card_id = str(row["card_id"])
        lexical_ids.append(card_id)
        by_id.setdefault(card_id, dict(row))
    for row in vector:
        card_id = str(row["card_id"])
        vector_ids.append(card_id)
        by_id.setdefault(card_id, dict(row))

    lex_rank = {card_id: idx for idx, card_id in enumerate(lexical_ids, start=1)}
    vec_rank = {card_id: idx for idx, card_id in enumerate(vector_ids, start=1)}
    lex_total = len(lexical_ids)
    vec_total = len(vector_ids)

    updated = [float(row.get("updated_at") or 0.0) for row in by_id.values()]
    min_updated = min(updated) if updated else 0.0
    max_updated = max(updated) if updated else 0.0

    ranked: list[dict[str, Any]] = []
    for card_id, row in by_id.items():
        lex = _rank_score(lex_rank.get(card_id), lex_total)
        vec = _rank_score(vec_rank.get(card_id), vec_total)
        if max_updated > min_updated:
            recency = (float(row.get("updated_at") or 0.0) - min_updated) / (max_updated - min_updated)
        else:
            recency = 0.0
        combined = (
            (_HYBRID_VEC_WEIGHT * vec)
            + (_HYBRID_LEX_WEIGHT * lex)
            + (_HYBRID_RECENCY_WEIGHT * recency)
        )
        row["_hybrid_score"] = float(combined)
        row["_hybrid_lex"] = float(lex)
        row["_hybrid_vec"] = float(vec)
        ranked.append(row)

    ranked.sort(
        key=lambda row: (
            -float(row.get("_hybrid_score") or 0.0),
            -float(row.get("_hybrid_vec") or 0.0),
            -float(row.get("_hybrid_lex") or 0.0),
            -float(row.get("salience") or 0.0),
            -float(row.get("updated_at") or 0.0),
            str(row.get("card_id") or ""),
        )
    )
    merged_ids = [str(row["card_id"]) for row in ranked]
    meta = {
        "candidate_counts": {
            "lex": lex_total,
            "vec": vec_total,
            "merged": len(merged_ids),
        },
        "weights": {
            "vec": _HYBRID_VEC_WEIGHT,
            "lex": _HYBRID_LEX_WEIGHT,
            "recency": _HYBRID_RECENCY_WEIGHT,
        },
        "top_ids": {
            "lexical": lexical_ids[:10],
            "vector": vector_ids[:10],
            "hybrid": merged_ids[:10],
        },
    }
    return ranked[:k_cards], meta


def _search_cards(
    req: CardexRetrieveRequest,
    conn,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    start = time.monotonic()
    lexical_limit = max(40, req.k_cards * 4)
    vector_limit = max(40, req.k_cards * 4)
    lexical_rows = _lexical_card_candidates(req, conn, lexical_limit)
    vector_rows, vector_meta = _vector_card_candidates(req, conn, vector_limit)
    ranked_cards, rank_meta = _hybrid_rank_cards(lexical_rows, vector_rows, req.k_cards)

    blocked: list[dict[str, Any]] = []
    if req.query.strip():
        blocked_query = f"%{req.query.lower()}%"
        blocked_rows = db.fetch_all(
            conn,
            """
            SELECT card_id, title, sensitivity_tier
            FROM cards
            WHERE namespace = ?
              AND status = 'active'
              AND sensitivity_tier > ?
              AND (
                lower(title) LIKE ? OR
                lower(summary) LIKE ? OR
                lower(tags_json) LIKE ?
              )
            ORDER BY sensitivity_tier DESC, updated_at DESC
            LIMIT ?
            """,
            (
                req.namespace,
                req.sensitivity_ceiling,
                blocked_query,
                blocked_query,
                blocked_query,
                req.k_cards,
            ),
        )
        blocked = [dict(row) for row in blocked_rows]

    duration_ms = int((time.monotonic() - start) * 1000)
    meta = dict(rank_meta)
    meta["model"] = vector_meta.get("model")
    meta["vector_scan"] = int(vector_meta.get("scanned") or 0)
    meta["duration_ms"] = duration_ms
    return ranked_cards, blocked, meta


def _resolve_chunk_ref(conn, namespace: str, chunk_id: str) -> dict[str, Any] | None:
    row = db.fetch_one(
        conn,
        """
        SELECT c.chunk_id, c.text, d.doc_id, s.source_id, s.title AS source_title, s.uri, s.sensitivity_tier
        FROM chunks c
        JOIN documents d ON d.doc_id = c.doc_id AND d.namespace = ?
        JOIN sources s ON s.source_id = d.source_id AND s.namespace = ?
        WHERE c.namespace = ? AND c.chunk_id = ?
        """,
        (namespace, namespace, namespace, chunk_id),
    )
    if not row:
        return None
    return {
        "source_id": row["source_id"],
        "ref_type": "chunk",
        "ref_id": row["chunk_id"],
        "snippet": row["text"],
        "doc_title": row["source_title"],
        "uri": row["uri"],
        "sensitivity_tier": int(row["sensitivity_tier"]),
    }


def _resolve_doc_ref(conn, namespace: str, doc_id: str) -> dict[str, Any] | None:
    row = db.fetch_one(
        conn,
        """
        SELECT d.doc_id, d.content_text, s.source_id, s.title AS source_title, s.uri, s.sensitivity_tier
        FROM documents d
        JOIN sources s ON s.source_id = d.source_id AND s.namespace = ?
        WHERE d.namespace = ? AND d.doc_id = ?
        """,
        (namespace, namespace, doc_id),
    )
    if not row:
        return None

    snippet = str(row["content_text"] or "")
    return {
        "source_id": row["source_id"],
        "ref_type": "doc",
        "ref_id": row["doc_id"],
        "snippet": snippet,
        "doc_title": row["source_title"],
        "uri": row["uri"],
        "sensitivity_tier": int(row["sensitivity_tier"]),
    }


def _resolve_source_ref(conn, namespace: str, source_id: str) -> dict[str, Any] | None:
    row = db.fetch_one(
        conn,
        """
        SELECT source_id, title, uri, sensitivity_tier
        FROM sources
        WHERE namespace = ? AND source_id = ?
        """,
        (namespace, source_id),
    )
    if not row:
        return None

    snippet = str(row["title"])
    art = db.fetch_one(
        conn,
        """
        SELECT artifact_id, content_text
        FROM artifacts
        WHERE namespace = ? AND source_id = ? AND content_text IS NOT NULL AND trim(content_text) != ''
        ORDER BY CASE artifact_type
            WHEN 'summary' THEN 0
            WHEN 'transcript' THEN 1
            WHEN 'caption' THEN 2
            WHEN 'ocr' THEN 3
            ELSE 9 END,
            created_at DESC
        LIMIT 1
        """,
        (namespace, source_id),
    )
    ref_type = "source"
    ref_id = str(source_id)
    if art:
        snippet = str(art["content_text"])
        ref_type = "artifact"
        ref_id = str(art["artifact_id"])

    return {
        "source_id": row["source_id"],
        "ref_type": ref_type,
        "ref_id": ref_id,
        "snippet": snippet,
        "doc_title": row["title"],
        "uri": row["uri"],
        "sensitivity_tier": int(row["sensitivity_tier"]),
    }


def _resolve_ref(conn, namespace: str, ref_type: str, ref_id: str) -> dict[str, Any] | None:
    if ref_type == "chunk":
        return _resolve_chunk_ref(conn, namespace, ref_id)
    if ref_type == "doc":
        return _resolve_doc_ref(conn, namespace, ref_id)
    if ref_type == "source":
        return _resolve_source_ref(conn, namespace, ref_id)
    return None


def _artifact_fallback(req: CardexRetrieveRequest, conn, seen_refs: set[str]) -> list[dict[str, Any]]:
    fts_query = _safe_query(req.query)
    out: list[dict[str, Any]] = []

    try:
        rows = db.fetch_all(
            conn,
            """
            SELECT a.artifact_id, a.source_id, a.content_text, s.title, s.uri, s.sensitivity_tier, bm25(artifacts_fts) AS rank
            FROM artifacts_fts
            JOIN artifacts a ON a.artifact_id = artifacts_fts.artifact_id
            JOIN sources s ON s.source_id = a.source_id
            WHERE a.namespace = ?
              AND s.namespace = ?
              AND s.sensitivity_tier <= ?
              AND artifacts_fts.namespace = ?
              AND artifacts_fts MATCH ?
            ORDER BY rank ASC
            LIMIT ?
            """,
            (
                req.namespace,
                req.namespace,
                req.sensitivity_ceiling,
                req.namespace,
                fts_query,
                max(req.k_evidence * 2, req.k_evidence),
            ),
        )
    except sqlite3.OperationalError:
        return out

    for row in rows:
        ref_key = f"artifact:{row['artifact_id']}"
        if ref_key in seen_refs:
            continue
        out.append(
            {
                "source_id": row["source_id"],
                "ref_type": "artifact",
                "ref_id": row["artifact_id"],
                "snippet": row["content_text"],
                "doc_title": row["title"],
                "uri": row["uri"],
                "sensitivity_tier": int(row["sensitivity_tier"]),
            }
        )
        seen_refs.add(ref_key)
    return out


def _parse_tags(raw_tags_json: str) -> list[str]:
    try:
        parsed = json.loads(raw_tags_json)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(tag) for tag in parsed]


def retrieve_context_pack(
    req: CardexRetrieveRequest,
) -> tuple[list[RetrievedCard], list[RetrievedEvidence], dict[str, Any], list[RedactionEvent]]:
    conn = db.connect()
    card_rows, blocked_cards, search_meta = _search_cards(req, conn)
    redaction_events: list[RedactionEvent] = []

    card_ids = [str(row["card_id"]) for row in card_rows]
    refs_by_card = store.list_card_refs(req.namespace, card_ids)

    cards: list[RetrievedCard] = []
    for row in card_rows:
        card_id = str(row["card_id"])
        refs = [RetrieveCardRef(**ref) for ref in refs_by_card.get(card_id, [])]
        cards.append(
            RetrievedCard(
                card_id=card_id,
                title=str(row["title"]),
                summary=str(row["summary"]),
                tags=_parse_tags(str(row["tags_json"])),
                confidence=float(row["confidence"]),
                refs=refs,
            )
        )

    for blocked in blocked_cards:
        redaction_events.append(
            RedactionEvent(
                type="tier_block",
                target_type="card",
                target_id=str(blocked["card_id"]),
                reason="tier_exceeded",
                tier=int(blocked["sensitivity_tier"]),
                details={"title": str(blocked.get("title") or "")},
            )
        )

    evidence: list[RetrievedEvidence] = []
    if "evidence" not in req.scope:
        conn.close()
        notes = {
            "policy": "tiered_redaction_v1",
            "retrieval": "hybrid_v1",
            "model": search_meta.get("model"),
            "candidate_counts": search_meta.get("candidate_counts", {}),
            "weights": search_meta.get("weights", {}),
            "top_ids": search_meta.get("top_ids", {}),
            "timing_ms": search_meta.get("duration_ms"),
            "scope": req.scope,
            "searched": ["cards", "card_embeddings"],
            "fallback": "none",
        }
        return cards, evidence, notes, redaction_events

    candidates: list[dict[str, Any]] = []
    seen_refs: set[str] = set()
    for card in cards:
        for ref in card.refs:
            resolved = _resolve_ref(conn, req.namespace, ref.ref_type, ref.ref_id)
            if not resolved:
                continue
            if int(resolved["sensitivity_tier"]) > req.sensitivity_ceiling:
                redaction_events.append(
                    RedactionEvent(
                        type="tier_block",
                        target_type="evidence",
                        target_id=f"{resolved['ref_type']}:{resolved['ref_id']}",
                        reason="tier_exceeded",
                        tier=int(resolved["sensitivity_tier"]),
                        details={"source_id": str(resolved.get("source_id") or "")},
                    )
                )
                if len(evidence) < req.k_evidence:
                    evidence.append(
                        RetrievedEvidence(
                            source_id=(
                                str(resolved["source_id"])
                                if resolved.get("source_id") is not None
                                else None
                            ),
                            ref=EvidenceRef(
                                type=str(resolved["ref_type"]),
                                id=str(resolved["ref_id"]),
                            ),
                            snippet="",
                            provenance=EvidenceProvenance(
                                doc_title=(
                                    str(resolved.get("doc_title"))
                                    if resolved.get("doc_title") is not None
                                    else None
                                ),
                                uri=(
                                    str(resolved.get("uri"))
                                    if resolved.get("uri") is not None
                                    else None
                                ),
                            ),
                            redactions=["tier_exceeded"],
                            blocked=True,
                            blocked_reason="tier_exceeded",
                        )
                    )
                continue
            ref_key = f"{resolved['ref_type']}:{resolved['ref_id']}"
            if ref_key in seen_refs:
                continue
            seen_refs.add(ref_key)
            candidates.append(resolved)

    used_artifact_fallback = False
    if len(candidates) < req.k_evidence:
        fallback_candidates = _artifact_fallback(req, conn, seen_refs)
        if fallback_candidates:
            used_artifact_fallback = True
        candidates.extend(fallback_candidates)

    tokens = _query_tokens(req.query)
    ranked: list[tuple[int, dict[str, Any]]] = []
    for candidate in candidates:
        snippet = str(candidate.get("snippet") or "")
        title = str(candidate.get("doc_title") or "")
        score = _score_text(tokens, snippet) + _score_text(tokens, title)
        ranked.append((score, candidate))

    ranked.sort(key=lambda pair: pair[0], reverse=True)

    for _, candidate in ranked:
        snippet, snippet_redactions = _redact_text(str(candidate.get("snippet") or ""))
        per_evidence_redactions = snippet_redactions
        for marker in per_evidence_redactions:
            redactions_event = RedactionEvent(
                type="content_redaction",
                target_type="evidence",
                target_id=f"{candidate['ref_type']}:{candidate['ref_id']}",
                reason=marker,
                details={"source_id": str(candidate.get("source_id") or "")},
            )
            redaction_events.append(redactions_event)
        evidence.append(
            RetrievedEvidence(
                source_id=(
                    str(candidate["source_id"])
                    if candidate.get("source_id") is not None
                    else None
                ),
                ref=EvidenceRef(type=str(candidate["ref_type"]), id=str(candidate["ref_id"])),
                snippet=snippet,
                provenance=EvidenceProvenance(
                    doc_title=(
                        str(candidate["doc_title"])
                        if candidate.get("doc_title") is not None
                        else None
                    ),
                    uri=str(candidate["uri"]) if candidate.get("uri") is not None else None,
                ),
                redactions=per_evidence_redactions,
                blocked=False,
                blocked_reason=None,
            )
        )
        if len(evidence) >= req.k_evidence:
            break

    conn.close()
    fallback_used = used_artifact_fallback
    notes = {
        "policy": "tiered_redaction_v1",
        "retrieval": "hybrid_v1",
        "model": search_meta.get("model"),
        "candidate_counts": search_meta.get("candidate_counts", {}),
        "weights": search_meta.get("weights", {}),
        "top_ids": search_meta.get("top_ids", {}),
        "timing_ms": search_meta.get("duration_ms"),
        "vector_scan": search_meta.get("vector_scan", 0),
        "searched": ["cards", "card_embeddings", "artifacts.content_text"],
        "fallback": "artifact_search" if fallback_used else "none",
    }
    return cards, evidence, notes, redaction_events
