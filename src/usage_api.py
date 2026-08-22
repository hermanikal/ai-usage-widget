#!/usr/bin/env python3
"""Local API for the Scriptable combined Claude + ChatGPT usage widget.

The server deliberately has no outbound network calls and no credential handling.
Claude data is read from Claude Desktop's local plan-usage cache. ChatGPT data is
provided by an opt-in local command configured by the owner.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Header, HTTPException

APP_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = APP_ROOT / "data"
CHATGPT_HISTORY = DATA_DIR / "chatgpt_usage_history.json"
CLAUDE_CACHE = Path.home() / "Library/Application Support/Claude/plan-usage-history.json"

API_KEY = os.environ.get("AI_USAGE_API_KEY", "")
if len(API_KEY) < 24 or API_KEY.lower() in {"changeme", "replace-with-a-long-random-secret"}:
    raise RuntimeError("Set AI_USAGE_API_KEY to a random value of at least 24 characters.")

app = FastAPI(title="AI Usage Widget API", version="1.0.0", docs_url=None, redoc_url=None)


def require_key(x_api_key: Optional[str]) -> None:
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


def parse_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result if result.tzinfo else result.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def claude_usage() -> dict[str, Any]:
    """Return Claude Desktop's latest official cached percentage values.

    File format is undocumented and may change; absence is reported as 503 rather
    than guessed from token counts.
    """
    command = os.environ.get("CLAUDE_USAGE_COMMAND")
    if command:
        try:
            run = subprocess.run(shlex.split(command), capture_output=True, text=True, timeout=20, check=True)
            snapshot = json.loads(run.stdout)
            weekly, session = snapshot.get("weekly", {}), snapshot.get("session", {})
            now = datetime.now(timezone.utc)
            weekly_projection = projection({"label": "Weekly", "used_percent": weekly.get("pct_actual"), "reset_at": weekly.get("reset_at"), "window_hours": weekly.get("window_hours")}, now)
            snapshot["projection"] = weekly_projection or {"status": "unavailable", "message": "Collector did not supply a complete weekly window."}
            return snapshot
        except (OSError, subprocess.SubprocessError, ValueError) as error:
            raise HTTPException(status_code=503, detail=f"Claude collector failed: {error}") from error
    try:
        samples = json.loads(CLAUDE_CACHE.read_text())["samples"]
        latest = samples[-1]
        usage = latest["u"]
        updated = datetime.fromtimestamp(latest["t"] / 1000, tz=timezone.utc)
        session = usage.get("fh")
        weekly = usage.get("sd")
        if session is None or weekly is None:
            raise KeyError("usage percentages missing")
    except (OSError, ValueError, KeyError, IndexError, TypeError) as error:
        raise HTTPException(status_code=503, detail=f"Claude Desktop usage cache unavailable: {error}") from error

    # Claude Desktop cache exposes current percentages, but not reset timestamps.
    return {
        "updated_at": iso(updated),
        "official": {"available": True, "source": "Claude Desktop local cache"},
        "weekly": {"pct_actual": float(weekly)},
        "session": {"pct_actual": float(session)},
        "projection": {"status": "unavailable", "message": "Claude cache does not expose reset timestamps."},
    }


def load_history() -> list[dict[str, Any]]:
    try:
        value = json.loads(CHATGPT_HISTORY.read_text())
        return value if isinstance(value, list) else []
    except (OSError, ValueError):
        return []


def save_history(history: list[dict[str, Any]]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    CHATGPT_HISTORY.write_text(json.dumps(history[-500:], indent=2))


def projection(window: dict[str, Any], now: datetime) -> dict[str, Any] | None:
    used = window.get("used_percent")
    reset_at = parse_time(window.get("reset_at"))
    duration = window.get("window_hours")
    if not isinstance(used, (int, float)) or reset_at is None or not isinstance(duration, (int, float)) or duration <= 0:
        return None
    started = reset_at - timedelta(hours=duration)
    elapsed = max((now - started).total_seconds() / 3600, 0.01)
    remaining = max((reset_at - now).total_seconds() / 3600, 0)
    pace = float(used) / elapsed
    projected = float(used) + pace * remaining
    safe = projected <= 100
    limit_at = now + timedelta(hours=(100 - float(used)) / pace) if pace > 0 and not safe else None
    return {
        "status": "ok", "label": window.get("label", "Usage"), "window_started_at": iso(started), "reset_at": iso(reset_at),
        "hours_remaining": round(remaining, 1), "pct_per_hour": round(pace, 2),
        "projected_pct_at_reset": round(projected, 1), "safe_until_reset": safe,
        "limit_reached_at": iso(limit_at) if limit_at else None,
    }


def chatgpt_snapshot() -> dict[str, Any]:
    command = os.environ.get("CHATGPT_USAGE_COMMAND")
    if not command:
        raise HTTPException(status_code=503, detail="CHATGPT_USAGE_COMMAND is not configured")
    try:
        run = subprocess.run(shlex.split(command), capture_output=True, text=True, timeout=20, check=True)
        snapshot = json.loads(run.stdout)
        if not isinstance(snapshot.get("windows"), list):
            raise ValueError("expected a JSON object with a windows array")
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        raise HTTPException(status_code=503, detail=f"ChatGPT collector failed: {error}") from error

    now = datetime.now(timezone.utc)
    snapshot["updated_at"] = snapshot.get("updated_at") or iso(now)
    snapshot["projections"] = [item for window in snapshot["windows"] if (item := projection(window, now))]
    # Persist only quota numbers and timestamps; never collector stdout, tokens, or credentials.
    history = load_history()
    history.extend({"timestamp": snapshot["updated_at"], "label": w.get("label"), "used_percent": w.get("used_percent"), "reset_at": w.get("reset_at")} for w in snapshot["windows"])
    save_history(history)
    return snapshot


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/claude-usage")
def get_claude(x_api_key: Optional[str] = Header(default=None)) -> dict[str, Any]:
    require_key(x_api_key)
    return claude_usage()


@app.get("/api/chatgpt-usage")
def get_chatgpt(x_api_key: Optional[str] = Header(default=None)) -> dict[str, Any]:
    require_key(x_api_key)
    return chatgpt_snapshot()
