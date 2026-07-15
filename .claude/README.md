# `.claude/` — Claude Code configuration for ReVision

This directory is repo-local Claude Code automation. It is **checked in**, so
every clone and every Claude Code on the web session picks it up automatically.

## What's here

| Path | Purpose |
|------|---------|
| `commands/check.md` | `/check` — the CI gate: `ruff check` + `ruff format --check` + `pytest` |
| `commands/run-app.md` | `/run-app` — start the ReVision server |
| `commands/smoke.md` | `/smoke` — curl health / UI / messages |
| `commands/{eli5,tldr,factcheck,proofread,keypoints,glossary,proscons}.md` | Content prompt-commands — text transforms on-theme with the ReVision toolkit (each takes text as its argument) |
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

## Vetting third-party Claude tools & repos

Community "Claude Code" plugin/repo lists circulate widely (often via lead-gen
posts). Before installing anything third-party into this project, confirm it's
real, current, and reputable — names go stale and attributions are often wrong.
Notes from a July 2026 review of one such list:

- **`ruvnet/claude-flow` → renamed `ruvnet/ruflo`** (Feb 2026). Use the current
  name if you go looking; the npm package is still `claude-flow`.
- `obra/superpowers` and `bmad-code-org/BMAD-METHOD` are real, active
  frameworks; `obra/superpowers` is installable from Anthropic's official plugin
  marketplace. Vet any others (stars, recent commits, official marketplace
  listing) before trusting them with repo access.
- Ignore tools that remove model safety alignment ("abliteration"/decensoring);
  they target open-weight models and are irrelevant to (and unusable with)
  Claude's API.
- Viral "Boris Cherny's CLAUDE.md operating system" graphics are community
  creations, not his real config — he's said his own setup is "surprisingly
  vanilla." Treat these principles as *ideas to adapt*, not gospel.

