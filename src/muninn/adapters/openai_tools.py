"""OpenAI-style tool definitions and dispatcher for Muninn."""

from __future__ import annotations

from typing import Any

from ..client import MuninnClient
from .common import dispatch_tool_call, load_tool_spec, public_tools_from_spec


def openai_tools_spec() -> list[dict[str, Any]]:
    spec = load_tool_spec()
    tools = public_tools_from_spec(spec)

    out: list[dict[str, Any]] = []
    for tool in tools:
        out.append(
            {
                "type": "function",
                "function": {
                    "name": tool["tool_name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get(
                        "request_schema",
                        {"type": "object", "properties": {}, "required": []},
                    ),
                },
            }
        )
    return out


def dispatch_openai_tool_call(
    client: MuninnClient,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    return dispatch_tool_call(client, tool_name, arguments)
