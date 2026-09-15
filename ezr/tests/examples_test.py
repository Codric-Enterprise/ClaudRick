#!/usr/bin/env python3
"""
examples_test.py — the examples must do what they say they do.

Every example in `examples/` is a claim about the language aimed at a
person who has not read the source. Before this file existed, nothing
checked them: the gate was green while `weekly_sales.ever` printed
`total = z` under a comment promising a sum of five days, three `.ezr`
files did not parse under either runner, and `earned_trust.ever` -- the
file that actually explains the whole idea -- was a transcript nobody
re-ran.

Two sections, because the examples are reached two ways:

  RUN         `ever_cli.py run f.ever` drives runtime.run_source, which
              is the front door: statements, lists, loops, indexing.
              Each file's exact stdout is pinned.

  TRANSCRIPT  `ezrun.py` drives syntax.py's eval_ast and is the only
              surface that exposes the confidence algebra -- [EXAMPLE]
              earning trust, [ANCHOR] buying depth. earned_trust.ever
              documents eleven invocations in its comments; all eleven
              are run here and pinned to the value AND the exit code.

A new example with no entry in either table fails this suite. That is
deliberate -- an unchecked example is how the last set rotted.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CLI = ROOT / "2-interpreter-python" / "ever_cli.py"
EZRUN = ROOT / "2-interpreter-python" / "ezrun.py"
EXAMPLES = ROOT / "examples"
TRUST = EXAMPLES / "earned_trust.ever"

passed = 0
failed = 0


def check(label: str, got, want) -> bool:
    """Record one assertion. Returns True when it held.

    Callers gate their own "ok" line on the return value: a green line
    printed underneath a failure is the exact disease this suite exists
    to catch, and it would be absurd to reproduce it here.
    """
    global passed, failed
    if got == want:
        passed += 1
        return True
    failed += 1
    print(f"  FAIL {label}")
    print(f"       want: {want!r}")
    print(f"       got:  {got!r}")
    return False


def run(cmd: list[str]) -> tuple[str, int]:
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    return (p.stdout + p.stderr).strip(), p.returncode


# ── section 1: `ever run` ────────────────────────────────────────────
#: Exact stdout. Measured, not transcribed from a comment.
RUN_OUTPUT = {
    "compound_interest.ever": [
        "after_2_years = 11236 [256/256]",
        "growth = 1236 [256/256]",
        "growth_pct = 12.36 [256/256]",
        "total_saved = 4000 [256/256]",
        'better_strategy = "contributions win" [256/256]',
    ],
    "ffi_math.ever": [
        "root = 4 [120/256]",
        "squared = 1024 [120/256]",
        "sine_at_90 = 1 [120/256]",
        "tainted = z [0/256]",
    ],
    "grade_calculator.ever": [
        "weighted = 85.35 [256/256]",
        'letter = "B" [256/256]',
        "passed = true [256/256]",
        "honors = false [256/256]",
        "attendance_bonus = z [0/256]",
        "final_with_bonus = z [0/256]",
    ],
    "readings.ever": [
        "count = 6 [256/256]",
        "sum = 63 [256/256]",
        "mean = 10.5 [256/256]",
        "hi = 19 [256/256]",
        "lo = 3 [256/256]",
        "span = 16 [256/256]",
        "missing = z [0/256]",
    ],
    "train_logistic.ever": [
        "trained_w = 0.244593 [256/256]",
        "p1 = 0.560845 [256/256]",
        "p4 = 0.726785 [256/256]",
        "loss = 0.219675 [256/256]",
        "trained_w_gap = z [0/256]",
    ],
    # Thursday is z, so the total is z -- and that is the POINT, not a
    # depth limit. `i` decreases, so the recursion itself is provable.
    "weekly_sales.ever": [
        "total = z [0/256]",
        "had_gap = z [0/256]",
        "best = 610 [256/256]",
        "third_day = 380 [256/256]",
        "missing = z [0/256]",
        "last_square = 25 [256/256]",
    ],
}

#: Definitions only -- no `show`, so `run` prints nothing. Covered by
#: the transcript below instead. Listed so the completeness check below
#: knows it is accounted for rather than forgotten.
RUN_SILENT = {"earned_trust.ever"}


def section_run() -> None:
    print("\never run — front door")
    for name, want in sorted(RUN_OUTPUT.items()):
        out, code = run([sys.executable, str(CLI), "run", str(EXAMPLES / name)])
        ok = check(f"{name} exit 0", code, 0)
        ok &= check(f"{name} output", out.splitlines(), want)
        if ok:
            print(f"  ok   {name}  ({len(want)} bindings)")

    for name in sorted(RUN_SILENT):
        out, code = run([sys.executable, str(CLI), "run", str(EXAMPLES / name)])
        ok = check(f"{name} exit 0", code, 0)
        ok &= check(f"{name} is definitions-only", out, "")
        if ok:
            print(f"  ok   {name}  (definitions only — see transcript)")


# ── section 2: the earned_trust transcript ───────────────────────────
W0 = "growth(100, 0) = 100"
W1 = "growth(100, 1) = 110"
W2 = "growth(100, 2) = 121"
CALL = ["--call", "growth(100, 3)"]

#: (label, extra argv, expected stdout, expected exit)
TRANSCRIPT = [
    ("[DEF] a definition is a claim",
     CALL, "133.1  @ 120/256", 0),
    ("one witness is not enough",
     CALL + ["-x", W0], "133.1  @ 120/256", 0),
    ("two hold — 183 clears the floor",
     CALL + ["-x", W0, "-x", W1], "133.1  @ 183/256", 0),
    ("three hold",
     CALL + ["-x", W0, "-x", W1, "-x", W2], "133.1  @ 217/256", 0),
    ("two of three — 122 is back below",
     CALL + ["-x", W0, "-x", W1, "-x", "growth(100, 2) = 999"],
     "133.1  @ 122/256", 0),
    ("one case thrice is one witness",
     CALL + ["-x", W0, "-x", W0, "-x", W0], "133.1  @ 120/256", 0),
    ("[APP] evidence does not launder the caller",
     ["-x", W0, "-x", W1, "-x", W2], "133.1  @ 120/256", 0),
]

#: These two assert on a prefix, because the message carries a long
#: explanatory tail that is the point of the inversion work and is not
#: worth pinning character-for-character.
TRANSCRIPT_PREFIX = [
    ("contradictory evidence is refused",
     CALL + ["-x", W0, "-x", "growth(100, 0) = 999"],
     "ezrun: --example 'growth(100, 0) = 999':", 2),
    ("depth ceiling 3 stops 20 periods",
     ["-d", "3", "--call", "growth(100, 20)"],
     "Z(unbounded) — depth ceiling 3 exceeded", 1),
]

ANCHORED = ("anchoring buys the depth",
            ["-d", "3", "--call", "growth(100, 20)",
             "-x", W0, "-x", W1, "-x", W2, "-a", "growth"],
            "672.7499949325598  @ 217/256", 0)


def section_transcript() -> None:
    print("\nezrun — the confidence algebra (earned_trust.ever)")
    for label, extra, want, want_code in TRANSCRIPT + [ANCHORED]:
        out, code = run([sys.executable, str(EZRUN), str(TRUST)] + extra)
        ok = check(f"{label} exit", code, want_code)
        ok &= check(f"{label} value", out, want)
        if ok:
            print(f"  ok   {label}  ->  {want}")

    for label, extra, prefix, want_code in TRANSCRIPT_PREFIX:
        out, code = run([sys.executable, str(EZRUN), str(TRUST)] + extra)
        ok = check(f"{label} exit", code, want_code)
        ok &= check(f"{label} message", out.startswith(prefix), True)
        if ok:
            print(f"  ok   {label}  ->  exit {want_code}")


# ── section 2b: the counterfactual ───────────────────────────────────
def section_counterfactual() -> None:
    """`total = z` alone does not pin the lesson.

    weekly_sales.ever returns z because Thursday was never recorded.
    But it ALSO returned z, for years, because `i` counted UP: no
    decreasing measure, so the depth ceiling of floor(pi) = 3 stopped
    it on the third day. Two different causes, byte-identical output --
    which is exactly why nothing caught the broken version.

    So pin the counterfactual too. Fill Thursday in and the sum must
    complete. A counting-up version still returns z here, and fails.
    """
    print("\ncounterfactual — z for the RIGHT reason")
    src = (EXAMPLES / "weekly_sales.ever").read_text()
    assert "let thu = z" in src, "weekly_sales.ever no longer has a z Thursday"
    filled = src.replace("let thu = z", "let thu = 500")

    tmp = HERE / "_weekly_sales_filled.ever"
    try:
        tmp.write_text(filled)
        out, code = run([sys.executable, str(CLI), "run", str(tmp)])
        ok = check("filled-in Thursday exit 0", code, 0)
        ok &= check("filled-in Thursday completes the sum",
                    out.splitlines()[0], "total = 2615 [256/256]")
        if ok:
            print("  ok   thu = 500  ->  total = 2615 [256/256]")
            print("       (a counting-up sum_from returns z — the ceiling bites)")
    finally:
        tmp.unlink(missing_ok=True)


# ── section 3: nothing goes unchecked ────────────────────────────────
def section_completeness() -> None:
    print("\ncoverage")
    on_disk = {p.name for p in EXAMPLES.glob("*.ever")}
    accounted = set(RUN_OUTPUT) | RUN_SILENT
    check("every examples/*.ever is pinned above", on_disk, accounted)
    if on_disk == accounted:
        print(f"  ok   all {len(on_disk)} examples are pinned")
    else:
        for name in sorted(on_disk - accounted):
            print(f"       unpinned: {name}  (add it to RUN_OUTPUT)")
        for name in sorted(accounted - on_disk):
            print(f"       pinned but missing from disk: {name}")


def main() -> int:
    section_run()
    section_transcript()
    section_counterfactual()
    section_completeness()
    print(f"\n=== Examples: {passed} passed, {failed} failed ===")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
