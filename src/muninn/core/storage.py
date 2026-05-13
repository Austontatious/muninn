from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any

from ..human_memory import adaptation as human_adaptation
from ..human_memory import bootstrap as human_bootstrap
from ..human_memory import cards as human_cards
from ..human_memory import interactions as human_interactions
from ..human_memory import policy as human_policy
from ..human_memory import rehydration as human_rehydration
from ..human_memory import spaces as human_spaces
from .config import MuninnConfig, default_db_path


class HumanMemoryStore:
    def __init__(self, config: MuninnConfig) -> None:
        self._db_path = config.db_path or default_db_path()
        self._user_id = config.user_id
        self._client_name = config.client_name

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def client_name(self) -> str | None:
        return self._client_name

    @contextmanager
    def connect(self, *, correlation_id: str | None = None):
        conn = human_bootstrap.open_db(self._db_path)
        try:
            human_bootstrap.apply_init_schema(conn, correlation_id=correlation_id)
            human_bootstrap.bootstrap_defaults(conn, correlation_id=correlation_id)
            yield conn
        finally:
            conn.close()

    def ensure_space_key(self, conn, *, space_key: str | None, cwd: str | None) -> str:
        if space_key:
            resolved = human_spaces.ResolvedSpace(
                key=str(space_key),
                label=str(space_key),
                meta_json=json.dumps({"identity": "explicit_space", "space_key": space_key}, separators=(",", ":")),
            )
        elif cwd:
            resolved = human_spaces.resolve_space_from_cwd(cwd)
        else:
            resolved = human_spaces.ResolvedSpace(
                key="global",
                label="global",
                meta_json=json.dumps({"identity": "default_global"}, separators=(",", ":")),
            )
        human_spaces.get_or_create_space(conn, user_id=self._user_id, resolved=resolved)
        return human_spaces.canonicalize_space_key(conn, user_id=self._user_id, space_key=resolved.key)

    def resolve_space_keys(self, conn, *, space_key: str, scope: str) -> list[str]:
        keys = human_spaces.resolve_space_lookup_keys(conn, user_id=self._user_id, space_key=space_key)
        if scope == "soft" and "global" not in keys:
            keys.append("global")
        return keys

    def upsert_card(
        self,
        conn,
        *,
        space_key: str,
        kind: str,
        title: str,
        summary: str,
        body: str,
        status: str = "active",
        salience: float = 0.5,
        tags: list[str] | None = None,
        created_by_client_name: str | None = None,
        source_confidence: float | None = None,
        context_json: dict[str, Any] | None = None,
        card_id: str | None = None,
        evidence_refs: list[dict[str, Any]] | None = None,
        dedupe_by_fingerprint: bool = True,
    ) -> str:
        return human_cards.card_upsert(
            conn,
            user_id=self._user_id,
            space_key=space_key,
            kind=kind,
            title=title,
            summary=summary,
            body=body,
            status=status,
            salience=salience,
            tags=tags,
            created_by_client_name=created_by_client_name or self._client_name,
            source_confidence=source_confidence,
            context_json=context_json,
            card_id=card_id,
            evidence_refs=evidence_refs,
            dedupe_by_fingerprint=dedupe_by_fingerprint,
        )

    def supersede_card(
        self,
        conn,
        *,
        space_key: str,
        old_card_id: str,
        kind: str,
        title: str,
        summary: str,
        body: str,
        status: str = "active",
        salience: float = 0.5,
        tags: list[str] | None = None,
        created_by_client_name: str | None = None,
        source_confidence: float | None = None,
        context_json: dict[str, Any] | None = None,
        evidence_refs: list[dict[str, Any]] | None = None,
        relation_type: str = "supersedes",
    ) -> dict[str, Any]:
        return human_cards.card_supersede(
            conn,
            user_id=self._user_id,
            space_key=space_key,
            old_card_id=old_card_id,
            kind=kind,
            title=title,
            summary=summary,
            body=body,
            status=status,
            salience=salience,
            tags=tags,
            created_by_client_name=created_by_client_name or self._client_name,
            source_confidence=source_confidence,
            context_json=context_json,
            evidence_refs=evidence_refs,
            relation_type=relation_type,
        )

    def merge_cards(
        self,
        conn,
        *,
        space_key: str,
        card_ids: list[str],
        kind: str,
        title: str,
        summary: str,
        body: str,
        status: str = "active",
        salience: float = 0.5,
        tags: list[str] | None = None,
        created_by_client_name: str | None = None,
        source_confidence: float | None = None,
        context_json: dict[str, Any] | None = None,
        evidence_refs: list[dict[str, Any]] | None = None,
        relation_type: str = "duplicates",
    ) -> dict[str, Any]:
        return human_cards.cards_merge(
            conn,
            user_id=self._user_id,
            space_key=space_key,
            card_ids=card_ids,
            kind=kind,
            title=title,
            summary=summary,
            body=body,
            status=status,
            salience=salience,
            tags=tags,
            created_by_client_name=created_by_client_name or self._client_name,
            source_confidence=source_confidence,
            context_json=context_json,
            evidence_refs=evidence_refs,
            relation_type=relation_type,
        )

    def fetch_card(self, conn, *, card_id: str) -> dict[str, Any] | None:
        row = conn.execute(
            """
            SELECT c.id, s.key AS space_key, c.kind, c.status, c.salience, c.title,
                   c.summary, c.body, c.context_json
            FROM cards c
            JOIN spaces s ON s.id = c.space_id
            WHERE c.id = ?
            """,
            (card_id,),
        ).fetchone()
        if row is None:
            return None
        data = dict(row)
        context_json = data.get("context_json")
        if isinstance(context_json, str) and context_json.strip():
            try:
                data["context_json"] = json.loads(context_json)
            except json.JSONDecodeError:
                data["context_json"] = None
        return data

    def revoke_card(self, conn, *, card_id: str) -> None:
        conn.execute("UPDATE cards SET status = 'revoked' WHERE id = ?", (card_id,))
        conn.commit()

    def search_cards(
        self,
        conn,
        *,
        space_key: str,
        query: str,
        kinds: list[str] | None,
        limit: int,
        include_body: bool = False,
        status: str = "active",
        tags: list[str] | None = None,
        include_context: bool = True,
    ) -> list[dict[str, Any]]:
        return human_cards.cards_search(
            conn,
            user_id=self._user_id,
            space_key=space_key,
            query=query,
            kinds=kinds,
            status=status,
            tags=tags,
            limit=limit,
            include_body=include_body,
            include_context=include_context,
        )

    def recent_cards(
        self,
        conn,
        *,
        space_key: str,
        kinds: list[str] | None,
        limit: int,
        include_body: bool = False,
        status: str = "active",
        tags: list[str] | None = None,
        include_context: bool = True,
    ) -> list[dict[str, Any]]:
        return human_cards.cards_recent(
            conn,
            user_id=self._user_id,
            space_key=space_key,
            kinds=kinds,
            status=status,
            tags=tags,
            limit=limit,
            include_body=include_body,
            include_context=include_context,
        )

    def search_count(
        self,
        conn,
        *,
        space_key: str,
        query: str,
        kinds: list[str] | None,
        status: str = "active",
        tags: list[str] | None = None,
    ) -> int:
        return human_cards.cards_search_count(
            conn,
            user_id=self._user_id,
            space_key=space_key,
            query=query,
            kinds=kinds,
            status=status,
            tags=tags,
        )

    def rehydrate_legacy_bundle(
        self,
        conn,
        *,
        space_key: str,
        query: str,
        kinds: list[str] | None,
        status: str = "active",
        tags: list[str] | None = None,
        limit: int,
        scope: str,
        include_body: bool,
        include_policy: bool,
        tool_name: str | None,
        task_type: str | None,
        vector_mode: str = "off",
    ) -> dict[str, Any]:
        return human_rehydration.rehydrate_bundle(
            conn,
            user_id=self._user_id,
            space_key=space_key,
            query=query,
            kinds=kinds,
            status=status,
            tags=tags,
            limit=limit,
            scope=scope,
            include_body=include_body,
            include_policy=include_policy,
            tool_name=tool_name,
            task_type=task_type,
            vector_mode=vector_mode,
        )

    def record_event(self, conn, *, space_key: str, event: dict[str, Any]) -> str:
        return human_interactions.record_interaction_event(
            conn,
            user_id=self._user_id,
            space_key=space_key,
            event_type=event["event_type"],
            actor=event["actor"],
            summary=event["summary"],
            payload=event.get("payload"),
            signal_type=event.get("signal_type"),
            outcome_type=event.get("outcome_type"),
            scope_type=event.get("scope_type") or "project",
            scope_key=event.get("scope_key"),
            session_id=event.get("session_id"),
            created_by_client_name=self._client_name,
        )

    def learn_policy(self, conn, *, space_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        return human_policy.learn_policy_signal(
            conn,
            user_id=self._user_id,
            space_key=space_key,
            summary=payload["summary"],
            signal_type=payload["signal_type"],
            outcome=payload["outcome"],
            scope_type=payload.get("scope_type") or "project",
            scope_key=payload.get("scope_key"),
            lesson=payload.get("lesson"),
            preferred_behavior=payload.get("preferred_behavior"),
            anti_pattern=payload.get("anti_pattern"),
            confidence=payload.get("confidence"),
            tool_name=payload.get("tool_name"),
            task_type=payload.get("task_type"),
            session_id=payload.get("session_id"),
            tags=payload.get("tags"),
            evidence_refs=payload.get("evidence_refs"),
            raw_payload=payload.get("raw_payload"),
            created_by_client_name=self._client_name,
        )

    def query_policy(self, conn, *, space_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        return human_policy.query_policy_cards(
            conn,
            user_id=self._user_id,
            space_key=space_key,
            query=payload.get("query"),
            scope=payload.get("scope") or "strict",
            scope_types=payload.get("scope_types"),
            scope_key=payload.get("scope_key"),
            tool_name=payload.get("tool_name"),
            task_type=payload.get("task_type"),
            include_global=bool(payload.get("include_global", False)),
            kinds=payload.get("kinds"),
            limit=payload.get("limit", 12),
            include_body=bool(payload.get("include_body", False)),
        )

    def query_adaptation(self, conn, *, space_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        return human_adaptation.query_adaptation_cards(
            conn,
            user_id=self._user_id,
            space_key=space_key,
            subject_id=payload.get("subject_id"),
            view=payload.get("view"),
            categories=payload.get("categories"),
            memory_types=payload.get("memory_types") or payload.get("kinds"),
            persistence=payload.get("persistence"),
            scope_types=payload.get("scope_types"),
            scope_id=payload.get("scope_id"),
            source_types=payload.get("source_types"),
            session_id=payload.get("session_id"),
            tags=payload.get("tags"),
            max_age_days=payload.get("max_age_days"),
            status=payload.get("status") or "active",
            limit=payload.get("limit", 20),
            include_body=bool(payload.get("include_body", False)),
        )
