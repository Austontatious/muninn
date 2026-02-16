from __future__ import annotations

from ..models import MemoryCard, RetrievedItem


def render_cards(items: list[RetrievedItem], profile: str = "generic") -> list[MemoryCard]:
    # v0: deterministic carding (no LLM required). v1 can add LLM compression.
    buckets: dict[str, list[RetrievedItem]] = {}
    for item in items:
        buckets.setdefault(item.entity_id, []).append(item)

    cards: list[MemoryCard] = []
    for entity_id, entity_items in buckets.items():
        title = f"Entity {entity_id}"
        bullets: list[str] = []
        constraints: list[str] = []
        for item in entity_items[:7]:
            bullets.append(
                f"[{item.kind}] {item.text} (conf={item.confidence:.2f}, src={item.provenance.source_type})"
            )

        card_type = {
            "lexi": "LexiMemoryCard",
            "friday": "FridayMemoryCard",
        }.get(profile, "MemoryCard")

        cards.append(
            MemoryCard(
                card_type=card_type,
                title=title,
                bullets=bullets,
                constraints=constraints,
                open_questions=[],
                do_not_use=[],
            )
        )
    return cards[:5]
