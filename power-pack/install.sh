#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────
#  Claude Power Pack Installer
#  77 slash commands + power-practices skill → ~/.claude/
#
#  Usage:
#    bash install.sh              # install to ~/.claude/
#    bash install.sh --dry-run    # preview without writing
#    bash install.sh --uninstall  # remove installed commands
# ─────────────────────────────────────────────────────────────────────

VERSION="1.0.0"
PACK_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="${CLAUDE_HOME:-$HOME/.claude}"
COMMANDS_SRC="$PACK_DIR/commands"
SKILLS_SRC="$PACK_DIR/skills/claude-power-practices"
DRY_RUN=false
UNINSTALL=false

for arg in "$@"; do
  case "$arg" in
    --dry-run)   DRY_RUN=true ;;
    --uninstall) UNINSTALL=true ;;
    --help|-h)
      echo "Usage: bash install.sh [--dry-run] [--uninstall]"
      echo ""
      echo "  --dry-run    Preview what would be installed/removed"
      echo "  --uninstall  Remove Power Pack commands and skill"
      echo ""
      exit 0
      ;;
    *)
      echo "Unknown option: $arg (try --help)"
      exit 1
      ;;
  esac
done

header() {
  echo ""
  echo "  ╔═══════════════════════════════════════╗"
  echo "  ║   Claude Power Pack  v${VERSION}         ║"
  echo "  ║   77 Commands + Power Practices       ║"
  echo "  ╚═══════════════════════════════════════╝"
  echo ""
}

# ── Uninstall ────────────────────────────────────────────────────────
if [[ "$UNINSTALL" == true ]]; then
  header
  removed=0
  if [[ -d "$COMMANDS_SRC" ]]; then
    for f in "$COMMANDS_SRC"/*.md; do
      name="$(basename "$f")"
      dest="$TARGET/commands/$name"
      if [[ -f "$dest" ]]; then
        if [[ "$DRY_RUN" == true ]]; then
          echo "  [dry-run] Would remove: $dest"
        else
          rm "$dest"
        fi
        ((removed++)) || true
      fi
    done
  fi
  skill_dest="$TARGET/skills/claude-power-practices/SKILL.md"
  if [[ -f "$skill_dest" ]]; then
    if [[ "$DRY_RUN" == true ]]; then
      echo "  [dry-run] Would remove: $skill_dest"
    else
      rm "$skill_dest"
      rmdir "$TARGET/skills/claude-power-practices" 2>/dev/null || true
    fi
    echo "  ✓ Removed power-practices skill"
  fi
  echo "  ✓ Removed $removed commands"
  echo ""
  exit 0
fi

# ── Install ──────────────────────────────────────────────────────────
header

# Preflight
if [[ ! -d "$COMMANDS_SRC" ]]; then
  echo "  ✗ Cannot find commands at: $COMMANDS_SRC"
  echo "    Run this script from the power-pack directory."
  exit 1
fi

if [[ "$DRY_RUN" == true ]]; then
  echo "  [dry-run mode — no files will be written]"
  echo ""
fi

echo "  Source:  $PACK_DIR"
echo "  Target:  $TARGET"
echo ""

# Backup existing commands (skip in dry-run)
if [[ -d "$TARGET/commands" ]] && ls "$TARGET/commands"/*.md &>/dev/null; then
  BACKUP="$TARGET/commands.backup.$(date +%Y%m%d%H%M%S)"
  if [[ "$DRY_RUN" == true ]]; then
    echo "  [dry-run] Would back up existing commands to:"
    echo "    $BACKUP"
  else
    echo "  → Backing up existing commands to:"
    echo "    $BACKUP"
    cp -r "$TARGET/commands" "$BACKUP"
  fi
fi

# Install commands
if [[ "$DRY_RUN" != true ]]; then
  mkdir -p "$TARGET/commands"
fi

installed=0
for f in "$COMMANDS_SRC"/*.md; do
  name="$(basename "$f")"
  if [[ "$DRY_RUN" == true ]]; then
    echo "  [dry-run] Would install: $name"
  else
    cp "$f" "$TARGET/commands/$name"
  fi
  ((installed++)) || true
done

echo "  ✓ Installed $installed commands → $TARGET/commands/"

# Install power-practices skill
if [[ -d "$SKILLS_SRC" ]]; then
  if [[ "$DRY_RUN" != true ]]; then
    mkdir -p "$TARGET/skills/claude-power-practices"
    cp "$SKILLS_SRC/SKILL.md" "$TARGET/skills/claude-power-practices/SKILL.md"
  fi
  echo "  ✓ Installed power-practices skill → $TARGET/skills/"
else
  echo "  ⚠ Power-practices skill not found; skipping."
fi

# Stamp version for future upgrades
if [[ "$DRY_RUN" != true ]]; then
  echo "$VERSION" > "$TARGET/.power-pack-version"
fi

# Summary
echo ""
echo "  ┌─────────────────────────────────────────┐"
echo "  │  Done. Start a new Claude Code session   │"
echo "  │  and type /think, /analyze, /brainstorm  │"
echo "  │  or any of the 77 commands.              │"
echo "  │                                          │"
echo "  │  They work in every project, globally.   │"
echo "  └─────────────────────────────────────────┘"
echo ""
echo "  Tip: Run with --dry-run to preview changes."
echo "  Tip: Run with --uninstall to cleanly remove."
echo ""
