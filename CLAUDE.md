# CLAUDE.md

Guidance for AI assistants (and humans) working in this repository.

## Current state: empty / greenfield

> **This repository currently has no source code.** As of the last update to this
> file, `Zdycomp/ClaudRick` contained no commits, no application code, no build
> configuration, and no dependencies — only this `CLAUDE.md`.
>
> Do **not** treat any of the sections below as descriptions of existing code.
> They are placeholders/scaffolding. As real code lands, replace each `TODO`
> with an accurate description of what actually exists. Never document a
> structure, command, or convention that isn't really present — an inaccurate
> `CLAUDE.md` is worse than none.

When you add the first real code to this project, please update the sections
below in the same change so this file stays trustworthy.

## Project overview

**TODO** — Describe what this project is, who it's for, and what it does.
(Name on the remote: `ClaudRick`. Purpose: not yet defined in the repo.)

## Repository structure

**TODO** — Document the directory layout once it exists. For example:

```
.
├── src/        # TODO: application source
├── tests/      # TODO: test suite
└── ...
```

## Getting started

**TODO** — Fill in once tooling is chosen. Typical items to document:

- Language / runtime and required version
- How to install dependencies
- Required environment variables / config files
- How to run the project locally

## Development workflows

**TODO** — Document the real commands once they exist, e.g.:

- **Install:** `TODO`
- **Run / dev server:** `TODO`
- **Build:** `TODO`
- **Test:** `TODO`
- **Lint / format:** `TODO`
- **Type-check:** `TODO`

Until these are defined, do not guess commands — inspect the repo (package
manifest, Makefile, CI config) and document what is actually configured.

## Conventions

**TODO** — Capture coding style, naming, commit-message format, and any
architectural rules once the project establishes them.

## Git & branching

These conventions are defined for this project independent of the code:

- **Feature branch:** development happens on `claude/claude-md-docs-kvdwbk`
  (create it from the latest default branch if it doesn't exist).
- **Push:** `git push -u origin <branch-name>`.
- **Pull requests:** only open a PR when explicitly requested.
- A merged PR is finished — start follow-up work from a fresh branch off the
  latest default branch rather than stacking onto merged history.

## Notes for AI assistants

- Verify claims against the actual repository before acting — this file is a
  scaffold, not a source of truth about existing code.
- Keep this file updated as the codebase evolves; treat documentation drift as
  a bug.
