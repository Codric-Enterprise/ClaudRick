"""The counts the docs claim, checked against the filesystem.

Three numbers in this repo were transcribed by hand and had drifted:
`claude-power-practices` said 83 commands with 84 on disk, and
`docs/commands-pack.md` carried two H1 titles — "62 commands" and "74
commands" — over 78 actual entries, because two cheat-sheets were merged
and each kept its own heading.

None of them broke anything, which is the point: a stale count fails
silently and forever. These tests make the claims checkable, so the next
command added to `.claude/commands/` turns CI red until the numbers move
with it.

Deliberately narrow. They assert the counts the docs state, not that the
docs are well written — a test that tries to judge prose gets disabled
the first time it is wrong.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: Each copy of the skill against the commands IT ships. They are not the
#: same set: `power-pack/` is a standalone distributable and deliberately
#: excludes the four repo-development commands (`/check`, `/run-app`,
#: `/smoke`, `/prd`). An earlier version of this file held both copies
#: against `.claude/commands/` — which is how it caught that the
#: power-pack skill was advertising three commands power-pack does not
#: ship, and also why it failed on a difference that is correct.
SKILLS = [
    (ROOT / ".claude/skills/claude-power-practices/SKILL.md", ROOT / ".claude/commands"),
    (ROOT / "power-pack/skills/claude-power-practices/SKILL.md", ROOT / "power-pack/commands"),
]
PACK = ROOT / "docs/commands-pack.md"

#: `/eli5` and `/pros-cons` both exist, so the pattern has to allow digits
#: and hyphens. An earlier version of this scan used `[a-z-]+`, read
#: `/eli5` as `eli`, and reported a missing command that was right there.
SLASH = re.compile(r"`/([a-z][a-z0-9-]*)`")
HEADING = re.compile(r"^#+ */([a-z0-9-]+)", re.M)


def command_files(where: Path) -> set[str]:
    return {p.stem for p in where.glob("*.md")}


def test_skill_states_the_real_command_count() -> None:
    for skill, commands in SKILLS:
        header = re.search(r"## Companion commands \((\d+) total\)", skill.read_text())
        assert header, f"{skill}: no 'Companion commands (N total)' heading"
        actual = len(command_files(commands))
        assert int(header.group(1)) == actual, (
            f"{skill.relative_to(ROOT)} claims {header.group(1)} commands; "
            f"{commands.relative_to(ROOT)} holds {actual}"
        )


def test_skill_lists_every_command_it_ships() -> None:
    """The header count is one claim; the grouped list is another.

    They can disagree in either direction, and both happened here. The
    repo copy's list was already complete at 84 while its heading said 83,
    so counting the list alone would have found nothing. The power-pack
    copy's heading was close but its list named three commands that
    distributable does not contain — someone installing it would read
    `/check` in the skill and find no such command.
    """
    for skill, commands in SKILLS:
        listed = set(SLASH.findall(skill.read_text()))
        shipped = command_files(commands)
        assert not (shipped - listed), (
            f"{skill.relative_to(ROOT)} does not list: {sorted(shipped - listed)}"
        )
        assert not (listed - shipped), (
            f"{skill.relative_to(ROOT)} lists commands not in "
            f"{commands.relative_to(ROOT)}: {sorted(listed - shipped)}"
        )


def test_commands_pack_has_one_title_and_it_is_right() -> None:
    text = PACK.read_text()
    titles = re.findall(r"^# Claude Commands Pack — (\d+) commands$", text, re.M)
    assert len(titles) == 1, (
        f"{PACK.relative_to(ROOT)} has {len(titles)} title lines; it carried "
        f"two for a while, claiming different totals"
    )
    documented = len(set(HEADING.findall(text)))
    assert int(titles[0]) == documented, (
        f"{PACK.relative_to(ROOT)} titles itself {titles[0]} commands and documents {documented}"
    )
