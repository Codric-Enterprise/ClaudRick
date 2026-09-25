"""accord — one language: you state what you want, the AI writes the body, Checks decide trust.

python3 accord.py check examples/classify.accord
python3 accord.py run examples/classify.accord 200
python3 accord.py run examples/stats.accord --fn mean the list of 1, 2 and 3
python3 accord.py tac examples/fact.accord
python3 accord.py build examples/stats.accord [--out stats.py]
python3 accord.py fill examples/clamp.intent.accord [--out F] [--attempts N] [--model M] [--fast]
"""

from __future__ import annotations

import sys
from pathlib import Path

import parse
from core import EXECUTE_FLOOR, AccordError, apply_program, format_tac, tac_hash, verify_program


def load(path: str):
    return parse.program(Path(path).read_text())


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


def explain_program(report) -> str:
    """A program's verdict. One function reads exactly as `explain`; several get one line each."""
    if report.errors:
        return "refused: the program breaks a rule\n  " + "\n  ".join(report.errors)
    if len(report.reports) == 1:
        return explain(next(iter(report.reports.values())))
    lines = []
    for name, r in report.reports.items():
        if r.accepted:
            lines.append(f"accepted: {name}, trusted at most {r.trust} of 256")
        elif r.stage == "depends":
            lines.append("refused: " + "; ".join(r.errors))
        else:
            lines.append(explain(r))
    total = len(report.reports)
    refused = sum(not r.accepted for r in report.reports.values())
    head = (
        f"accepted: all {total} functions"
        if report.accepted
        else f"refused: {refused} of {total} functions"
    )
    return head + "\n" + "\n".join(lines)


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
        outcome = fill.fill(source, ask, int(options["--attempts"]), explain_program)
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


def build_command(argv: list[str]) -> int:
    """An accepted program, as a standalone Python module whose Checks agree with Accord."""
    import build

    out = None
    if argv[1:3] and argv[1] == "--out" and len(argv) == 3:
        out = argv[2]
    elif len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        report = verify_program(load(argv[0]))
    except AccordError as err:
        print(f"refused: {err}", file=sys.stderr)
        return 1
    if not report.accepted:
        print(explain_program(report), file=sys.stderr)
        return 1
    try:
        module = build.build(report)
    except build.BuildError as err:
        print(f"refused: {err}", file=sys.stderr)
        return 1
    if out:
        Path(out).write_text(module)
    else:
        print(module, end="")
    return 0


def main(argv: list[str]) -> int:
    if argv and argv[0] == "fill":
        return fill_command(argv[1:])
    if argv and argv[0] == "build" and len(argv) >= 2:
        return build_command(argv[1:])
    if len(argv) >= 2 and argv[0] in ("check", "run", "tac"):
        try:
            functions = load(argv[1])
        except AccordError as err:
            print(f"refused: {err}")
            return 1
        report = verify_program(functions)
        if argv[0] == "tac":
            lowered = [(n, r.tac) for n, r in report.reports.items() if r.tac]
            if not lowered:
                print(explain_program(report))
                return 1
            for name, tac in lowered:
                print(f"# {name}\n{format_tac(tac)}\n# sha256 {tac_hash(tac)}")
            return 0
        if argv[0] == "check" and len(argv) == 2:
            print(explain_program(report))
            return 0 if report.accepted else 1
        if argv[0] == "run":
            rest = argv[2:]
            name = functions[-1].name
            if rest[:1] == ["--fn"] and len(rest) >= 2:
                name, rest = rest[1], rest[2:]
            target = report.reports.get(name)
            if target is None:
                print(f"refused: {name} is not a function of this program")
                return 1
            if not target.accepted:
                print(explain_program(report))
                return 1
            try:
                args = parse.values(" ".join(rest))
            except AccordError as err:
                print(f"refused: the arguments: {err.message}")
                return 1
            got = apply_program(report, name, args)
            if got.void:
                print(f"refused: {got.reason}")
                return 1
            print(f"{parse.render_value(got.value)}, trusted {got.trust} of 256")
            return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
