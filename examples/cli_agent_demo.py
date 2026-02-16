import json
import os
import textwrap

import httpx

BASE = os.getenv("MUNINN_BASE_URL", "http://127.0.0.1:8000")


def rehydrate(namespace: str, entity_id: str, profile: str, query: str, k: int = 8) -> dict:
    payload = {
        "namespace": namespace,
        "query": query,
        "entity_id": entity_id,
        "k": k,
        "profile": profile,
    }
    response = httpx.post(f"{BASE}/v0/memory/rehydrate", json=payload, timeout=20)
    response.raise_for_status()
    return response.json()


def main() -> None:
    namespace = os.getenv("MUNINN_NAMESPACE", "default")
    profile = os.getenv("MUNINN_PROFILE", "generic")
    entity_id = os.getenv("MUNINN_ENTITY_ID", "ent_user")

    print(
        f"Muninn demo -> base={BASE} namespace={namespace} profile={profile} entity_id={entity_id}"
    )
    print("Type a message. Ctrl+C to exit.\n")

    while True:
        try:
            msg = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break
        if not msg:
            continue

        data = rehydrate(namespace, entity_id, profile, msg, k=8)
        cards = data.get("cards", [])

        memory_block_lines = ["<SYSTEM_MEMORY>"]
        for card in cards:
            memory_block_lines.append(
                f"- {card.get('title', '(untitled)')} [{card.get('card_type', 'MemoryCard')}]"
            )
            for bullet in card.get("bullets", []):
                memory_block_lines.append(f"  - {bullet}")
            for constraint in card.get("constraints", []):
                memory_block_lines.append(f"  - CONSTRAINT: {constraint}")
            for open_question in card.get("open_questions", []):
                memory_block_lines.append(f"  - OPEN: {open_question}")
        memory_block_lines.append("</SYSTEM_MEMORY>")

        composed = "\n".join(memory_block_lines) + "\n\nUSER:\n" + msg

        print("\n--- COMPOSED PROMPT (for your agent/model) ---")
        print(textwrap.indent(composed, ""))
        print("\n--- RAW ITEMS (debug/audit) ---")
        print(json.dumps(data.get("items", []), indent=2))
        print()


if __name__ == "__main__":
    main()
