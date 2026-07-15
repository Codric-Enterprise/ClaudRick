#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────
#  Claude Power Pack Installer
#  80 slash commands + power-practices skill → ~/.claude/
#  Run:  bash install-power-pack.sh
# ─────────────────────────────────────────────────────────────────────

PACK_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="${CLAUDE_HOME:-$HOME/.claude}"
COMMANDS_SRC="$PACK_DIR/.claude/commands"
SKILLS_SRC="$PACK_DIR/.claude/skills/claude-power-practices"

echo ""
echo "  ╔═══════════════════════════════════════╗"
echo "  ║   Claude Power Pack — 80 Commands     ║"
echo "  ║   + Power Practices Guardrails        ║"
echo "  ╚═══════════════════════════════════════╝"
echo ""

# ── Preflight ────────────────────────────────────────────────────────
if [[ ! -d "$COMMANDS_SRC" ]]; then
  echo "  ✗ Cannot find commands at: $COMMANDS_SRC"
  echo "    Run this script from the repo root."
  exit 1
fi

echo "  Source:  $PACK_DIR"
echo "  Target:  $TARGET"
echo ""

# ── Backup existing commands if any ──────────────────────────────────
if [[ -d "$TARGET/commands" ]] && ls "$TARGET/commands"/*.md &>/dev/null; then
  BACKUP="$TARGET/commands.backup.$(date +%Y%m%d%H%M%S)"
  echo "  → Backing up existing commands to:"
  echo "    $BACKUP"
  cp -r "$TARGET/commands" "$BACKUP"
fi

# ── Install commands ─────────────────────────────────────────────────
mkdir -p "$TARGET/commands"
installed=0
skipped=0
for f in "$COMMANDS_SRC"/*.md; do
  name="$(basename "$f")"
  # Skip repo-specific dev commands (check, run-app, smoke)
  case "$name" in
    check.md|run-app.md|smoke.md)
      ((skipped++)) || true
      continue
      ;;
  esac
  cp "$f" "$TARGET/commands/$name"
  ((installed++)) || true
done

echo "  ✓ Installed $installed commands → $TARGET/commands/"
if ((skipped > 0)); then
  echo "    ($skipped repo-specific dev commands skipped: check, run-app, smoke)"
fi

# ── Install power-practices skill ────────────────────────────────────
if [[ -d "$SKILLS_SRC" ]]; then
  mkdir -p "$TARGET/skills/claude-power-practices"
  cp "$SKILLS_SRC/SKILL.md" "$TARGET/skills/claude-power-practices/SKILL.md"
  echo "  ✓ Installed power-practices skill → $TARGET/skills/claude-power-practices/"
else
  echo "  ⚠ Power-practices skill not found; skipping."
fi

# ── Summary ──────────────────────────────────────────────────────────
echo ""
echo "  ┌─────────────────────────────────────────┐"
echo "  │  Done. Start a new Claude Code session   │"
echo "  │  and type /think, /analyze, /brainstorm  │"
echo "  │  or any of the 77 commands.              │"
echo "  │                                          │"
echo "  │  They work in every project, globally.   │"
echo "  └─────────────────────────────────────────┘"
echo ""
echo "  Tip: See docs/commands-pack.md for the"
echo "  paste-ready version (for claude.ai chats)."
echo ""
