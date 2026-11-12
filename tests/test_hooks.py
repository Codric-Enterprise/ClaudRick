"""The PreToolUse hooks in ``.claude/hooks/``, driven the way Claude Code drives them.

Each case feeds the hook a ``tool_input`` JSON on stdin and reads the exit code:
2 means "blocked", 0 means "allowed". The commands below are the ones the hooks
used to let through (global options between ``git`` and the verb, clustered
short flags, ``--force`` next to ``--force-with-lease``, ``git commit -a``) as
well as the ones they must keep allowing.

Fake credentials are assembled at runtime so this file never contains a string
the secret scan would itself reject.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude" / "hooks"
GUARD = HOOKS / "git-safety-guard.sh"
SCAN = HOOKS / "secret-scan-precommit.sh"

needs_tools = pytest.mark.skipif(
    shutil.which("jq") is None or shutil.which("bash") is None,
    reason="hooks need bash and jq",
)


def _run(script: Path, command: str, *, env: dict | None = None, tool="Bash"):
    payload = json.dumps({"tool_name": tool, "tool_input": {"command": command}})
    return subprocess.run(
        ["bash", str(script)],
        input=payload,
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
        timeout=30,
    )


BLOCKED = [
    # force pushes, including every spelling that used to evade the check
    "git push --force",
    "git push -f origin main",
    "git push -fu origin feature",
    "git push -uf origin feature",
    "git push --force=true origin main",
    "git -C . push --force",
    "git -c user.name=x push -f",
    "git --no-pager push --force",
    "git push --force-with-lease --force",
    "git push origin +main",
    "git push origin :main",
    "git push --delete origin stale",
    "git push -d origin stale",
    "git push --mirror",
    "git push --no-verify",
    # history / working-tree destruction
    "git reset --hard HEAD~1",
    "git -C sub reset --hard",
    "git clean -fd",
    "git clean --force",
    "git -C . clean -fdx",
    "git branch -D old",
    "git branch -d -f old",
    "git branch -df old",
    "git branch --delete --force old",
    "git checkout .",
    "git checkout -- .",
    "git checkout -f",
    "git checkout --force main",
    "git restore .",
    "git restore --source=HEAD --staged --worktree .",
    # skipping hooks / signing
    "git commit --no-verify -m x",
    "git commit -n -m x",
    "git commit -nm x",
    "git -C . commit -n -m x",
    "git commit --no-gpg-sign -m x",
    "git -c commit.gpgsign=false commit -m x",
    # a harmless first command must not hide the dangerous second one
    "git status && git push -f",
    "git push origin x && git reset --hard",
    "git push \\\n  --force",
    "echo start\ngit push origin\ngit clean -f",
]

ALLOWED = [
    "git status",
    "git push",
    "git push -u origin feature",
    "git push origin main:other",
    "git push --force-with-lease",
    "git push --force-with-lease origin main",
    "git push --force-with-lease origin +main",
    "git -C sub status",
    "git log --oneline -n 5",
    "git diff --stat -- .",
    "git reset --soft HEAD~1",
    "git reset HEAD file.txt",
    "git clean -n",
    "git branch -d merged",
    "git branch --list",
    "git checkout -b new-branch",
    "git checkout main",
    "git restore --staged .",
    "git restore file.txt",
    "git commit -m 'fix the thing'",
    "git commit -am 'fix the thing'",
    "git commit --amend --no-edit",
    "git stash",
    "ls -la",
    "echo 'remember not to use --force here'",
]


@needs_tools
@pytest.mark.parametrize("command", BLOCKED)
def test_guard_blocks(command):
    result = _run(GUARD, command)
    assert result.returncode == 2, f"expected block: {command!r}\n{result.stderr}"
    assert "git-safety-guard blocked" in result.stderr


@needs_tools
@pytest.mark.parametrize("command", ALLOWED)
def test_guard_allows(command):
    result = _run(GUARD, command)
    assert result.returncode == 0, f"expected allow: {command!r}\n{result.stderr}"


@needs_tools
def test_guard_ignores_other_tools():
    assert _run(GUARD, "git push --force", tool="Read").returncode == 0


# --- secret scan --------------------------------------------------------------

#: Built from pieces so no literal in this file matches the scanner's patterns.
SECRETS = {
    "anthropic": "sk-" + "ant-" + "a" * 30,
    "openai-project": "sk-" + "proj-" + "b" * 30,
    "aws": "AK" + "IA" + "A" * 16,
    "github-classic": "gh" + "p_" + "c" * 36,
    "github-oauth": "gh" + "o_" + "c" * 36,
    "github-fine-grained": "github" + "_pat_" + "d" * 30,
    "stripe": "sk" + "_live_" + "e" * 24,
    "google": "AI" + "za" + "f" * 35,
    "pem": "-----BEGIN " + "RSA PRIVATE KEY-----",
}


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "app.py").write_text("print('hello')\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "init")
    return tmp_path


def _scan(repo: Path, command: str):
    return _run(SCAN, command, env={"CLAUDE_PROJECT_DIR": str(repo)})


@needs_tools
@pytest.mark.parametrize("secret", SECRETS.values(), ids=SECRETS.keys())
def test_scan_blocks_staged_secret(repo, secret):
    (repo / "app.py").write_text(f"KEY = '{secret}'\n")
    _git(repo, "add", "app.py")
    result = _scan(repo, "git commit -m 'add key'")
    assert result.returncode == 2, result.stderr
    assert "secret-scan-precommit blocked" in result.stderr


@needs_tools
@pytest.mark.parametrize(
    "command",
    [
        "git commit -am 'x'",
        "git commit -a -m 'x'",
        "git commit --all -m 'x'",
        "git -C . commit -am x",
    ],
)
def test_scan_blocks_unstaged_secret_when_commit_takes_it(repo, command):
    (repo / "app.py").write_text(f"KEY = '{SECRETS['anthropic']}'\n")  # modified, not staged
    assert _scan(repo, command).returncode == 2


@needs_tools
def test_scan_ignores_unstaged_secret_for_plain_commit(repo):
    """A plain `git commit` records only the index, so an unstaged secret isn't in it."""
    (repo / "app.py").write_text(f"KEY = '{SECRETS['anthropic']}'\n")
    assert _scan(repo, "git commit -m 'nothing staged'").returncode == 0


@needs_tools
def test_scan_sees_commit_behind_global_options(repo):
    (repo / "app.py").write_text(f"KEY = '{SECRETS['aws']}'\n")
    _git(repo, "add", "app.py")
    assert _scan(repo, "git -C . commit -m x").returncode == 2
    assert _scan(repo, "git -c user.name=x commit -m x").returncode == 2


@needs_tools
def test_scan_allows_clean_commits_and_non_commits(repo):
    (repo / "app.py").write_text("print('still fine')\n")
    _git(repo, "add", "app.py")
    assert _scan(repo, "git commit -m 'clean'").returncode == 0
    assert _scan(repo, "git commit -am 'clean'").returncode == 0
    assert _scan(repo, "git status").returncode == 0
    (repo / "app.py").write_text(f"KEY = '{SECRETS['anthropic']}'\n")
    _git(repo, "add", "app.py")
    assert _scan(repo, "git log").returncode == 0  # not a commit: not scanned


# --- no jq --------------------------------------------------------------------


@pytest.fixture
def no_jq_env(tmp_path):
    """A PATH holding the few tools the hooks need, but not jq."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in ("grep", "sed", "cat"):
        found = shutil.which(tool)
        if found is None:
            pytest.skip(f"{tool} not available")
        (bin_dir / tool).symlink_to(found)
    return {"PATH": str(bin_dir)}


@pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")
@pytest.mark.parametrize("script", [GUARD, SCAN], ids=["guard", "scan"])
def test_hooks_fail_closed_on_git_commands_without_jq(script, no_jq_env):
    bash = shutil.which("bash")
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}})
    result = subprocess.run(
        [bash, str(script)], input=payload, capture_output=True, text=True, env=no_jq_env
    )
    assert result.returncode == 2
    assert "jq is not installed" in result.stderr


@pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")
@pytest.mark.parametrize("script", [GUARD, SCAN], ids=["guard", "scan"])
def test_hooks_let_non_git_commands_through_without_jq(script, no_jq_env):
    bash = shutil.which("bash")
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls -la"}})
    result = subprocess.run(
        [bash, str(script)], input=payload, capture_output=True, text=True, env=no_jq_env
    )
    assert result.returncode == 0
