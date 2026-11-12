"""Keep .claude/commands/ and docs/commands-pack.md in sync.

CLAUDE.md points at the pack instead of listing commands inline, so the pack must
document every portable command. Repo-specific dev commands (check/run-app/smoke)
are file-only by design and excluded here.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
COMMANDS_DIR = REPO_ROOT / ".claude" / "commands"
COMMANDS_PACK = REPO_ROOT / "docs" / "commands-pack.md"

# Commands that live in .claude/commands/ but are deliberately not in the pack.
DEV_ONLY_COMMANDS = {"check", "run-app", "smoke"}

# A /name slash form, e.g. in "### /pros-cons  (also /proscons)".
_SLASH_NAME = re.compile(r"/([a-z][a-z0-9-]*)")


def _command_files():
    return {path.stem for path in COMMANDS_DIR.glob("*.md")}


def _documented_commands():
    names = set()
    for line in COMMANDS_PACK.read_text(encoding="utf-8").splitlines():
        if line.startswith("### /"):
            names.update(_SLASH_NAME.findall(line))
    return names


def test_fixtures_exist():
    # Guard against a moved path passing vacuously on empty sets.
    assert COMMANDS_DIR.is_dir(), f"missing commands dir: {COMMANDS_DIR}"
    assert COMMANDS_PACK.is_file(), f"missing pack: {COMMANDS_PACK}"
    assert _command_files()
    assert _documented_commands()


def test_every_portable_command_is_documented():
    undocumented = _command_files() - _documented_commands() - DEV_ONLY_COMMANDS
    assert not undocumented, (
        "Command files missing from docs/commands-pack.md: "
        f"{', '.join(sorted(undocumented))}. Add a `### /name` entry, or add a "
        "repo-specific dev command to DEV_ONLY_COMMANDS."
    )


def test_no_documented_command_lacks_a_file():
    orphaned = _documented_commands() - _command_files()
    assert not orphaned, (
        "docs/commands-pack.md documents commands with no file: "
        f"{', '.join(sorted(orphaned))}. Add the file or remove its pack entry."
    )


def test_dev_only_commands_are_real():
    missing = DEV_ONLY_COMMANDS - _command_files()
    assert not missing, f"DEV_ONLY_COMMANDS lists nonexistent commands: {sorted(missing)}"
