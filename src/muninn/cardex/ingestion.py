from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import urlparse

from .. import db
from ..models import (
    CardRefInput,
    CardType,
    IngestChunk,
    IngestRequest,
    IngestResponse,
    ProposeRequest,
    SourceRecord,
)
from . import proposals, store

_STOPWORDS = {
    "about",
    "after",
    "also",
    "been",
    "from",
    "have",
    "into",
    "more",
    "that",
    "their",
    "there",
    "these",
    "this",
    "those",
    "with",
    "where",
    "which",
    "while",
    "would",
}


@dataclass(frozen=True)
class _Block:
    start: int
    end: int
    text: str
    heading_path: list[str]


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _stable_id(prefix: str, *parts: object) -> str:
    base = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(base.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{digest}"


def _json_dumps(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=True)


def _normalize_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in normalized.split("\n")]
    normalized = "\n".join(lines)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def _resolve_uri(req: IngestRequest, content_hash: str | None) -> str:
    if req.uri:
        return req.uri
    if req.file_path:
        return f"file://{req.file_path}"
    suffix = content_hash or "pending"
    return f"ingest://{req.source_type}/{suffix}"


def _default_title(req: IngestRequest, uri: str) -> str:
    if req.title:
        return req.title.strip() or f"{req.source_type} source"

    if req.file_path:
        file_name = PurePosixPath(req.file_path).name
        if file_name:
            return file_name

    parsed = urlparse(uri)
    if parsed.scheme in {"http", "https"}:
        host = parsed.netloc or "web"
        path = PurePosixPath(parsed.path or "/")
        tail = path.name if path.name else host
        return tail

    return f"{req.source_type} source"


def _source_input(req: IngestRequest, has_text: bool) -> str:
    if has_text:
        return "inline_text"
    if req.file_path:
        return "file_stub"
    if req.uri and req.uri.startswith(("http://", "https://")):
        return "url_stub"
    return "source_stub"


def _keyword_tags(title: str, text: str, limit: int = 6) -> list[str]:
    sample = f"{title}\n{text[:1200]}".lower()
    words = re.findall(r"[a-z][a-z0-9_]{2,}", sample)
    freq: dict[str, int] = {}
    for word in words:
        if word in _STOPWORDS:
            continue
        freq[word] = freq.get(word, 0) + 1
    ordered = sorted(freq.items(), key=lambda pair: (-pair[1], pair[0]))
    return [f"kw:{word}" for word, _ in ordered[:limit]]


def _kind_tags(source_type: str, title: str, text: str) -> list[str]:
    blob = f"{title}\n{text[:2000]}".lower()
    tags = [f"type:{source_type}"]

    if "ingredient" in blob or "recipe" in blob:
        tags.append("kind:recipe")
    if "doi" in blob or "abstract" in blob or "journal" in blob:
        tags.append("kind:paper")
    if any(token in blob for token in ["contact", "email", "phone", "linkedin"]):
        tags.append("kind:contact")
    if source_type in {"image", "audio", "video"}:
        tags.append(f"modality:{source_type}")

    return tags


def _location_tags(uri: str, file_path: str | None) -> list[str]:
    tags: list[str] = []
    parsed = urlparse(uri)
    if parsed.netloc:
        tags.append(f"domain:{parsed.netloc.lower()}")

    path = file_path or parsed.path
    if path:
        leaf = PurePosixPath(path).name
        if leaf:
            tags.append(f"file:{leaf.lower()}")
        suffix = PurePosixPath(path).suffix.lower().lstrip(".")
        if suffix:
            tags.append(f"ext:{suffix}")
    return tags


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def _infer_tags(req: IngestRequest, uri: str, title: str, normalized_text: str) -> list[str]:
    tags = []
    tags.extend(_location_tags(uri, req.file_path))
    tags.extend(_kind_tags(req.source_type, title, normalized_text))
    tags.extend(_keyword_tags(title, normalized_text))
    tags.extend(req.user_tags)
    return _dedupe_keep_order(tags)


def _split_blocks(normalized_text: str) -> list[_Block]:
    if not normalized_text:
        return []

    blocks: list[_Block] = []
    heading_stack: list[str] = []

    for match in re.finditer(r".+?(?:\n{2,}|\Z)", normalized_text, re.S):
        raw = match.group(0)
        stripped = raw.strip()
        if not stripped:
            continue

        rel_start = raw.find(stripped)
        start = match.start() + max(0, rel_start)
        end = start + len(stripped)

        first_line = stripped.split("\n", 1)[0].strip()
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", first_line)
        if heading_match:
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()
            heading_stack = heading_stack[: max(0, level - 1)] + [heading_text]

        blocks.append(
            _Block(
                start=start,
                end=end,
                text=stripped,
                heading_path=list(heading_stack),
            )
        )

    return blocks


def _assemble_chunks(
    blocks: list[_Block],
    target_chars: int,
    overlap_chars: int,
) -> list[tuple[int, int, str, list[str]]]:
    if not blocks:
        return []

    chunks: list[tuple[int, int, str, list[str]]] = []
    i = 0
    target = max(200, target_chars)
    overlap = max(0, min(overlap_chars, target - 1))

    while i < len(blocks):
        start_i = i
        end_i = i
        acc = 0

        while end_i < len(blocks):
            block_len = len(blocks[end_i].text)
            added = block_len + (2 if end_i > start_i else 0)
            if end_i > start_i and acc + added > target:
                break
            acc += added
            end_i += 1

        selected = blocks[start_i:end_i]
        chunk_text = "\n\n".join(block.text for block in selected)
        heading_path: list[str] = []
        for block in reversed(selected):
            if block.heading_path:
                heading_path = block.heading_path
                break

        chunks.append(
            (
                selected[0].start,
                selected[-1].end,
                chunk_text,
                heading_path,
            )
        )

        if end_i >= len(blocks):
            break

        overlap_i = end_i
        overlap_acc = 0
        j = end_i - 1
        while j >= start_i:
            block_len = len(blocks[j].text) + 2
            if overlap_acc + block_len > overlap and j < end_i - 1:
                break
            overlap_acc += block_len
            overlap_i = j
            j -= 1

        if overlap_i <= start_i:
            i = end_i
        else:
            i = overlap_i

    return chunks


def _pending_artifact_types(req: IngestRequest, has_text: bool) -> list[str]:
    if has_text:
        return []

    if req.source_type in {"document", "web", "note", "file", "email", "chat", "other"}:
        return ["extracted_text"]
    if req.source_type == "image":
        return ["caption", "ocr", "objects"]
    if req.source_type == "audio":
        return ["transcript"]
    if req.source_type == "video":
        return ["transcript", "caption", "keyframes"]
    return []


def _artifact_payload_for_pending(source_input: str) -> str:
    return _json_dumps(
        {
            "status": "pending",
            "reason": "ingest_v1_placeholder",
            "source_input": source_input,
        }
    )


def _source_row_to_record(row) -> SourceRecord:
    metadata: dict[str, Any]
    try:
        metadata = json.loads(str(row["metadata_json"]))
        if not isinstance(metadata, dict):
            metadata = {}
    except json.JSONDecodeError:
        metadata = {}

    return SourceRecord(
        source_id=str(row["source_id"]),
        namespace=str(row["namespace"]),
        source_type=str(row["source_type"]),
        uri=str(row["uri"]),
        title=str(row["title"]),
        metadata_json=metadata,
        content_hash=row["content_hash"],
        sensitivity_tier=int(row["sensitivity_tier"]),
        created_at=float(row["created_at"]),
    )


def _infer_card_type(source_type: str, tags: list[str], explicit: CardType | None) -> CardType:
    if explicit is not None:
        return explicit
    if any(tag == "kind:recipe" for tag in tags):
        return "recipe"
    if any(tag == "kind:paper" for tag in tags):
        return "paper"
    if any(tag == "kind:contact" for tag in tags):
        return "contact"
    if source_type in {"image", "audio", "video"}:
        return "media"
    return "fact"


def _default_card_summary(title: str, normalized_text: str, source_type: str) -> str:
    if normalized_text:
        snippet = normalized_text[:260].replace("\n", " ").strip()
        return snippet if len(snippet) < len(normalized_text) else snippet
    return f"Ingested {source_type} source: {title}"


def ingest(req: IngestRequest) -> IngestResponse:
    normalized_text = _normalize_text(req.text or "")
    has_text = bool(normalized_text)
    content_hash = _sha256_text(normalized_text) if has_text else None

    uri = _resolve_uri(req, content_hash)
    title = _default_title(req, uri)
    tags = _infer_tags(req, uri, title, normalized_text)
    source_input = _source_input(req, has_text)

    source_id = _stable_id(
        "src",
        req.namespace,
        req.source_type,
        uri,
        content_hash or "pending",
    )

    metadata_json = dict(req.metadata_json)
    metadata_json.update(
        {
            "ingest_v": 1,
            "source_input": source_input,
            "mime_type": req.mime_type,
            "file_path": req.file_path,
            "tags": tags,
        }
    )

    doc_id: str | None = None
    chunk_ids: list[str] = []
    chunk_rows: list[IngestChunk] = []
    artifact_ids: list[str] = []
    artifact_types: list[str] = []

    conn = db.connect()
    now_ts = db.now()

    conn.execute(
        """
        INSERT INTO sources
            (source_id, namespace, source_type, uri, title, metadata_json, content_hash, sensitivity_tier, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_id) DO UPDATE SET
            title = excluded.title,
            metadata_json = excluded.metadata_json,
            content_hash = excluded.content_hash,
            sensitivity_tier = excluded.sensitivity_tier
        """,
        (
            source_id,
            req.namespace,
            req.source_type,
            uri,
            title,
            _json_dumps(metadata_json),
            content_hash,
            req.sensitivity_tier,
            now_ts,
        ),
    )

    if has_text:
        doc_id = _stable_id("doc", source_id, content_hash or "text")
        conn.execute(
            """
            INSERT OR IGNORE INTO documents (doc_id, namespace, source_id, content_text, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (doc_id, req.namespace, source_id, normalized_text, now_ts),
        )

        blocks = _split_blocks(normalized_text)
        if not blocks:
            blocks = [
                _Block(start=0, end=len(normalized_text), text=normalized_text, heading_path=[])
            ]

        target_chars = int(req.chunk_target_tokens) * 4
        overlap_chars = int(req.chunk_overlap_tokens) * 4
        assembled = _assemble_chunks(blocks, target_chars=target_chars, overlap_chars=overlap_chars)

        for idx, (char_start, char_end, chunk_text, heading_path) in enumerate(assembled):
            text_hash = _sha256_text(chunk_text)
            chunk_id = _stable_id(
                "chunk",
                doc_id,
                idx,
                char_start,
                char_end,
                text_hash,
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO chunks
                    (chunk_id, namespace, doc_id, idx, text, heading_path_json, char_start, char_end, text_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk_id,
                    req.namespace,
                    doc_id,
                    idx,
                    chunk_text,
                    _json_dumps(heading_path) if heading_path else None,
                    char_start,
                    char_end,
                    text_hash,
                    now_ts,
                ),
            )
            chunk_ids.append(chunk_id)
            chunk_rows.append(
                IngestChunk(
                    chunk_id=chunk_id,
                    idx=idx,
                    char_start=char_start,
                    char_end=char_end,
                    text_hash=text_hash,
                )
            )

        extracted_artifact_id = _stable_id("art", source_id, "extracted_text", content_hash or "")
        conn.execute(
            """
            INSERT OR IGNORE INTO artifacts
                (artifact_id, namespace, source_id, artifact_type, content_text, content_json, created_at, generator)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                extracted_artifact_id,
                req.namespace,
                source_id,
                "extracted_text",
                normalized_text,
                _json_dumps({"content_hash": content_hash}),
                now_ts,
                "ingest_v1",
            ),
        )
        artifact_ids.append(extracted_artifact_id)
        artifact_types.append("extracted_text")

    for artifact_type in _pending_artifact_types(req, has_text):
        artifact_id = _stable_id("art", source_id, artifact_type, "pending")
        conn.execute(
            """
            INSERT OR IGNORE INTO artifacts
                (artifact_id, namespace, source_id, artifact_type, content_text, content_json, created_at, generator)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                artifact_id,
                req.namespace,
                source_id,
                artifact_type,
                None,
                _artifact_payload_for_pending(source_input),
                now_ts,
                "ingest_v1",
            ),
        )
        artifact_ids.append(artifact_id)
        artifact_types.append(artifact_type)

    conn.commit()

    source_row = db.fetch_one(
        conn,
        "SELECT * FROM sources WHERE namespace = ? AND source_id = ?",
        (req.namespace, source_id),
    )
    conn.close()
    if not source_row:  # pragma: no cover - defensive
        raise ValueError("ingest_source_missing")

    suggested_refs: list[dict[str, Any]] = [
        {"ref_type": "source", "ref_id": source_id, "role": "primary"}
    ]
    if doc_id:
        suggested_refs.append({"ref_type": "doc", "ref_id": doc_id, "role": "evidence"})
    for chunk_id in chunk_ids[:8]:
        suggested_refs.append({"ref_type": "chunk", "ref_id": chunk_id, "role": "evidence"})

    card_id: str | None = None
    proposal_id: str | None = None
    if req.card_mode != "none":
        stable_card_id = _stable_id("card", req.namespace, source_id, "ingest")
        card_type = _infer_card_type(req.source_type, tags, req.card_type)
        card_title = req.card_title or title
        card_summary = req.card_summary or _default_card_summary(title, normalized_text, req.source_type)
        details_json = {
            "source_id": source_id,
            "doc_id": doc_id,
            "content_hash": content_hash,
            "ingest_v": 1,
            "source_input": source_input,
        }

        if req.card_mode == "trusted":
            existing = store.get_card(req.namespace, stable_card_id)
            if existing is None:
                card = store.create_card(
                    namespace=req.namespace,
                    card_type=card_type,
                    title=card_title,
                    summary=card_summary,
                    details_json=details_json,
                    tags_json=tags,
                    salience=0.55,
                    confidence=0.8,
                    sensitivity_tier=req.sensitivity_tier,
                    status="active",
                    card_id=stable_card_id,
                )
            else:
                card = store.update_card(
                    namespace=req.namespace,
                    card_id=stable_card_id,
                    updates={
                        "title": card_title,
                        "summary": card_summary,
                        "details_json": details_json,
                        "tags_json": tags,
                        "sensitivity_tier": req.sensitivity_tier,
                        "status": "active",
                    },
                )
                if card is None:  # pragma: no cover - defensive
                    raise ValueError("card_update_failed")

            ref_models = [CardRefInput(**ref) for ref in suggested_refs]
            store.link_card_refs(req.namespace, card.card_id, ref_models)
            card_id = card.card_id
        else:
            proposal = proposals.create_proposal(
                ProposeRequest(
                    namespace=req.namespace,
                    proposal_type="create_card",
                    payload_json={
                        "card_id": stable_card_id,
                        "type": card_type,
                        "title": card_title,
                        "summary": card_summary,
                        "details_json": details_json,
                        "tags_json": tags,
                        "sensitivity_tier": req.sensitivity_tier,
                    },
                    requested_by=req.requested_by,
                    reason="ingest_v1_auto_card",
                )
            )
            card_id = stable_card_id
            proposal_id = proposal.proposal_id

    return IngestResponse(
        source=_source_row_to_record(source_row),
        content_hash=content_hash,
        tags=tags,
        doc_id=doc_id,
        chunk_ids=chunk_ids,
        chunks=chunk_rows,
        artifact_ids=artifact_ids,
        artifact_types=artifact_types,
        card_id=card_id,
        proposal_id=proposal_id,
        suggested_refs=suggested_refs,
        notes={
            "ingest_version": "v1",
            "deterministic_ids": True,
            "chunk_target_tokens": req.chunk_target_tokens,
            "chunk_overlap_tokens": req.chunk_overlap_tokens,
            "source_input": source_input,
        },
    )
