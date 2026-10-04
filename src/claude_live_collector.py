#!/usr/bin/env python3
"""Live Claude Pro/Max quota collector for CLAUDE_USAGE_COMMAND (macOS).

Prints one JSON object matching examples/claude-snapshot.example.json, using
the Claude Code login that already exists on this Mac:

  - Reads Claude Code's OAuth access token from the macOS Keychain
    ("Claude Code-credentials"). The token is never printed, logged, or saved.
  - Queries the usage endpoint Claude Code itself uses for `/usage`. It is
    undocumented and may change; any failure exits non-zero instead of
    guessing or reusing old numbers.
  - If the access token has expired (or is rejected), runs the local
    `claude -p /usage` slash command so Claude Code refreshes its own token —
    no model call, no quota spent — then retries once. Claude Code keeps
    ownership of refresh-token rotation; this script never touches it.

Requires Claude Code installed and logged in with a claude.ai subscription.
Set CLAUDE_BIN if `claude` is not on PATH.

  CLAUDE_USAGE_COMMAND=/absolute/path/to/.venv/bin/python /absolute/path/to/src/claude_live_collector.py
"""

from __future__ import annotations

import fcntl
import getpass
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

KEYCHAIN_SERVICE = "Claude Code-credentials"
USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
LOCK_FILE = Path(tempfile.gettempdir()) / "ai-usage-claude-refresh.lock"
REFRESH_TIMEOUT = 15
EXPIRY_MARGIN_MS = 60_000
WINDOWS = {"session": ("five_hour", 5), "weekly": ("seven_day", 168)}


class CollectorError(Exception):
    pass


class TokenRejected(CollectorError):
    pass


def _oauth() -> dict:
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", getpass.getuser(), "-w"],
            capture_output=True, text=True, check=True, timeout=10,
        )
        raw = result.stdout.strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = json.loads(bytes.fromhex(raw))
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise CollectorError("Claude Code login not found in Keychain") from exc
    return data.get("claudeAiOauth") or {}


def _token_is_fresh(oauth: dict) -> bool:
    expires_at = oauth.get("expiresAt")
    return isinstance(expires_at, (int, float)) and expires_at > time.time() * 1000 + EXPIRY_MARGIN_MS


def _claude_bin() -> str | None:
    candidates = [
        os.environ.get("CLAUDE_BIN"),
        shutil.which("claude"),
        "/opt/homebrew/bin/claude",
        str(Path.home() / ".local/bin/claude"),
        "/usr/local/bin/claude",
    ]
    return next((c for c in candidates if c and os.access(c, os.X_OK)), None)


def _refresh_via_claude_code() -> None:
    binary = _claude_bin()
    if not binary:
        raise CollectorError("Claude Code CLI not found; set CLAUDE_BIN")
    env = {**os.environ, "PATH": f"{Path(binary).parent}:/usr/bin:/bin:{os.environ.get('PATH', '')}"}
    with open(LOCK_FILE, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if _token_is_fresh(_oauth()):  # a concurrent request already refreshed it
            return
        try:
            subprocess.run(
                [binary, "-p", "/usage"], cwd=str(Path.home()), env=env, stdin=subprocess.DEVNULL,
                capture_output=True, text=True, timeout=REFRESH_TIMEOUT, check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise CollectorError("Claude Code token refresh failed") from exc


def _token(allow_refresh: bool = True) -> str:
    oauth = _oauth()
    token = oauth.get("accessToken")
    if not isinstance(token, str) or not token:
        raise CollectorError("Claude Code is not logged in with a claude.ai subscription")
    if _token_is_fresh(oauth):
        return token
    if not allow_refresh:
        raise CollectorError("Claude Code token expired and could not be refreshed")
    _refresh_via_claude_code()
    return _token(allow_refresh=False)


def _get_usage(token: str) -> dict:
    request = Request(USAGE_URL, headers={
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "anthropic-beta": "oauth-2025-04-20",
    })
    try:
        with urlopen(request, timeout=10) as response:
            data = json.load(response)
    except HTTPError as exc:
        if exc.code == 401:
            raise TokenRejected("Claude usage endpoint rejected the token") from exc
        raise CollectorError(f"Claude usage endpoint returned HTTP {exc.code}") from exc
    except (URLError, OSError, ValueError) as exc:
        raise CollectorError("Claude usage endpoint unreachable") from exc
    if not isinstance(data, dict):
        raise CollectorError("Unexpected Claude usage response")
    return data


def _window(data: dict, key: str, hours: int) -> dict:
    value = data.get(key)
    if not isinstance(value, dict):
        return {}
    pct, reset = value.get("utilization"), value.get("resets_at")
    if isinstance(pct, bool) or not isinstance(pct, (int, float)):
        return {}
    window = {"pct_actual": float(pct), "window_hours": hours}
    if isinstance(reset, str):
        datetime.fromisoformat(reset.replace("Z", "+00:00"))  # validate
        window["reset_at"] = reset
    return window


def collect() -> dict:
    try:
        data = _get_usage(_token())
    except TokenRejected:
        _refresh_via_claude_code()
        data = _get_usage(_token(allow_refresh=False))
    snapshot = {"updated_at": datetime.now(timezone.utc).isoformat()}
    for name, (key, hours) in WINDOWS.items():
        snapshot[name] = _window(data, key, hours)
    if not snapshot["weekly"] and not snapshot["session"]:
        raise CollectorError("Claude usage response had no usable windows")
    snapshot["official"] = {"available": True, "source": "Claude Code usage endpoint"}
    return snapshot


def main() -> int:
    try:
        print(json.dumps(collect()))
        return 0
    except (CollectorError, ValueError) as error:
        print(f"claude_live_collector: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
