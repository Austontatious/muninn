#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH=./src
python scripts/init_db.py >/dev/null 2>&1 || true
uvicorn muninn.api:app --host "${MUNINN_HOST:-127.0.0.1}" --port "${MUNINN_PORT:-8000}" --reload
