from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from muninn import db
from muninn.api import app
from muninn.human_memory.bootstrap import DEFAULT_USER_ID, apply_init_schema, bootstrap_defaults, open_db
from muninn.human_memory.cards import card_upsert
from muninn.human_memory.rehydration import rehydrate_bundle
from muninn.human_memory.spaces import ResolvedSpace, get_or_create_space

CONTRACT_ROOT = Path(__file__).resolve().parents[1] / "docs" / "contracts" / "muninn_mimir" / "v1"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _versions() -> dict:
    return _read_json(CONTRACT_ROOT / "versions.json")


def _schema(schema_key: str) -> dict:
    versions = _versions()
    rel_path = versions["schemas"][schema_key]
    return _read_json(CONTRACT_ROOT / rel_path)


def _validator(schema_key: str) -> Draft202012Validator:
    return Draft202012Validator(_schema(schema_key))


def _example_cases(group: str) -> list[tuple[str, str]]:
    versions = _versions()
    cases: list[tuple[str, str]] = []
    for schema_key, rel_paths in versions["examples"][group].items():
        for rel_path in rel_paths:
            cases.append((schema_key, rel_path))
    return cases


def _clamp_score(score: float) -> float:
    return max(0.0, min(1.0, float(score)))


def _trust_level(score: float) -> str:
    if score >= 0.85:
        return "high"
    if score >= 0.6:
        return "medium"
    return "low"


def _map_lifecycle_from_status(status: str) -> str:
    normalized = (status or "").strip().lower()
    if normalized in {"active", "superseded", "archived"}:
        return normalized
    return "active"


def _map_status(status: str) -> str:
    normalized = (status or "").strip().lower()
    if normalized in {"active", "superseded", "archived", "candidate", "confirmed", "deprecated"}:
        return normalized
    return "confirmed"


def _map_ref_kind(ref_type: str) -> str:
    table = {
        "source": "source",
        "doc": "file",
        "chunk": "chunk",
        "entity": "entity",
        "external": "entity",
    }
    return table.get((ref_type or "").strip().lower(), "entity")


def _topology_ref_from_retrieve_ref(ref: dict[str, object]) -> dict[str, object]:
    return {
        "ref_kind": _map_ref_kind(str(ref.get("ref_type") or "")),
        "ref_id": str(ref.get("ref_id") or ""),
        "relation": str(ref.get("role") or "related"),
        "metadata": {
            "source_ref_type": str(ref.get("ref_type") or ""),
        },
    }


def _card_envelope_from_card_record(
    *,
    card_record: dict[str, object],
    retrieve_card: dict[str, object],
) -> dict[str, object]:
    score = _clamp_score(float(card_record.get("confidence") or 0.0))
    status = _map_status(str(card_record.get("status") or "active"))
    refs = retrieve_card.get("refs") or []
    topology_refs = [_topology_ref_from_retrieve_ref(ref) for ref in refs]

    envelope: dict[str, object] = {
        "contract_version": "1.0.0",
        "stable_id": str(card_record.get("card_id") or ""),
        "kind": str(card_record.get("type") or "card"),
        "title": str(card_record.get("title") or ""),
        "summary": str(card_record.get("summary") or ""),
        "lifecycle": {
            "lifecycle_state": _map_lifecycle_from_status(status),
            "status": status,
        },
        "confidence": {
            "score": score,
            "trust_level": _trust_level(score),
        },
        "provenance": {
            "source_type": "api",
            "source_id": "muninn:/retrieve",
            "evidence": [
                {
                    "type": "api",
                    "ref": "/retrieve",
                }
            ],
        },
        "topology_refs": topology_refs,
    }
    return envelope


def _project_rehydrate_card(row: dict[str, object]) -> dict[str, object]:
    score = _clamp_score(float(row.get("score") or 0.0))
    status = _map_status(str(row.get("status") or "active"))
    stage = str(row.get("stage") or "rehydrate")
    space_key = str(row.get("space_key") or "global")

    return {
        "contract_version": "1.0.0",
        "stable_id": str(row.get("id") or ""),
        "kind": str(row.get("kind") or "card"),
        "title": str(row.get("title") or ""),
        "summary": str(row.get("summary") or ""),
        "lifecycle": {
            "lifecycle_state": _map_lifecycle_from_status(status),
            "status": status,
        },
        "confidence": {
            "score": score,
            "trust_level": _trust_level(score),
        },
        "provenance": {
            "source_type": "retrieval",
            "source_id": f"stage:{stage}",
            "evidence_count": int(row.get("evidence_count") or 0),
            "evidence": [
                {
                    "type": "stage",
                    "ref": stage,
                }
            ],
        },
        "topology_refs": [
            {
                "ref_kind": "space",
                "ref_id": space_key,
                "relation": "resolved_in",
            }
        ],
    }


def _bundle_confidence(scores: list[float]) -> str:
    if not scores:
        return "unknown"
    spread = max(scores) - min(scores)
    if spread >= 0.35:
        return "mixed"
    if max(scores) >= 0.85:
        return "high"
    if max(scores) >= 0.6:
        return "medium"
    return "low"


def _manifest(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        out[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def _seed_card_with_source(client: TestClient, namespace: str, title: str, source_text: str) -> str:
    source_resp = client.post(
        "/sources",
        json={
            "namespace": namespace,
            "source_type": "note",
            "uri": f"local://{title}",
            "title": f"{title} source",
            "artifacts": [{"artifact_type": "summary", "content_text": source_text}],
        },
    )
    assert source_resp.status_code == 200
    source_id = source_resp.json()["source"]["source_id"]

    card_resp = client.post(
        "/cards",
        json={
            "namespace": namespace,
            "type": "fact",
            "title": title,
            "summary": f"Summary for {title}",
            "trusted_mode": True,
        },
    )
    assert card_resp.status_code == 200
    card_id = card_resp.json()["card_id"]

    link_resp = client.post(
        f"/cards/{card_id}/refs",
        json={
            "namespace": namespace,
            "refs": [{"ref_type": "source", "ref_id": source_id, "role": "evidence"}],
        },
    )
    assert link_resp.status_code == 200
    return card_id


def _init_human_memory(tmp_path: Path) -> tuple[object, str]:
    db_path = tmp_path / "human_memory_contracts.db"
    conn = open_db(str(db_path))
    apply_init_schema(conn)
    bootstrap_defaults(conn)
    resolved = ResolvedSpace(
        key="repo:muninnmimircontract0001",
        label="muninn-mimir-contract",
        meta_json=json.dumps({"root_path": "/tmp/muninn-mimir-contract"}, separators=(",", ":")),
    )
    get_or_create_space(conn, user_id=DEFAULT_USER_ID, resolved=resolved)
    return conn, resolved.key


@pytest.mark.parametrize(("schema_key", "example_rel"), _example_cases("valid"))
def test_shared_contract_valid_examples_pass(schema_key: str, example_rel: str) -> None:
    payload = _read_json(CONTRACT_ROOT / example_rel)
    _validator(schema_key).validate(payload)


@pytest.mark.parametrize(("schema_key", "example_rel"), _example_cases("invalid"))
def test_shared_contract_invalid_examples_fail(schema_key: str, example_rel: str) -> None:
    payload = _read_json(CONTRACT_ROOT / example_rel)
    with pytest.raises(ValidationError):
        _validator(schema_key).validate(payload)


def test_versions_file_declares_expected_schema_keys() -> None:
    versions = _versions()
    assert versions["contract_set"] == "muninn-mimir-shared"
    assert versions["current_version"] == "1.0.0"
    assert set(versions["schemas"].keys()) == {
        "card_envelope",
        "lifecycle_state",
        "mimir_memory_proposal_batch",
        "provenance_envelope",
        "confidence_trust",
        "rehydrate_request",
        "rehydrate_response",
        "topology_ref",
    }


def test_shared_contract_artifacts_match_sibling_repo_when_available() -> None:
    sibling_root = Path("/mnt/data/Mimir/docs/contracts/muninn_mimir/v1")
    if not sibling_root.exists():
        pytest.skip(f"Sibling contract directory not found: {sibling_root}")

    assert _manifest(CONTRACT_ROOT) == _manifest(sibling_root)


def test_muninn_card_and_topology_projections_match_shared_schema(tmp_path: Path, monkeypatch) -> None:
    test_db = tmp_path / "muninn_contracts.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)
    conn.close()

    client = TestClient(app)
    card_id = _seed_card_with_source(
        client,
        namespace="default",
        title="Cross project contract",
        source_text="Contract fixtures enforce shared shape.",
    )

    retrieve_resp = client.post(
        "/retrieve",
        json={
            "namespace": "default",
            "query": "shared contract",
            "scope": ["cards", "evidence"],
            "k_cards": 5,
            "k_evidence": 2,
        },
    )
    assert retrieve_resp.status_code == 200
    retrieve_body = retrieve_resp.json()

    retrieve_card = next(card for card in retrieve_body["cards"] if card["card_id"] == card_id)
    card_resp = client.get(f"/cards/{card_id}", params={"namespace": "default"})
    assert card_resp.status_code == 200
    card_record = card_resp.json()

    envelope = _card_envelope_from_card_record(card_record=card_record, retrieve_card=retrieve_card)
    _validator("card_envelope").validate(envelope)

    for ref in envelope["topology_refs"]:
        _validator("topology_ref").validate(ref)


def test_muninn_rehydrate_projection_matches_shared_schema(tmp_path: Path) -> None:
    conn, space_key = _init_human_memory(tmp_path)
    try:
        card_upsert(
            conn,
            user_id=DEFAULT_USER_ID,
            space_key=space_key,
            kind="runbook",
            title="Exact docker logs command",
            summary="Use docker logs first for service diagnostics.",
            body="Run docker logs <container> before deeper inspection.",
            created_by_client_name="contract-test",
            evidence_refs=[
                {
                    "id": "evidence-contract-1",
                    "type": "file",
                    "ref": "/tmp/runbook.md",
                    "excerpt": "docker logs command",
                    "created_by_client_name": "contract-test",
                }
            ],
        )

        request_projection = {
            "contract_version": "1.0.0",
            "query": "docker logs exact commands",
            "limit": 6,
            "scope": "soft",
            "kinds": ["runbook", "decision"],
            "include_body": False,
            "include_policy": True,
            "space": {
                "strategy": "explicit",
                "key": space_key,
            },
            "task_type": "troubleshooting",
            "tool_name": "shell",
        }
        _validator("rehydrate_request").validate(request_projection)

        payload = rehydrate_bundle(
            conn,
            user_id=DEFAULT_USER_ID,
            space_key=space_key,
            query="docker logs exact commands",
            kinds=["runbook", "decision"],
            status="active",
            limit=6,
            include_body=False,
            include_policy=True,
            scope="soft",
            tool_name="shell",
            task_type="troubleshooting",
        )

        items = [_project_rehydrate_card(row) for row in payload["project_cards"]]
        policy_items = [_project_rehydrate_card(row) for row in payload["policy_cards"]]
        for item in [*items, *policy_items]:
            _validator("card_envelope").validate(item)

        scores = [float(item["confidence"]["score"]) for item in [*items, *policy_items]]
        warnings = [
            str(stage["zero_reason"])
            for stage in payload["stages"]
            if stage.get("zero_reason")
        ]
        response_projection = {
            "contract_version": "1.0.0",
            "query": str(payload["query"]),
            "result_count": len(items),
            "items": items,
            "policy_items": policy_items,
            "stages": [
                {
                    "stage": str(stage["stage"]),
                    "results": int(stage["results"]),
                    "attempted": bool(stage["attempted"]),
                    "skipped": bool(stage["skipped"]),
                    "skip_reason": stage.get("skip_reason"),
                }
                for stage in payload["stages"]
            ],
            "confidence": _bundle_confidence(scores),
            "warnings": warnings,
            "metadata": {
                "canonical_space": payload["space"]["canonical_key"],
            },
        }

        _validator("rehydrate_response").validate(response_projection)
        assert response_projection["result_count"] == len(response_projection["items"])
    finally:
        conn.close()


def test_close_enough_topology_shape_is_rejected() -> None:
    close_enough = {
        "ref_kind": "source",
        "ref_id": "src_123",
        "role": "evidence"
    }

    with pytest.raises(ValidationError):
        _validator("topology_ref").validate(close_enough)
