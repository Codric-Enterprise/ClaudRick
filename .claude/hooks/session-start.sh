#!/bin/bash
# SessionStart hook for this repository.
#
# Two jobs, because the repo holds two unrelated projects:
#
#   1. ReVision (src/revision) — install the package (editable) and the dev
#      tools (pytest, ruff) so tests and linters work.
#   2. EZR (ezr/) — do not install, but VERIFY the C / C++ / Ruby / Java
#      toolchains its gate needs, because `ezr/run.sh` and
#      `ezr/tests/algebra_parity.py` SKIP a layer whose toolchain is absent
#      and still exit 0. A container missing gcc reports
#      "verified 8  skipped 14  failed 0" and reads green while a third of
#      the language went unchecked. Silence is the failure mode, so the
#      hook breaks the silence at session start.
#
# Runs only in the remote web environment. Fires on startup/resume/clear/
# compact, so each half fast-paths when it is already satisfied.
set -euo pipefail

# Only run in Claude Code on the web; local machines manage their own venvs.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-.}"

# Load local env vars (GITHUB_TOKEN, ANTHROPIC_API_KEY, etc.) from a gitignored
# `.env` if the developer created one from `.env.example`. Scoped to this hook
# process; use it for anything the hook runs, and source `.env` in your own
# shell (`set -a; . ./.env; set +a`) for interactive work.
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

# ---------------------------------------------------------------- ReVision --
# Fast path: nothing to do if the package imports and both dev tools resolve.
# The container caches the install, so this is the common case on resume/compact.
if python -c 'import revision' 2>/dev/null \
  && command -v ruff >/dev/null 2>&1 \
  && command -v pytest >/dev/null 2>&1; then
  echo "ReVision dev environment already present — skipping install."
else
  # Cold container: editable install with dev extras. Idempotent.
  python -m pip install --quiet --disable-pip-version-check -e ".[dev]"
  echo "ReVision dev environment ready (pip install -e '.[dev]')."
fi

# --------------------------------------------------------------------- EZR --
# Only relevant if the language project is present in this checkout.
[ -d ezr ] || exit 0

# tool:apt-package:what silently goes unverified when it is missing
EZR_TOOLCHAIN=(
  "gcc:gcc:layers 0/TAC/EvScope/Bridge/IR/EValue/ABI (C) + algebra_parity C"
  "g++:g++:layer 1 (C++ phase engine)"
  "ruby:ruby:layer 3 (Ruby DSL) + algebra_parity Ruby"
  "javac:default-jdk:5-runtime-java build + algebra_parity Java"
  "java:default-jre:5-runtime-java RuntimeTest + differential.py"
)

missing_pkgs=()
missing_report=()
for entry in "${EZR_TOOLCHAIN[@]}"; do
  tool="${entry%%:*}"
  rest="${entry#*:}"
  pkg="${rest%%:*}"
  covers="${rest#*:}"
  if ! command -v "$tool" >/dev/null 2>&1; then
    missing_pkgs+=("$pkg")
    missing_report+=("$tool -> $covers")
  fi
done

if [ ${#missing_pkgs[@]} -eq 0 ]; then
  echo "EZR toolchain complete (gcc, g++, ruby, javac, java) — no layer will be skipped."
else
  echo "EZR toolchain INCOMPLETE — these layers would be SKIPPED, and the gate would still exit 0:"
  for line in "${missing_report[@]}"; do
    echo "    $line"
  done
  # Best effort. Never fail the session over it: a degraded container that is
  # KNOWN to be degraded is workable; one that looks green is not.
  if command -v apt-get >/dev/null 2>&1 && [ "$(id -u)" = "0" ]; then
    echo "  attempting: apt-get install ${missing_pkgs[*]}"
    if apt-get update -qq >/dev/null 2>&1 \
      && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${missing_pkgs[@]}" >/dev/null 2>&1; then
      echo "  install completed — re-checking:"
    else
      echo "  install failed (no network, or package unavailable)."
    fi
    still=()
    for entry in "${EZR_TOOLCHAIN[@]}"; do
      tool="${entry%%:*}"
      command -v "$tool" >/dev/null 2>&1 || still+=("$tool")
    done
    if [ ${#still[@]} -eq 0 ]; then
      echo "  EZR toolchain now complete."
    else
      echo "  STILL MISSING: ${still[*]} — treat any 'skipped' line in run.sh as a real gap, not a pass."
    fi
  else
    echo "  no apt-get or not root — install these manually before trusting the EZR gate."
  fi
fi

# `JAVA_TOOL_OPTIONS` makes the JVM print a banner to stderr on every start,
# which breaks the byte comparison differential.py depends on. Setting it empty
# does not help; it has to be removed at the call site (`env -u`). Warn rather
# than pretend the hook can unset it for the session.
if [ -n "${JAVA_TOOL_OPTIONS:-}" ]; then
  echo "WARNING: JAVA_TOOL_OPTIONS is set — its banner corrupts differential.py's byte comparison."
  echo "         Run java as: env -u JAVA_TOOL_OPTIONS java ...  (the ezr/5-runtime-java/ezr wrapper already does)"
fi
