# `.claude/` — Claude Code configuration for ReVision

This directory is repo-local Claude Code automation. It is **checked in**, so
every clone and every Claude Code on the web session picks it up automatically.

## What's here

| Path | Purpose |
|------|---------|
| `commands/check.md` | `/check` — the CI gate: `ruff check` + `ruff format --check` + `pytest` |
| `commands/run-app.md` | `/run-app` — start the ReVision server |
| `commands/smoke.md` | `/smoke` — curl health / UI / messages |
| `skills/claude-power-practices/` | Repo invariants checklist (points at `CLAUDE.md`) |
| `hooks/session-start.sh` | `SessionStart` — installs dev deps on a cold remote container |
| `settings.json` | permissions allowlist, `PostToolUse` auto-format hook, hidden attribution |

## Durable install: project `.claude/`, not `~/.claude/`

The durable, team-shared install **is this directory** — it loads directly from
the repo. Do **not** copy these files into `~/.claude/` on Claude Code on the
web: that home directory lives in an ephemeral container and is reclaimed after
the session. Copying to `~/.claude/` only makes sense on a persistent local
machine where you want the assets outside a single repo.

## Gotcha: settings created mid-session don't activate until reload

Claude Code's settings watcher only watches `.claude/` directories that already
contained a settings file when the session started. If you **create or edit**
`settings.json` (or the hooks) during a session, the new hooks and permission
rules do not take effect in that same session. To activate them:

- start a **new** session (the common case for web — the next session reads the
  committed files), or
- open the `/hooks` menu once, which reloads config.

A `SessionStart` hook added mid-session is subject to the same rule; it runs
from the *next* session onward.

## Overlap: command `allowed-tools` vs `settings.json` permissions

These are intentionally redundant, at different scopes — don't "dedupe" them:

- Each command's `allowed-tools:` frontmatter pre-authorizes the tools **that
  command** uses (e.g. `/smoke` → `Bash(curl:*)`).
- `settings.json` → `permissions.allow` pre-authorizes those same tools
  **project-wide**, so ad-hoc `ruff` / `pytest` / `curl` calls outside a command
  also skip the prompt.

Removing one does not make the other redundant; keep both.
