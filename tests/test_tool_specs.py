from __future__ import annotations

import hashlib
from pathlib import Path

from muninn.adapters.anthropic_tools import anthropic_tools_spec
from muninn.adapters.common import load_tool_spec, public_tools_from_spec
from muninn.adapters.openai_tools import openai_tools_spec

REQUIRED_TOOLS = {
    "muninn_rehydrate",
    "muninn_write_candidates",
    "muninn_stage_candidates",
    "muninn_list_pending",
    "muninn_confirm_candidates",
    "muninn_upsert_embeddings",
    "muninn_query_vector",
    "muninn_version",
    "muninn_debug_vector_backend",
    "muninn_cardex_create_card",
    "muninn_cardex_get_card",
    "muninn_cardex_create_source",
    "muninn_cardex_ingest",
    "muninn_cardex_add_source_artifacts",
    "muninn_cardex_link_refs",
    "muninn_cardex_retrieve",
    "muninn_cardex_promote",
    "muninn_cardex_propose",
    "muninn_cardex_confirm",
    "muninn_cardex_reject",
    "muninn_cardex_upsert_embedding",
}


def test_provider_tool_specs_include_required_public_tools() -> None:
    openai_names = {tool["function"]["name"] for tool in openai_tools_spec()}
    anthropic_names = {tool["name"] for tool in anthropic_tools_spec()}

    assert REQUIRED_TOOLS.issubset(openai_names)
    assert REQUIRED_TOOLS.issubset(anthropic_names)

    assert "muninn_reindex_vectors" not in openai_names
    assert "muninn_reindex_vectors" not in anthropic_names


def test_provider_tool_schemas_align_with_tool_spec_source() -> None:
    source_spec = load_tool_spec()
    source_tools = {tool["tool_name"]: tool for tool in public_tools_from_spec(source_spec)}

    openai_schemas = {
        tool["function"]["name"]: tool["function"]["parameters"] for tool in openai_tools_spec()
    }
    anthropic_schemas = {tool["name"]: tool["input_schema"] for tool in anthropic_tools_spec()}

    for name, tool in source_tools.items():
        assert name in openai_schemas
        assert name in anthropic_schemas

        source_schema = tool.get("request_schema", {"type": "object", "properties": {}, "required": []})
        openai_schema = openai_schemas[name]
        anthropic_schema = anthropic_schemas[name]

        source_required = set(source_schema.get("required", []))
        source_properties = set(source_schema.get("properties", {}).keys())

        assert source_required.issubset(set(openai_schema.get("required", [])))
        assert source_required.issubset(set(anthropic_schema.get("required", [])))

        assert source_properties.issubset(set(openai_schema.get("properties", {}).keys()))
        assert source_properties.issubset(set(anthropic_schema.get("properties", {}).keys()))


def test_tool_spec_files_are_byte_identical() -> None:
    root = Path(__file__).resolve().parents[1]
    source = root / "schemas" / "tooling" / "muninn_tool_spec.json"
    packaged = root / "src" / "muninn" / "resources" / "muninn_tool_spec.json"

    source_bytes = source.read_bytes()
    packaged_bytes = packaged.read_bytes()

    source_sha = hashlib.sha256(source_bytes).hexdigest()
    packaged_sha = hashlib.sha256(packaged_bytes).hexdigest()

    assert source_sha == packaged_sha
    assert source_bytes == packaged_bytes
