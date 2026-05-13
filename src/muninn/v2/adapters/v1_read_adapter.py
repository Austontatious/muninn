from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from ..core.models import EvidenceRef, MemoryAssociation, MemoryCard, OntologyProfile


class V1ReadAdapter:
    """Read-only adapter for Muninn v1 human-memory databases."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path).expanduser()

    def _connect(self) -> sqlite3.Connection:
        uri = f"{self.db_path.resolve().as_uri()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON;")
        return conn

    @staticmethod
    def _json_dict(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return dict(value)
        text = str(value or "").strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {"raw": text, "parse_error": "invalid_json"}
        return parsed if isinstance(parsed, dict) else {"value": parsed}

    def list_cards(self, *, space_key: str | None = None, limit: int | None = None) -> list[MemoryCard]:
        params: list[Any] = []
        where = ""
        if space_key:
            where = "WHERE s.key = ?"
            params.append(space_key)
        sql = f"""
            SELECT c.id, s.key AS space_key, c.kind, c.status, c.salience, c.title, c.summary,
                   c.body, c.source_confidence, c.context_json, c.created_at, c.updated_at
            FROM cards c
            JOIN spaces s ON s.id = c.space_id
            {where}
            ORDER BY c.updated_at DESC, c.id ASC
        """
        if limit is not None:
            sql += " LIMIT ?"
            params.append(max(1, int(limit)))
        with self._connect() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
            evidence_by_card = self._load_evidence_for_cards(conn, [str(row["id"]) for row in rows])
            tags_by_card = self._load_tags_for_cards(conn, [str(row["id"]) for row in rows])
        return [self._map_card(row, evidence_by_card.get(str(row["id"]), []), tags_by_card.get(str(row["id"]), [])) for row in rows]

    def list_associations(
        self,
        *,
        space_key: str | None = None,
        limit: int | None = None,
    ) -> list[MemoryAssociation]:
        params: list[Any] = []
        if space_key:
            sql = """
                SELECT cr.from_card_id, cr.to_card_id, cr.relation_type, cr.created_at
                FROM card_relations cr
                JOIN cards from_card ON from_card.id = cr.from_card_id
                JOIN cards to_card ON to_card.id = cr.to_card_id
                JOIN spaces s ON s.id = from_card.space_id AND s.id = to_card.space_id
                WHERE s.key = ?
                ORDER BY cr.created_at DESC, cr.from_card_id ASC, cr.to_card_id ASC
            """
            params.append(space_key)
        else:
            sql = """
                SELECT from_card_id, to_card_id, relation_type, created_at
                FROM card_relations
                ORDER BY created_at DESC, from_card_id ASC, to_card_id ASC
            """
        if limit is not None:
            sql += " LIMIT ?"
            params.append(max(1, int(limit)))
        with self._connect() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
        return [self._map_association(row) for row in rows]

    def list_ontology_profiles(
        self,
        *,
        space_key: str | None = None,
        limit: int | None = None,
    ) -> list[OntologyProfile]:
        params: list[Any] = []
        where = ""
        if space_key:
            where = "WHERE s.key = ?"
            params.append(space_key)
        sql = """
            SELECT s.key, s.label, s.meta_json,
                   GROUP_CONCAT(DISTINCT c.kind) AS card_kinds
            FROM spaces s
            LEFT JOIN cards c ON c.space_id = s.id
            {where}
            GROUP BY s.id
            ORDER BY s.updated_at DESC, s.key ASC
        """.format(where=where)
        if limit is not None:
            sql += " LIMIT ?"
            params.append(max(1, int(limit)))
        with self._connect() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
        return [self._map_profile(row) for row in rows]

    def _load_evidence_for_cards(
        self,
        conn: sqlite3.Connection,
        card_ids: list[str],
    ) -> dict[str, list[EvidenceRef]]:
        if not card_ids:
            return {}
        placeholders = ", ".join(["?"] * len(card_ids))
        rows = conn.execute(
            f"""
            SELECT ce.card_id, e.id, e.type, e.ref, e.excerpt, e.blob_path, e.meta_json, e.created_at
            FROM card_evidence ce
            JOIN evidence e ON e.id = ce.evidence_id
            WHERE ce.card_id IN ({placeholders})
            ORDER BY e.created_at ASC, e.id ASC
            """,
            tuple(card_ids),
        ).fetchall()
        out: dict[str, list[EvidenceRef]] = {card_id: [] for card_id in card_ids}
        for row in rows:
            metadata = self._json_dict(row["meta_json"])
            if row["blob_path"]:
                metadata.setdefault("blob_path", str(row["blob_path"]))
            metadata["source_system"] = "muninn_v1"
            out.setdefault(str(row["card_id"]), []).append(
                EvidenceRef(
                    id=str(row["id"]),
                    evidence_type=str(row["type"]),
                    ref=(None if row["ref"] is None else str(row["ref"])),
                    excerpt=(None if row["excerpt"] is None else str(row["excerpt"])),
                    metadata=metadata,
                    created_at=str(row["created_at"]),
                )
            )
        return out

    def _load_tags_for_cards(
        self,
        conn: sqlite3.Connection,
        card_ids: list[str],
    ) -> dict[str, list[str]]:
        if not card_ids:
            return {}
        placeholders = ", ".join(["?"] * len(card_ids))
        rows = conn.execute(
            f"""
            SELECT ct.card_id, t.name
            FROM card_tags ct
            JOIN tags t ON t.id = ct.tag_id
            WHERE ct.card_id IN ({placeholders})
            ORDER BY t.name ASC
            """,
            tuple(card_ids),
        ).fetchall()
        out: dict[str, list[str]] = {card_id: [] for card_id in card_ids}
        for row in rows:
            out.setdefault(str(row["card_id"]), []).append(str(row["name"]))
        return out

    def _map_card(
        self,
        row: sqlite3.Row,
        evidence: list[EvidenceRef],
        tags: list[str],
    ) -> MemoryCard:
        metadata = self._json_dict(row["context_json"])
        metadata.setdefault("source_system", "muninn_v1")
        metadata.setdefault("source_table", "cards")
        metadata.setdefault("v1_salience", float(row["salience"] or 0.0))
        return MemoryCard(
            id=str(row["id"]),
            kind=str(row["kind"]),
            title=str(row["title"]),
            summary=str(row["summary"]),
            body=str(row["body"] or ""),
            status=str(row["status"]),
            confidence=float(row["source_confidence"] or 0.5),
            scope_key=str(row["space_key"]),
            tags=tags,
            evidence=evidence,
            provenance={"source_system": "muninn_v1", "source_table": "cards"},
            metadata=metadata,
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    @staticmethod
    def _map_association(row: sqlite3.Row) -> MemoryAssociation:
        relation_type = str(row["relation_type"])
        from_id = str(row["from_card_id"])
        to_id = str(row["to_card_id"])
        return MemoryAssociation(
            id=f"v1-relation:{from_id}:{relation_type}:{to_id}",
            source_id=from_id,
            source_type="memory_card",
            target_id=to_id,
            target_type="memory_card",
            association_type=relation_type,
            metadata={"source_system": "muninn_v1", "source_table": "card_relations"},
            created_at=str(row["created_at"]),
            updated_at=str(row["created_at"]),
        )

    def _map_profile(self, row: sqlite3.Row) -> OntologyProfile:
        space_key = str(row["key"])
        raw_kinds = str(row["card_kinds"] or "")
        card_kinds = sorted({kind for kind in raw_kinds.split(",") if kind})
        return OntologyProfile(
            id=f"v1-space:{space_key}",
            name=f"muninn-v1-space:{space_key}",
            version="v1",
            description="Read-only v1 space profile projected for Muninn v2 pilot imports.",
            entity_types=["space", "card", "evidence"],
            card_kinds=card_kinds,
            association_types=["supersedes", "duplicates", "contradicts", "refines"],
            metadata={
                "source_system": "muninn_v1",
                "space_key": space_key,
                "space_label": row["label"],
                "space_meta": self._json_dict(row["meta_json"]),
            },
            created_at="1970-01-01T00:00:00Z",
            updated_at="1970-01-01T00:00:00Z",
        )
