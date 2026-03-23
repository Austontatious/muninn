from __future__ import annotations

from typing import Any

import httpx

from ..models import (
    CardCreateRequest,
    CardCreateResponse,
    CardEmbeddingUpsertRequest,
    CardEmbeddingUpsertResponse,
    CardexRetrieveRequest,
    CardexRetrieveResponse,
    CardRecord,
    CleanupRequest,
    CleanupResponse,
    ConfirmCandidatesRequest,
    ConfirmCandidatesResponse,
    DecideProposalRequest,
    DecideProposalResponse,
    IngestRequest,
    IngestResponse,
    LinkCardRefsRequest,
    LinkCardRefsResponse,
    ListPendingRequest,
    ListPendingResponse,
    PromoteRequest,
    PromoteResponse,
    ProposeRequest,
    ProposeResponse,
    QueryVectorRequest,
    QueryVectorResponse,
    RehydrateRequest,
    RehydrateResponse,
    ReindexVectorsRequest,
    ReindexVectorsResponse,
    RenderCardsRequest,
    RenderCardsResponse,
    RetrieveRequest,
    RetrieveResponse,
    SourceArtifactsRequest,
    SourceArtifactsResponse,
    SourceCreateRequest,
    SourceCreateResponse,
    StageCandidatesRequest,
    StageCandidatesResponse,
    UpsertEmbeddingsRequest,
    UpsertEmbeddingsResponse,
    WriteCandidatesRequest,
    WriteCandidatesResponse,
)


class MuninnClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        timeout: float = 20.0,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._client = httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout, headers=headers)
        self._owns_client = True

    @classmethod
    def from_httpx(cls, client: Any) -> MuninnClient:
        obj = cls.__new__(cls)
        obj._client = client
        obj._owns_client = False
        return obj

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> MuninnClient:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = self._client.request(method, path, json=json_payload, params=params)
        if response.status_code >= 400:
            raise RuntimeError(
                f"Muninn request failed [{response.status_code}] {path}: {response.text}"
            )
        if not response.content:
            return {}
        return response.json()

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def create_card(self, req: CardCreateRequest) -> CardCreateResponse:
        data = self._request("POST", "/cards", json_payload=req.model_dump())
        return CardCreateResponse(**data)

    def get_card(self, card_id: str, namespace: str = "default") -> CardRecord:
        data = self._request("GET", f"/cards/{card_id}", params={"namespace": namespace})
        return CardRecord(**data)

    def create_source(self, req: SourceCreateRequest) -> SourceCreateResponse:
        data = self._request("POST", "/sources", json_payload=req.model_dump())
        return SourceCreateResponse(**data)

    def ingest(self, req: IngestRequest) -> IngestResponse:
        data = self._request("POST", "/ingest", json_payload=req.model_dump())
        return IngestResponse(**data)

    def add_source_artifacts(
        self,
        source_id: str,
        req: SourceArtifactsRequest,
    ) -> SourceArtifactsResponse:
        data = self._request(
            "POST",
            f"/sources/{source_id}/artifacts",
            json_payload=req.model_dump(),
        )
        return SourceArtifactsResponse(**data)

    def link_card_refs(self, card_id: str, req: LinkCardRefsRequest) -> LinkCardRefsResponse:
        data = self._request("POST", f"/cards/{card_id}/refs", json_payload=req.model_dump())
        return LinkCardRefsResponse(**data)

    def cardex_retrieve(self, req: CardexRetrieveRequest) -> CardexRetrieveResponse:
        data = self._request("POST", "/retrieve", json_payload=req.model_dump())
        return CardexRetrieveResponse(**data)

    def promote(self, req: PromoteRequest) -> PromoteResponse:
        data = self._request("POST", "/promote", json_payload=req.model_dump())
        return PromoteResponse(**data)

    def propose(self, req: ProposeRequest) -> ProposeResponse:
        data = self._request("POST", "/propose", json_payload=req.model_dump())
        return ProposeResponse(**data)

    def confirm_proposal(self, proposal_id: str, req: DecideProposalRequest) -> DecideProposalResponse:
        data = self._request("POST", f"/confirm/{proposal_id}", json_payload=req.model_dump())
        return DecideProposalResponse(**data)

    def reject_proposal(self, proposal_id: str, req: DecideProposalRequest) -> DecideProposalResponse:
        data = self._request("POST", f"/reject/{proposal_id}", json_payload=req.model_dump())
        return DecideProposalResponse(**data)

    def upsert_card_embedding(self, req: CardEmbeddingUpsertRequest) -> CardEmbeddingUpsertResponse:
        data = self._request("POST", "/embeddings", json_payload=req.model_dump())
        return CardEmbeddingUpsertResponse(**data)

    def write_candidates(self, req: WriteCandidatesRequest) -> WriteCandidatesResponse:
        data = self._request("POST", "/v0/memory/write_candidates", json_payload=req.model_dump())
        return WriteCandidatesResponse(**data)

    def stage_candidates(self, req: StageCandidatesRequest) -> StageCandidatesResponse:
        data = self._request("POST", "/v0/memory/stage_candidates", json_payload=req.model_dump())
        return StageCandidatesResponse(**data)

    def list_pending(self, req: ListPendingRequest) -> ListPendingResponse:
        data = self._request("POST", "/v0/memory/list_pending", json_payload=req.model_dump())
        return ListPendingResponse(**data)

    def confirm_candidates(self, req: ConfirmCandidatesRequest) -> ConfirmCandidatesResponse:
        data = self._request("POST", "/v0/memory/confirm_candidates", json_payload=req.model_dump())
        return ConfirmCandidatesResponse(**data)

    def retrieve(self, req: RetrieveRequest) -> RetrieveResponse:
        data = self._request("POST", "/v0/memory/retrieve", json_payload=req.model_dump())
        return RetrieveResponse(**data)

    def render_cards(self, req: RenderCardsRequest) -> RenderCardsResponse:
        data = self._request("POST", "/v0/memory/render_cards", json_payload=req.model_dump())
        return RenderCardsResponse(**data)

    def rehydrate(self, req: RehydrateRequest) -> RehydrateResponse:
        data = self._request("POST", "/v0/memory/rehydrate", json_payload=req.model_dump())
        return RehydrateResponse(**data)

    def upsert_embeddings(self, req: UpsertEmbeddingsRequest) -> UpsertEmbeddingsResponse:
        data = self._request("POST", "/v0/memory/upsert_embeddings", json_payload=req.model_dump())
        return UpsertEmbeddingsResponse(**data)

    def query_vector(self, req: QueryVectorRequest) -> QueryVectorResponse:
        data = self._request("POST", "/v0/memory/query_vector", json_payload=req.model_dump())
        return QueryVectorResponse(**data)

    def version(
        self,
        namespace: str = "default",
        profile: str = "generic",
        embedding_model: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"namespace": namespace, "profile": profile}
        if embedding_model is not None:
            params["embedding_model"] = embedding_model
        return self._request("GET", "/v0/memory/version", params=params)

    def debug_vector_backend(self) -> dict[str, Any]:
        return self._request("GET", "/v0/debug/vector_backend")

    def debug_stats(self, namespace: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] | None = None
        if namespace is not None:
            params = {"namespace": namespace}
        return self._request("GET", "/v0/debug/stats", params=params)

    def admin_reindex_vectors(self, req: ReindexVectorsRequest) -> ReindexVectorsResponse:
        data = self._request("POST", "/v0/admin/reindex_vectors", json_payload=req.model_dump())
        return ReindexVectorsResponse(**data)

    def admin_cleanup(self, req: CleanupRequest) -> CleanupResponse:
        data = self._request("POST", "/v0/admin/cleanup", json_payload=req.model_dump())
        return CleanupResponse(**data)
