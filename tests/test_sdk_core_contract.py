from __future__ import annotations

from pathlib import Path

import pytest

from muninn import EvidenceRef, MemoryItem, Muninn, MuninnConfig
from muninn.packs import LexiPack


def _config(tmp_path: Path) -> MuninnConfig:
    return MuninnConfig(db_path=str(tmp_path / "human_memory.db"), space_key="sdk-test", scope="strict")


def test_sdk_write_and_query(tmp_path: Path) -> None:
    mem = Muninn(app_pack=LexiPack(), config=_config(tmp_path))
    item = MemoryItem(
        app_id="lexi",
        kind="profile_fact",
        title="Profile fact",
        summary="Prefers concise responses",
        payload={"subject": "user", "fact": "prefers concise responses"},
    )
    mem.write(item)

    results = mem.query(query="concise responses")
    assert results
    assert any("concise" in entry.summary for entry in results)


def test_sdk_evidence_required(tmp_path: Path) -> None:
    mem = Muninn(app_pack=LexiPack(), config=_config(tmp_path))
    item = MemoryItem(
        app_id="lexi",
        kind="constraint",
        title="Constraint",
        summary="Always include citations",
        payload={"constraint": "Always include citations"},
    )
    with pytest.raises(ValueError, match="evidence_required"):
        mem.write(item)

    item.evidence = [EvidenceRef(type="file", ref="/tmp/example.py:1")]
    mem.write(item)


def test_sdk_bundle_stages(tmp_path: Path) -> None:
    mem = Muninn(app_pack=LexiPack(), config=_config(tmp_path))
    mem.write(
        MemoryItem(
            app_id="lexi",
            kind="project",
            title="Project",
            summary="SDK refactor",
            payload={"name": "SDK refactor"},
        )
    )
    mem.write(
        MemoryItem(
            app_id="lexi",
            kind="constraint",
            title="Constraint",
            summary="Keep compatibility",
            payload={"constraint": "Keep compatibility"},
            evidence=[EvidenceRef(type="file", ref="/tmp/example.py:2")],
        )
    )

    bundle = mem.rehydrate_bundle(query="compatibility")
    assert bundle.bundle_name == "lexi_default"
    assert len(bundle.stages) == 3
    assert bundle.explanation.decisions
