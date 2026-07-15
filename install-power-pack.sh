#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────
#  Claude Power Pack Installer (wrapper)
#  Delegates to power-pack/install.sh — the standalone distributable.
#  Run:  bash install-power-pack.sh [--dry-run] [--uninstall]
# ─────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec bash "$SCRIPT_DIR/power-pack/install.sh" "$@"
