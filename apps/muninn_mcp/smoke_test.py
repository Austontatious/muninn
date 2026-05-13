from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

EXPECTED_TOOLS = {
    "search",
    "fetch",
    "search_memory",
    "fetch_memory",
    "rehydrate_project",
    "stage_memory_candidates",
    "list_pending_memory",
    "confirm_memory_candidates",
}

FORBIDDEN_TOOL_FRAGMENTS = {
    "write_candidates",
    "direct_write",
    "upsert",
    "admin",
    "debug",
    "cleanup",
    "delete",
    "shell",
    "exec",
}


def _extract_text(result: Any) -> str:
    content = getattr(result, "content", None)
    if not content:
        return ""
    first = content[0]
    return str(getattr(first, "text", ""))


async def run(url: str) -> None:
    async with streamablehttp_client(url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            listed = await session.list_tools()
            tool_names = {tool.name for tool in listed.tools}

            missing = sorted(EXPECTED_TOOLS - tool_names)
            if missing:
                raise AssertionError(f"missing expected tools: {missing}")

            forbidden = sorted(
                name
                for name in tool_names
                for fragment in FORBIDDEN_TOOL_FRAGMENTS
                if fragment in name
            )
            if forbidden:
                raise AssertionError(f"forbidden tools exposed: {forbidden}")

            search_result = await session.call_tool("search", {"query": "Mimir"})
            rehydrate_result = await session.call_tool(
                "rehydrate_project",
                {"project": "Mimir"},
            )
            pending_result = await session.call_tool("list_pending_memory", {})

    print(json.dumps({"ok": True, "tools": sorted(tool_names)}, sort_keys=True))
    print("search:", _extract_text(search_result)[:500])
    print("rehydrate_project:", _extract_text(rehydrate_result)[:500])
    print("list_pending_memory:", _extract_text(pending_result)[:500])


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test the Muninn Memory MCP bridge.")
    parser.add_argument("url", help="Streamable HTTP MCP URL, for example https://host/mcp-secret/mcp")
    args = parser.parse_args()
    asyncio.run(run(args.url))


if __name__ == "__main__":
    main()
