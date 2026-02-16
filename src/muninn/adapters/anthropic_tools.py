"""Anthropic-style tool definitions and dispatcher for Muninn."""

from __future__ import annotations

from typing import Any

from ..client import MuninnClient
from .common import dispatch_tool_call, load_tool_spec, public_tools_from_spec


def anthropic_tools_spec() -> list[dict[str, Any]]:
    spec = load_tool_spec()
    tools = public_tools_from_spec(spec)

    out: list[dict[str, Any]] = []
    for tool in tools:
        out.append(
            {
                "name": tool["tool_name"],
                "description": tool.get("description", ""),
                "input_schema": tool.get(
                    "request_schema",
                    {"type": "object", "properties": {}, "required": []},
                ),
            }
        )
    return out


def dispatch_anthropic_tool_call(
    client: MuninnClient,
    tool_name: str,
    tool_input: dict[str, Any],
) -> dict[str, Any]:
    return dispatch_tool_call(client, tool_name, tool_input)
