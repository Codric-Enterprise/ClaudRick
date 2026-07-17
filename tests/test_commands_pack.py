"""Guard: keep ``.claude/commands/`` and ``docs/commands-pack.md`` in sync.

CLAUDE.md points readers at ``docs/commands-pack.md`` (and ``ls .claude/commands/``)
instead of enumerating every slash command inline, so that pointer must stay
honest. This test fails if a portable command file is missing from the pack, or
the pack documents a command that has no file.

Repo-specific dev commands (``/check``, ``/run-app``, ``/smoke``) are
intentionally file-only — they don't belong in the portable, paste-into-any-chat
pack — so they're excluded here. Add any new dev-only command to
``DEV_ONLY_COMMANDS``.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
COMMANDS_DIR = REPO_ROOT / ".claude" / "commands"
COMMANDS_PACK = REPO_ROOT / "docs" / "commands-pack.md"

#: Commands that live in ``.claude/commands/`` but are deliberately NOT in the
#: portable pack (repo-specific dev workflows).
DEV_ONLY_COMMANDS = {"check", "run-app", "smoke"}

#: Matches a ``/name`` slash form, e.g. in ``### /pros-cons  (also /proscons)``.
_SLASH_NAME = re.compile(r"/([a-z][a-z0-9-]*)")


def _command_files() -> set[str]:
    """Every command defined as a file: the ``.md`` stem under ``commands/``."""
    return {path.stem for path in COMMANDS_DIR.glob("*.md")}


def _documented_commands() -> set[str]:
    """Every command named in a ``### /name`` header (aliases included)."""
    names: set[str] = set()
    for line in COMMANDS_PACK.read_text(encoding="utf-8").splitlines():
        if line.startswith("### /"):
            names.update(_SLASH_NAME.findall(line))
    return names


def test_fixtures_exist() -> None:
    """Fail loudly if the paths moved, rather than passing on empty sets."""
    assert COMMANDS_DIR.is_dir(), f"missing commands dir: {COMMANDS_DIR}"
    assert COMMANDS_PACK.is_file(), f"missing pack: {COMMANDS_PACK}"
    assert _command_files(), "no command files found — check COMMANDS_DIR"
    assert _documented_commands(), "no commands parsed from the pack — check format"


def test_every_portable_command_is_documented() -> None:
    undocumented = _command_files() - _documented_commands() - DEV_ONLY_COMMANDS
    assert not undocumented, (
        "Command files missing from docs/commands-pack.md: "
        f"{', '.join(sorted(undocumented))}. Add a `### /name` entry to the pack, "
        "or, if it's a repo-specific dev command, add it to DEV_ONLY_COMMANDS."
    )


def test_no_documented_command_lacks_a_file() -> None:
    orphaned = _documented_commands() - _command_files()
    assert not orphaned, (
        "docs/commands-pack.md documents commands with no file in .claude/commands/: "
        f"{', '.join(sorted(orphaned))}. Add the command file, or remove its pack entry."
    )


def test_dev_only_commands_are_real() -> None:
    """The exclusion list must not rot: every dev-only name must still exist."""
    missing = DEV_ONLY_COMMANDS - _command_files()
    assert not missing, (
        "DEV_ONLY_COMMANDS lists commands that no longer exist: "
        f"{', '.join(sorted(missing))}. Remove them from the exclusion set."
    )
