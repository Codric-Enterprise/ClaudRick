# CLAUDE.md

Guidance for AI assistants (and humans) working in this repository.

## Project overview

**ClaudRick** is a Python project scaffolded with a modern `src/` layout. It
ships a small library (`claudrick.core`) and a console entry point
(`claudrick`) as a working starting point. Build/packaging is handled by
Hatchling via `pyproject.toml`.

## Repository structure

```
.
├── src/claudrick/       # package source (importable as `claudrick`)
│   ├── __init__.py      # package metadata (__version__)
│   ├── core.py          # library code (e.g. greet())
│   └── cli.py           # argparse CLI; entry point `claudrick` -> cli:main
├── tests/               # pytest suite (mirrors the package)
│   ├── test_core.py
│   └── test_cli.py
├── pyproject.toml       # build backend, deps, and tool config (pytest, ruff)
├── README.md
└── .gitignore
```

The project uses a **src layout**: importable code lives under `src/`, so tests
run against the installed/`pythonpath`-resolved package rather than loose
top-level modules. `pyproject.toml` sets `pythonpath = ["src"]` for pytest so
the suite runs without an editable install.

## Getting started

- **Python:** requires `>=3.11`.
- **Install (editable, with dev tools):**
  ```bash
  python -m venv .venv && source .venv/bin/activate
  pip install -e ".[dev]"
  ```

## Development workflows

- **Run tests:** `pytest`
- **Lint:** `ruff check .`
- **Format:** `ruff format .`
- **Run the CLI:** `claudrick [name]` (after install) or
  `PYTHONPATH=src python -m claudrick.cli [name]` (without install)

> Note: in some environments `pytest` and `ruff` are installed as standalone
> binaries rather than into the active interpreter's site-packages. If
> `python -m pytest` reports "No module named pytest", invoke the `pytest` /
> `ruff` commands directly.

## Conventions

- **Layout:** all shippable code goes under `src/claudrick/`; tests under
  `tests/` mirror the module they cover (`core.py` -> `test_core.py`).
- **Style/lint:** ruff enforces line length 100 and the rule sets
  `E, F, I, UP, B, SIM` (see `[tool.ruff.lint]`). Run `ruff format` before
  committing.
- **Typing:** prefer type hints on public functions (see `core.py` / `cli.py`).
- **CLI:** `cli.main(argv)` takes an optional argument vector and returns an
  int exit code, which keeps it directly unit-testable (see `tests/test_cli.py`).
- **Adding a dependency:** add it to `[project].dependencies` (runtime) or
  `[project.optional-dependencies].dev` (tooling) in `pyproject.toml`.

## Git & branching

- **Feature branch:** development happens on `claude/claude-md-docs-kvdwbk`
  (create it from the latest default branch if it doesn't exist).
- **Push:** `git push -u origin <branch-name>`.
- **Pull requests:** only open a PR when explicitly requested.
- A merged PR is finished — start follow-up work from a fresh branch off the
  latest default branch rather than stacking onto merged history.

## Notes for AI assistants

- Verify claims against the actual repository before acting.
- Keep this file updated as the codebase evolves; treat documentation drift as
  a bug. When you add a top-level directory, tool, or workflow, update the
  relevant section here in the same change.
- Before committing non-trivial changes, run `pytest` and `ruff check .`.
