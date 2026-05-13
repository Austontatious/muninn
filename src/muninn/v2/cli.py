from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

from muninn.human_memory.bootstrap import DEFAULT_USER_ID
from muninn.human_memory.cards import cards_search

from .adapters import V1ReadAdapter
from .core.models import (
    SCHEMA_VERSION,
    EvidenceRef,
    MemoryAssociation,
    MemoryCard,
    MemoryEntity,
    MemoryEvent,
    OntologyProfile,
)
from .storage import SQLiteMemoryStore


class PilotSafetyError(RuntimeError):
    """Raised when a pilot import would violate explicit safety gates."""


class RecallParityError(RuntimeError):
    """Raised when recall parity cannot run safely."""


_RECALL_TOKEN_RE = re.compile(r"[a-z0-9_]+")


def _sha16(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _normalize_remote(remote: str) -> str:
    value = str(remote or "").strip()
    value = value.replace("git@github.com:", "https://github.com/")
    if value.endswith(".git"):
        value = value[:-4]
    return value.lower()


def _run_git(cwd: Path, args: list[str]) -> str | None:
    try:
        out = subprocess.check_output(
            ["git", *args],
            cwd=str(cwd),
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return None
    decoded = out.decode("utf-8", "replace").strip()
    return decoded or None


def _json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    text = str(value or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text, "parse_error": "invalid_json"}
    return parsed if isinstance(parsed, dict) else {"value": parsed}


def _connect_v1_readonly(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise PilotSafetyError(f"v1_db_not_found:{db_path}")
    uri = f"{db_path.resolve().as_uri()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def _connect_v2_readonly(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise RecallParityError(f"v2_db_not_found:{db_path}")
    uri = f"{db_path.resolve().as_uri()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1",
        (table_name,),
    ).fetchone()
    return row is not None


def _table_names(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name ASC
        """
    ).fetchall()
    return [str(row["name"]) for row in rows]


def _collect_row_counts(conn: sqlite3.Connection) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table_name in _table_names(conn):
        row = conn.execute(f'SELECT COUNT(*) AS n FROM "{table_name}"').fetchone()
        counts[table_name] = int(row["n"] or 0)
    return counts


def _row_count_report(before: dict[str, int], after: dict[str, int]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for table_name in sorted(set(before) | set(after)):
        before_count = before.get(table_name)
        after_count = after.get(table_name)
        rows.append(
            {
                "table": table_name,
                "before": before_count,
                "after": after_count,
                "changed": before_count != after_count,
            }
        )
    return rows


def _project_identity(project_path: Path) -> dict[str, Any]:
    if not project_path.exists():
        raise PilotSafetyError(f"project_path_not_found:{project_path}")
    absolute = project_path.resolve()
    repo_root = _run_git(absolute, ["rev-parse", "--show-toplevel"])
    if repo_root:
        root = Path(repo_root).resolve()
        path_key = f"path:{_sha16(str(root))}"
        remote = _run_git(absolute, ["config", "--get", "remote.origin.url"])
        if remote:
            remote_norm = _normalize_remote(remote)
            space_key = f"repo:{_sha16(remote_norm)}"
            alias_keys = [path_key]
            identity = "repo_remote"
        else:
            remote_norm = None
            space_key = path_key
            alias_keys = []
            identity = "repo_path"
        label = root.name or str(root)
        return {
            "identity": identity,
            "project_path": str(absolute),
            "root_path": str(root),
            "label": label,
            "git_remote": remote,
            "git_remote_norm": remote_norm,
            "expected_space_key": space_key,
            "expected_alias_keys": alias_keys,
        }

    legacy_cwd_key = f"cwd:{_sha16(str(absolute))}"
    return {
        "identity": "path",
        "project_path": str(absolute),
        "root_path": str(absolute),
        "label": absolute.name or str(absolute),
        "git_remote": None,
        "git_remote_norm": None,
        "expected_space_key": f"path:{_sha16(str(absolute))}",
        "expected_alias_keys": [legacy_cwd_key],
    }


def _space_rows_for_key(conn: sqlite3.Connection, space_key: str) -> list[sqlite3.Row]:
    if not _table_exists(conn, "spaces"):
        raise PilotSafetyError("v1_spaces_table_missing")
    return list(
        conn.execute(
            """
            SELECT id, user_id, key, label, meta_json, created_at, updated_at
            FROM spaces
            WHERE key = ?
            ORDER BY user_id ASC, key ASC
            """,
            (space_key,),
        ).fetchall()
    )


def _space_rows_for_alias(conn: sqlite3.Connection, alias_key: str) -> list[sqlite3.Row]:
    if not _table_exists(conn, "space_aliases"):
        return []
    return list(
        conn.execute(
            """
            SELECT s.id, s.user_id, s.key, s.label, s.meta_json, s.created_at, s.updated_at
            FROM space_aliases a
            JOIN spaces s ON s.user_id = a.user_id AND s.key = a.canonical_key
            WHERE a.alias_key = ?
            ORDER BY s.user_id ASC, s.key ASC
            """,
            (alias_key,),
        ).fetchall()
    )


def _candidate_spaces(conn: sqlite3.Connection, identity: dict[str, Any]) -> list[dict[str, Any]]:
    keys = [
        str(identity.get("expected_space_key") or ""),
        *[str(item) for item in identity.get("expected_alias_keys", [])],
    ]
    keys = [key for key in dict.fromkeys(keys) if key]
    clauses: list[str] = []
    params: list[Any] = []
    if keys:
        placeholders = ", ".join(["?"] * len(keys))
        clauses.append(f"s.key IN ({placeholders})")
        params.extend(keys)
    for value in (
        identity.get("root_path"),
        identity.get("project_path"),
        identity.get("git_remote_norm"),
        identity.get("label"),
    ):
        text = str(value or "").strip()
        if text:
            clauses.append("s.meta_json LIKE ?")
            params.append(f"%{text}%")
            clauses.append("s.label LIKE ?")
            params.append(f"%{text}%")
    if not clauses or not _table_exists(conn, "spaces"):
        return []
    rows = conn.execute(
        f"""
        SELECT s.id, s.user_id, s.key, s.label, s.meta_json, s.created_at, s.updated_at
        FROM spaces s
        WHERE {" OR ".join(clauses)}
        ORDER BY s.key ASC, s.user_id ASC
        """,
        tuple(params),
    ).fetchall()
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        marker = f"{row['user_id']}:{row['key']}"
        if marker in seen:
            continue
        seen.add(marker)
        out.append(_space_row_payload(row))
    return out


def _space_row_payload(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "user_id": str(row["user_id"]),
        "key": str(row["key"]),
        "label": str(row["label"] or ""),
        "meta": _json_dict(row["meta_json"]),
        "created_at": str(row["created_at"] or ""),
        "updated_at": str(row["updated_at"] or ""),
    }


def _resolve_space_selection(
    conn: sqlite3.Connection,
    *,
    requested_space_key: str,
    identity: dict[str, Any],
    strict: bool,
) -> tuple[sqlite3.Row, list[dict[str, Any]]]:
    direct_rows = _space_rows_for_key(conn, requested_space_key)
    alias_rows: list[sqlite3.Row] = [] if direct_rows else _space_rows_for_alias(conn, requested_space_key)
    rows = direct_rows or alias_rows
    candidate_rows = _candidate_spaces(conn, identity)
    ambiguous_records: list[dict[str, Any]] = []

    if not rows:
        raise PilotSafetyError(
            "space_not_found:"
            + json.dumps(
                {
                    "requested_space_key": requested_space_key,
                    "candidate_spaces": candidate_rows,
                },
                sort_keys=True,
            )
        )
    if len(rows) > 1:
        raise PilotSafetyError(
            "space_selector_ambiguous:"
            + json.dumps(
                {
                    "requested_space_key": requested_space_key,
                    "matching_spaces": [_space_row_payload(row) for row in rows],
                },
                sort_keys=True,
            )
        )

    selected = rows[0]
    selected_key = str(selected["key"])
    expected_key = str(identity.get("expected_space_key") or "")
    expected_aliases = [str(item) for item in identity.get("expected_alias_keys", [])]
    if expected_key and selected_key != expected_key and requested_space_key not in expected_aliases:
        ambiguous_records.append(
            {
                "type": "space_key_identity_mismatch",
                "requested_space_key": requested_space_key,
                "selected_space_key": selected_key,
                "expected_space_key": expected_key,
                "expected_alias_keys": expected_aliases,
                "candidate_spaces": candidate_rows,
            }
        )

    meta = _json_dict(selected["meta_json"])
    root_path = str(identity.get("root_path") or "")
    meta_root = str(meta.get("root_path") or meta.get("cwd") or "")
    if root_path and meta_root and Path(meta_root).expanduser().resolve() != Path(root_path).expanduser().resolve():
        ambiguous_records.append(
            {
                "type": "space_root_path_mismatch",
                "selected_space_key": selected_key,
                "space_root_path": meta_root,
                "project_root_path": root_path,
            }
        )

    if strict and ambiguous_records:
        raise PilotSafetyError(
            "strict_space_validation_failed:" + json.dumps(ambiguous_records, sort_keys=True)
        )
    return selected, ambiguous_records


def _count_query(
    conn: sqlite3.Connection,
    table_name: str,
    sql: str,
    params: tuple[Any, ...],
) -> tuple[bool, int]:
    if not _table_exists(conn, table_name):
        return False, 0
    row = conn.execute(sql, params).fetchone()
    return True, int(row["n"] if row is not None else 0)


def _collect_unsupported_records(
    conn: sqlite3.Connection,
    *,
    space_id: str,
    space_key: str,
) -> dict[str, Any]:
    specs = [
        {
            "record_type": "interaction_events",
            "table": "interaction_events",
            "reason": "v1 behavioral interaction stream is not mapped in the pilot slice.",
            "sql": "SELECT COUNT(*) AS n FROM interaction_events WHERE space_id = ?",
            "params": (space_id,),
        },
        {
            "record_type": "card_vectors",
            "table": "card_vectors",
            "reason": "v1 vector blobs are derived indexes, not canonical v2 truth.",
            "sql": "SELECT COUNT(*) AS n FROM card_vectors WHERE space_key = ?",
            "params": (space_key,),
        },
        {
            "record_type": "vector_index_state",
            "table": "vector_index_state",
            "reason": "v1 vector index state is store-local operational metadata.",
            "sql": "SELECT COUNT(*) AS n FROM vector_index_state",
            "params": (),
        },
    ]
    rows: list[dict[str, Any]] = []
    total = 0
    for spec in specs:
        present, count = _count_query(
            conn,
            str(spec["table"]),
            str(spec["sql"]),
            tuple(spec["params"]),
        )
        if present:
            total += count
        rows.append(
            {
                "record_type": spec["record_type"],
                "table": spec["table"],
                "table_present": present,
                "count": count,
                "reason": spec["reason"],
            }
        )
    return {
        "unsupported_record_types": rows,
        "total_unsupported_records": total,
    }


def _project_entity(
    *,
    space_key: str,
    identity: dict[str, Any],
    space_row: sqlite3.Row,
) -> MemoryEntity:
    aliases = [
        str(identity.get("expected_space_key") or ""),
        *[str(item) for item in identity.get("expected_alias_keys", [])],
    ]
    aliases = [item for item in dict.fromkeys(aliases) if item]
    return MemoryEntity(
        id=f"v1-project:{space_key}",
        entity_type="project",
        name=str(identity.get("label") or Path(str(identity.get("root_path") or "")).name or space_key),
        aliases=aliases,
        properties={
            "space_key": space_key,
            "project_path": identity.get("project_path"),
            "root_path": identity.get("root_path"),
            "git_remote": identity.get("git_remote"),
            "git_remote_norm": identity.get("git_remote_norm"),
            "v1_space": _space_row_payload(space_row),
        },
        provenance={"source_system": "muninn_v1", "source_table": "spaces"},
    )


def _attach_project_entity(cards: list[MemoryCard], entity: MemoryEntity) -> None:
    for card in cards:
        card.entity_ids = list(dict.fromkeys([*card.entity_ids, entity.id]))
        metadata = dict(card.metadata)
        metadata.setdefault("project_entity_id", entity.id)
        metadata.setdefault("project_path", entity.properties.get("project_path"))
        metadata.setdefault("project_root_path", entity.properties.get("root_path"))
        card.metadata = metadata


def _dedupe_evidence(cards: list[MemoryCard]) -> list[EvidenceRef]:
    by_id: dict[str, EvidenceRef] = {}
    for card in cards:
        for evidence in card.evidence:
            by_id.setdefault(evidence.id, evidence)
    return list(by_id.values())


def _stable_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _checksum_payload(payload: Any) -> str:
    return hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()


def _sorted_payloads(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [dict(row) for row in rows],
        key=lambda row: (
            str(row.get("record_type") or row.get("source_table") or ""),
            str(row.get("id") or row.get("source_id") or row.get("target_id") or ""),
        ),
    )


def _load_v1_tags_by_card_ids(
    conn: sqlite3.Connection,
    card_ids: Sequence[str],
) -> dict[str, list[str]]:
    if not card_ids:
        return {}
    placeholders = ", ".join(["?"] * len(card_ids))
    rows = conn.execute(
        f"""
        SELECT ct.card_id, t.name
        FROM card_tags ct
        JOIN tags t ON t.id = ct.tag_id
        WHERE ct.card_id IN ({placeholders})
        ORDER BY t.name ASC
        """,
        tuple(card_ids),
    ).fetchall()
    out: dict[str, list[str]] = {card_id: [] for card_id in card_ids}
    for row in rows:
        out.setdefault(str(row["card_id"]), []).append(str(row["name"]))
    return out


def _load_v1_evidence_by_card_ids(
    conn: sqlite3.Connection,
    card_ids: Sequence[str],
) -> dict[str, list[dict[str, Any]]]:
    if not card_ids:
        return {}
    placeholders = ", ".join(["?"] * len(card_ids))
    rows = conn.execute(
        f"""
        SELECT ce.card_id, e.id, e.type, e.ref, e.excerpt, e.blob_path, e.meta_json, e.created_at
        FROM card_evidence ce
        JOIN evidence e ON e.id = ce.evidence_id
        WHERE ce.card_id IN ({placeholders})
        ORDER BY e.created_at ASC, e.id ASC
        """,
        tuple(card_ids),
    ).fetchall()
    out: dict[str, list[dict[str, Any]]] = {card_id: [] for card_id in card_ids}
    for row in rows:
        out.setdefault(str(row["card_id"]), []).append(
            {
                "source_system": "muninn_v1",
                "source_table": "evidence",
                "card_id": str(row["card_id"]),
                "id": str(row["id"]),
                "type": str(row["type"]),
                "ref": None if row["ref"] is None else str(row["ref"]),
                "excerpt": None if row["excerpt"] is None else str(row["excerpt"]),
                "blob_path": None if row["blob_path"] is None else str(row["blob_path"]),
                "metadata": _json_dict(row["meta_json"]),
                "created_at": str(row["created_at"]),
            }
        )
    return out


def _load_v1_card_sources(
    conn: sqlite3.Connection,
    card_ids: Sequence[str],
) -> dict[str, dict[str, Any]]:
    if not card_ids:
        return {}
    placeholders = ", ".join(["?"] * len(card_ids))
    rows = conn.execute(
        f"""
        SELECT c.id, s.key AS space_key, c.kind, c.status, c.salience, c.title, c.summary,
               c.body, c.source_confidence, c.context_json, c.created_at, c.updated_at
        FROM cards c
        JOIN spaces s ON s.id = c.space_id
        WHERE c.id IN ({placeholders})
        """,
        tuple(card_ids),
    ).fetchall()
    tags_by_card = _load_v1_tags_by_card_ids(conn, card_ids)
    evidence_by_card = _load_v1_evidence_by_card_ids(conn, card_ids)
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        card_id = str(row["id"])
        out[card_id] = {
            "source_system": "muninn_v1",
            "source_table": "cards",
            "id": card_id,
            "scope_key": str(row["space_key"]),
            "kind": str(row["kind"]),
            "status": str(row["status"]),
            "salience": float(row["salience"] or 0.0),
            "title": str(row["title"]),
            "summary": str(row["summary"]),
            "body": str(row["body"] or ""),
            "source_confidence": float(row["source_confidence"] or 0.5),
            "context": _json_dict(row["context_json"]),
            "tags": tags_by_card.get(card_id, []),
            "evidence": evidence_by_card.get(card_id, []),
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
        }
    return out


def _load_v1_association_sources(
    conn: sqlite3.Connection,
    *,
    space_key: str,
    limit: int | None,
) -> list[dict[str, Any]]:
    if not _table_exists(conn, "card_relations"):
        return []
    sql = """
        SELECT cr.from_card_id, cr.to_card_id, cr.relation_type, cr.created_at
        FROM card_relations cr
        JOIN cards from_card ON from_card.id = cr.from_card_id
        JOIN cards to_card ON to_card.id = cr.to_card_id
        JOIN spaces s ON s.id = from_card.space_id AND s.id = to_card.space_id
        WHERE s.key = ?
        ORDER BY cr.created_at DESC, cr.from_card_id ASC, cr.to_card_id ASC
    """
    params: list[Any] = [space_key]
    if limit is not None:
        sql += " LIMIT ?"
        params.append(max(1, int(limit)))
    rows = conn.execute(sql, tuple(params)).fetchall()
    return [
        {
            "source_system": "muninn_v1",
            "source_table": "card_relations",
            "from_card_id": str(row["from_card_id"]),
            "to_card_id": str(row["to_card_id"]),
            "relation_type": str(row["relation_type"]),
            "created_at": str(row["created_at"]),
        }
        for row in rows
    ]


def _space_source_payload(
    *,
    space_row: sqlite3.Row,
    card_sources: dict[str, dict[str, Any]],
    identity: dict[str, Any],
) -> dict[str, Any]:
    return {
        "source_system": "muninn_v1",
        "source_table": "spaces",
        "id": str(space_row["id"]),
        "user_id": str(space_row["user_id"]),
        "key": str(space_row["key"]),
        "label": str(space_row["label"] or ""),
        "metadata": _json_dict(space_row["meta_json"]),
        "card_kinds": sorted({str(card["kind"]) for card in card_sources.values()}),
        "project_identity": dict(identity),
        "created_at": str(space_row["created_at"] or ""),
        "updated_at": str(space_row["updated_at"] or ""),
    }


def _evidence_sources_by_id(
    card_sources: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for card in card_sources.values():
        for evidence in card.get("evidence", []):
            out.setdefault(str(evidence["id"]), dict(evidence))
    return out


def _bool_checks_status(field_checks: dict[str, bool]) -> str:
    return "ok" if all(field_checks.values()) else "failed"


def _card_fidelity(
    *,
    source: dict[str, Any],
    target: MemoryCard,
) -> dict[str, Any]:
    target_payload = target.to_dict()
    target_evidence = target_payload["evidence"]
    source_evidence = source.get("evidence", [])
    source_context = dict(source.get("context") or {})
    target_metadata = dict(target_payload.get("metadata") or {})
    field_checks = {
        "id": source["id"] == target_payload["id"],
        "kind": source["kind"] == target_payload["kind"],
        "title": source["title"] == target_payload["title"],
        "summary": source["summary"] == target_payload["summary"],
        "body": source["body"] == target_payload["body"],
        "status": source["status"] == target_payload["status"],
        "scope_key": source["scope_key"] == target_payload["scope_key"],
        "confidence": abs(float(source["source_confidence"]) - float(target_payload["confidence"])) < 1e-9,
        "tags": sorted(source.get("tags", [])) == sorted(target_payload.get("tags", [])),
        "evidence_ids": sorted(str(item["id"]) for item in source_evidence)
        == sorted(str(item["id"]) for item in target_evidence),
        "source_metadata": target_metadata.get("source_system") == "muninn_v1"
        and target_metadata.get("source_table") == "cards",
        "salience_metadata": abs(float(target_metadata.get("v1_salience", 0.0)) - float(source["salience"])) < 1e-9,
        "context_metadata": all(target_metadata.get(key) == value for key, value in source_context.items()),
    }
    return {
        "record_type": "card_fidelity",
        "source_id": source["id"],
        "target_id": target.id,
        "status": _bool_checks_status(field_checks),
        "field_checks": field_checks,
        "source_checksum": _checksum_payload(source),
        "target_checksum": _checksum_payload(target_payload),
        "expected_target_additions": ["entity_ids", "metadata.project_entity_id", "metadata.project_path"],
    }


def _evidence_fidelity(
    *,
    source: dict[str, Any],
    target: EvidenceRef,
) -> dict[str, Any]:
    target_payload = target.to_dict()
    target_metadata = dict(target_payload.get("metadata") or {})
    source_metadata = dict(source.get("metadata") or {})
    field_checks = {
        "id": source["id"] == target_payload["id"],
        "type": source["type"] == target_payload["evidence_type"],
        "ref": source.get("ref") == target_payload.get("ref"),
        "excerpt": source.get("excerpt") == target_payload.get("excerpt"),
        "created_at": source["created_at"] == target_payload["created_at"],
        "source_metadata": target_metadata.get("source_system") == "muninn_v1",
        "metadata_subset": all(target_metadata.get(key) == value for key, value in source_metadata.items()),
    }
    return {
        "record_type": "evidence_fidelity",
        "source_id": source["id"],
        "target_id": target.id,
        "status": _bool_checks_status(field_checks),
        "field_checks": field_checks,
        "source_checksum": _checksum_payload(source),
        "target_checksum": _checksum_payload(target_payload),
    }


def _association_fidelity(
    *,
    source: dict[str, Any],
    target: MemoryAssociation,
) -> dict[str, Any]:
    target_payload = target.to_dict()
    expected_id = f"v1-relation:{source['from_card_id']}:{source['relation_type']}:{source['to_card_id']}"
    field_checks = {
        "id": expected_id == target_payload["id"],
        "source_id": source["from_card_id"] == target_payload["source_id"],
        "target_id": source["to_card_id"] == target_payload["target_id"],
        "association_type": source["relation_type"] == target_payload["association_type"],
        "created_at": source["created_at"] == target_payload["created_at"],
        "source_metadata": target_payload["metadata"].get("source_system") == "muninn_v1",
    }
    return {
        "record_type": "association_fidelity",
        "source_id": expected_id,
        "target_id": target.id,
        "status": _bool_checks_status(field_checks),
        "field_checks": field_checks,
        "source_checksum": _checksum_payload(source),
        "target_checksum": _checksum_payload(target_payload),
    }


def _profile_fidelity(
    *,
    source: dict[str, Any],
    target: OntologyProfile,
) -> dict[str, Any]:
    target_payload = target.to_dict()
    metadata = dict(target_payload.get("metadata") or {})
    field_checks = {
        "space_key": source["key"] == metadata.get("space_key"),
        "space_label": source["label"] == metadata.get("space_label"),
        "card_kinds": sorted(source["card_kinds"]) == sorted(target_payload["card_kinds"]),
        "source_metadata": metadata.get("source_system") == "muninn_v1",
    }
    return {
        "record_type": "ontology_profile_fidelity",
        "source_id": source["id"],
        "target_id": target.id,
        "status": _bool_checks_status(field_checks),
        "field_checks": field_checks,
        "source_checksum": _checksum_payload(source),
        "target_checksum": _checksum_payload(target_payload),
    }


def _entity_fidelity(
    *,
    source: dict[str, Any],
    target: MemoryEntity,
) -> dict[str, Any]:
    target_payload = target.to_dict()
    properties = dict(target_payload.get("properties") or {})
    v1_space = dict(properties.get("v1_space") or {})
    identity = dict(source.get("project_identity") or {})
    field_checks = {
        "space_key": source["key"] == properties.get("space_key"),
        "project_path": identity.get("project_path") == properties.get("project_path"),
        "root_path": identity.get("root_path") == properties.get("root_path"),
        "v1_space_key": source["key"] == v1_space.get("key"),
        "source_provenance": target_payload["provenance"].get("source_system") == "muninn_v1",
    }
    return {
        "record_type": "entity_fidelity",
        "source_id": source["id"],
        "target_id": target.id,
        "status": _bool_checks_status(field_checks),
        "field_checks": field_checks,
        "source_checksum": _checksum_payload(source),
        "target_checksum": _checksum_payload(target_payload),
    }


def _build_fidelity_report(
    *,
    source_cards: dict[str, dict[str, Any]],
    source_associations: list[dict[str, Any]],
    source_space: dict[str, Any],
    cards: list[MemoryCard],
    evidence_refs: list[EvidenceRef],
    associations: list[MemoryAssociation],
    profiles: list[OntologyProfile],
    entities: list[MemoryEntity],
) -> dict[str, Any]:
    evidence_sources = _evidence_sources_by_id(source_cards)
    association_sources_by_id = {
        f"v1-relation:{source['from_card_id']}:{source['relation_type']}:{source['to_card_id']}": source
        for source in source_associations
    }
    card_checks = [
        _card_fidelity(source=source_cards[card.id], target=card)
        for card in cards
        if card.id in source_cards
    ]
    evidence_checks = [
        _evidence_fidelity(source=evidence_sources[evidence.id], target=evidence)
        for evidence in evidence_refs
        if evidence.id in evidence_sources
    ]
    association_checks = [
        _association_fidelity(source=association_sources_by_id[association.id], target=association)
        for association in associations
        if association.id in association_sources_by_id
    ]
    profile_checks = [_profile_fidelity(source=source_space, target=profile) for profile in profiles]
    entity_checks = [_entity_fidelity(source=source_space, target=entity) for entity in entities]
    all_checks = [*card_checks, *evidence_checks, *association_checks, *profile_checks, *entity_checks]
    failures = [item for item in all_checks if item["status"] != "ok"]
    summary = {
        "fidelity_passed": not failures,
        "records_checked": len(all_checks),
        "failures": len(failures),
        "cards_checked": len(card_checks),
        "cards_passed": sum(1 for item in card_checks if item["status"] == "ok"),
        "evidence_refs_checked": len(evidence_checks),
        "evidence_refs_passed": sum(1 for item in evidence_checks if item["status"] == "ok"),
        "associations_checked": len(association_checks),
        "associations_passed": sum(1 for item in association_checks if item["status"] == "ok"),
        "ontology_profiles_checked": len(profile_checks),
        "entities_checked": len(entity_checks),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "muninn_v2_record_fidelity_report",
        "summary": summary,
        "cards": card_checks,
        "evidence_refs": evidence_checks,
        "associations": association_checks,
        "ontology_profiles": profile_checks,
        "entities": entity_checks,
        "failures": failures,
    }


def _build_migration_ledger(
    *,
    source_cards: dict[str, dict[str, Any]],
    source_associations: list[dict[str, Any]],
    source_space: dict[str, Any],
    cards: list[MemoryCard],
    evidence_refs: list[EvidenceRef],
    associations: list[MemoryAssociation],
    profiles: list[OntologyProfile],
    entities: list[MemoryEntity],
    fidelity_report: dict[str, Any],
) -> list[dict[str, Any]]:
    fidelity_by_target = {
        str(item["target_id"]): item
        for group_name in ("cards", "evidence_refs", "associations", "ontology_profiles", "entities")
        for item in fidelity_report.get(group_name, [])
    }
    evidence_sources = _evidence_sources_by_id(source_cards)
    association_sources_by_id = {
        f"v1-relation:{source['from_card_id']}:{source['relation_type']}:{source['to_card_id']}": source
        for source in source_associations
    }
    entries: list[dict[str, Any]] = []

    def add(
        *,
        source_table: str,
        source_id: str,
        source_payload: dict[str, Any],
        target_record_type: str,
        target_payload: dict[str, Any],
    ) -> None:
        fidelity = fidelity_by_target.get(str(target_payload["id"]), {})
        entries.append(
            {
                "schema_version": SCHEMA_VERSION,
                "record_type": "muninn_v2_migration_ledger_entry",
                "sequence": len(entries) + 1,
                "source_system": "muninn_v1",
                "source_table": source_table,
                "source_id": source_id,
                "target_system": "muninn_v2",
                "target_record_type": target_record_type,
                "target_id": str(target_payload["id"]),
                "source_checksum": _checksum_payload(source_payload),
                "target_checksum": _checksum_payload(target_payload),
                "fidelity_status": str(fidelity.get("status") or "not_checked"),
                "fidelity_failure_count": sum(
                    1 for ok in dict(fidelity.get("field_checks") or {}).values() if not ok
                ),
            }
        )

    for profile in profiles:
        add(
            source_table="spaces",
            source_id=source_space["id"],
            source_payload=source_space,
            target_record_type=profile.record_type,
            target_payload=profile.to_dict(),
        )
    for entity in entities:
        add(
            source_table="spaces",
            source_id=source_space["id"],
            source_payload=source_space,
            target_record_type=entity.record_type,
            target_payload=entity.to_dict(),
        )
    for card in cards:
        source = source_cards.get(card.id, {})
        add(
            source_table="cards",
            source_id=card.id,
            source_payload=source,
            target_record_type=card.record_type,
            target_payload=card.to_dict(),
        )
    for evidence in evidence_refs:
        source = evidence_sources.get(evidence.id, {})
        add(
            source_table="evidence",
            source_id=evidence.id,
            source_payload=source,
            target_record_type=evidence.record_type,
            target_payload=evidence.to_dict(),
        )
    for association in associations:
        source = association_sources_by_id.get(association.id, {})
        add(
            source_table="card_relations",
            source_id=association.id,
            source_payload=source,
            target_record_type=association.record_type,
            target_payload=association.to_dict(),
        )
    return entries


def _build_checksums(
    *,
    source_cards: dict[str, dict[str, Any]],
    source_associations: list[dict[str, Any]],
    source_space: dict[str, Any],
    cards: list[MemoryCard],
    evidence_refs: list[EvidenceRef],
    associations: list[MemoryAssociation],
    profiles: list[OntologyProfile],
    entities: list[MemoryEntity],
    bundle: dict[str, Any],
    ledger: list[dict[str, Any]],
    fidelity_report: dict[str, Any],
) -> dict[str, Any]:
    source_evidence = _evidence_sources_by_id(source_cards)
    source_payload = {
        "space": source_space,
        "cards": _sorted_payloads(list(source_cards.values())),
        "evidence_refs": _sorted_payloads(list(source_evidence.values())),
        "associations": _sorted_payloads(source_associations),
    }
    target_payload = {
        "ontology_profiles": _sorted_payloads([item.to_dict() for item in profiles]),
        "entities": _sorted_payloads([item.to_dict() for item in entities]),
        "cards": _sorted_payloads([item.to_dict() for item in cards]),
        "evidence_refs": _sorted_payloads([item.to_dict() for item in evidence_refs]),
        "associations": _sorted_payloads([item.to_dict() for item in associations]),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "muninn_v2_migration_checksums",
        "algorithm": "sha256",
        "canonicalization": "json.dumps(sort_keys=True,separators=(',',':'),ensure_ascii=True)",
        "source": {
            "aggregate": _checksum_payload(source_payload),
            "space": _checksum_payload(source_space),
            "cards": _checksum_payload(source_payload["cards"]),
            "evidence_refs": _checksum_payload(source_payload["evidence_refs"]),
            "associations": _checksum_payload(source_payload["associations"]),
        },
        "target": {
            "aggregate": _checksum_payload(target_payload),
            "ontology_profiles": _checksum_payload(target_payload["ontology_profiles"]),
            "entities": _checksum_payload(target_payload["entities"]),
            "cards": _checksum_payload(target_payload["cards"]),
            "evidence_refs": _checksum_payload(target_payload["evidence_refs"]),
            "associations": _checksum_payload(target_payload["associations"]),
            "bundle": _checksum_payload(bundle),
        },
        "ledger": {
            "entries": len(ledger),
            "checksum": _checksum_payload(ledger),
        },
        "fidelity_report": {
            "records_checked": fidelity_report["summary"]["records_checked"],
            "failures": fidelity_report["summary"]["failures"],
            "checksum": _checksum_payload(fidelity_report),
        },
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")


def _sqlite_sidecar_paths(db_path: Path) -> list[Path]:
    return [db_path, Path(f"{db_path}-wal"), Path(f"{db_path}-shm")]


def _remove_scratch_db(db_path: Path) -> None:
    for path in _sqlite_sidecar_paths(db_path):
        if path.exists():
            path.unlink()


def _write_records_to_store(
    *,
    store_path: Path,
    profiles: list[OntologyProfile],
    entities: list[MemoryEntity],
    cards: list[MemoryCard],
    associations: list[MemoryAssociation],
    events: list[MemoryEvent],
) -> SQLiteMemoryStore:
    store = SQLiteMemoryStore(store_path)
    store.initialize()
    for profile in profiles:
        store.create_ontology_profile(profile)
    for entity in entities:
        store.create_entity(entity)
    for card in cards:
        store.create_card(card)
    for association in associations:
        store.create_association(association)
    for event in events:
        store.create_event(event)
    return store


def _write_pilot_markdown(path: Path, report: dict[str, Any]) -> None:
    counts = report["counts"]
    fidelity = report.get("record_fidelity", {}).get("summary", {})
    row_count_changed = "yes" if report["v1_row_counts_changed"] else "no"
    lines = [
        "# Muninn v2 Pilot Import Report",
        "",
        f"- Mode: `{report['mode']}`",
        f"- v1 DB: `{report['v1_db']}`",
        f"- Requested v2 DB: `{report['v2_db_requested']}`",
        f"- Written v2 DB: `{report['v2_db_written']}`",
        f"- Space key: `{report['space_key_canonical']}`",
        f"- Project path: `{report['project_path']}`",
        f"- v1 row counts changed: `{row_count_changed}`",
        "",
        "## Counts",
        "",
        f"- Scanned cards: {counts['scanned_cards']}",
        f"- Migrated cards: {counts['migrated_cards']}",
        f"- Evidence refs: {counts['migrated_evidence_refs']}",
        f"- Associations: {counts['migrated_associations']}",
        f"- Entities: {counts['created_entities']}",
        f"- Ontology profiles: {counts['created_ontology_profiles']}",
        f"- Unsupported records: {counts['skipped_records']}",
        f"- Ledger entries: {counts.get('ledger_entries', 0)}",
        f"- Fidelity records checked: {fidelity.get('records_checked', 0)}",
        f"- Fidelity failures: {fidelity.get('failures', 0)}",
        "",
        "## Safety",
        "",
        "The v1 database was opened using SQLite read-only mode and `PRAGMA query_only=ON`.",
        "The requested v2 DB is written only when `--write-v2` is passed.",
        "",
        "## Unsupported Records",
        "",
    ]
    for item in report["unsupported_records"]["unsupported_record_types"]:
        lines.append(
            f"- `{item['record_type']}`: {item['count']} "
            f"(present={str(item['table_present']).lower()})"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _artifact_paths(out_dir: Path) -> dict[str, str]:
    return {
        "pilot_import_report_md": str(out_dir / "pilot_import_report.md"),
        "pilot_import_report_json": str(out_dir / "pilot_import_report.json"),
        "v1_row_count_before_after": str(out_dir / "v1_row_count_before_after.json"),
        "unsupported_records": str(out_dir / "unsupported_records.json"),
        "ambiguous_records": str(out_dir / "ambiguous_records.json"),
        "migrated_cards": str(out_dir / "migrated_cards.jsonl"),
        "migrated_events": str(out_dir / "migrated_events.jsonl"),
        "migrated_entities": str(out_dir / "migrated_entities.jsonl"),
        "migrated_associations": str(out_dir / "migrated_associations.jsonl"),
        "evidence_refs": str(out_dir / "evidence_refs.jsonl"),
        "ontology_profile": str(out_dir / "ontology_profile.json"),
        "v2_export_bundle": str(out_dir / "v2_export_bundle.json"),
        "v2_export_jsonl": str(out_dir / "v2_export_bundle.jsonl"),
        "migration_ledger": str(out_dir / "migration_ledger.jsonl"),
        "migration_checksums": str(out_dir / "migration_checksums.json"),
        "record_fidelity_report_json": str(out_dir / "record_fidelity_report.json"),
        "record_fidelity_report_md": str(out_dir / "record_fidelity_report.md"),
    }


def _write_fidelity_markdown(path: Path, fidelity_report: dict[str, Any]) -> None:
    summary = fidelity_report["summary"]
    lines = [
        "# Muninn v2 Record Fidelity Report",
        "",
        f"- Fidelity passed: `{str(summary['fidelity_passed']).lower()}`",
        f"- Records checked: {summary['records_checked']}",
        f"- Failures: {summary['failures']}",
        f"- Cards checked: {summary['cards_checked']}",
        f"- Evidence refs checked: {summary['evidence_refs_checked']}",
        f"- Associations checked: {summary['associations_checked']}",
        f"- Ontology profiles checked: {summary['ontology_profiles_checked']}",
        f"- Entities checked: {summary['entities_checked']}",
        "",
        "## Failures",
        "",
    ]
    failures = list(fidelity_report.get("failures") or [])
    if not failures:
        lines.append("No fidelity failures.")
    else:
        for item in failures:
            failed_fields = [
                field_name
                for field_name, ok in dict(item.get("field_checks") or {}).items()
                if not ok
            ]
            lines.append(
                f"- `{item['record_type']}` source `{item['source_id']}` "
                f"target `{item['target_id']}` failed fields: {', '.join(failed_fields)}"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _recall_artifact_paths(out_dir: Path) -> dict[str, str]:
    return {
        "recall_parity_report_md": str(out_dir / "recall_parity_report.md"),
        "recall_parity_report_json": str(out_dir / "recall_parity_report.json"),
        "recall_parity_results": str(out_dir / "recall_parity_results.jsonl"),
        "missing_from_v2": str(out_dir / "missing_from_v2.json"),
        "extra_from_v2": str(out_dir / "extra_from_v2.json"),
        "ranking_deltas": str(out_dir / "ranking_deltas.json"),
        "evidence_parity_report": str(out_dir / "evidence_parity_report.json"),
        "readyplayer1_recall_queries": str(out_dir / "readyplayer1_recall_queries.json"),
    }


def _load_recall_queries(*, query_values: Sequence[str] | None, query_file: str | None) -> list[str]:
    queries: list[str] = []
    for raw in query_values or []:
        text = str(raw or "").strip()
        if text:
            queries.append(text)
    if query_file:
        path = Path(query_file).expanduser()
        if not path.exists():
            raise RecallParityError(f"query_file_not_found:{path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RecallParityError(f"query_file_invalid_json:{path}:{exc}") from exc
        raw_queries: Any
        if isinstance(payload, list):
            raw_queries = payload
        elif isinstance(payload, dict):
            raw_queries = payload.get("queries")
        else:
            raise RecallParityError(f"query_file_invalid_shape:{path}")
        if not isinstance(raw_queries, list):
            raise RecallParityError(f"query_file_missing_queries:{path}")
        for item in raw_queries:
            if isinstance(item, dict):
                text = str(item.get("query") or item.get("text") or "").strip()
            else:
                text = str(item or "").strip()
            if text:
                queries.append(text)
    deduped: list[str] = []
    seen: set[str] = set()
    for query in queries:
        if query in seen:
            continue
        seen.add(query)
        deduped.append(query)
    if not deduped:
        raise RecallParityError("recall_query_set_empty")
    return deduped


def _recall_tokens(text: str) -> list[str]:
    return _RECALL_TOKEN_RE.findall(str(text or "").lower())


def _result_payload(
    *,
    card_id: str,
    rank: int,
    score: float | None,
    title: str,
    summary: str,
    kind: str,
    evidence_count: int,
    source: str,
    body: str = "",
    explanation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "id": card_id,
        "rank": rank,
        "score": score,
        "title": title,
        "summary": summary,
        "kind": kind,
        "evidence_count": evidence_count,
        "source": source,
    }
    if body:
        payload["body"] = body
    if explanation is not None:
        payload["explanation"] = explanation
    return payload


def _v1_recall(
    *,
    conn: sqlite3.Connection,
    space_key: str,
    query: str,
    limit: int,
    include_evidence: bool,
    include_explanations: bool,
) -> tuple[list[dict[str, Any]], list[str]]:
    notes = [
        "v1 retrieval path: muninn.human_memory.cards.cards_search using FTS5 bm25; lower score is better."
    ]
    try:
        rows = cards_search(
            conn,
            user_id=DEFAULT_USER_ID,
            space_key=space_key,
            query=query,
            limit=limit,
            include_body=True,
            include_context=True,
        )
    except ValueError as exc:
        return [], [*notes, f"v1 query rejected by existing search normalizer: {exc}"]

    evidence_by_card: dict[str, list[dict[str, Any]]] = {}
    if include_evidence:
        evidence_by_card = _load_v1_evidence_by_card_ids(conn, [str(row["id"]) for row in rows])
    results: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        card_id = str(row["id"])
        evidence_count = int(row.get("evidence_count") or len(evidence_by_card.get(card_id, [])))
        explanation = None
        if include_explanations:
            explanation = {
                "retrieval_path": "v1_fts_cards_search",
                "score_semantics": "bm25 lower-is-better",
                "has_evidence": bool(row.get("has_evidence")),
            }
        item = _result_payload(
            card_id=card_id,
            rank=index,
            score=(None if row.get("score") is None else float(row["score"])),
            title=str(row["title"]),
            summary=str(row["summary"]),
            kind=str(row["kind"]),
            evidence_count=evidence_count,
            source="v1",
            body=str(row.get("body") or ""),
            explanation=explanation,
        )
        if include_evidence:
            item["evidence"] = evidence_by_card.get(card_id, [])
        results.append(item)
    return results, notes


def _load_v2_cards_readonly(conn: sqlite3.Connection, *, space_key: str) -> list[MemoryCard]:
    if not _table_exists(conn, "v2_cards"):
        raise RecallParityError("v2_cards_table_missing")
    rows = conn.execute(
        """
        SELECT record_json
        FROM v2_cards
        WHERE scope_key = ?
        ORDER BY updated_at DESC, id ASC
        """,
        (space_key,),
    ).fetchall()
    return [MemoryCard.from_dict(json.loads(str(row["record_json"]))) for row in rows]


def _score_v2_card(card: MemoryCard, query: str) -> tuple[float, dict[str, Any]]:
    tokens = _recall_tokens(query)
    title = card.title.lower()
    summary = card.summary.lower()
    body = card.body.lower()
    tags = " ".join(card.tags).lower()
    evidence_text = " ".join(
        " ".join(str(part or "") for part in (evidence.ref, evidence.excerpt))
        for evidence in card.evidence
    ).lower()
    combined = " ".join([title, summary, body, tags, evidence_text])
    matched_tokens = sorted({token for token in tokens if token in combined})
    score = 0.0
    field_hits: dict[str, list[str]] = {}
    weights = {
        "title": (title, 5.0),
        "summary": (summary, 3.0),
        "body": (body, 1.0),
        "tags": (tags, 2.0),
        "evidence": (evidence_text, 1.0),
    }
    for field_name, (text, weight) in weights.items():
        hits = [token for token in tokens if token in text]
        if hits:
            field_hits[field_name] = sorted(set(hits))
            score += weight * len(set(hits))
    normalized_query = " ".join(tokens)
    phrase_hit = bool(normalized_query and normalized_query in combined)
    if phrase_hit:
        score += 10.0
    return score, {
        "retrieval_path": "v2_provisional_lexical_card_match",
        "score_semantics": "higher-is-better weighted token/phrase match",
        "matched_tokens": matched_tokens,
        "field_hits": field_hits,
        "phrase_hit": phrase_hit,
        "provisional": True,
    }


def _v2_recall(
    *,
    conn: sqlite3.Connection,
    space_key: str,
    query: str,
    limit: int,
    include_evidence: bool,
    include_explanations: bool,
) -> tuple[list[dict[str, Any]], list[str]]:
    cards = _load_v2_cards_readonly(conn, space_key=space_key)
    scored: list[tuple[float, dict[str, Any], MemoryCard]] = []
    for card in cards:
        score, explanation = _score_v2_card(card, query)
        if score <= 0:
            continue
        scored.append((score, explanation, card))
    scored.sort(key=lambda item: (-item[0], item[2].updated_at, item[2].id))
    results: list[dict[str, Any]] = []
    for index, (score, explanation, card) in enumerate(scored[: max(1, int(limit))], start=1):
        item = _result_payload(
            card_id=card.id,
            rank=index,
            score=score,
            title=card.title,
            summary=card.summary,
            kind=card.kind,
            evidence_count=len(card.evidence),
            source="v2",
            body=card.body,
            explanation=(explanation if include_explanations else None),
        )
        if include_evidence:
            item["evidence"] = [evidence.to_dict() for evidence in card.evidence]
        results.append(item)
    return results, [
        "v2 retrieval path: provisional lexical matcher over v2 MemoryCard title, summary, body, tags, and evidence text; higher score is better.",
        "v2 retrieval is measurement-only and not a live recall engine.",
    ]


def _compare_recall_result(
    *,
    query: str,
    v1_results: list[dict[str, Any]],
    v2_results: list[dict[str, Any]],
    include_ranking: bool,
    include_evidence: bool,
    notes: list[str],
) -> dict[str, Any]:
    v1_ids = [str(item["id"]) for item in v1_results]
    v2_ids = [str(item["id"]) for item in v2_results]
    v1_set = set(v1_ids)
    v2_set = set(v2_ids)
    overlap_ids = [card_id for card_id in v1_ids if card_id in v2_set]
    union_count = len(v1_set | v2_set)
    overlap_ratio = 1.0 if union_count == 0 else len(set(overlap_ids)) / union_count
    v1_rank = {card_id: index for index, card_id in enumerate(v1_ids, start=1)}
    v2_rank = {card_id: index for index, card_id in enumerate(v2_ids, start=1)}
    ranking_deltas = []
    if include_ranking:
        for card_id in overlap_ids:
            ranking_deltas.append(
                {
                    "query": query,
                    "card_id": card_id,
                    "v1_rank": v1_rank[card_id],
                    "v2_rank": v2_rank[card_id],
                    "rank_delta_v2_minus_v1": v2_rank[card_id] - v1_rank[card_id],
                }
            )
    v1_by_id = {str(item["id"]): item for item in v1_results}
    v2_by_id = {str(item["id"]): item for item in v2_results}
    evidence_checks = []
    if include_evidence:
        for card_id in overlap_ids:
            v1_count = int(v1_by_id[card_id].get("evidence_count") or 0)
            v2_count = int(v2_by_id[card_id].get("evidence_count") or 0)
            evidence_checks.append(
                {
                    "query": query,
                    "card_id": card_id,
                    "v1_evidence_count": v1_count,
                    "v2_evidence_count": v2_count,
                    "status": "ok" if v1_count == v2_count else "count_mismatch",
                }
            )
        for card_id in sorted(v1_set - v2_set):
            evidence_checks.append(
                {
                    "query": query,
                    "card_id": card_id,
                    "v1_evidence_count": int(v1_by_id[card_id].get("evidence_count") or 0),
                    "v2_evidence_count": None,
                    "status": "missing_from_v2",
                }
            )
        for card_id in sorted(v2_set - v1_set):
            evidence_checks.append(
                {
                    "query": query,
                    "card_id": card_id,
                    "v1_evidence_count": None,
                    "v2_evidence_count": int(v2_by_id[card_id].get("evidence_count") or 0),
                    "status": "extra_from_v2",
                }
            )
    return {
        "query": query,
        "v1_result_count": len(v1_results),
        "v2_result_count": len(v2_results),
        "matched_card_ids": overlap_ids,
        "overlap_count": len(set(overlap_ids)),
        "overlap_ratio": overlap_ratio,
        "missing_from_v2": [v1_by_id[card_id] for card_id in v1_ids if card_id not in v2_set],
        "extra_from_v2": [v2_by_id[card_id] for card_id in v2_ids if card_id not in v1_set],
        "ranking_deltas": ranking_deltas,
        "evidence_checks": evidence_checks,
        "v1_results": v1_results,
        "v2_results": v2_results,
        "explanation_notes": notes,
    }


def _aggregate_recall_parity(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    ratios = [float(item["overlap_ratio"]) for item in results]
    full = sum(1 for item in results if item["overlap_ratio"] == 1.0)
    zero = sum(1 for item in results if item["overlap_count"] == 0 and (item["v1_result_count"] or item["v2_result_count"]))
    partial = total - full - zero
    missing = sum(len(item["missing_from_v2"]) for item in results)
    extra = sum(len(item["extra_from_v2"]) for item in results)
    evidence_mismatches = sum(
        1
        for item in results
        for check in item["evidence_checks"]
        if check["status"] != "ok"
    )
    likely_causes = []
    if missing:
        likely_causes.append("v2 provisional lexical scoring differs from v1 FTS bm25 ranking/windowing")
    if extra:
        likely_causes.append("v2 provisional matcher searches evidence/body text with different weights than v1 FTS")
    if evidence_mismatches:
        likely_causes.append("some overlapping or one-sided records have evidence availability differences")
    return {
        "total_queries": total,
        "average_overlap_ratio": (sum(ratios) / total if total else 0.0),
        "queries_with_full_overlap": full,
        "queries_with_partial_overlap": max(0, partial),
        "queries_with_zero_overlap": zero,
        "total_missing_from_v2": missing,
        "total_extra_from_v2": extra,
        "evidence_mismatches": evidence_mismatches,
        "likely_causes_of_mismatch": likely_causes,
    }


def _write_recall_parity_markdown(path: Path, report: dict[str, Any]) -> None:
    aggregate = report["aggregate"]
    lines = [
        "# Muninn v2 Recall Parity Report",
        "",
        f"- Mode: `{report['mode']}`",
        f"- Space key: `{report['space_key_canonical']}`",
        f"- Query count: {aggregate['total_queries']}",
        f"- Average overlap ratio: {aggregate['average_overlap_ratio']:.4f}",
        f"- Full overlap queries: {aggregate['queries_with_full_overlap']}",
        f"- Partial overlap queries: {aggregate['queries_with_partial_overlap']}",
        f"- Zero overlap queries: {aggregate['queries_with_zero_overlap']}",
        f"- Missing from v2: {aggregate['total_missing_from_v2']}",
        f"- Extra from v2: {aggregate['total_extra_from_v2']}",
        f"- Evidence mismatches: {aggregate['evidence_mismatches']}",
        f"- v1 row counts changed: `{str(report['v1_row_counts_changed']).lower()}`",
        f"- v2 row counts changed: `{str(report['v2_row_counts_changed']).lower()}`",
        "",
        "## Query Results",
        "",
    ]
    for result in report["results"]:
        lines.extend(
            [
                f"### {result['query']}",
                "",
                f"- v1 count: {result['v1_result_count']}",
                f"- v2 count: {result['v2_result_count']}",
                f"- overlap: {result['overlap_count']}",
                f"- overlap ratio: {result['overlap_ratio']:.4f}",
                f"- missing from v2: {len(result['missing_from_v2'])}",
                f"- extra from v2: {len(result['extra_from_v2'])}",
                "",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_recall_parity(args: argparse.Namespace) -> dict[str, Any]:
    v1_db = Path(args.v1_db).expanduser()
    v2_db = Path(args.v2_db).expanduser()
    out_dir = Path(args.out_dir).expanduser()
    project_path = Path(args.project_path).expanduser()
    requested_space_key = str(args.space_key or "").strip()
    if not requested_space_key:
        raise RecallParityError("space_key_required")
    queries = _load_recall_queries(query_values=args.query, query_file=args.query_file)
    limit = max(1, int(args.limit or 10))
    out_dir.mkdir(parents=True, exist_ok=True)
    artifacts = _recall_artifact_paths(out_dir)
    identity = _project_identity(project_path)

    with _connect_v1_readonly(v1_db) as v1_conn:
        v1_counts_before = _collect_row_counts(v1_conn)
        space_row, ambiguous_records = _resolve_space_selection(
            v1_conn,
            requested_space_key=requested_space_key,
            identity=identity,
            strict=bool(args.strict),
        )
        canonical_space_key = str(space_row["key"])

    with _connect_v2_readonly(v2_db) as v2_conn:
        v2_counts_before = _collect_row_counts(v2_conn)

    results: list[dict[str, Any]] = []
    with _connect_v1_readonly(v1_db) as v1_conn, _connect_v2_readonly(v2_db) as v2_conn:
        for query in queries:
            v1_results, v1_notes = _v1_recall(
                conn=v1_conn,
                space_key=canonical_space_key,
                query=query,
                limit=limit,
                include_evidence=bool(args.include_evidence),
                include_explanations=bool(args.include_explanations),
            )
            v2_results, v2_notes = _v2_recall(
                conn=v2_conn,
                space_key=canonical_space_key,
                query=query,
                limit=limit,
                include_evidence=bool(args.include_evidence),
                include_explanations=bool(args.include_explanations),
            )
            results.append(
                _compare_recall_result(
                    query=query,
                    v1_results=v1_results,
                    v2_results=v2_results,
                    include_ranking=bool(args.include_ranking),
                    include_evidence=bool(args.include_evidence),
                    notes=[*v1_notes, *v2_notes],
                )
            )

    with _connect_v1_readonly(v1_db) as v1_conn:
        v1_counts_after = _collect_row_counts(v1_conn)
    with _connect_v2_readonly(v2_db) as v2_conn:
        v2_counts_after = _collect_row_counts(v2_conn)

    v1_row_counts = _row_count_report(v1_counts_before, v1_counts_after)
    v2_row_counts = _row_count_report(v2_counts_before, v2_counts_after)
    v1_changed = any(item["changed"] for item in v1_row_counts)
    v2_changed = any(item["changed"] for item in v2_row_counts)
    aggregate = _aggregate_recall_parity(results)
    missing_records = [
        {"query": item["query"], "records": item["missing_from_v2"]}
        for item in results
        if item["missing_from_v2"]
    ]
    extra_records = [
        {"query": item["query"], "records": item["extra_from_v2"]}
        for item in results
        if item["extra_from_v2"]
    ]
    ranking_deltas = [
        delta for item in results for delta in item["ranking_deltas"]
    ]
    evidence_checks = [
        check for item in results for check in item["evidence_checks"]
    ]
    evidence_report = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "muninn_v2_evidence_parity_report",
        "summary": {
            "checks": len(evidence_checks),
            "ok": sum(1 for item in evidence_checks if item["status"] == "ok"),
            "mismatches": sum(1 for item in evidence_checks if item["status"] != "ok"),
        },
        "checks": evidence_checks,
    }
    report = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "muninn_v2_recall_parity_report",
        "mode": "measurement_only",
        "retrieval_parity_definition": "v1 FTS cards_search compared with provisional v2 lexical MemoryCard matcher; overlap ratio is Jaccard over returned card IDs.",
        "v1_db": str(v1_db),
        "v2_db": str(v2_db),
        "out_dir": str(out_dir),
        "space_key_requested": requested_space_key,
        "space_key_canonical": canonical_space_key,
        "project_path": str(project_path.resolve()),
        "project_identity": identity,
        "limit": limit,
        "queries": queries,
        "aggregate": aggregate,
        "results": results,
        "missing_from_v2": missing_records,
        "extra_from_v2": extra_records,
        "ranking_deltas": ranking_deltas,
        "evidence_parity": evidence_report,
        "v1_row_counts": v1_row_counts,
        "v2_row_counts": v2_row_counts,
        "v1_row_counts_changed": v1_changed,
        "v2_row_counts_changed": v2_changed,
        "ambiguous_records": ambiguous_records,
        "artifacts": artifacts,
    }

    _write_json(Path(artifacts["readyplayer1_recall_queries"]), {"queries": queries})
    _write_json(Path(artifacts["recall_parity_report_json"]), report)
    _write_jsonl(Path(artifacts["recall_parity_results"]), results)
    _write_json(Path(artifacts["missing_from_v2"]), {"records": missing_records})
    _write_json(Path(artifacts["extra_from_v2"]), {"records": extra_records})
    _write_json(Path(artifacts["ranking_deltas"]), {"records": ranking_deltas})
    _write_json(Path(artifacts["evidence_parity_report"]), evidence_report)
    _write_recall_parity_markdown(Path(artifacts["recall_parity_report_md"]), report)
    if args.json_report:
        _write_json(Path(args.json_report).expanduser(), report)

    if v1_changed or v2_changed:
        raise RecallParityError(
            "recall_parity_row_counts_changed:"
            + json.dumps({"v1": v1_row_counts, "v2": v2_row_counts}, sort_keys=True)
        )
    return report


def run_pilot_import(args: argparse.Namespace) -> dict[str, Any]:
    if args.dry_run and args.write_v2:
        raise PilotSafetyError("choose either --dry-run or --write-v2, not both")

    v1_db = Path(args.v1_db).expanduser()
    v2_db = Path(args.v2_db).expanduser()
    out_dir = Path(args.out_dir).expanduser()
    project_path = Path(args.project_path).expanduser()
    requested_space_key = str(args.space_key or "").strip()
    if not requested_space_key:
        raise PilotSafetyError("space_key_required")

    dry_run = not bool(args.write_v2)
    mode = "dry_run" if dry_run else "write_v2"
    if args.write_v2 and v2_db.exists() and not args.allow_existing_v2:
        raise PilotSafetyError(f"v2_db_already_exists:{v2_db}:pass --allow-existing-v2 to reuse it")

    out_dir.mkdir(parents=True, exist_ok=True)
    identity = _project_identity(project_path)
    artifacts = _artifact_paths(out_dir)

    before_counts: dict[str, int]
    after_counts: dict[str, int]
    with _connect_v1_readonly(v1_db) as conn:
        before_counts = _collect_row_counts(conn)
        space_row, ambiguous_records = _resolve_space_selection(
            conn,
            requested_space_key=requested_space_key,
            identity=identity,
            strict=bool(args.strict),
        )
        canonical_space_key = str(space_row["key"])
        space_id = str(space_row["id"])
        unsupported_records = _collect_unsupported_records(
            conn,
            space_id=space_id,
            space_key=canonical_space_key,
        )

    reader = V1ReadAdapter(v1_db)
    cards = reader.list_cards(space_key=canonical_space_key, limit=args.limit)
    if not args.include_evidence:
        for card in cards:
            card.evidence = []
    associations = (
        reader.list_associations(space_key=canonical_space_key, limit=args.limit)
        if args.include_relations
        else []
    )
    profiles = reader.list_ontology_profiles(space_key=canonical_space_key, limit=1)
    with _connect_v1_readonly(v1_db) as conn:
        source_cards = _load_v1_card_sources(conn, [card.id for card in cards])
        source_associations = (
            _load_v1_association_sources(
                conn,
                space_key=canonical_space_key,
                limit=args.limit,
            )
            if args.include_relations
            else []
        )
        source_space = _space_source_payload(
            space_row=space_row,
            card_sources=source_cards,
            identity=identity,
        )
    project_entity = _project_entity(
        space_key=canonical_space_key,
        identity=identity,
        space_row=space_row,
    )
    entities = [project_entity]
    _attach_project_entity(cards, project_entity)
    events: list[MemoryEvent] = []
    evidence_refs = _dedupe_evidence(cards)

    scratch_db = out_dir / "scratch_v2.db"
    store_path = scratch_db if dry_run else v2_db
    if dry_run:
        _remove_scratch_db(scratch_db)
    store = _write_records_to_store(
        store_path=store_path,
        profiles=profiles,
        entities=entities,
        cards=cards,
        associations=associations,
        events=events,
    )
    bundle = store.export_bundle()
    jsonl_export = store.export_jsonl()
    fidelity_report = _build_fidelity_report(
        source_cards=source_cards,
        source_associations=source_associations,
        source_space=source_space,
        cards=cards,
        evidence_refs=evidence_refs,
        associations=associations,
        profiles=profiles,
        entities=entities,
    )
    migration_ledger = _build_migration_ledger(
        source_cards=source_cards,
        source_associations=source_associations,
        source_space=source_space,
        cards=cards,
        evidence_refs=evidence_refs,
        associations=associations,
        profiles=profiles,
        entities=entities,
        fidelity_report=fidelity_report,
    )
    migration_checksums = _build_checksums(
        source_cards=source_cards,
        source_associations=source_associations,
        source_space=source_space,
        cards=cards,
        evidence_refs=evidence_refs,
        associations=associations,
        profiles=profiles,
        entities=entities,
        bundle=bundle,
        ledger=migration_ledger,
        fidelity_report=fidelity_report,
    )

    with _connect_v1_readonly(v1_db) as conn:
        after_counts = _collect_row_counts(conn)
    row_counts = _row_count_report(before_counts, after_counts)
    row_counts_changed = any(item["changed"] for item in row_counts)

    counts = {
        "scanned_records": len(cards) + len(evidence_refs) + len(associations),
        "scanned_cards": len(cards),
        "migrated_cards": len(cards),
        "migrated_events": len(events),
        "migrated_evidence_refs": len(evidence_refs),
        "migrated_associations": len(associations),
        "created_entities": len(entities),
        "created_ontology_profiles": len(profiles),
        "skipped_records": int(unsupported_records["total_unsupported_records"]),
        "unsupported_record_types": len(
            [
                item
                for item in unsupported_records["unsupported_record_types"]
                if int(item["count"]) > 0
            ]
        ),
        "ambiguous_records": len(ambiguous_records),
        "ledger_entries": len(migration_ledger),
        "fidelity_records_checked": int(fidelity_report["summary"]["records_checked"]),
        "fidelity_failures": int(fidelity_report["summary"]["failures"]),
        "errors": 0,
    }
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "muninn_v2_pilot_import_report",
        "mode": mode,
        "dry_run": dry_run,
        "write_v2": bool(args.write_v2),
        "v1_db": str(v1_db),
        "v2_db_requested": str(v2_db),
        "v2_db_written": str(store_path),
        "out_dir": str(out_dir),
        "space_key_requested": requested_space_key,
        "space_key_canonical": canonical_space_key,
        "space": _space_row_payload(space_row),
        "project_path": str(project_path.resolve()),
        "project_identity": identity,
        "counts": counts,
        "v1_row_counts_changed": row_counts_changed,
        "v1_row_counts": row_counts,
        "unsupported_records": unsupported_records,
        "ambiguous_records": ambiguous_records,
        "migration_checksums": migration_checksums,
        "record_fidelity": fidelity_report,
        "artifacts": artifacts,
        "errors": [],
    }

    _write_json(Path(artifacts["unsupported_records"]), unsupported_records)
    _write_json(Path(artifacts["ambiguous_records"]), {"records": ambiguous_records})
    _write_json(Path(artifacts["v1_row_count_before_after"]), row_counts)
    _write_jsonl(Path(artifacts["migrated_cards"]), [card.to_dict() for card in cards])
    _write_jsonl(Path(artifacts["migrated_events"]), [event.to_dict() for event in events])
    _write_jsonl(Path(artifacts["migrated_entities"]), [entity.to_dict() for entity in entities])
    _write_jsonl(
        Path(artifacts["migrated_associations"]),
        [association.to_dict() for association in associations],
    )
    _write_jsonl(Path(artifacts["evidence_refs"]), [evidence.to_dict() for evidence in evidence_refs])
    _write_json(Path(artifacts["ontology_profile"]), {"ontology_profiles": [p.to_dict() for p in profiles]})
    _write_json(Path(artifacts["v2_export_bundle"]), bundle)
    Path(artifacts["v2_export_jsonl"]).write_text(jsonl_export, encoding="utf-8")
    _write_jsonl(Path(artifacts["migration_ledger"]), migration_ledger)
    _write_json(Path(artifacts["migration_checksums"]), migration_checksums)
    _write_json(Path(artifacts["record_fidelity_report_json"]), fidelity_report)
    _write_fidelity_markdown(Path(artifacts["record_fidelity_report_md"]), fidelity_report)
    _write_json(Path(artifacts["pilot_import_report_json"]), report)
    _write_pilot_markdown(Path(artifacts["pilot_import_report_md"]), report)
    if args.json_report:
        _write_json(Path(args.json_report).expanduser(), report)

    if row_counts_changed:
        raise PilotSafetyError("v1_row_counts_changed:" + json.dumps(row_counts, sort_keys=True))
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m muninn.v2.cli",
        description="Muninn v2 adjacent-core tooling.",
    )
    subparsers = parser.add_subparsers(dest="command")
    pilot = subparsers.add_parser(
        "pilot-import",
        help="Dry-run import one explicit v1 space into adjacent v2 artifacts.",
    )
    pilot.add_argument("--v1-db", required=True, help="Explicit Muninn v1 SQLite DB path.")
    pilot.add_argument("--v2-db", required=True, help="Explicit Muninn v2 output DB path.")
    pilot.add_argument("--space-key", required=True, help="Explicit v1 project/space key.")
    pilot.add_argument("--project-path", required=True, help="Explicit project path for identity checks.")
    pilot.add_argument("--out-dir", required=True, help="Explicit non-production output artifact directory.")
    pilot.add_argument("--dry-run", action="store_true", help="Force dry-run behavior. This is the default.")
    pilot.add_argument("--write-v2", action="store_true", help="Write to --v2-db instead of scratch DB.")
    pilot.add_argument(
        "--allow-existing-v2",
        action="store_true",
        help="Allow --write-v2 to reuse an existing explicit v2 DB.",
    )
    pilot.add_argument("--limit", type=int, default=None, help="Optional card/relation limit.")
    pilot.add_argument(
        "--include-relations",
        dest="include_relations",
        action="store_true",
        default=True,
        help="Include v1 card relations. Enabled by default.",
    )
    pilot.add_argument("--no-relations", dest="include_relations", action="store_false")
    pilot.add_argument(
        "--include-evidence",
        dest="include_evidence",
        action="store_true",
        default=True,
        help="Include v1 evidence refs. Enabled by default.",
    )
    pilot.add_argument("--no-evidence", dest="include_evidence", action="store_false")
    pilot.add_argument("--strict", action="store_true", help="Fail if project identity does not match the space.")
    pilot.add_argument("--json-report", help="Optional additional report JSON path.")
    pilot.set_defaults(func=run_pilot_import)

    parity = subparsers.add_parser(
        "recall-parity",
        help="Measure opt-in v1/v2 recall parity for one explicit space.",
    )
    parity.add_argument("--v1-db", required=True, help="Explicit Muninn v1 SQLite DB path.")
    parity.add_argument("--v2-db", required=True, help="Explicit Muninn v2 SQLite DB path.")
    parity.add_argument("--space-key", required=True, help="Explicit v1/v2 project/space key.")
    parity.add_argument("--project-path", required=True, help="Explicit project path for identity checks.")
    parity.add_argument("--out-dir", required=True, help="Explicit output artifact directory.")
    parity.add_argument("--query", action="append", default=[], help="Recall query text. Repeatable.")
    parity.add_argument("--query-file", help="JSON file containing a query list or {'queries': [...]} object.")
    parity.add_argument("--limit", type=int, default=10, help="Result limit per side per query.")
    parity.add_argument("--strict", action="store_true", help="Fail if project identity does not match the space.")
    parity.add_argument("--json-report", help="Optional additional report JSON path.")
    parity.add_argument("--include-evidence", action="store_true", help="Include evidence availability details.")
    parity.add_argument("--include-ranking", action="store_true", help="Include ranking deltas for overlapping cards.")
    parity.add_argument("--include-explanations", action="store_true", help="Include retrieval explanation notes.")
    parity.set_defaults(func=run_recall_parity)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    if not hasattr(args, "func"):
        parser.print_help(sys.stderr)
        return 2
    try:
        report = args.func(args)
    except (PilotSafetyError, RecallParityError) as exc:
        print(f"muninn.v2 command failed: {exc}", file=sys.stderr)
        return 2
    if report["record_type"] == "muninn_v2_recall_parity_report":
        payload = {
            "status": "ok",
            "mode": report["mode"],
            "space_key": report["space_key_canonical"],
            "aggregate": report["aggregate"],
            "v1_row_counts_changed": report["v1_row_counts_changed"],
            "v2_row_counts_changed": report["v2_row_counts_changed"],
            "out_dir": report["out_dir"],
        }
    else:
        payload = {
            "status": "ok",
            "mode": report["mode"],
            "space_key": report["space_key_canonical"],
            "counts": report["counts"],
            "v1_row_counts_changed": report["v1_row_counts_changed"],
            "fidelity_failures": report["record_fidelity"]["summary"]["failures"],
            "out_dir": report["out_dir"],
        }
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
