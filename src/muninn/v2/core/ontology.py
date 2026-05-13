from .models import OntologyProfile

DEFAULT_FOUNDATION_ONTOLOGY = OntologyProfile(
    id="ontology:muninn-v2-foundation",
    name="muninn-v2-foundation",
    version="0.1",
    description="Minimal durable-memory substrate ontology for adjacent Muninn v2 pilots.",
    entity_types=["person", "place", "organization", "repository", "artifact", "concept", "event", "custom"],
    card_kinds=["decision", "constraint", "interface", "runbook", "note", "custom"],
    association_types=["related", "supersedes", "duplicates", "contradicts", "refines", "evidenced_by"],
)

__all__ = ["DEFAULT_FOUNDATION_ONTOLOGY", "OntologyProfile"]
