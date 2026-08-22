#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
LABEL="com.example.ai-usage-widget"
TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"

[[ -f "$ROOT/.env" ]] || { echo "Create .env from .env.example first." >&2; exit 1; }
grep -q '^AI_USAGE_API_KEY=.' "$ROOT/.env" || { echo "AI_USAGE_API_KEY is missing in .env." >&2; exit 1; }
mkdir -p "$ROOT/logs" "$HOME/Library/LaunchAgents"
chmod 600 "$ROOT/.env"
sed "s|YOUR_REPOSITORY_PATH|$ROOT|g" "$ROOT/examples/$LABEL.plist" > "$TARGET"
plutil -lint "$TARGET" >/dev/null
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$TARGET"
echo "Installed $LABEL. Check: launchctl print gui/$(id -u)/$LABEL"
