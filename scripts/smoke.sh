#!/usr/bin/env bash
set -euo pipefail

PORT=$((8800 + RANDOM % 1000))
BASE_URL="http://127.0.0.1:${PORT}"

export PYTHONPATH=./src
python3 scripts/init_db.py >/dev/null 2>&1 || true

uvicorn muninn.api:app --host 127.0.0.1 --port "${PORT}" >/tmp/muninn-smoke.log 2>&1 &
PID=$!
cleanup() {
  kill "${PID}" >/dev/null 2>&1 || true
  wait "${PID}" 2>/dev/null || true
}
trap cleanup EXIT

sleep 2
MUNINN_BASE_URL="${BASE_URL}" python3 examples/local_client_demo.py >/tmp/muninn-smoke-client.log

MUNINN_BASE_URL="${BASE_URL}" python3 - <<'PY'
import os
import httpx

base = os.environ["MUNINN_BASE_URL"]
stage = httpx.post(
    f"{base}/v0/memory/stage_candidates",
    json={
        "namespace": "default",
        "candidates": [
            {
                "kind": "preference",
                "entity": {"id": "ent_smoke", "kind": "user", "name": "Smoke"},
                "payload": {"key": "health.note", "value": "ok"},
                "confidence": 0.9,
                "provenance": {"source_type": "user", "source_id": "smoke"},
            }
        ],
    },
    timeout=20,
)
stage.raise_for_status()
body = stage.json()
pending_id = body["pending_ids"][0]

confirm = httpx.post(
    f"{base}/v0/memory/confirm_candidates",
    json={
        "namespace": "default",
        "pending_ids": [pending_id],
        "decision": "accept",
        "decided_by": "user:smoke",
    },
    timeout=20,
)
confirm.raise_for_status()
out = confirm.json()
assert out["accepted_writes"] >= 1, out
print("smoke workflow ok")
PY

echo "Smoke succeeded: ${BASE_URL}" 
