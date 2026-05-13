from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, ClassVar
import uuid


SCHEMA_VERSION = "muninn.v2.foundation.v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def new_memory_id(prefix: str) -> str:
    safe_prefix = "".join(ch for ch in str(prefix or "item").lower() if ch.isalnum() or ch == "_")
    return f"{safe_prefix or 'item'}_{uuid.uuid4().hex}"


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _str_list(value: Any) -> list[str]:
    return [str(item) for item in _list(value) if str(item).strip()]


def _evidence_list(value: Any) -> list["EvidenceRef"]:
    out: list[EvidenceRef] = []
    for item in _list(value):
        if isinstance(item, EvidenceRef):
            out.append(item)
        elif isinstance(item, dict):
            out.append(EvidenceRef.from_dict(item))
    return out


@dataclass(slots=True)
class EvidenceRef:
    evidence_type: str
    id: str = field(default_factory=lambda: new_memory_id("evidence"))
    ref: str | None = None
    excerpt: str | None = None
    source_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)

    record_type: ClassVar[str] = "evidence"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "record_type": self.record_type,
            "id": self.id,
            "evidence_type": self.evidence_type,
            "ref": self.ref,
            "excerpt": self.excerpt,
            "source_id": self.source_id,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EvidenceRef":
        evidence_type = payload.get("evidence_type", payload.get("type", "unknown"))
        return cls(
            id=str(payload.get("id") or new_memory_id("evidence")),
            evidence_type=str(evidence_type or "unknown"),
            ref=(None if payload.get("ref") is None else str(payload.get("ref"))),
            excerpt=(None if payload.get("excerpt") is None else str(payload.get("excerpt"))),
            source_id=(None if payload.get("source_id") is None else str(payload.get("source_id"))),
            metadata=_dict(payload.get("metadata") or payload.get("meta")),
            created_at=str(payload.get("created_at") or utc_now()),
        )


@dataclass(slots=True)
class MemoryEvent:
    event_type: str
    actor: str
    summary: str
    id: str = field(default_factory=lambda: new_memory_id("event"))
    scope_key: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    evidence: list[EvidenceRef] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)

    record_type: ClassVar[str] = "memory_event"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "record_type": self.record_type,
            "id": self.id,
            "event_type": self.event_type,
            "actor": self.actor,
            "summary": self.summary,
            "scope_key": self.scope_key,
            "payload": dict(self.payload),
            "evidence": [item.to_dict() for item in self.evidence],
            "provenance": dict(self.provenance),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MemoryEvent":
        return cls(
            id=str(payload.get("id") or new_memory_id("event")),
            event_type=str(payload.get("event_type") or "unknown"),
            actor=str(payload.get("actor") or "unknown"),
            summary=str(payload.get("summary") or ""),
            scope_key=(None if payload.get("scope_key") is None else str(payload.get("scope_key"))),
            payload=_dict(payload.get("payload")),
            evidence=_evidence_list(payload.get("evidence")),
            provenance=_dict(payload.get("provenance")),
            created_at=str(payload.get("created_at") or utc_now()),
        )


@dataclass(slots=True)
class MemoryCard:
    kind: str
    title: str
    summary: str
    id: str = field(default_factory=lambda: new_memory_id("card"))
    body: str = ""
    status: str = "active"
    confidence: float = 0.5
    scope_key: str | None = None
    entity_ids: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    evidence: list[EvidenceRef] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    record_type: ClassVar[str] = "memory_card"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "record_type": self.record_type,
            "id": self.id,
            "kind": self.kind,
            "title": self.title,
            "summary": self.summary,
            "body": self.body,
            "status": self.status,
            "confidence": float(self.confidence),
            "scope_key": self.scope_key,
            "entity_ids": list(self.entity_ids),
            "tags": list(self.tags),
            "evidence": [item.to_dict() for item in self.evidence],
            "provenance": dict(self.provenance),
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MemoryCard":
        return cls(
            id=str(payload.get("id") or new_memory_id("card")),
            kind=str(payload.get("kind") or "custom"),
            title=str(payload.get("title") or ""),
            summary=str(payload.get("summary") or ""),
            body=str(payload.get("body") or ""),
            status=str(payload.get("status") or "active"),
            confidence=float(payload.get("confidence", 0.5) or 0.0),
            scope_key=(None if payload.get("scope_key") is None else str(payload.get("scope_key"))),
            entity_ids=_str_list(payload.get("entity_ids")),
            tags=_str_list(payload.get("tags")),
            evidence=_evidence_list(payload.get("evidence")),
            provenance=_dict(payload.get("provenance")),
            metadata=_dict(payload.get("metadata")),
            created_at=str(payload.get("created_at") or utc_now()),
            updated_at=str(payload.get("updated_at") or payload.get("created_at") or utc_now()),
        )


@dataclass(slots=True)
class MemoryEntity:
    entity_type: str
    name: str
    id: str = field(default_factory=lambda: new_memory_id("entity"))
    aliases: list[str] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)
    evidence: list[EvidenceRef] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    record_type: ClassVar[str] = "memory_entity"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "record_type": self.record_type,
            "id": self.id,
            "entity_type": self.entity_type,
            "name": self.name,
            "aliases": list(self.aliases),
            "properties": dict(self.properties),
            "evidence": [item.to_dict() for item in self.evidence],
            "provenance": dict(self.provenance),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MemoryEntity":
        return cls(
            id=str(payload.get("id") or new_memory_id("entity")),
            entity_type=str(payload.get("entity_type") or "custom"),
            name=str(payload.get("name") or ""),
            aliases=_str_list(payload.get("aliases")),
            properties=_dict(payload.get("properties")),
            evidence=_evidence_list(payload.get("evidence")),
            provenance=_dict(payload.get("provenance")),
            created_at=str(payload.get("created_at") or utc_now()),
            updated_at=str(payload.get("updated_at") or payload.get("created_at") or utc_now()),
        )


@dataclass(slots=True)
class MemoryAssociation:
    source_id: str
    target_id: str
    association_type: str
    id: str = field(default_factory=lambda: new_memory_id("association"))
    source_type: str = "memory"
    target_type: str = "memory"
    weight: float = 1.0
    evidence: list[EvidenceRef] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    record_type: ClassVar[str] = "memory_association"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "record_type": self.record_type,
            "id": self.id,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "target_id": self.target_id,
            "target_type": self.target_type,
            "association_type": self.association_type,
            "weight": float(self.weight),
            "evidence": [item.to_dict() for item in self.evidence],
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MemoryAssociation":
        return cls(
            id=str(payload.get("id") or new_memory_id("association")),
            source_id=str(payload.get("source_id") or ""),
            source_type=str(payload.get("source_type") or "memory"),
            target_id=str(payload.get("target_id") or ""),
            target_type=str(payload.get("target_type") or "memory"),
            association_type=str(payload.get("association_type") or "related"),
            weight=float(payload.get("weight", 1.0) or 0.0),
            evidence=_evidence_list(payload.get("evidence")),
            metadata=_dict(payload.get("metadata")),
            created_at=str(payload.get("created_at") or utc_now()),
            updated_at=str(payload.get("updated_at") or payload.get("created_at") or utc_now()),
        )


@dataclass(slots=True)
class RecallEvent:
    query: str
    recalled_ids: list[str]
    id: str = field(default_factory=lambda: new_memory_id("recall"))
    actor: str = "unknown"
    scope_key: str | None = None
    accepted_ids: list[str] = field(default_factory=list)
    suppressed_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)

    record_type: ClassVar[str] = "recall_event"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "record_type": self.record_type,
            "id": self.id,
            "query": self.query,
            "actor": self.actor,
            "scope_key": self.scope_key,
            "recalled_ids": list(self.recalled_ids),
            "accepted_ids": list(self.accepted_ids),
            "suppressed_ids": list(self.suppressed_ids),
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RecallEvent":
        return cls(
            id=str(payload.get("id") or new_memory_id("recall")),
            query=str(payload.get("query") or ""),
            actor=str(payload.get("actor") or "unknown"),
            scope_key=(None if payload.get("scope_key") is None else str(payload.get("scope_key"))),
            recalled_ids=_str_list(payload.get("recalled_ids")),
            accepted_ids=_str_list(payload.get("accepted_ids")),
            suppressed_ids=_str_list(payload.get("suppressed_ids")),
            metadata=_dict(payload.get("metadata")),
            created_at=str(payload.get("created_at") or utc_now()),
        )


@dataclass(slots=True)
class OntologyProfile:
    name: str
    version: str
    id: str = field(default_factory=lambda: new_memory_id("ontology"))
    description: str = ""
    entity_types: list[str] = field(default_factory=list)
    card_kinds: list[str] = field(default_factory=list)
    association_types: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    record_type: ClassVar[str] = "ontology_profile"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "record_type": self.record_type,
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "entity_types": list(self.entity_types),
            "card_kinds": list(self.card_kinds),
            "association_types": list(self.association_types),
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "OntologyProfile":
        return cls(
            id=str(payload.get("id") or new_memory_id("ontology")),
            name=str(payload.get("name") or "default"),
            version=str(payload.get("version") or "v1"),
            description=str(payload.get("description") or ""),
            entity_types=_str_list(payload.get("entity_types")),
            card_kinds=_str_list(payload.get("card_kinds")),
            association_types=_str_list(payload.get("association_types")),
            metadata=_dict(payload.get("metadata")),
            created_at=str(payload.get("created_at") or utc_now()),
            updated_at=str(payload.get("updated_at") or payload.get("created_at") or utc_now()),
        )
