---
description: Run the full CI gate locally — ruff lint, format check, and pytest.
allowed-tools: Bash(ruff:*), Bash(pytest:*), Bash(python:*)
---

Run the same checks CI enforces, in order, and report results concisely.

1. `ruff check .`
2. `ruff format --check .`
3. `pytest`

If `python -m pytest` reports "No module named pytest", call the `pytest` /
`ruff` binaries directly (see CLAUDE.md). Summarize failures with file:line and
propose fixes; do not auto-commit.
