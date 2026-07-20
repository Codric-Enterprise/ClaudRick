# ✨ ReVision

A Claude-powered **document toolkit**. One web app, four tools:

- **🔍 Fine Print Analyzer** — flags manipulative language (deceptive wording, tone manipulation, scare tactics, artificial urgency) and scores overall risk.
- **✨ Enhance** — rewrites a draft with adjustable tone / clarity / persuasiveness spectrums.
- **🌐 Translate** — translates between 20+ languages while preserving legal/professional meaning.
- **📖 Jargonary** — decodes dense legal, technical, or bureaucratic text into plain English with a glossary.

## Architecture

ReVision is a static single-page UI served by a small Python backend. The
browser never talks to the Anthropic API directly — it calls the backend's
`/api/messages` endpoint, which injects the API key **server-side** and proxies
the request to Claude. This keeps the key out of the client and lets the server
control which model is used.

```
browser (static/index.html)  ──POST /api/messages──►  Python server  ──►  Anthropic API
        callClaude()                                   (adds x-api-key)
```

The backend uses only the Python standard library — **no runtime dependencies**.

## Requirements

- Python >= 3.11
- An Anthropic API key

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export ANTHROPIC_API_KEY=sk-ant-...
```

Prefer a local env file? Copy the template and fill it in — `.env` is
gitignored, so real secrets never get committed:

```bash
cp .env.example .env          # then edit .env
set -a; . ./.env; set +a      # load it into your shell
```

The Claude Code session-start hook also auto-loads `.env` when it's present.

## Run

```bash
revision                 # serves http://127.0.0.1:8000
revision --port 3000     # custom port
revision --model claude-opus-4-8
```

Then open the printed URL in a browser.

Without installing:

```bash
ANTHROPIC_API_KEY=sk-ant-... PYTHONPATH=src python -m revision.cli
```

## Configuration

All settings come from the environment (CLI flags override where provided):

| Variable               | Default            | Purpose                                                        |
| ---------------------- | ------------------ | -------------------------------------------------------------- |
| `ANTHROPIC_API_KEY`    | *(required)*       | Anthropic API key (server-side only).                          |
| `REVISION_MODEL`       | `claude-sonnet-5`  | Claude model id.                                               |
| `REVISION_HOST`        | `127.0.0.1`        | Bind host.                                                     |
| `REVISION_PORT`        | `8000`             | Bind port.                                                     |
| `REVISION_API_TOKEN`   | *(unset)*          | If set, `/api/messages` requires `Authorization: Bearer <token>`. |
| `REVISION_RATE_LIMIT`  | `30`               | Max `/api/messages` requests per window per client (0 = off). |
| `REVISION_RATE_WINDOW` | `60`               | Rate-limit window, in seconds.                                 |
| `REVISION_GLOBAL_RATE_LIMIT` | `0` (off)    | Max `/api/messages` requests per window across **all** clients combined — a hard ceiling on total Anthropic API spend. |
| `REVISION_GLOBAL_RATE_WINDOW` | `3600`     | Global rate-limit window, in seconds.                          |
| `REVISION_TRUST_PROXY` | `false`            | Trust `X-Forwarded-For` for client IP (enable only behind a proxy). |
| `GITHUB_TOKEN`         | *(unset)*          | GitHub token for local GitHub API / git operations (not used by the server). |

### Auth & rate limiting

- **Rate limiting** is on by default (30 requests / 60s per client IP) via a
  thread-safe sliding window. Exceeding it returns `429` with a `Retry-After`
  header. Set `REVISION_RATE_LIMIT=0` to disable.
- **Global request budget** is opt-in (off by default): set
  `REVISION_GLOBAL_RATE_LIMIT` to cap total `/api/messages` requests across
  every client combined, regardless of how many distinct IPs are involved.
  This is the guardrail to set before running ReVision publicly on a shared
  API key — per-client limiting alone doesn't bound total spend against
  someone rotating IPs.
- **Bearer auth** is opt-in: set `REVISION_API_TOKEN` and callers must send
  `Authorization: Bearer <token>` on `/api/messages` (constant-time compared).
  Leave it unset for open local use.
- Behind a reverse proxy, set `REVISION_TRUST_PROXY=true` so per-client rate
  limiting keys off the real client IP from `X-Forwarded-For` rather than the
  proxy's address.

## Docker

```bash
docker build -t revision .
docker run -e ANTHROPIC_API_KEY=sk-ant-... -p 8000:8000 revision
```

The image has no dependencies beyond the standard library, binds `0.0.0.0:8000`,
and includes a `HEALTHCHECK` hitting `/healthz`.

## CI

`.github/workflows/ci.yml` runs on pushes and PRs: `ruff check`,
`ruff format --check`, and `pytest` across Python 3.11–3.13, plus a Docker image
build.

## Development

```bash
pytest              # run tests
ruff check .        # lint
ruff format .       # format
```

> In some environments `pytest`/`ruff` are installed as standalone binaries
> rather than into the active interpreter. If `python -m pytest` reports
> "No module named pytest", invoke `pytest` / `ruff` directly.

## Project layout

```
.
├── src/revision/
│   ├── __init__.py
│   ├── config.py            # env-driven configuration
│   ├── anthropic_client.py  # server-side Anthropic API client (stdlib only)
│   ├── ratelimit.py         # thread-safe sliding-window rate limiter
│   ├── server.py            # serves the UI + /api/messages proxy (auth + limits)
│   ├── cli.py               # `revision` entry point
│   └── static/index.html    # the single-page UI
├── tests/                   # pytest suite (config, client, ratelimit, server)
├── .github/workflows/ci.yml # lint + format + tests + docker build
├── Dockerfile
└── pyproject.toml
```

## Security notes

- The API key is only ever read server-side; it is never sent to the browser.
- The static file server is restricted to `src/revision/static/` and rejects
  path traversal.
- Rate limiting (on by default) and optional bearer auth guard `/api/messages`.
- For public deployment, additionally put ReVision behind HTTPS (terminate TLS at
  a reverse proxy) and set `REVISION_TRUST_PROXY=true`.
