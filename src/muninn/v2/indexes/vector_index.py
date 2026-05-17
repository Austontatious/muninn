from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, Sequence

from ..core.models import MemoryCard, utc_now

DEFAULT_VECTOR_MODEL_ID = "muninn-v2-hash-v1"
DEFAULT_VECTOR_DIMENSION = 96
INDEX_SCHEMA_VERSION = "muninn.v2.derived_indexes.v1"


@dataclass(frozen=True)
class VectorIndexStatus:
    backend: str
    backend_available: bool
    eligible_records: int
    indexed_records: int
    missing_records: int
    stale_records: int
    degraded: bool
    reason: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "backend_available": bool(self.backend_available),
            "eligible_records": int(self.eligible_records),
            "indexed_records": int(self.indexed_records),
            "missing_records": int(self.missing_records),
            "stale_records": int(self.stale_records),
            "degraded": bool(self.degraded),
            "reason": list(self.reason),
        }


class DerivedIndexProvider(Protocol):
    def status(self) -> VectorIndexStatus:
        ...

    def rebuild(self, records: Sequence[MemoryCard], dry_run: bool = True) -> dict[str, Any]:
        ...

    def query(self, text: str, limit: int = 10) -> list[dict[str, Any]]:
        ...

    def explain(self, record_id: str) -> dict[str, Any]:
        ...


class HashEmbeddingProvider:
    def __init__(
        self,
        *,
        model_id: str = DEFAULT_VECTOR_MODEL_ID,
        dimension: int = DEFAULT_VECTOR_DIMENSION,
    ) -> None:
        self.model_id = model_id
        self.dimension = int(dimension)

    def embed_text(self, text: str) -> list[float]:
        values = [0.0] * self.dimension
        for token in _tokens(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            weight = 1.0 + (digest[5] / 255.0)
            values[bucket] += sign * weight
        return _l2_normalize(values)


class SQLiteDerivedIndexProvider:
    """Optional v2 derived vector index backed by the explicit v2 SQLite DB.

    This provider never opens v1 DBs and never initializes during import. The
    derived index tables are created only by explicit rebuild writes.
    """

    def __init__(
        self,
        db_path: str | Path,
        *,
        records: Sequence[MemoryCard] | None = None,
        embedding_provider: HashEmbeddingProvider | None = None,
        read_only: bool = False,
    ) -> None:
        self.db_path = Path(db_path).expanduser()
        self.records = list(records or [])
        self.embedding_provider = embedding_provider or HashEmbeddingProvider()
        self.read_only = bool(read_only)

    def status(self) -> VectorIndexStatus:
        backend = self._backend_name()
        reasons = self._backend_reasons()
        eligible = _eligible_records(self.records)
        if not self.db_path.exists() or not self._table_exists("v2_vector_indexes"):
            return VectorIndexStatus(
                backend=backend,
                backend_available=True,
                eligible_records=len(eligible),
                indexed_records=0,
                missing_records=len(eligible),
                stale_records=0,
                degraded=True,
                reason=[*reasons, "index_table_missing", "rebuild_required"],
            )

        rows = self._load_index_rows()
        healthy, missing, stale = self._classify_rows(eligible, rows)
        out_reasons = list(reasons)
        if missing:
            out_reasons.append(f"missing_records:{len(missing)}")
        if stale:
            out_reasons.append(f"stale_records:{len(stale)}")
        if not eligible:
            out_reasons.append("no_eligible_records")
        return VectorIndexStatus(
            backend=backend,
            backend_available=True,
            eligible_records=len(eligible),
            indexed_records=len(healthy),
            missing_records=len(missing),
            stale_records=len(stale),
            degraded=bool(out_reasons),
            reason=out_reasons,
        )

    def rebuild(self, records: Sequence[MemoryCard], dry_run: bool = True) -> dict[str, Any]:
        self.records = list(records)
        before = self.status()
        eligible = _eligible_records(self.records)
        rows = self._load_index_rows() if self.db_path.exists() and self._table_exists("v2_vector_indexes") else {}
        healthy, missing, stale = self._classify_rows(eligible, rows)
        eligible_by_id = {card.id: card for card in eligible}
        planned_upserts = [eligible_by_id[card_id] for card_id in [*missing, *stale] if card_id in eligible_by_id]
        orphaned = sorted(set(rows) - set(eligible_by_id))
        written_upserts = 0
        deleted_records = 0
        if not dry_run:
            if self.read_only:
                raise RuntimeError("derived_index_provider_read_only")
            self._ensure_schema()
            with self._connect() as conn:
                for card in planned_upserts:
                    payload = _index_payload(card, self.embedding_provider)
                    conn.execute(
                        """
                        INSERT INTO v2_vector_indexes(
                          record_id, record_type, scope_key, source_updated_at,
                          content_hash, embedding_model, embedding_dim, vector_json, indexed_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(record_id) DO UPDATE SET
                          record_type = excluded.record_type,
                          scope_key = excluded.scope_key,
                          source_updated_at = excluded.source_updated_at,
                          content_hash = excluded.content_hash,
                          embedding_model = excluded.embedding_model,
                          embedding_dim = excluded.embedding_dim,
                          vector_json = excluded.vector_json,
                          indexed_at = excluded.indexed_at
                        """,
                        (
                            payload["record_id"],
                            payload["record_type"],
                            payload["scope_key"],
                            payload["source_updated_at"],
                            payload["content_hash"],
                            payload["embedding_model"],
                            payload["embedding_dim"],
                            payload["vector_json"],
                            payload["indexed_at"],
                        ),
                    )
                    written_upserts += 1
                for record_id in orphaned:
                    conn.execute("DELETE FROM v2_vector_indexes WHERE record_id = ?", (record_id,))
                    deleted_records += 1
                _upsert_state(conn, "schema_version", INDEX_SCHEMA_VERSION)
                _upsert_state(conn, "last_rebuild_at", utc_now())
                _upsert_state(conn, "last_rebuild_model", self.embedding_provider.model_id)
                conn.commit()
        after = self.status()
        return {
            "record_type": "muninn_v2_index_rebuild_report",
            "dry_run": bool(dry_run),
            "write_index": not bool(dry_run),
            "backend": self._backend_name(),
            "before": before.to_dict(),
            "after": after.to_dict(),
            "planned_upserts": len(planned_upserts),
            "planned_deletes": len(orphaned),
            "written_upserts": written_upserts,
            "deleted_records": deleted_records,
            "planned_record_ids": [card.id for card in planned_upserts],
            "deleted_record_ids": orphaned,
        }

    def query(self, text: str, limit: int = 10) -> list[dict[str, Any]]:
        if not self.db_path.exists() or not self._table_exists("v2_vector_indexes"):
            return []
        rows = self._load_index_rows()
        cards_by_id = {card.id: card for card in _eligible_records(self.records)}
        query_vector = self.embedding_provider.embed_text(text)
        scored: list[dict[str, Any]] = []
        for record_id, row in rows.items():
            card = cards_by_id.get(record_id)
            if card is None:
                continue
            if row.get("content_hash") != _content_hash(card):
                continue
            try:
                vector = [float(item) for item in json.loads(str(row.get("vector_json") or "[]"))]
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            score = _dot(query_vector, vector)
            if score <= 0:
                continue
            scored.append(
                {
                    "record_id": record_id,
                    "score": round(float(score), 6),
                    "backend": self._backend_name(),
                    "scope_key": card.scope_key,
                    "record": card.to_dict(),
                    "explanation": {
                        "retrieval_path": "v2_derived_vector_index",
                        "derived": True,
                        "score_semantics": "higher cosine-like dot score is better",
                    },
                }
            )
        scored.sort(key=lambda item: (-float(item["score"]), str(item["record_id"])))
        return scored[: max(1, int(limit))]

    def explain(self, record_id: str) -> dict[str, Any]:
        rows = self._load_index_rows() if self.db_path.exists() and self._table_exists("v2_vector_indexes") else {}
        row = rows.get(str(record_id))
        card = {card.id: card for card in self.records}.get(str(record_id))
        return {
            "record_id": str(record_id),
            "indexed": row is not None,
            "eligible": card is not None and _is_eligible(card),
            "stale": bool(row and card and row.get("content_hash") != _content_hash(card)),
            "row": row,
            "record": card.to_dict() if card else None,
        }

    def _backend_name(self) -> str:
        return "json_vector_fallback" if not _sqlite_vec_available() else "json_vector"

    def _backend_reasons(self) -> list[str]:
        if _sqlite_vec_available():
            return []
        return ["sqlite_vec_unavailable_using_json_vector_fallback"]

    def _connect(self) -> sqlite3.Connection:
        if self.read_only:
            if not self.db_path.exists():
                raise FileNotFoundError(f"v2_db_not_found:{self.db_path}")
            uri = f"{self.db_path.resolve().as_uri()}?mode=ro&immutable=1"
            conn = sqlite3.connect(uri, uri=True)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA query_only=ON;")
            conn.execute("PRAGMA foreign_keys=ON;")
            return conn
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _ensure_schema(self) -> None:
        if self.read_only:
            raise RuntimeError("derived_index_provider_read_only")
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS v2_vector_indexes (
                  record_id TEXT PRIMARY KEY,
                  record_type TEXT NOT NULL,
                  scope_key TEXT,
                  source_updated_at TEXT NOT NULL,
                  content_hash TEXT NOT NULL,
                  embedding_model TEXT NOT NULL,
                  embedding_dim INTEGER NOT NULL,
                  vector_json TEXT NOT NULL,
                  indexed_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_v2_vector_indexes_scope
                ON v2_vector_indexes(scope_key, embedding_model, indexed_at DESC);

                CREATE TABLE IF NOT EXISTS v2_index_state (
                  key TEXT PRIMARY KEY,
                  value TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );
                """
            )
            _upsert_state(conn, "schema_version", INDEX_SCHEMA_VERSION)
            conn.commit()

    def _table_exists(self, table_name: str) -> bool:
        if not self.db_path.exists():
            return False
        if self.read_only:
            uri = f"{self.db_path.resolve().as_uri()}?mode=ro&immutable=1"
            conn = sqlite3.connect(uri, uri=True)
            conn.execute("PRAGMA query_only=ON;")
        else:
            conn = sqlite3.connect(str(self.db_path))
        with conn:
            row = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
                (table_name,),
            ).fetchone()
        return row is not None

    def _load_index_rows(self) -> dict[str, dict[str, Any]]:
        if not self.db_path.exists() or not self._table_exists("v2_vector_indexes"):
            return {}
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT record_id, record_type, scope_key, source_updated_at, content_hash,
                       embedding_model, embedding_dim, vector_json, indexed_at
                FROM v2_vector_indexes
                ORDER BY record_id ASC
                """
            ).fetchall()
        return {str(row["record_id"]): dict(row) for row in rows}

    def _classify_rows(
        self,
        eligible: Sequence[MemoryCard],
        rows: dict[str, dict[str, Any]],
    ) -> tuple[list[str], list[str], list[str]]:
        healthy: list[str] = []
        missing: list[str] = []
        stale: list[str] = []
        for card in eligible:
            row = rows.get(card.id)
            if row is None:
                missing.append(card.id)
                continue
            row_stale = (
                str(row.get("source_updated_at") or "") != str(card.updated_at)
                or str(row.get("content_hash") or "") != _content_hash(card)
                or str(row.get("embedding_model") or "") != self.embedding_provider.model_id
                or int(row.get("embedding_dim") or 0) != self.embedding_provider.dimension
            )
            if row_stale:
                stale.append(card.id)
            else:
                healthy.append(card.id)
        return healthy, missing, stale


def load_v2_cards(db_path: str | Path, *, immutable: bool = False) -> list[MemoryCard]:
    path = Path(db_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"v2_db_not_found:{path}")
    immutable_flag = "&immutable=1" if immutable else ""
    uri = f"{path.resolve().as_uri()}?mode=ro{immutable_flag}"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON;")
    try:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='v2_cards' LIMIT 1"
        ).fetchone()
        if row is None:
            return []
        rows = conn.execute(
            "SELECT record_json FROM v2_cards ORDER BY updated_at DESC, id ASC"
        ).fetchall()
    finally:
        conn.close()
    return [MemoryCard.from_dict(json.loads(str(row["record_json"]))) for row in rows]


def _index_payload(card: MemoryCard, provider: HashEmbeddingProvider) -> dict[str, Any]:
    vector = provider.embed_text(_card_text(card))
    return {
        "record_id": card.id,
        "record_type": card.record_type,
        "scope_key": card.scope_key,
        "source_updated_at": card.updated_at,
        "content_hash": _content_hash(card),
        "embedding_model": provider.model_id,
        "embedding_dim": provider.dimension,
        "vector_json": json.dumps(vector, separators=(",", ":"), ensure_ascii=True),
        "indexed_at": utc_now(),
    }


def _eligible_records(records: Sequence[MemoryCard]) -> list[MemoryCard]:
    return [card for card in records if _is_eligible(card)]


def _is_eligible(card: MemoryCard) -> bool:
    return str(card.status or "active") == "active"


def _card_text(card: MemoryCard) -> str:
    evidence_text = "\n".join(
        " ".join(str(part or "") for part in (evidence.ref, evidence.excerpt))
        for evidence in card.evidence
    )
    return "\n".join(
        [
            f"kind: {card.kind}",
            f"title: {card.title}",
            f"summary: {card.summary}",
            f"body: {card.body}",
            f"tags: {', '.join(sorted(card.tags))}",
            f"evidence: {evidence_text}",
        ]
    )


def _content_hash(card: MemoryCard) -> str:
    payload = {
        "kind": card.kind,
        "title": card.title,
        "summary": card.summary,
        "body": card.body,
        "tags": sorted(card.tags),
        "evidence": [
            {
                "id": evidence.id,
                "type": evidence.evidence_type,
                "ref": evidence.ref,
                "excerpt": evidence.excerpt,
            }
            for evidence in card.evidence
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _tokens(text: str) -> list[str]:
    out: list[str] = []
    token = []
    for ch in str(text or "").lower():
        if ch.isalnum() or ch == "_":
            token.append(ch)
        elif token:
            out.append("".join(token))
            token = []
    if token:
        out.append("".join(token))
    return out


def _l2_normalize(values: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(float(value) * float(value) for value in values))
    if norm <= 0:
        return [0.0 for _ in values]
    return [float(value) / norm for value in values]


def _dot(left: Sequence[float], right: Sequence[float]) -> float:
    return sum(float(a) * float(b) for a, b in zip(left, right))


def _sqlite_vec_available() -> bool:
    try:
        __import__("sqlite_vec")
    except Exception:
        return False
    return True


def _upsert_state(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        """
        INSERT INTO v2_index_state(key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
          value = excluded.value,
          updated_at = excluded.updated_at
        """,
        (key, value, utc_now()),
    )
