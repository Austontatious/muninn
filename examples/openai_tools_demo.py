from __future__ import annotations

import json
import os

from muninn.adapters.openai_tools import dispatch_openai_tool_call, openai_tools_spec
from muninn.client import MuninnClient


def main() -> None:
    base_url = os.getenv("MUNINN_BASE_URL", "http://127.0.0.1:8000")
    print(f"Muninn OpenAI tools demo -> base={base_url}")
    print("\nTools payload:")
    print(json.dumps(openai_tools_spec(), indent=2))

    sample_args = {
        "namespace": "default",
        "query": "how should I respond",
        "entity_id": "ent_user",
        "k": 5,
        "profile": "generic",
    }

    with MuninnClient(base_url=base_url) as client:
        try:
            out = dispatch_openai_tool_call(client, "muninn_rehydrate", sample_args)
        except Exception as exc:
            print("\nRehydrate call failed (is the dev server running?):")
            print(str(exc))
            return

    cards = out.get("cards", [])
    items = out.get("items", [])
    print("\nRehydrate summary:")
    print(json.dumps({"cards": len(cards), "items": len(items)}, indent=2))


if __name__ == "__main__":
    main()
