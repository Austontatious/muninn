from __future__ import annotations

from ..core.contracts import MemoryStore
from .v1_read_adapter import V1ReadAdapter


class V1ImportAdapter:
    """Partial non-destructive importer from v1 human-memory into v2 stores."""

    def __init__(self, reader: V1ReadAdapter, target: MemoryStore) -> None:
        self.reader = reader
        self.target = target

    def import_cards(self, *, space_key: str | None = None, limit: int | None = None) -> int:
        count = 0
        for card in self.reader.list_cards(space_key=space_key, limit=limit):
            self.target.create_card(card)
            count += 1
        return count

    def import_associations(self, *, space_key: str | None = None, limit: int | None = None) -> int:
        count = 0
        for association in self.reader.list_associations(space_key=space_key, limit=limit):
            self.target.create_association(association)
            count += 1
        return count

    def import_ontology_profiles(self, *, space_key: str | None = None, limit: int | None = None) -> int:
        count = 0
        for profile in self.reader.list_ontology_profiles(space_key=space_key, limit=limit):
            self.target.create_ontology_profile(profile)
            count += 1
        return count

    def import_all(self, *, space_key: str | None = None, limit: int | None = None) -> dict[str, int]:
        return {
            "ontology_profiles": self.import_ontology_profiles(space_key=space_key, limit=limit),
            "cards": self.import_cards(space_key=space_key, limit=limit),
            "associations": self.import_associations(space_key=space_key, limit=limit),
        }
