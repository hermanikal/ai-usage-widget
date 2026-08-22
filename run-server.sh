#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
if [[ -f "$ROOT/.env" ]]; then
  set -a
  source "$ROOT/.env"
  set +a
fi

: "${AI_USAGE_API_KEY:?Create .env from .env.example and set AI_USAGE_API_KEY first.}"
PYTHON="$ROOT/.venv/bin/python"
[[ -x "$PYTHON" ]] || PYTHON="python3"
exec "$PYTHON" -m uvicorn src.usage_api:app --host "${AI_USAGE_BIND_HOST:-127.0.0.1}" --port "${AI_USAGE_PORT:-8787}"
