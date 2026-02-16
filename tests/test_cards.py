from muninn.memory.cards import render_cards
from muninn.models import Provenance, RetrievedItem


def test_cards_render() -> None:
    items = [
        RetrievedItem(
            kind="fact",
            id="f1",
            entity_id="e1",
            text="prefers: direct",
            confidence=0.9,
            provenance=Provenance(source_type="user"),
        ),
        RetrievedItem(
            kind="episode",
            id="ep1",
            entity_id="e1",
            text="worked on memory system",
            confidence=0.8,
            provenance=Provenance(source_type="assistant"),
        ),
    ]
    cards = render_cards(items, "generic")
    assert len(cards) >= 1
    assert "Entity e1" in cards[0].title
