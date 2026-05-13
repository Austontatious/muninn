from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Callable, TypeVar

from ..core.models import (
    SCHEMA_VERSION,
    MemoryAssociation,
    MemoryCard,
    MemoryEntity,
    MemoryEvent,
    OntologyProfile,
    RecallEvent,
)
from .export_bundle import bundle_to_jsonl

T = TypeVar("T")


_SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS v2_schema_info (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS v2_events (
  id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL,
  actor TEXT NOT NULL,
  scope_key TEXT,
  created_at TEXT NOT NULL,
  record_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_v2_events_created ON v2_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_v2_events_scope ON v2_events(scope_key, created_at DESC);

CREATE TABLE IF NOT EXISTS v2_cards (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  status TEXT NOT NULL,
  scope_key TEXT,
  updated_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  record_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_v2_cards_scope_kind ON v2_cards(scope_key, kind, updated_at DESC);

CREATE TABLE IF NOT EXISTS v2_entities (
  id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL,
  name TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  record_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_v2_entities_type_name ON v2_entities(entity_type, name);

CREATE TABLE IF NOT EXISTS v2_associations (
  id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  target_id TEXT NOT NULL,
  association_type TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  record_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_v2_associations_source ON v2_associations(source_id, association_type);
CREATE INDEX IF NOT EXISTS idx_v2_associations_target ON v2_associations(target_id, association_type);

CREATE TABLE IF NOT EXISTS v2_recall_events (
  id TEXT PRIMARY KEY,
  query TEXT NOT NULL,
  actor TEXT NOT NULL,
  scope_key TEXT,
  created_at TEXT NOT NULL,
  record_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_v2_recall_scope_created ON v2_recall_events(scope_key, created_at DESC);

CREATE TABLE IF NOT EXISTS v2_ontology_profiles (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  version TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  record_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_v2_ontology_name_version ON v2_ontology_profiles(name, version);
"""


class SQLiteMemoryStore:
    """Minimal adjacent v2 SQLite store.

    The store only touches the path passed to it. It does not inspect v1
    environment variables, v1 schemas, or production DB locations.
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path).expanduser()

    def initialize(self) -> None:
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA_SQL)
            conn.execute(
                """
                INSERT INTO v2_schema_info (key, value)
                VALUES ('schema_version', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = datetime('now')
                """,
                (SCHEMA_VERSION,),
            )
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _ensure_initialized(self, conn: sqlite3.Connection) -> None:
        conn.executescript(_SCHEMA_SQL)
        conn.execute(
            "INSERT OR IGNORE INTO v2_schema_info (key, value) VALUES ('schema_version', ?)",
            (SCHEMA_VERSION,),
        )

    @staticmethod
    def _dump(record: dict[str, Any]) -> str:
        return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def create_event(self, event: MemoryEvent) -> MemoryEvent:
        payload = event.to_dict()
        with self._connect() as conn:
            self._ensure_initialized(conn)
            conn.execute(
                """
                INSERT OR REPLACE INTO v2_events
                    (id, event_type, actor, scope_key, created_at, record_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (event.id, event.event_type, event.actor, event.scope_key, event.created_at, self._dump(payload)),
            )
            conn.commit()
        return event

    def get_event(self, event_id: str) -> MemoryEvent | None:
        return self._get("v2_events", event_id, MemoryEvent.from_dict)

    def list_events(self, *, limit: int | None = None) -> list[MemoryEvent]:
        return self._list("v2_events", MemoryEvent.from_dict, order_by="created_at DESC", limit=limit)

    def create_card(self, card: MemoryCard) -> MemoryCard:
        payload = card.to_dict()
        with self._connect() as conn:
            self._ensure_initialized(conn)
            conn.execute(
                """
                INSERT OR REPLACE INTO v2_cards
                    (id, kind, status, scope_key, updated_at, created_at, record_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    card.id,
                    card.kind,
                    card.status,
                    card.scope_key,
                    card.updated_at,
                    card.created_at,
                    self._dump(payload),
                ),
            )
            conn.commit()
        return card

    def get_card(self, card_id: str) -> MemoryCard | None:
        return self._get("v2_cards", card_id, MemoryCard.from_dict)

    def list_cards(self, *, limit: int | None = None) -> list[MemoryCard]:
        return self._list("v2_cards", MemoryCard.from_dict, order_by="updated_at DESC", limit=limit)

    def create_entity(self, entity: MemoryEntity) -> MemoryEntity:
        payload = entity.to_dict()
        with self._connect() as conn:
            self._ensure_initialized(conn)
            conn.execute(
                """
                INSERT OR REPLACE INTO v2_entities
                    (id, entity_type, name, updated_at, created_at, record_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    entity.id,
                    entity.entity_type,
                    entity.name,
                    entity.updated_at,
                    entity.created_at,
                    self._dump(payload),
                ),
            )
            conn.commit()
        return entity

    def get_entity(self, entity_id: str) -> MemoryEntity | None:
        return self._get("v2_entities", entity_id, MemoryEntity.from_dict)

    def list_entities(
        self,
        *,
        entity_type: str | None = None,
        limit: int | None = None,
    ) -> list[MemoryEntity]:
        where = "entity_type = ?" if entity_type else None
        params = (entity_type,) if entity_type else ()
        return self._list(
            "v2_entities",
            MemoryEntity.from_dict,
            order_by="updated_at DESC",
            where=where,
            params=params,
            limit=limit,
        )

    def create_association(self, association: MemoryAssociation) -> MemoryAssociation:
        payload = association.to_dict()
        with self._connect() as conn:
            self._ensure_initialized(conn)
            conn.execute(
                """
                INSERT OR REPLACE INTO v2_associations
                    (id, source_id, target_id, association_type, updated_at, created_at, record_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    association.id,
                    association.source_id,
                    association.target_id,
                    association.association_type,
                    association.updated_at,
                    association.created_at,
                    self._dump(payload),
                ),
            )
            conn.commit()
        return association

    def get_association(self, association_id: str) -> MemoryAssociation | None:
        return self._get("v2_associations", association_id, MemoryAssociation.from_dict)

    def list_associations(
        self,
        *,
        source_id: str | None = None,
        target_id: str | None = None,
        limit: int | None = None,
    ) -> list[MemoryAssociation]:
        clauses: list[str] = []
        params: list[str] = []
        if source_id:
            clauses.append("source_id = ?")
            params.append(source_id)
        if target_id:
            clauses.append("target_id = ?")
            params.append(target_id)
        where = " AND ".join(clauses) if clauses else None
        return self._list(
            "v2_associations",
            MemoryAssociation.from_dict,
            order_by="updated_at DESC",
            where=where,
            params=tuple(params),
            limit=limit,
        )

    def log_recall(self, recall: RecallEvent) -> RecallEvent:
        payload = recall.to_dict()
        with self._connect() as conn:
            self._ensure_initialized(conn)
            conn.execute(
                """
                INSERT OR REPLACE INTO v2_recall_events
                    (id, query, actor, scope_key, created_at, record_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (recall.id, recall.query, recall.actor, recall.scope_key, recall.created_at, self._dump(payload)),
            )
            conn.commit()
        return recall

    def get_recall(self, recall_id: str) -> RecallEvent | None:
        return self._get("v2_recall_events", recall_id, RecallEvent.from_dict)

    def list_recalls(self, *, limit: int | None = None) -> list[RecallEvent]:
        return self._list("v2_recall_events", RecallEvent.from_dict, order_by="created_at DESC", limit=limit)

    def create_ontology_profile(self, profile: OntologyProfile) -> OntologyProfile:
        payload = profile.to_dict()
        with self._connect() as conn:
            self._ensure_initialized(conn)
            conn.execute(
                """
                INSERT OR REPLACE INTO v2_ontology_profiles
                    (id, name, version, updated_at, created_at, record_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    profile.id,
                    profile.name,
                    profile.version,
                    profile.updated_at,
                    profile.created_at,
                    self._dump(payload),
                ),
            )
            conn.commit()
        return profile

    def get_ontology_profile(self, profile_id: str) -> OntologyProfile | None:
        return self._get("v2_ontology_profiles", profile_id, OntologyProfile.from_dict)

    def list_ontology_profiles(self, *, limit: int | None = None) -> list[OntologyProfile]:
        return self._list(
            "v2_ontology_profiles",
            OntologyProfile.from_dict,
            order_by="updated_at DESC",
            limit=limit,
        )

    def export_bundle(self) -> dict[str, Any]:
        cards = [item.to_dict() for item in self.list_cards()]
        entities = [item.to_dict() for item in self.list_entities()]
        associations = [item.to_dict() for item in self.list_associations()]
        events = [item.to_dict() for item in self.list_events()]
        recall_events = [item.to_dict() for item in self.list_recalls()]
        ontology_profiles = [item.to_dict() for item in self.list_ontology_profiles()]
        return {
            "schema_version": SCHEMA_VERSION,
            "record_type": "muninn_v2_export_bundle",
            "counts": {
                "ontology_profiles": len(ontology_profiles),
                "entities": len(entities),
                "cards": len(cards),
                "associations": len(associations),
                "events": len(events),
                "recall_events": len(recall_events),
            },
            "ontology_profiles": ontology_profiles,
            "entities": entities,
            "cards": cards,
            "associations": associations,
            "events": events,
            "recall_events": recall_events,
        }

    def export_jsonl(self) -> str:
        return bundle_to_jsonl(self.export_bundle())

    def import_bundle(self, bundle: dict[str, Any]) -> dict[str, int]:
        counts = {
            "ontology_profiles": 0,
            "entities": 0,
            "cards": 0,
            "associations": 0,
            "events": 0,
            "recall_events": 0,
        }
        for payload in bundle.get("ontology_profiles", []) or []:
            self.create_ontology_profile(OntologyProfile.from_dict(payload))
            counts["ontology_profiles"] += 1
        for payload in bundle.get("entities", []) or []:
            self.create_entity(MemoryEntity.from_dict(payload))
            counts["entities"] += 1
        for payload in bundle.get("cards", []) or []:
            self.create_card(MemoryCard.from_dict(payload))
            counts["cards"] += 1
        for payload in bundle.get("associations", []) or []:
            self.create_association(MemoryAssociation.from_dict(payload))
            counts["associations"] += 1
        for payload in bundle.get("events", []) or []:
            self.create_event(MemoryEvent.from_dict(payload))
            counts["events"] += 1
        for payload in bundle.get("recall_events", []) or []:
            self.log_recall(RecallEvent.from_dict(payload))
            counts["recall_events"] += 1
        return counts

    def _get(self, table: str, record_id: str, factory: Callable[[dict[str, Any]], T]) -> T | None:
        with self._connect() as conn:
            self._ensure_initialized(conn)
            row = conn.execute(
                f"SELECT record_json FROM {table} WHERE id = ? LIMIT 1",
                (record_id,),
            ).fetchone()
        if row is None:
            return None
        return factory(json.loads(str(row["record_json"])))

    def _list(
        self,
        table: str,
        factory: Callable[[dict[str, Any]], T],
        *,
        order_by: str,
        where: str | None = None,
        params: tuple[Any, ...] = (),
        limit: int | None = None,
    ) -> list[T]:
        sql = f"SELECT record_json FROM {table}"
        if where:
            sql += f" WHERE {where}"
        sql += f" ORDER BY {order_by}"
        query_params: list[Any] = list(params)
        if limit is not None:
            sql += " LIMIT ?"
            query_params.append(max(1, int(limit)))
        with self._connect() as conn:
            self._ensure_initialized(conn)
            rows = conn.execute(sql, tuple(query_params)).fetchall()
        return [factory(json.loads(str(row["record_json"]))) for row in rows]
