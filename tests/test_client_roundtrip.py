from __future__ import annotations

import asyncio

import httpx

from muninn import db
from muninn.api import app
from muninn.client import MuninnClient
from muninn.models import MemoryCandidate, Provenance, RehydrateRequest, WriteCandidatesRequest


class _SyncASGIClient:
    def __init__(self) -> None:
        self._async_client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        )

    def request(self, method: str, path: str, *, json=None, params=None) -> httpx.Response:
        return asyncio.run(self._async_client.request(method, path, json=json, params=params))

    def close(self) -> None:
        asyncio.run(self._async_client.aclose())


def test_muninn_client_roundtrip_with_asgi_transport(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)

    http_client = _SyncASGIClient()
    try:
        client = MuninnClient.from_httpx(http_client)
        health = client.health()
        assert "ok" in health

        candidate = MemoryCandidate(
            kind="preference",
            entity={"id": "ent_user", "kind": "user", "name": "Auston"},
            payload={"key": "style.response", "value": "direct"},
            confidence=0.9,
            provenance=Provenance(source_type="user", source_id="roundtrip_turn"),
        )

        write_out = client.write_candidates(
            WriteCandidatesRequest(namespace="default", candidates=[candidate])
        )
        assert write_out.accepted == 1
        assert write_out.rejected == 0

        rehydrate_out = client.rehydrate(
            RehydrateRequest(
                namespace="default",
                query="please be direct",
                entity_id="ent_user",
                k=8,
                profile="generic",
            )
        )
        assert len(rehydrate_out.items) >= 1
        assert len(rehydrate_out.cards) >= 1

        version_out = client.version(namespace="default", profile="generic")
        assert version_out["namespace"] == "default"
        assert isinstance(version_out["version"], str)

        debug_out = client.debug_vector_backend()
        assert "effective_backend" in debug_out
        assert "sqlite_vec_loaded" in debug_out
    finally:
        http_client.close()
