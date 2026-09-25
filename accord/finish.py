"""finish: everything that must hold before an Accord change is done, in one command.

python3 finish.py            # every step
python3 finish.py --quick    # every step except the mutants (seconds instead of ~half a minute)

Steps, each pass or fail, never silently skipped:
  gate       accord_test.py passes, and its tally is read back
  no-sdk     the gate passes with the anthropic SDK made unimportable, as in CI
  counts     every document that states the gate's size states this tally
  examples   every example program is accepted, builds, and its module runs standalone
  mutants    every deliberate bug in mutants.py is caught by the gate
  lint       ruff check and ruff format --check (a failure if ruff is not installed)

Exit 0 only when every step passed. What this cannot decide is listed in LANGUAGE.md.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TALLY = re.compile(r"accord: (\d+)/(\d+) passed")

# Where the gate's size is written down, as (file, pattern with {n}). Each must match once.
COUNTS = (
    (HERE / "LANGUAGE.md", "# the gate: {n} assertions"),
    (ROOT / "CLAUDE.md", "Rime (74) and Accord ({n})"),
    (ROOT / "CLAUDE.md", "accord_test.py        # the gate: {n} assertions"),
    (ROOT / "CLAUDE.md", "python3 accord_test.py` — {n} assertions,"),
    (ROOT / ".github" / "workflows" / "ci.yml", "Checks decide trust ({n} assertions)"),
)


def gate(cwd: Path, extra_env: dict | None = None) -> tuple[int, str]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", **(extra_env or {}))
    done = subprocess.run(
        [sys.executable, "accord_test.py"],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    return done.returncode, done.stdout + done.stderr


def step_gate() -> tuple[bool, str, int]:
    code, out = gate(HERE)
    found = TALLY.search(out)
    if code or not found or found[1] != found[2]:
        return False, out.strip().splitlines()[-1] if out.strip() else "no output", 0
    return True, found[0], int(found[1])


def step_no_sdk() -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as blocked:
        Path(blocked, "anthropic.py").write_text('raise ImportError("blocked by finish.py")\n')
        code, out = gate(HERE, {"PYTHONPATH": blocked})
    last = out.strip().splitlines()[-1] if out.strip() else "no output"
    return code == 0, last


def step_counts(n: int) -> tuple[bool, str]:
    wrong = []
    for path, pattern in COUNTS:
        text = path.read_text()
        if text.count(pattern.format(n=n)) != 1:
            stated = re.findall(re.escape(pattern).replace(r"\{n\}", r"(\d+)"), text)
            wrong.append(f"{path.relative_to(ROOT)} says {stated or 'nothing'}")
    return not wrong, "; ".join(wrong) or f"{len(COUNTS)} places say {n}"


def step_examples() -> tuple[bool, str]:
    sys.path.insert(0, str(HERE))
    import build
    import parse
    from core import verify_program

    problems, built = [], 0
    with tempfile.TemporaryDirectory() as out:
        for path in sorted((HERE / "examples").glob("*.accord")):
            if path.name.endswith(".intent.accord"):
                continue  # a person's part, awaiting fill: it has no bodies to accept
            report = verify_program(parse.program(path.read_text()))
            if not report.accepted:
                problems.append(f"{path.name} refused at {report.stage}")
                continue
            try:
                module = build.build(report)
            except build.BuildError as err:
                problems.append(f"{path.name}: {err}")
                continue
            stem = f"built_{path.stem}"
            Path(out, f"{stem}.py").write_text(module)
            first = next(iter(report.reports.values()))
            probe = (
                f"import sys, {stem} as m\n"
                f"assert not {{'core', 'parse', 'build', 'accord'}} & set(sys.modules)\n"
                f"print(m.trusted({first.fn.name!r}, *{first.fn.examples[0].args!r}))\n"
            )
            ran = subprocess.run(
                [sys.executable, "-E", "-s", "-c", probe],
                cwd=out,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if ran.returncode:
                problems.append(f"{path.name}: built module failed standalone: {ran.stderr[-200:]}")
            else:
                built += 1
    return not problems, "; ".join(problems) or f"{built} programs accepted, built and run alone"


def step_mutants() -> tuple[bool, str]:
    sys.path.insert(0, str(HERE))
    from mutants import MUTANTS

    stale, survived = [], []
    with tempfile.TemporaryDirectory() as scratch:
        for fname, old, new, label in MUTANTS:
            work = Path(scratch, "copy")
            shutil.rmtree(work, ignore_errors=True)
            shutil.copytree(HERE, work, ignore=shutil.ignore_patterns("__pycache__"))
            text = (work / fname).read_text()
            if old not in text:
                stale.append(label)
                continue
            (work / fname).write_text(text.replace(old, new))
            code, _ = gate(work)
            if code == 0:
                survived.append(label)
    notes = [f"stale: {', '.join(stale)}"] * bool(stale)
    notes += [f"survived: {', '.join(survived)}"] * bool(survived)
    caught = len(MUTANTS) - len(stale) - len(survived)
    return not (stale or survived), "; ".join(notes) or f"{caught} of {len(MUTANTS)} caught"


def step_lint() -> tuple[bool, str]:
    ruff = shutil.which("ruff")
    if ruff is None:
        return False, "ruff is not installed (pip install ruff); lint was not checked"
    for args in (["check", "."], ["format", "--check", "."]):
        done = subprocess.run([ruff, *args], cwd=HERE, capture_output=True, text=True)
        if done.returncode:
            return False, f"ruff {' '.join(args)}: {done.stdout.strip().splitlines()[-1]}"
    return True, "ruff check and format are clean"


def main(argv: list[str]) -> int:
    if set(argv) - {"--quick"}:
        print(__doc__)
        return 2
    results = []
    ok, note, n = step_gate()
    results.append(("gate", ok, note))
    results.append(("no-sdk", *step_no_sdk()))
    results.append(("counts", *step_counts(n)) if ok else ("counts", False, "the gate failed"))
    results.append(("examples", *step_examples()))
    if "--quick" not in argv:
        results.append(("mutants", *step_mutants()))
    results.append(("lint", *step_lint()))
    for name, passed, detail in results:
        print(f"{'pass' if passed else 'FAIL'}  {name:9} {detail}")
    failed = [name for name, passed, _ in results if not passed]
    print("finished: every step passed" if not failed else f"not finished: {', '.join(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
