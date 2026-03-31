from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

pytest.importorskip("mcp")

from muninn.human_memory.bootstrap import DEFAULT_USER_ID, apply_init_schema, bootstrap_defaults, open_db
from muninn.human_memory.spaces import ResolvedSpace, get_or_create_space
from muninn.mcp_server import (
    LensInput,
    PolicySignalInput,
    SearchQueryInput,
    _handle_tool_exception,
    _scope_space_keys,
)


def _init_conn(tmp_path):
    db_path = tmp_path / "mcp_human_memory_contracts.db"
    conn = open_db(str(db_path))
    apply_init_schema(conn)
    bootstrap_defaults(conn)
    resolved = ResolvedSpace(
        key="repo:contractrepo0001",
        label="contract-repo",
        meta_json=json.dumps({"root_path": "/tmp/contract-repo"}, separators=(",", ":")),
        alias_keys=("path:contractpath0001",),
    )
    get_or_create_space(conn, user_id=DEFAULT_USER_ID, resolved=resolved)
    return conn, resolved.key, resolved.alias_keys[0]


def test_lens_input_accepts_nested_object_and_legacy_string_shapes() -> None:
    nested = LensInput.model_validate(
        {
            "lens": {
                "space": "auto",
                "cwd": "/tmp/example",
                "kind": "decision",
                "tags": "schema,docs",
                "limit": "5",
            }
        }
    )
    legacy = LensInput.model_validate("space_key:repo:abc123 scope:soft kind:runbook limit:3")

    assert nested.kinds == ["decision"]
    assert nested.tags == ["schema", "docs"]
    assert nested.limit == 5
    assert legacy.space_key == "repo:abc123"
    assert legacy.scope == "soft"
    assert legacy.kinds == ["runbook"]
    assert legacy.limit == 3


@pytest.mark.parametrize("cwd_value", [None, "", "   "])
def test_lens_input_rejects_auto_space_without_cwd(cwd_value) -> None:
    with pytest.raises(ValidationError) as exc_info:
        LensInput.model_validate({"space": "auto", "cwd": cwd_value})

    err = _handle_tool_exception(exc_info.value)
    assert err["error"]["code"] == "InvalidArguments"
    assert err["error"]["details"]["field"] == "cwd"
    assert "lens.cwd is required when lens.space='auto'." in err["error"]["details"]["error"]


def test_lens_input_accepts_auto_space_with_trimmed_cwd() -> None:
    lens = LensInput.model_validate({"space": "auto", "cwd": "  /tmp/example  "})

    assert lens.cwd == "/tmp/example"


def test_search_query_input_accepts_legacy_shapes() -> None:
    assert SearchQueryInput.model_validate("docker logs").resolved_text() == "docker logs"
    assert SearchQueryInput.model_validate(["docker", "logs"]).resolved_text() == "docker logs"
    assert SearchQueryInput.model_validate({"q": "docker logs"}).resolved_text() == "docker logs"


def test_validation_errors_map_to_invalid_arguments_with_field_details() -> None:
    with pytest.raises(ValidationError) as exc_info:
        SearchQueryInput.model_validate({"terms": 123})

    err = _handle_tool_exception(exc_info.value)
    assert err["error"]["code"] == "InvalidArguments"
    assert err["error"]["details"]["field"] == "terms"
    assert "terms" in err["error"]["details"]["error"]


def test_soft_scope_includes_alias_lookup_and_global(tmp_path) -> None:
    conn, canonical_key, alias_key = _init_conn(tmp_path)
    lens = LensInput(space_key=alias_key, scope="soft")

    scoped = _scope_space_keys(conn, lens)

    assert scoped[0] == canonical_key
    assert alias_key in scoped
    assert scoped[-1] == "global"
    conn.close()


def test_policy_signal_input_rejects_bad_signal_type() -> None:
    with pytest.raises(ValidationError):
        PolicySignalInput.model_validate({"summary": "bad signal", "signal_type": "bogus"})
