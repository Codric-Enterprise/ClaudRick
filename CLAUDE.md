# CLAUDE.md

Guidance for AI assistants (and humans) working in this repository.

## Project overview

**ReVision** is a Claude-powered document toolkit exposed as a single-page web
app with four tools:

- **Fine Print Analyzer** — detects manipulative language and scores risk.
- **Enhance** — rewrites drafts along tone / clarity / persuasiveness spectrums.
- **Translate** — translates across 20+ languages, preserving legal meaning.
- **Jargonary** — simplifies dense text and builds a jargon glossary.

The UI is a static page; a small Python backend serves it and proxies AI
requests to the Anthropic API so the API key stays server-side.

## Architecture

```
browser (static/index.html)  ──POST /api/messages──►  Python server  ──►  Anthropic API
        callClaude()                                   (injects x-api-key,
                                                         chooses the model)
```

Key design decisions:

- **Server-side key.** The browser calls the same-origin `/api/messages`
  endpoint, never `api.anthropic.com` directly. `anthropic_client.py` adds the
  `x-api-key` and `anthropic-version` headers server-side. **Never** move the
  key or a direct Anthropic call into `static/index.html`.
- **Model is server-controlled.** The model id lives in `config.py`
  (`REVISION_MODEL`, default `claude-sonnet-5`), not in the frontend. Use a real
  model id — the original prototype used an invalid one.
- **Zero runtime dependencies.** The backend uses only the standard library
  (`http.server`, `urllib`). Keep it that way unless there's a strong reason;
  `pytest`/`ruff` are dev-only.

## Repository structure

```
.
├── src/revision/
│   ├── __init__.py            # package metadata (__version__)
│   ├── config.py             # Config.from_env(); model/host/port/key/auth/limits
│   ├── anthropic_client.py   # AnthropicClient.create_message() (stdlib urllib)
│   ├── ratelimit.py          # RateLimiter: thread-safe sliding window
│   ├── server.py             # RevisionHandler, create_server(), serve()
│   ├── cli.py                # `revision` console entry point
│   └── static/index.html     # the single-page UI (all four tools)
├── tests/
│   ├── test_config.py
│   ├── test_anthropic_client.py   # mocks urllib.request.urlopen
│   ├── test_ratelimit.py          # limiter unit tests (monkeypatched clock)
│   └── test_server.py             # runs a live server on port 0, fake client
├── .claude/                  # checked-in Claude Code tooling (see "Claude tooling" below)
│   ├── settings.json         # permissions allowlist + hooks
│   ├── hooks/session-start.sh     # SessionStart: loads .env if present, installs dev deps on cold containers
│   ├── commands/             # custom slash commands (/analyze, /think, /check, /run-app, …)
│   ├── skills/               # claude-power-practices + dev skills (dev-check, run-app, add-tool, test-and-lint)
│   └── README.md             # explains the whole .claude/ setup
├── docs/claude-playbook.md   # full Claude tips + command reference (source of the above)
├── docs/commands-pack.md     # all 80 commands: slash form + paste-ready prompt
├── docs/command-console.html # interactive searchable console (shareable artifact)
├── power-pack/               # "S.L.A.S.H." — standalone distributable (see below)
│   ├── commands/             # 77 portable commands (excludes repo-specific dev ones)
│   ├── skills/               # power-practices skill
│   ├── cli.js                # cross-platform Node installer (npx slash-pack)
│   ├── package.json          # npm-publishable package
│   ├── install.sh            # Unix bash installer (--dry-run, --uninstall, backup)
│   ├── index.html            # product landing page
│   ├── README.md             # standalone product README
│   └── LICENSE               # MIT
├── install-power-pack.sh     # legacy installer (wraps power-pack/install.sh)
├── .github/workflows/ci.yml  # ruff check + ruff format --check + pytest (3.11-3.13) + docker build
├── Dockerfile                # stdlib-only image; binds 0.0.0.0:8000; HEALTHCHECK /healthz
├── .dockerignore
├── pyproject.toml            # hatchling build; pytest + ruff config
├── .env.example              # local env template (ANTHROPIC_API_KEY, GITHUB_TOKEN, …); copy to gitignored .env
├── README.md
└── .gitignore
```

## HTTP endpoints

- `GET /` and other paths → static files from `src/revision/static/` (traversal-guarded).
- `GET /healthz` → `{"status": "ok"}`; does not call Anthropic (used by Docker HEALTHCHECK).
- `POST /api/messages` → `{prompt, max_tokens?, stream?}`; enforces optional
  bearer auth, then rate limiting, then proxies to Claude. Errors are
  `{"error": {"message"}}` with `400` (bad input), `401` (auth), `429` (rate
  limit, sends `Retry-After`), or `502` (Anthropic error).
- With `"stream": true`, the response is `text/event-stream`: one
  `data: {"delta": <text>}` event per chunk, terminated by `data: [DONE]`.
  Errors before the first chunk still return 502 JSON; mid-stream errors are
  emitted as a `data: {"error": ...}` event. The frontend's
  `callClaudeStream()` consumes this (used by Enhance, which renders live);
  tools that parse strict JSON output (Analyzer, Translate, Jargonary) keep
  the buffered path.

Uses a **src layout**: importable code is under `src/`; `pyproject.toml` sets
`pythonpath = ["src"]` so tests run without an editable install. The
`static/` directory lives inside the package so it ships in the wheel.

## Getting started

- **Python:** requires `>=3.11`.
- **Install (editable, with dev tools):**
  ```bash
  python -m venv .venv && source .venv/bin/activate
  pip install -e ".[dev]"
  ```
- **Run:** `ANTHROPIC_API_KEY=sk-ant-... revision` (serves http://127.0.0.1:8000).

## Development workflows

- **Run tests:** `pytest`
- **Lint:** `ruff check .`
- **Format:** `ruff format .`
- **Run the app:** `revision [--host H --port P --model M]`, or without install
  `ANTHROPIC_API_KEY=... PYTHONPATH=src python -m revision.cli`
- **Manual smoke test:** start the server, then
  `curl localhost:8000/` (UI) and
  `curl -X POST localhost:8000/api/messages -d '{"prompt":"hi"}'`
  (returns a graceful error if no key is set).

> Note: in some environments `pytest`/`ruff` are standalone binaries, not in the
> interpreter's site-packages. If `python -m pytest` says "No module named
> pytest", call `pytest` / `ruff` directly.

## Conventions

- **Layout:** shippable code under `src/revision/`; tests under `tests/` mirror
  the module they cover (`server.py` -> `test_server.py`).
- **Style/lint:** ruff, line length 100, rules `E, F, I, UP, B, SIM`
  (see `[tool.ruff.lint]`). Run `ruff format` before committing.
- **Typing:** type-hint public functions.
- **HTTP handlers:** `do_GET` / `do_POST` are the `http.server` API and carry
  `# noqa: N802`; keep the handler bound to its client via `make_handler`.
- **Testability:** `create_server(config, client=...)` accepts an injected
  client so tests can run a real server against a fake Anthropic client with no
  network. Preserve this seam.
- **Errors to the browser:** return `{"error": {"message": ...}}` JSON with an
  appropriate status; the frontend's `callClaude` reads `data.error.message`.
- **Adding a dependency:** prefer not to (stdlib backend). If unavoidable, add
  to `[project].dependencies` (runtime) or `[project.optional-dependencies].dev`.

## Security notes

- The API key is read only server-side; it must never reach the browser.
- The static file server is confined to `src/revision/static/` and rejects path
  traversal — keep that guard when touching `do_GET`.
- Rate limiting (on by default) and optional bearer auth guard `/api/messages`;
  see `config.py`. Before any public deployment, additionally serve over HTTPS
  (terminate TLS at a reverse proxy) and set `REVISION_TRUST_PROXY=true` so rate
  limiting keys off the real client IP.

## Roadmap / "going mainstream" notes

Done:

- ✅ Per-client rate limiting and optional bearer auth on `/api/messages`.
- ✅ Docker image with `/healthz` HEALTHCHECK.
- ✅ CI: ruff (lint + format) and pytest on 3.11–3.13, plus a Docker build.
- ✅ Streaming responses (SSE) on `/api/messages` (`stream: true`); Enhance
  renders live.

Likely next steps toward production:

- Persisting the model/config and per-tool token limits.
- Publishing the Docker image (registry) and a deploy target.
- A proper ASGI stack (e.g. FastAPI + uvicorn) *if* concurrency needs outgrow
  the stdlib `ThreadingHTTPServer` — this would add the first runtime deps.
- Shared/persistent rate-limit store (e.g. Redis) if run multi-process.

## Git & branching

- **Feature branches:** start each change on a fresh branch off the latest
  `main` (e.g. `claude/<short-topic>`); don't develop directly on `main`.
- **Push:** `git push -u origin <branch-name>`.
- **Pull requests:** only open a PR when explicitly requested.
- A merged PR is finished — start follow-up work from a fresh branch off the
  latest default branch rather than stacking onto merged history.

## Claude tooling (commands, skills, playbook)

This repo ships Claude Code helpers under `.claude/`, distilled from two
power-user cheat-sheets (see `docs/claude-playbook.md` for the full source):

- **Commands pack** — `docs/commands-pack.md` lists every command's slash form
  alongside its paste-ready prompt (for use in a plain claude.ai chat, where
  slash commands aren't available).
- **Slash commands** in `.claude/commands/` — the full command reference as
  reusable prompt shortcuts across six groups (focus/context, think/solve,
  organize, code, automate, personalize): `/think`, `/analyze`, `/challenge`,
  `/compare`, `/recommend`, `/solve`, `/summary`, `/outline`, `/table`,
  `/mindmap`, `/flowchart`, `/explain`, `/debug`, `/optimize`, `/refactor`,
  `/test`, `/convert`, `/workflow`, `/automate`, `/tasklist`, `/checklist`, and
  more — plus `/ultracode`, the six-stage chain described under "Working
  practices" below. Invoke with `/name [args]`. Note: `/clear`, `/memory`, and `/review`
  collide with Claude Code built-ins, which take precedence.
- **Skills** in `.claude/skills/` —
  - `claude-power-practices`: auto-applied guardrails for high-stakes work (pick
    the right model, structure prompts with XML tags, use extended thinking,
    verify facts / never fabricate links, produce real deliverables).
  - `dev-check` / `test-and-lint`: run the CI gate locally (ruff + pytest).
  - `run-app`: start and smoke-test the ReVision server.
  - `add-tool`: add a new document tool (tab) to the single-page UI.
- **`settings.json` + `hooks/`** — a `permissions.allow` list pre-authorizing
  `ruff`/`pytest`/`python`/`revision`/`curl`, plus a `SessionStart` hook
  (`hooks/session-start.sh`) that installs dev deps on a cold remote container so
  tests and linters are ready. See `.claude/README.md` for the full rundown.

> Gotcha: Claude Code only watches `.claude/` dirs that had a settings file when
> the session **started**. Editing `settings.json` or the hooks mid-session
> doesn't take effect until the next session (or opening `/hooks` once).

The prompt/command aids don't touch the ReVision app's runtime code, endpoints,
or the server-side-key rules above.

## Working practices — the 2026 loop

Integrated from the ten-panel *How To Actually Use Claude* cheat sheet
(2026 edition, framework by Denis Panjuta). These are standing instructions for
every session in this repo, alongside the playbook and skills above.

**The core loop** — apply it to every non-trivial task:

`give context → attach/read the files → set a clear success target → pick the
right model → review & refine → save the winning process as a skill`

When a process wins twice, turn it into a skill under `.claude/skills/` (that's
how `dev-check`, `run-app`, and `add-tool` got here).

**Model choice** (session-level; the *app's* model stays server-controlled in
`config.py` — verify current ids before hard-coding any):

| Model | Reach for it when… |
| --- | --- |
| Fable 5 | Hardest coding, long-horizon tasks, ambitious projects |
| Opus 4.8 | Top-tier reasoning, writing, strategy, deep analysis |
| Sonnet 5 | Default balance of speed, quality, and cost |
| Haiku 4.5 | Bulk tasks, triage, classification, simple transforms |

Start with Sonnet; upgrade to Fable or Opus when quality matters.

**The prompt template** — a good brief defines the finish line before work
starts. Expect (and when briefing sub-tasks, provide) these fields:

- **Task** — what to do · **Context** — background it needs
- **Inputs/files** — material to work from · **Constraints** — what to respect
- **Success criteria** — how "done" is judged · **Output format** — shape of
  the deliverable
- Ask a clarifying question if anything is unclear; start only when aligned.

**Standing rules** (every response):

- Read this file and the relevant repo/uploaded files *before* acting.
- Check the active project folder / branch before assuming state.
- Ask clarifying questions when the brief is ambiguous — don't guess.
- Be concise, accurate, and source-aware; never present unverified links or
  claims as fact (see `claude-power-practices`).

**Lean into / avoid:**

- ✅ Writing in the user's voice · long-context analysis · project planning ·
  research synthesis · file-based work · connected-app workflows.
- ⛔ Photo/image editing · web-search results used without checking sources ·
  vague one-line briefs · sensitive work shipped without review.

**The Ultracode** — for high-stakes tasks, run the whole loop as one six-stage
chain via [`/ultracode`](.claude/commands/ultracode.md):

`rigor → brainstorm → evaluate → detail → edit → verify`

Ground rules first, go wide, score the shortlist against stated criteria,
make the winner concrete, tighten the prose, and gate on evidence before
calling it done. Deliver the result first; then one line per stage.

## Notes for AI assistants

- Verify claims against the actual repository before acting.
- Run `pytest` and `ruff check .` before committing non-trivial changes.
- Keep this file updated as the codebase evolves; treat documentation drift as a
  bug. When you add a top-level directory, tool, endpoint, or workflow, update
  the relevant section here in the same change.
