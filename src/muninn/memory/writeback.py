from __future__ import annotations

from .. import db
from ..models import MemoryCandidate
from .policy import decide_write
from .provenance import normalize_provenance


def write_candidates(
    namespace: str, candidates: list[MemoryCandidate]
) -> tuple[list[str], list[str]]:
    _ = namespace
    conn = db.connect()
    ids: list[str] = []
    reasons: list[str] = []

    for candidate in candidates:
        decision = decide_write(candidate)
        if not decision.accept:
            reasons.append(decision.reason)
            continue

        prov = normalize_provenance(candidate.provenance)
        prov_json = prov.model_dump_json()

        # Entity upsert (v0: require id or name; generate if missing).
        entity = candidate.entity
        ent_id = entity.get("id") or db.new_id("ent")
        ent_kind = entity.get("kind", "unknown")
        ent_name = entity.get("name", ent_id)

        db.execute_one(
            conn,
            "INSERT OR IGNORE INTO entities (id, kind, name, created_at) VALUES (?,?,?,?)",
            (ent_id, ent_kind, ent_name, db.now()),
        )

        if candidate.kind == "fact":
            subject_id = ent_id
            predicate = str(candidate.payload.get("predicate", "related_to"))
            obj = str(candidate.payload.get("object", ""))
            conf = float(candidate.confidence)
            existing = db.fetch_one(
                conn,
                """
                SELECT id, confidence FROM facts
                WHERE subject_id = ? AND predicate = ? AND object = ?
                LIMIT 1
                """,
                (subject_id, predicate, obj),
            )
            if existing:
                fact_id = existing["id"]
                merged_conf = max(float(existing["confidence"]), conf)
                db.execute_one(
                    conn,
                    "UPDATE facts SET confidence = ?, provenance_json = ? WHERE id = ?",
                    (merged_conf, prov_json, fact_id),
                )
                ids.append(fact_id)
                reasons.append("Accepted: fact_merged")
            else:
                fact_id = db.new_id("fact")
                db.execute_one(
                    conn,
                    """
                    INSERT INTO facts (id, subject_id, predicate, object, confidence, provenance_json, created_at)
                    VALUES (?,?,?,?,?,?,?)
                    """,
                    (fact_id, subject_id, predicate, obj, conf, prov_json, db.now()),
                )
                ids.append(fact_id)
                reasons.append("Accepted: fact")

        elif candidate.kind == "episode":
            episode_id = db.new_id("ep")
            summary = str(candidate.payload.get("summary", ""))
            start_ts = candidate.payload.get("start_ts")
            end_ts = candidate.payload.get("end_ts")
            conf = float(candidate.confidence)
            db.execute_one(
                conn,
                """
                INSERT INTO episodes (id, entity_id, summary, start_ts, end_ts, confidence, provenance_json, created_at)
                VALUES (?,?,?,?,?,?,?,?)
                """,
                (episode_id, ent_id, summary, start_ts, end_ts, conf, prov_json, db.now()),
            )
            ids.append(episode_id)
            reasons.append("Accepted: episode")

        elif candidate.kind == "preference":
            key = str(candidate.payload.get("key", ""))
            value = str(candidate.payload.get("value", ""))
            conf = float(candidate.confidence)
            decay_ts = candidate.payload.get("decay_ts")
            existing = db.fetch_one(
                conn,
                """
                SELECT id, confidence FROM preferences
                WHERE entity_id = ? AND key = ?
                LIMIT 1
                """,
                (ent_id, key),
            )
            if existing:
                pref_id = existing["id"]
                merged_conf = max(float(existing["confidence"]), conf)
                db.execute_one(
                    conn,
                    """
                    UPDATE preferences
                    SET value = ?, confidence = ?, decay_ts = ?, provenance_json = ?, created_at = ?
                    WHERE id = ?
                    """,
                    (value, merged_conf, decay_ts, prov_json, db.now(), pref_id),
                )
                ids.append(pref_id)
                reasons.append("Accepted: preference_merged")
            else:
                pref_id = db.new_id("pref")
                db.execute_one(
                    conn,
                    """
                    INSERT INTO preferences (id, entity_id, key, value, confidence, decay_ts, provenance_json, created_at)
                    VALUES (?,?,?,?,?,?,?,?)
                    """,
                    (pref_id, ent_id, key, value, conf, decay_ts, prov_json, db.now()),
                )
                ids.append(pref_id)
                reasons.append("Accepted: preference")

        else:
            reasons.append("Rejected: unknown kind")

    return ids, reasons
