"""Adjacent Muninn v2 foundation.

This package is intentionally independent from the live v1 runtime. Importing
it does not initialize v1 storage, register MCP tools, or run migrations.
"""

from .core.contracts import (
    AssociationStore,
    CardStore,
    EntityResolver,
    EventLog,
    ExportProvider,
    ImportProvider,
    MemoryStore,
    RecallLog,
)
from .core.models import (
    EvidenceRef,
    MemoryAssociation,
    MemoryCard,
    MemoryEntity,
    MemoryEvent,
    OntologyProfile,
    RecallEvent,
)
from .storage.sqlite_store import SQLiteMemoryStore

__all__ = [
    "AssociationStore",
    "CardStore",
    "EntityResolver",
    "EventLog",
    "EvidenceRef",
    "ExportProvider",
    "ImportProvider",
    "MemoryAssociation",
    "MemoryCard",
    "MemoryEntity",
    "MemoryEvent",
    "MemoryStore",
    "OntologyProfile",
    "RecallEvent",
    "RecallLog",
    "SQLiteMemoryStore",
]
