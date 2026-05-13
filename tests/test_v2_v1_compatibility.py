from __future__ import annotations

import pytest

pytest.importorskip("mcp")

from muninn.mcp_server import create_mcp_server


def test_importing_v2_does_not_remove_existing_mcp_tools() -> None:
    import muninn.v2  # noqa: F401

    server = create_mcp_server()
    tool_names = set(server._tool_manager._tools)

    assert "muninn.spaces.resolve" in tool_names
    assert "muninn.cards.search" in tool_names
    assert "muninn.rehydrate.bundle" in tool_names
    assert "muninn.cards.upsert" in tool_names
