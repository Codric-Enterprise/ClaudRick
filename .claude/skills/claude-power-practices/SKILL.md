---
name: claude-power-practices
description: Repo-specific working agreements for the ReVision toolkit — the invariants and workflows an AI assistant must respect when editing this codebase. Use when adding endpoints, touching the Anthropic proxy, wiring the frontend, adding dependencies, or before committing changes.
---

# Claude power practices for ReVision

Distilled from `CLAUDE.md`. When any of these apply to your change, follow them
exactly — they encode security and architecture invariants, not preferences.

## Hard invariants (do not break)

- **Server-side API key.** The browser calls same-origin `/api/messages` only,
  never `api.anthropic.com`. The `x-api-key` / `anthropic-version` headers are
  added in `anthropic_client.py`. Never move the key or a direct Anthropic call
  into `static/index.html`.
- **Model is server-controlled.** The model id lives in `config.py`
  (`REVISION_MODEL`, default `claude-sonnet-5`) — never hard-code it in the
  frontend, and always use a real model id.
- **Stdlib-only backend.** Runtime code uses only the standard library
  (`http.server`, `urllib`). Don't add runtime deps without a strong reason;
  `pytest` / `ruff` are dev-only.
- **Static server is sandboxed.** `do_GET` serves only from
  `src/revision/static/` with a path-traversal guard — preserve it.
- **Preserve the test seam.** `create_server(config, client=...)` accepts an
  injected client so tests run a real server against a fake Anthropic client
  with no network. Keep it injectable.

## Conventions

- **src layout.** Shippable code under `src/revision/`; tests under `tests/`
  mirror their module (`server.py` → `test_server.py`). `static/` lives inside
  the package so it ships in the wheel.
- **Errors to the browser.** Return `{"error": {"message": ...}}` JSON with an
  apt status (400 bad input, 401 auth, 429 rate limit + `Retry-After`, 502
  Anthropic). The frontend's `callClaude` reads `data.error.message`.
- **HTTP handlers.** `do_GET` / `do_POST` carry `# noqa: N802`; keep the handler
  bound to its client via `make_handler`.
- **Style.** ruff, line length 100, rules `E, F, I, UP, B, SIM`. Type-hint
  public functions. Run `ruff format` before committing.

## Before you commit

- Run the CI gate: `ruff check .`, `ruff format --check .`, `pytest` (the
  `/check` command does all three). Note: if `python -m pytest` can't find the
  module, call the `pytest` / `ruff` binaries directly.
- Keep docs honest: when you add a top-level directory, tool, endpoint, or
  workflow, update the matching section of `CLAUDE.md` in the same change.
- Verify claims against the actual repo before asserting them.
- Only open a PR when explicitly asked.
