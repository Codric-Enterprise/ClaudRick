#!/bin/bash
# SessionStart hook for ReVision.
# Ensures the package (editable) and dev tools (pytest, ruff) are available so
# tests and linters work in Claude Code on the web. Runs only in the remote
# web environment. Fires on startup/resume/clear/compact, so it skips the
# install when the environment is already set up to keep those events fast.
set -euo pipefail

# Only run in Claude Code on the web; local machines manage their own venvs.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-.}"

# Fast path: nothing to do if the package imports and both dev tools resolve.
# The container caches the install, so this is the common case on resume/compact.
if python -c 'import revision' 2>/dev/null \
  && command -v ruff >/dev/null 2>&1 \
  && command -v pytest >/dev/null 2>&1; then
  echo "ReVision dev environment already present — skipping install."
  exit 0
fi

# Cold container: editable install with dev extras. Idempotent.
python -m pip install --quiet --disable-pip-version-check -e ".[dev]"
echo "ReVision dev environment ready (pip install -e '.[dev]')."
