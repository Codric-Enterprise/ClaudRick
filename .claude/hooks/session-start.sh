#!/bin/bash
# SessionStart hook for ReVision.
# Installs the package (editable) with dev tools so pytest and ruff work in
# Claude Code on the web. Runs only in the remote web environment.
set -euo pipefail

# Only run in Claude Code on the web; local machines manage their own venvs.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-.}"

# Editable install with dev extras (pytest, ruff). Idempotent: safe to re-run,
# and the container caches the result after the hook completes.
python -m pip install --quiet --disable-pip-version-check -e ".[dev]"

echo "ReVision dev environment ready (pip install -e '.[dev]')."
