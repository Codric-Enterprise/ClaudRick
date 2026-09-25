"""accord — one language: you state what you want, the AI writes the body, Checks decide trust.

python3 accord.py check examples/classify.accord
python3 accord.py run examples/classify.accord 200
python3 accord.py tac examples/fact.accord
python3 accord.py fill examples/clamp.intent.accord [--out F] [--attempts N] [--model M] [--fast]
"""

from __future__ import annotations

import sys
from pathlib import Path

import parse
from core import EXECUTE_FLOOR, AccordError, apply, format_tac, tac_hash, verify


def load(path: str):
    return parse.parse(Path(path).read_text())


def explain(report) -> str:
    """The verdict, in words a person can act on, quoting the program in its own language."""
    name = report.fn.name if report.fn else "program"
    if report.stage == "check":
        return "refused: " + "\n  ".join([f"{name} breaks a rule", *report.errors])
    if report.stage == "checks":
        lines = [f"refused: {name} does not do what its Checks say"]
        for ex, got in report.failed:
            shown = [parse.render_value(a) for a in ex.args]
            if len(shown) > 1:
                shown = [
                    f"({s})" if isinstance(a, tuple) else s
                    for a, s in zip(ex.args, shown, strict=True)
                ]
            call = f"{name} of " + " and ".join(shown)
            want = f"{parse.render_value(ex.value)}, trusted {ex.trust}"
            gave = (
                got.reason if got.void else f"{parse.render_value(got.value)}, trusted {got.trust}"
            )
            lines.append(f"{call} should give {want}; it gave {gave}")
        return "\n  ".join(lines)
    if report.stage == "coverage":
        lines = [f"refused: the Checks leave part of {name} untried; add a Check for each"]
        for kind, i, outcome in report.gaps:
            node = report.notes[i]
            if kind == "edge":
                left, right = parse.render(node.left), parse.render(node.right)
                lines.append(
                    f"no Check tries {left} equal to {right}, the edge of '{parse.render(node)}'"
                )
            else:
                truth = "true" if outcome else "false"
                lines.append(f"no Check makes '{parse.render(node)}' {truth}")
        return "\n  ".join(lines)
    if report.stage == "floor":
        held = len(report.fn.examples)
        return (
            f"refused: only {held} Check holds, which earns trust {report.trust}; "
            f"one case proves nothing, and nothing runs below {EXECUTE_FLOOR}. Add a Check."
        )
    held = len(report.fn.examples)
    return (
        f"accepted: {name}\n"
        f"  {held} Checks hold, so its answers are trusted at most {report.trust} of 256\n"
        f"  every decision was tried both ways, and every comparison at its edge"
    )


def fill_command(argv: list[str]) -> int:
    import fill

    options = {"--out": None, "--attempts": str(fill.ATTEMPTS), "--model": fill.MODEL}
    fast, rest = "--fast" in argv, [a for a in argv if a != "--fast"]
    paths = []
    while rest:
        arg = rest.pop(0)
        if arg in options and rest:
            options[arg] = rest.pop(0)
        elif arg.startswith("-") or paths:
            print(__doc__, file=sys.stderr)
            return 2
        else:
            paths.append(arg)
    if not paths or not options["--attempts"].isdigit():
        print(__doc__, file=sys.stderr)
        return 2
    try:
        source = Path(paths[0]).read_text()
        ask = fill.claude(options["--model"], fast)
        outcome = fill.fill(source, ask, int(options["--attempts"]), explain)
    except AccordError as err:
        print(f"refused: {err}", file=sys.stderr)
        return 1
    except fill.FillError as err:
        print(f"stopped: {err}", file=sys.stderr)
        return 3
    for line in outcome.log:
        print(line, file=sys.stderr)
    if outcome.program:
        if options["--out"]:
            Path(options["--out"]).write_text(outcome.program)
        else:
            print(outcome.program, end="")
    return outcome.code


def main(argv: list[str]) -> int:
    if argv and argv[0] == "fill":
        return fill_command(argv[1:])
    if len(argv) >= 2 and argv[0] in ("check", "run", "tac"):
        try:
            fn = load(argv[1])
        except AccordError as err:
            print(f"refused: {err}")
            return 1
        report = verify(fn)
        if argv[0] == "tac":
            print(format_tac(report.tac) if report.tac else explain(report))
            if report.tac:
                print(f"# sha256 {tac_hash(report.tac)}")
            return 0 if report.tac else 1
        if argv[0] == "check" and len(argv) == 2:
            print(explain(report))
            return 0 if report.accepted else 1
        if argv[0] == "run":
            if not report.accepted:
                print(explain(report))
                return 1
            try:
                args = parse.values(" ".join(argv[2:]))
            except AccordError as err:
                print(f"refused: the arguments: {err.message}")
                return 1
            got = apply(report, args)
            if got.void:
                print(f"refused: {got.reason}")
                return 1
            print(f"{parse.render_value(got.value)}, trusted {got.trust} of 256")
            return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
