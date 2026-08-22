#!/usr/bin/env bash
set -euo pipefail

patterns="AIza[0-9A-Za-z_-]{20,}|sk-[0-9A-Za-z_-]{20,}|Bearer[[:space:]][0-9A-Za-z._-]{20,}|(api[_-]?key|token|secret|chat_id)[[:space:]]*[:=][[:space:]]*['\"]?[0-9A-Za-z._-]{24,}|100\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}"
if git diff --cached --unified=0 -- . ':!.env.example' | rg -n -i "^\+[^+].*($patterns)"; then
  echo "Potential secret or private endpoint found. Review before pushing." >&2
  exit 1
fi
echo "No obvious secrets or private endpoints found in staged changes."
