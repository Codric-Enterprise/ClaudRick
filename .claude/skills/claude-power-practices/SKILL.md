---
name: claude-power-practices
description: Repo-specific working agreements for the ReVision toolkit — the security/architecture invariants an AI assistant must respect when editing this codebase. Use when adding endpoints, touching the Anthropic proxy, wiring the frontend, adding dependencies, or before committing changes.
---

# Claude power practices for ReVision

`CLAUDE.md` at the repo root is the **single source of truth** for how this
project is built. This skill is a fast-access checklist of the load-bearing
invariants plus the local automation that supports them — not a second copy of
the docs. When this skill and `CLAUDE.md` disagree, `CLAUDE.md` wins; fix the
skill in the same change (see "Keep in sync" below).

## Hard invariants (break these and you break the product)

Kept inline because they're safety-critical and you should see them without
opening another file. Full rationale lives in `CLAUDE.md` → *Architecture* and
*Security notes*.

- **Server-side API key.** The browser calls same-origin `/api/messages` only,
  never `api.anthropic.com`. The `x-api-key` / `anthropic-version` headers are
  added in `anthropic_client.py`. Never move the key or a direct Anthropic call
  into `static/index.html`.
- **Model is server-controlled.** The model id lives in `config.py`
  (`REVISION_MODEL`) — never hard-code it in the frontend, and always use a
  real model id.
- **Stdlib-only backend.** Runtime code uses only the standard library; add a
  runtime dependency only with strong reason. `pytest` / `ruff` are dev-only.
- **Static server is sandboxed.** `do_GET` serves only from
  `src/revision/static/` with a path-traversal guard — preserve it.
- **Preserve the test seam.** `create_server(config, client=...)` accepts an
  injected client so tests run a real server against a fake Anthropic client
  with no network. Keep it injectable.

## Conventions — see `CLAUDE.md`, don't duplicate here

These live in `CLAUDE.md` and are the authority; this is just a map so you know
which section to open:

- **Layout & structure** → *Repository structure* (src layout; `tests/` mirror
  their module; `static/` ships inside the package).
- **Error contract** → *HTTP endpoints* (`{"error": {"message": ...}}` with
  400 / 401 / 429+`Retry-After` / 502; `callClaude` reads `data.error.message`).
- **Handler style & lint rules** → *Conventions* (`do_GET`/`do_POST` `# noqa:
  N802` via `make_handler`; ruff line length 100, rules `E,F,I,UP,B,SIM`;
  type-hint public functions).

## Local automation (this repo's `.claude/`)

- `/check` — the CI gate: `ruff check .` + `ruff format --check .` + `pytest`.
- `/run-app` — start the server; `/smoke` — curl health / UI / messages.
- A `PostToolUse` hook auto-runs `ruff check --fix --select I` then
  `ruff format` on `.py` files, so writes don't leave import order failing the
  gate. It's a safety net, not a substitute for running `/check`.
- The `SessionStart` hook installs `pip install -e ".[dev]"` on a cold remote
  container. See `.claude/README.md` for how these load (and the mid-session
  watcher caveat).

## Before you commit

- Run `/check` (or `ruff check .`, `ruff format --check .`, `pytest`). If
  `python -m pytest` can't find the module, call the `pytest` / `ruff` binaries
  directly.
- Verify claims against the actual repo before asserting them.
- Only open a PR when explicitly asked.

## Keep in sync

When you change a rule this skill mentions, update `CLAUDE.md` (the source of
truth) **and** this skill in the same change. Documentation drift is a bug —
`CLAUDE.md` says so, and a checklist that lies is worse than none.
