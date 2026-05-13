from __future__ import annotations

from muninn.packs import FridayPack, LexiPack


def test_lexi_pack_spec() -> None:
    spec = LexiPack().spec()
    assert spec.app_id == "lexi"
    assert spec.default_bundle == "lexi_default"
    assert "constraint" in spec.memory_types


def test_friday_pack_spec() -> None:
    spec = FridayPack().spec()
    assert spec.app_id == "friday"
    assert spec.default_bundle == "friday_default"
    assert "procedure_lesson" in spec.memory_types
