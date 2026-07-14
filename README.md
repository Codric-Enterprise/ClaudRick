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

| Variable             | Default             | Purpose                          |
| -------------------- | ------------------- | -------------------------------- |
| `ANTHROPIC_API_KEY`  | *(required)*        | Anthropic API key (server-side). |
| `REVISION_MODEL`     | `claude-sonnet-5`   | Claude model id.                 |
| `REVISION_HOST`      | `127.0.0.1`         | Bind host.                       |
| `REVISION_PORT`      | `8000`              | Bind port.                       |

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
│   ├── server.py            # serves the UI + /api/messages proxy
│   ├── cli.py               # `revision` entry point
│   └── static/index.html    # the single-page UI
├── tests/                   # pytest suite (config, client, server)
└── pyproject.toml
```

## Security notes

- The API key is only ever read server-side; it is never sent to the browser.
- The static file server is restricted to `src/revision/static/` and rejects
  path traversal.
- For public deployment you should additionally put ReVision behind HTTPS and
  consider adding rate limiting / auth on `/api/messages`.
