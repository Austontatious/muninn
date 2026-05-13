from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from muninn.cli import main
from muninn.mimir_proposals import (
    approve_proposal_batch,
    preview_proposal_batch,
    validate_proposal_batch,
)


CONTRACT_ROOT = Path(__file__).resolve().parents[1] / "docs" / "contracts" / "muninn_mimir" / "v1"


def _valid_batch() -> dict:
    return json.loads((CONTRACT_ROOT / "examples" / "valid" / "mimir-memory-proposal-batch.basic.v1.json").read_text(encoding="utf-8"))


def _write_batch(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "mimir-proposals.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def test_valid_mimir_proposal_batch_validates() -> None:
    result = validate_proposal_batch(_valid_batch())

    assert result["ok"] is True
    assert result["source_system"] == "mimir"
    assert result["proposal_count"] == 1
    assert result["proposal_types"] == ["guardrail"]


def test_legacy_mimir_batch_shape_validates_with_normalization_warnings() -> None:
    payload = _valid_batch()
    payload.pop("batch_id")
    payload.pop("source_system")
    payload.pop("generated_by_command")
    payload.pop("review_required")
    payload.pop("writes_to_muninn")
    payload.pop("writes_durable_memory")
    payload["write_behavior"] = {
        "writes_to_muninn": False,
        "writes_durable_memory": False,
        "review_required_for_all_proposals": True,
    }

    result = validate_proposal_batch(payload)

    assert result["ok"] is True
    assert result["source_system"] == "mimir"
    assert "source_system_inferred_from_mimir_schema_version" in result["warnings"]
    assert result["batch_id"].startswith("mimir-proposals-")


def test_missing_evidence_fails() -> None:
    payload = _valid_batch()
    payload["proposals"][0]["evidence"] = []

    result = validate_proposal_batch(payload)

    assert result["ok"] is False
    assert any("missing_evidence" in error for error in result["errors"])


def test_review_required_false_fails() -> None:
    payload = _valid_batch()
    payload["review_required"] = False
    payload["proposals"][0]["review_required"] = False

    result = validate_proposal_batch(payload)

    assert result["ok"] is False
    assert "batch_review_required_not_true" in result["errors"]
    assert any("review_required_not_true" in error for error in result["errors"])


def test_write_claims_fail() -> None:
    payload = _valid_batch()
    payload["writes_to_muninn"] = True
    payload["writes_durable_memory"] = True

    result = validate_proposal_batch(payload)

    assert result["ok"] is False
    assert "batch_claims_writes_to_muninn" in result["errors"]
    assert "batch_claims_writes_durable_memory" in result["errors"]


def test_preview_maps_card_envelopes_without_writing() -> None:
    payload = _valid_batch()

    result = preview_proposal_batch(payload, namespace="default")

    assert result["ok"] is True
    assert result["would_write"] is False
    assert result["selected_count"] == 1
    card = result["cards"][0]
    schema = json.loads((CONTRACT_ROOT / "schemas" / "card-envelope.v1.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(card)
    assert card["title"] == "Muninn remains the durable memory owner"
    assert card["provenance"]["metadata"]["proposal_id"] == payload["proposals"][0]["proposal_id"]


def test_approve_dry_run_selected_proposal_only() -> None:
    payload = _valid_batch()
    second = dict(payload["proposals"][0])
    second["proposal_id"] = "mem-proposal-002-second"
    second["title"] = "Second proposal"
    payload["proposals"].append(second)

    result = approve_proposal_batch(
        payload,
        namespace="default",
        proposal_ids=["mem-proposal-002-second"],
    )

    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["wrote"] is False
    assert result["selected_count"] == 1
    assert result["cards"][0]["title"] == "Second proposal"


def test_approve_all_requires_explicit_flag() -> None:
    result = approve_proposal_batch(_valid_batch(), namespace="default")

    assert result["ok"] is False
    assert "approval_requires_proposal_id_or_approve_all" in result["errors"]


def test_write_mode_is_rejected() -> None:
    result = approve_proposal_batch(
        _valid_batch(),
        namespace="default",
        proposal_ids=["mem-proposal-001-muninn-remains-memory-owner"],
        write=True,
    )

    assert result["ok"] is False
    assert result["wrote"] is False
    assert "write_mode_not_implemented_in_this_contract_slice" in result["errors"]


def test_cli_proposals_validate_preview_and_approve(tmp_path: Path, capsys) -> None:
    path = _write_batch(tmp_path, _valid_batch())

    rc = main(["proposals", "validate", "--proposal-batch", str(path), "--json"])
    assert rc == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True

    rc = main(["proposals", "preview", "--proposal-batch", str(path), "--json"])
    assert rc == 0
    assert json.loads(capsys.readouterr().out)["would_write"] is False

    rc = main([
        "proposals",
        "approve",
        "--proposal-batch",
        str(path),
        "--proposal-id",
        "mem-proposal-001-muninn-remains-memory-owner",
        "--json",
    ])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["dry_run"] is True
    assert payload["wrote"] is False


def test_malformed_batch_cli_fails_clearly(tmp_path: Path, capsys) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{bad json", encoding="utf-8")

    rc = main(["proposals", "validate", "--proposal-batch", str(path), "--json"])

    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["errors"]
