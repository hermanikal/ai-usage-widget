#!/usr/bin/env python3
"""Send a combined widget-style usage report through Telegram Bot API."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any, Optional


def parse_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed.astimezone() if parsed.tzinfo else parsed.astimezone()


def format_time(value: Optional[str]) -> str:
    parsed = parse_time(value)
    return parsed.strftime("%d %b %H:%M") if parsed else "—"


def session_reset(value: Optional[str], now: datetime) -> str:
    parsed = parse_time(value)
    if parsed is None or parsed <= now:
        return "Not started yet"
    return parsed.strftime("%d %b %H:%M")


def bar(percent: Any, width: int = 12) -> str:
    if not isinstance(percent, (int, float)):
        return "░" * width
    filled = max(0, min(width, round(float(percent) / 100 * width)))
    return "█" * filled + "░" * (width - filled)


def percent(value: Any) -> str:
    return "—" if not isinstance(value, (int, float)) else f"{round(float(value))}%"


def window_duration_minutes(item: dict[str, Any]) -> float:
    if isinstance(item.get("window_duration_minutes"), (int, float)):
        return float(item["window_duration_minutes"])
    if isinstance(item.get("window_hours"), (int, float)):
        return float(item["window_hours"]) * 60
    return 10080 if "week" in str(item.get("label", "")).lower() else 300


def find_window(data: dict[str, Any], duration: int, keyword: str) -> dict[str, Any]:
    return next(
        (
            item
            for item in data.get("windows", [])
            if window_duration_minutes(item) == duration
            or keyword in str(item.get("label", "")).lower()
        ),
        {},
    )


def weekly_projection(data: dict[str, Any]) -> dict[str, Any]:
    return next(
        (
            item
            for item in data.get("projections", [])
            if "week" in str(item.get("label", "")).lower()
        ),
        {},
    )


def projection_lines(reset_at: Optional[str], projection: dict[str, Any]) -> list[str]:
    projected = projection.get("projected_pct_at_reset")
    suffix = f" · ~{projected}% weekly" if isinstance(projected, (int, float)) else ""
    lines = [f"Reset    {format_time(reset_at)}{suffix}"]
    if projection.get("safe_until_reset") is True:
        lines.append("✅ Aman sampai reset")
    elif projection.get("safe_until_reset") is False:
        lines.append("⚠️ Tidak aman sebelum reset")
    else:
        lines.append("ℹ️ Proyeksi belum tersedia")
    return lines


def format_message(claude: dict[str, Any], chatgpt: dict[str, Any], now: Optional[datetime] = None) -> str:
    now = now or datetime.now().astimezone()
    claude_session = claude.get("session", {})
    claude_weekly = claude.get("weekly", {})
    claude_projection = claude.get("projection", {})
    gpt_session = find_window(chatgpt, 300, "5 hour") or find_window(chatgpt, 300, "session")
    gpt_weekly = find_window(chatgpt, 10080, "week")
    gpt_projection = weekly_projection(chatgpt)

    return "\n".join(
        [
            "🤖 AI Usage",
            f"Updated {now:%d %b %Y, %H:%M %Z}",
            "",
            "🟠 Claude Pro",
            f"5 hour  [{bar(claude_session.get('pct_actual'))}] {percent(claude_session.get('pct_actual'))}",
            f"5h reset: {session_reset(claude_session.get('resets_at') or claude_session.get('reset_at'), now)}",
            f"Weekly  [{bar(claude_weekly.get('pct_actual'))}] {percent(claude_weekly.get('pct_actual'))}",
            *projection_lines(
                claude_weekly.get("resets_at") or claude_weekly.get("reset_at") or claude_projection.get("reset_at"),
                claude_projection if claude_projection.get("status") == "ok" else {},
            ),
            "",
            "🟢 ChatGPT Plus",
            f"5 hour  [{bar(gpt_session.get('used_percent'))}] {percent(gpt_session.get('used_percent'))}",
            f"5h reset: {session_reset(gpt_session.get('reset_at'), now)}",
            f"Weekly  [{bar(gpt_weekly.get('used_percent'))}] {percent(gpt_weekly.get('used_percent'))}",
            *projection_lines(gpt_weekly.get("reset_at") or gpt_projection.get("reset_at"), gpt_projection),
        ]
    )


def fetch_json(base_url: str, path: str, api_key: str) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        headers={"X-API-Key": api_key, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.loads(response.read())


def send_telegram(token: str, chat_id: str, message: str) -> None:
    payload = json.dumps({"chat_id": chat_id, "text": message}).encode()
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.status != 200:
            raise RuntimeError(f"Telegram returned HTTP {response.status}")


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Set {name} in your private .env file.")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true", help="Print the report without sending it to Telegram.")
    args = parser.parse_args()

    base_url = os.environ.get("AI_USAGE_API_URL", "http://127.0.0.1:8787")
    api_key = required_env("AI_USAGE_API_KEY")
    claude = fetch_json(base_url, "/api/claude-usage", api_key)
    chatgpt = fetch_json(base_url, "/api/chatgpt-usage", api_key)
    message = format_message(claude, chatgpt)
    print(message)

    if not args.preview:
        send_telegram(required_env("TELEGRAM_BOT_TOKEN"), required_env("TELEGRAM_CHAT_ID"), message)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, ValueError, urllib.error.URLError) as error:
        raise SystemExit(f"AI Usage Telegram report failed: {error}")
