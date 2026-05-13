from __future__ import annotations

from typing import Any

from .. import db
from ..config import audit_retention_days, cleanup_batch_limit, max_vec_scan, pending_retention_days
from ..memory import pending as pending_memory
from ..memory.cards import render_cards
from ..memory.retrieval import retrieve
from ..memory.writeback import write_candidates
from ..ops import cleanup as ops_cleanup
from ..vector import reindex as vector_reindex
from ..vector import store as vector_store


class V0Runtime:
    def write_candidates(self, namespace: str, candidates: list[Any]) -> tuple[list[str], list[str]]:
        return write_candidates(namespace, candidates)

    def stage_candidates(
        self,
        *,
        namespace: str,
        candidates: list[Any],
        ttl_seconds: int | None = None,
    ) -> tuple[list[str], list[str], list[tuple[str, str]], list[str]]:
        return pending_memory.stage_candidates(
            namespace=namespace,
            candidates=candidates,
            ttl_seconds=ttl_seconds,
        )

    def list_pending(
        self,
        *,
        namespace: str,
        entity_id: str | None,
        status: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        return pending_memory.list_pending(
            namespace=namespace,
            entity_id=entity_id,
            status=status,
            limit=limit,
        )

    def confirm_candidates(
        self,
        *,
        namespace: str,
        pending_ids: list[str],
        decision: str,
        decided_by: str,
        note: str | None,
    ):
        return pending_memory.confirm_candidates(
            namespace=namespace,
            pending_ids=pending_ids,
            decision=decision,
            decided_by=decided_by,
            note=note,
        )

    def upsert_embeddings(self, namespace: str, items: list[Any]) -> tuple[int, int, list[str]]:
        return vector_store.upsert_embeddings(namespace, items)

    def vector_backend_info(self) -> tuple[str, bool, str]:
        return vector_store.effective_backend()

    def query_vector(
        self,
        *,
        namespace: str,
        model: str,
        query_vector: list[float],
        entity_id: str | None,
        kinds: list[str] | None,
        k: int,
    ) -> list[Any]:
        return vector_store.query_vector(
            namespace=namespace,
            model=model,
            query_vec=query_vector,
            entity_id=entity_id,
            kinds=kinds,
            k=k,
            max_scan=max_vec_scan(),
        )

    def reindex_vectors(
        self,
        *,
        namespace: str,
        model: str | None,
        dim: int | None,
        batch_size: int,
        dry_run: bool,
        force_backend: str,
    ):
        return vector_reindex.reindex_vectors(
            namespace=namespace,
            model=model,
            dim=dim,
            batch_size=batch_size,
            dry_run=dry_run,
            force_backend=force_backend,
        )

    def cleanup(
        self,
        *,
        namespace: str,
        targets: list[str],
        statuses: list[str] | None,
        older_than_seconds: int | None,
        limit: int,
        dry_run: bool,
    ) -> dict[str, Any]:
        conn = db.connect()
        try:
            limit = max(1, min(limit, cleanup_batch_limit()))
            now_ts = db.now()
            base_cutoff = now_ts - older_than_seconds if older_than_seconds is not None else None
            ordered_targets: list[str] = []
            for preferred in ["decisions", "pending", "audit"]:
                if preferred in targets:
                    ordered_targets.append(preferred)
            for target in targets:
                if target not in ordered_targets:
                    ordered_targets.append(target)
            targets = ordered_targets

            deleted_pending = 0
            deleted_decisions = 0
            deleted_audit = 0
            scanned = 0
            reasons: list[str] = []

            for target in targets:
                if target == "pending":
                    pending_statuses = statuses or ["accepted", "rejected", "expired"]
                    cutoff = base_cutoff
                    if cutoff is None:
                        cutoff = now_ts - (pending_retention_days() * 24 * 60 * 60)
                    deleted, seen = ops_cleanup.cleanup_pending(
                        conn=conn,
                        namespace=namespace,
                        statuses=pending_statuses,
                        cutoff_ts=cutoff,
                        limit=limit,
                        dry_run=dry_run,
                    )
                    deleted_pending += deleted
                    scanned += seen
                    continue

                if target == "decisions":
                    cutoff = base_cutoff
                    if cutoff is None:
                        cutoff = now_ts - (pending_retention_days() * 24 * 60 * 60)
                    deleted, seen = ops_cleanup.cleanup_decisions(
                        conn=conn,
                        namespace=namespace,
                        cutoff_ts=cutoff,
                        limit=limit,
                        dry_run=dry_run,
                    )
                    deleted_decisions += deleted
                    scanned += seen
                    continue

                if target == "audit":
                    cutoff = base_cutoff
                    if cutoff is None:
                        cutoff = now_ts - (audit_retention_days() * 24 * 60 * 60)
                    deleted, seen = ops_cleanup.cleanup_audit(
                        conn=conn,
                        namespace=namespace,
                        cutoff_ts=cutoff,
                        limit=limit,
                        dry_run=dry_run,
                    )
                    deleted_audit += deleted
                    scanned += seen
                    if not dry_run:
                        reasons.append("audit_append_only")
                    continue

                reasons.append(f"unknown_target:{target}")

            return {
                "targets": targets,
                "namespace": namespace,
                "deleted_pending": deleted_pending,
                "deleted_decisions": deleted_decisions,
                "deleted_audit": deleted_audit,
                "scanned": scanned,
                "reasons": reasons,
            }
        finally:
            conn.close()

    def retrieve(self, *, namespace: str, query: str, entity_id: str | None, k: int, query_embedding, embedding_model):
        return retrieve(
            namespace=namespace,
            query=query,
            entity_id=entity_id,
            k=k,
            query_embedding=query_embedding,
            embedding_model=embedding_model,
        )

    def render_cards(self, items: list[Any], profile: str):
        return render_cards(items, profile)

    def rehydrate(
        self,
        *,
        namespace: str,
        query: str,
        entity_id: str | None,
        k: int,
        query_embedding,
        embedding_model,
        profile: str,
    ) -> dict[str, Any]:
        items = self.retrieve(
            namespace=namespace,
            query=query,
            entity_id=entity_id,
            k=k,
            query_embedding=query_embedding,
            embedding_model=embedding_model,
        )
        cards = render_cards(items, profile)
        return {"items": items, "cards": cards}
