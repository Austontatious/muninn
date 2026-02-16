from __future__ import annotations

import json
import os

from muninn.client import MuninnClient
from muninn.models import MemoryCandidate, Provenance, RehydrateRequest, WriteCandidatesRequest


def main() -> None:
    base_url = os.getenv("MUNINN_BASE_URL", "http://127.0.0.1:8000")
    namespace = os.getenv("MUNINN_NAMESPACE", "default")
    profile = os.getenv("MUNINN_PROFILE", "generic")
    entity_id = os.getenv("MUNINN_ENTITY_ID", "ent_user")

    print(f"Muninn local client demo -> base={base_url} namespace={namespace} profile={profile}")

    with MuninnClient(base_url=base_url) as client:
        print("\nHealth:")
        print(json.dumps(client.health(), indent=2))

        candidate = MemoryCandidate(
            kind="preference",
            entity={"id": entity_id, "kind": "user", "name": "Demo User"},
            payload={"key": "style.response", "value": "direct"},
            confidence=0.9,
            provenance=Provenance(source_type="user", source_id="demo_turn_1"),
        )

        write_out = client.write_candidates(
            WriteCandidatesRequest(namespace=namespace, candidates=[candidate])
        )
        print("\nWrite result:")
        print(write_out.model_dump_json(indent=2))

        rehydrate_out = client.rehydrate(
            RehydrateRequest(
                namespace=namespace,
                query="Please answer directly",
                entity_id=entity_id,
                k=8,
                profile=profile,
            )
        )
        print("\nRehydrate result summary:")
        print(
            json.dumps(
                {
                    "cards": len(rehydrate_out.cards),
                    "items": len(rehydrate_out.items),
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
