# AI Usage Widget

Private, self-hosted iPhone Scriptable widget for **Claude Pro** and **ChatGPT Plus** usage. It exposes only your own percentage, reset time, and local projection through an API protected by a secret header.

It is designed to be published safely: no credentials, private IP addresses, user IDs, usage history, or logs are tracked.

## Architecture

```text
Claude Desktop cache / Claude collector ─┐
                                         ├─ local FastAPI ── authenticated HTTPS/VPN ── Scriptable widget
ChatGPT collector command (optional) ───┘
                                               │
                                               └─ minimal local quota history → projection
```

The server makes no outbound requests. A collector runs on the same machine and emits JSON to stdout. The ChatGPT collector is intentionally an owner-supplied adapter: this repository does not scrape a website, copy browser sessions, or contain OAuth credentials.

## Quick start (macOS)

```bash
git clone https://github.com/YOUR-ACCOUNT/ai-usage-widget.git
cd ai-usage-widget
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
openssl rand -hex 32
# paste that value as AI_USAGE_API_KEY in .env
.venv/bin/python -m uvicorn src.usage_api:app --host 127.0.0.1 --port 8787
```

Test locally (replace the key):

```bash
curl -H 'X-API-Key: YOUR_KEY' http://127.0.0.1:8787/health
curl -H 'X-API-Key: YOUR_KEY' http://127.0.0.1:8787/api/claude-usage
```

For the iPhone, use a private VPN such as Tailscale, or a TLS reverse proxy. Change `AI_USAGE_BIND_HOST` to `0.0.0.0` only when that network path is already protected. Do not expose port 8787 directly to the public internet.

## iPhone widget

1. Install [Scriptable](https://scriptable.app/).
2. Create a script and paste [`widget/ai_usage_widget.js`](widget/ai_usage_widget.js).
3. Set `CONFIG.baseUrl` to your private HTTPS/VPN address and `CONFIG.apiKey` to the value in `.env`.
4. Add a Large widget to the Home Screen and select the script. Medium and Small layouts also work.

The widget caches its last successful response locally, so a temporary network failure does not blank the display.

## Collectors

### Claude baseline

Without configuration, `/api/claude-usage` reads the current percentage values from Claude Desktop's local cache. The cache is undocumented and provides no reset timestamp, so projection is unavailable in that baseline mode.

For weekly projection, set `CLAUDE_USAGE_COMMAND` to your own local collector command. It must print JSON matching [`examples/claude-snapshot.example.json`](examples/claude-snapshot.example.json). The server calculates the weekly pace and projected percentage at reset.

### ChatGPT adapter

Set `CHATGPT_USAGE_COMMAND` to an absolute command that prints one JSON object matching [`examples/chatgpt-snapshot.example.json`](examples/chatgpt-snapshot.example.json). Each usage window needs `used_percent`, `reset_at`, and `window_hours` for projection.

Example pattern:

```bash
CHATGPT_USAGE_COMMAND=/Users/me/bin/chatgpt-usage-collector --json
```

The command is split with `shlex` and executed without `shell=True`; shell interpolation is not used. Keep its credentials in the operating system keychain or its own ignored config file—never in this repository.

## Deployment

Use [`examples/com.example.ai-usage-widget.plist`](examples/com.example.ai-usage-widget.plist) as a macOS LaunchAgent template. Replace `YOUR_USERNAME` and `YOUR_REPOSITORY_PATH`, set permissions to `600` for `.env`, then load it with `launchctl bootstrap gui/$(id -u) ...`.

Full design, endpoint contracts, projection assumptions, and security checklist: [docs/PIPELINE.md](docs/PIPELINE.md).

Using an AI coding agent for local setup? A ready-to-paste, security-scoped prompt is available in [docs/AI_SETUP_PROMPT.md](docs/AI_SETUP_PROMPT.md).

## Limitations

- This is a personal monitoring tool, not an official Claude or OpenAI product.
- Usage sources and local cache formats can change without notice.
- Projection is a linear estimate, not a quota guarantee.
- Do not use this as billing, access-control, or security data.

## License

MIT. See [LICENSE](LICENSE).
