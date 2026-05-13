from __future__ import annotations

from typing import Any, Protocol

from .models import (
    MemoryAssociation,
    MemoryCard,
    MemoryEntity,
    MemoryEvent,
    OntologyProfile,
    RecallEvent,
)


class EventLog(Protocol):
    def create_event(self, event: MemoryEvent) -> MemoryEvent: ...

    def get_event(self, event_id: str) -> MemoryEvent | None: ...

    def list_events(self, *, limit: int | None = None) -> list[MemoryEvent]: ...


class CardStore(Protocol):
    def create_card(self, card: MemoryCard) -> MemoryCard: ...

    def get_card(self, card_id: str) -> MemoryCard | None: ...

    def list_cards(self, *, limit: int | None = None) -> list[MemoryCard]: ...


class EntityResolver(Protocol):
    def create_entity(self, entity: MemoryEntity) -> MemoryEntity: ...

    def get_entity(self, entity_id: str) -> MemoryEntity | None: ...

    def list_entities(self, *, entity_type: str | None = None, limit: int | None = None) -> list[MemoryEntity]: ...


class AssociationStore(Protocol):
    def create_association(self, association: MemoryAssociation) -> MemoryAssociation: ...

    def get_association(self, association_id: str) -> MemoryAssociation | None: ...

    def list_associations(
        self,
        *,
        source_id: str | None = None,
        target_id: str | None = None,
        limit: int | None = None,
    ) -> list[MemoryAssociation]: ...


class RecallLog(Protocol):
    def log_recall(self, recall: RecallEvent) -> RecallEvent: ...

    def get_recall(self, recall_id: str) -> RecallEvent | None: ...

    def list_recalls(self, *, limit: int | None = None) -> list[RecallEvent]: ...


class ExportProvider(Protocol):
    def export_bundle(self) -> dict[str, Any]: ...

    def export_jsonl(self) -> str: ...


class ImportProvider(Protocol):
    def import_bundle(self, bundle: dict[str, Any]) -> dict[str, int]: ...


class MemoryStore(
    EventLog,
    CardStore,
    EntityResolver,
    AssociationStore,
    RecallLog,
    ExportProvider,
    ImportProvider,
    Protocol,
):
    def initialize(self) -> None: ...

    def create_ontology_profile(self, profile: OntologyProfile) -> OntologyProfile: ...

    def get_ontology_profile(self, profile_id: str) -> OntologyProfile | None: ...

    def list_ontology_profiles(self, *, limit: int | None = None) -> list[OntologyProfile]: ...
