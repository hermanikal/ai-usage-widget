#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
[[ -f "$ROOT/.env" ]] || { echo "Create .env from .env.example first." >&2; exit 1; }
set -a
source "$ROOT/.env"
set +a
exec "$ROOT/.venv/bin/python" "$ROOT/src/telegram_report.py" "$@"
