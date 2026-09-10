# End-to-end pipeline

## 1. Data collection

Claude has two modes. Baseline mode reads Claude Desktop's locally cached official percentage. Advanced mode calls the command in `CLAUDE_USAGE_COMMAND`; the command returns weekly and session percentages, reset timestamps, and window lengths.

ChatGPT is always adapter-based. `CHATGPT_USAGE_COMMAND` runs only on the owner’s server and must output a JSON object with `plan`, `updated_at`, and `windows`. A window is valid for projection when it contains `label`, `used_percent` (0–100), `reset_at` (ISO-8601 with timezone), and `window_hours`.

The API itself sends no collector output to third parties. If the optional Telegram reporter is enabled, it sends only the formatted percentages, reset timestamps, and projections to the owner-configured chat. The API persists only label, percentage, and reset timestamp for the ChatGPT projection history in ignored `data/`.

## 2. API and projection

`src/usage_api.py` requires `X-API-Key` for both data endpoints. It refuses to boot with an empty, default, or short key. `/health` is intentionally unauthenticated and returns no personal data.

For a window, the projection is:

```text
pace = used_percent / elapsed_window_hours
projected_at_reset = used_percent + pace × remaining_hours
```

`safe_until_reset` is true if the projection is at most 100%. The estimate assumes a constant pace; it should be treated as guidance only.

Endpoints:

| Endpoint | Authentication | Result |
| --- | --- | --- |
| `GET /health` | none | liveness only |
| `GET /api/claude-usage` | `X-API-Key` | Claude weekly/session percentages + weekly projection when supplied |
| `GET /api/chatgpt-usage` | `X-API-Key` | ChatGPT windows + per-window projection |

## 3. Network boundary

The default bind address is `127.0.0.1`, meaning no device other than the server can reach it. For iPhone access, choose one of these:

1. Tailscale/private VPN and bind `0.0.0.0`.
2. A reverse proxy with HTTPS, authentication/rate limiting, and restricted source access.

Do not publish raw port `8787` through router port-forwarding. The API key is a bearer secret stored in Scriptable, so anyone holding it can view the usage data.

## 4. Widget behavior

Scriptable requests both endpoints in parallel every 30 minutes. The combined widget treats them independently, so one section can still render if the other provider is unavailable. It displays Claude Pro and ChatGPT Plus with their brand-color dots, 5-hour usage/reset, weekly usage/reset/projection, and safe/unsafe status. The last successful response is cached in Scriptable Documents for offline display.

## 5. Optional Telegram delivery

`src/telegram_report.py` requests the same two authenticated endpoints and formats one combined plain-text message. `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` must exist only in the ignored `.env` file or another private environment source. The tracked LaunchAgent template uses a fixed script and label; integrations should map `ai usage` to that fixed label instead of executing user-provided shell text.

## 6. Publishing checklist

- [ ] Run `git status --ignored`; `.env`, `data/`, `logs/`, and `.venv/` must not be staged.
- [ ] Search staged files for `apiKey`, IPs, Telegram IDs, account IDs, tokens, and absolute home paths.
- [ ] Confirm real `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` values exist only in ignored/private configuration.
- [ ] Generate a new API key before the public release if an old key ever appeared in a commit or screenshot.
- [ ] Verify `AI_USAGE_BIND_HOST=127.0.0.1` is the default in the tracked example.
- [ ] Keep any ChatGPT OAuth/browser-session collector private; publish only the adapter contract unless it uses a documented, user-authorized integration.
- [ ] Enable GitHub secret scanning and push protection on the repository.

Suggested pre-push audit:

```bash
git diff --cached | rg -n 'AIza|sk-|Bearer |api[_-]?key|token|chat_id|100\.'
```
