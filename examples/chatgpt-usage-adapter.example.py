#!/usr/bin/env python3
"""Template for a CHATGPT_USAGE_COMMAND adapter.

This is a STARTING POINT, not a working collector. It intentionally contains
no scraping, no OAuth flow, and no browser-cookie handling — wire in your own
authorized data source in `fetch_snapshot()` and keep its credentials outside
this repository (OS keychain, a config file that is gitignored, etc).

Contract (see examples/chatgpt-snapshot.example.json):
  - Print exactly one JSON object to stdout, nothing else.
  - Top level: "plan" (str or null), "updated_at" (ISO-8601 with timezone),
    "windows" (list).
  - Each window needs "label", "used_percent" (0-100), "reset_at"
    (ISO-8601 with timezone), and "window_hours" (duration the window
    covers, e.g. 5 for a rolling session or 168 for weekly) — usage_api.py
    needs all four to compute a projection for that window.
  - Exit non-zero and print nothing to stdout on failure; usage_api.py
    surfaces that as a 503 rather than guessing at stale numbers.

Wire it up:
  chmod +x examples/chatgpt-usage-adapter.example.py
  # then in .env:
  CHATGPT_USAGE_COMMAND=/absolute/path/to/chatgpt-usage-adapter.example.py

Try the contract end-to-end before writing real collection logic:
  ./examples/chatgpt-usage-adapter.example.py --demo
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone


def fetch_snapshot() -> dict:
    """Replace this with your own authorized ChatGPT usage lookup.

    Whatever you plug in here must be something YOU are authorized to read
    locally — e.g. a CLI you already use that exposes your own account's
    quota, or a small script that reads a session you already maintain.
    Never copy browser cookies, OAuth tokens, or credentials into this repo.
    """
    raise NotImplementedError(
        "Implement fetch_snapshot() with your own authorized ChatGPT usage "
        "source, or run this script with --demo to see the expected shape."
    )


def demo_snapshot() -> dict:
    """Static example matching examples/chatgpt-snapshot.example.json's shape."""
    now = datetime.now(timezone.utc).astimezone()
    return {
        "plan": "Plus",
        "updated_at": now.isoformat(),
        "windows": [
            {
                "label": "5 hour",
                "used_percent": 12,
                "reset_at": (now + timedelta(hours=3)).isoformat(),
                "window_hours": 5,
            },
            {
                "label": "Weekly",
                "used_percent": 41,
                "reset_at": (now + timedelta(days=4)).isoformat(),
                "window_hours": 168,
            },
        ],
    }


def main() -> int:
    snapshot = demo_snapshot() if "--demo" in sys.argv[1:] else fetch_snapshot()
    print(json.dumps(snapshot))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NotImplementedError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
