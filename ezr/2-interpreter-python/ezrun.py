#!/usr/bin/env python3
"""
ezrun.py — run an EZR program.

The core language had no runner. `ezr.py <file>` exists and runs a
*different* language: the directive surface (`tax = 40`, `expect`,
`learn`) that the browser interface also speaks. Lists, `let`, `show`
and the builtins live in the AST pipeline in `syntax.py`, and until
this file the only way to reach any of them was to import the module
and call `compile_ever` by hand. A language feature you can only use by
importing the implementation is not shipped.

    ezrun.py program.ezr                  run it
    ezrun.py program.ezr --call 'f(3)'    run it, then evaluate a call
    ezrun.py -e '[1, 2] '                 run one expression
    echo '1 + 1' | ezrun.py -             read from stdin

## Entry points

`program := definitions | expression` (CORE.md 1), and there is
deliberately no trailing expression -- that grammar is ambiguous and
the chart parser proved it. So a file of definitions defines things and
produces nothing, and the runner needs to be told what to evaluate:

  * a program that is a single expression is evaluated and printed;
  * a program of definitions that defines `main()` has `main()` called;
  * otherwise `--call` names the expression to evaluate.

`main()` is a convention of *this runner*, not a rule of the language.
Nothing in the grammar knows about it.

## Depth

`--depth` defaults to 100 rather than to floor(pi) = 3. That is a
divergence from SEMANTICS.md 4.6 and is worth being plain about: the
earned-depth rule is anchoring, and anchoring lives in `abstract.py`'s
Lambda, not in the AST evaluator. `eval_ast` has no anchor mechanism at
all, only a `limit` argument. Defaulting to 3 would impose the ceiling
without shipping the way to earn past it, which is half a rule and
worse than either half. The divergence is tracked by `audit.py` rather
than left to be discovered.

Codric Enterprise
"""

from __future__ import annotations

import argparse
import sys
from typing import Dict, List, Optional

from ever import E, E_CERTAIN, E_EXECUTE_FLOOR, E_INTAKE
from syntax import (Call, FnDef, Program, Semantic, Trust,
                    compile_ever, eval_ast)

EXIT_OK = 0
EXIT_REFUSED = 1        # the program ran and produced Z
EXIT_BAD_INPUT = 2      # could not read it, or it did not compile


def definitions(node) -> Dict[str, object]:
    """The function table a program defines.

    v3.0's syntax.py exported this; v4.10's does not, so the runner
    carries it. Kept tiny and local rather than added to syntax.py:
    which functions a *runner* wants to call is a runner's business.
    """
    if isinstance(node, Program):
        return {d.name: d for d in node.defs if isinstance(d, FnDef)}
    if isinstance(node, FnDef):
        return {node.name: node}
    return {}


def _read(path: str) -> Optional[str]:
    """Source text, or None with the reason already reported.

    A missing file is a refusal with a sentence, not a traceback. The
    old entry point raised FileNotFoundError straight at the user, in a
    project whose first guarantee is that things do not raise.
    """
    if path == "-":
        return sys.stdin.read()
    try:
        with open(path) as fh:
            return fh.read()
    except IsADirectoryError:
        print(f"ezrun: {path} is a directory, not a program",
              file=sys.stderr)
    except FileNotFoundError:
        print(f"ezrun: no such file: {path}", file=sys.stderr)
    except OSError as exc:
        print(f"ezrun: cannot read {path}: {exc.strerror}", file=sys.stderr)
    return None


def _report_compile(c, where: str) -> None:
    """Say what the pipeline refused, and at which stage."""
    if c.error is not None:
        print(f"ezrun: {where}: {c.stage}: {c.error.reason}", file=sys.stderr)
        return
    for msg in (c.analysis.errors if c.analysis else []):
        print(f"ezrun: {where}: semantic: {msg}", file=sys.stderr)


def _show(result: E, quiet: bool) -> None:
    if result.is_z:
        defect = result.defect.name.lower() if result.defect else "unknown"
        print(f"Z({defect}) — {result.reason}", file=sys.stderr)
        return
    if quiet:
        print(result.value)
    else:
        print(f"{result.value}  @ {result.confidence}/{E_CERTAIN}")


def confidence_from_examples(passed: int, total: int) -> int:
    """[EXAMPLE], SEMANTICS.md 4.2.

    u_f = ((256 - 120)/256) ** p, then c_f = floor(256 * (1 - u_f) * p/t),
    capped one short of CERTAIN. Each passing Example is an independent
    witness at intake strength, so Examples corroborate rather than
    chain: 1/1 is 120 and still below the floor, 2/2 clears at 183, 3/3
    is 217. A failure scales the result by the share that held.
    """
    if total <= 0:
        return 0
    u = ((E_CERTAIN - E_INTAKE) / E_CERTAIN) ** passed if passed else 1.0
    c = int(E_CERTAIN * (1.0 - u) * (passed / total))
    return max(0, min(E_CERTAIN - 1, c))


def _split_example(text: str) -> Optional[tuple]:
    """`f(1) = 1` into ('f(1)', '1'). Splits on the first `=` that is not
    part of `==`, `<=`, `>=` or `!=`, so an expected value may compare."""
    for i, ch in enumerate(text):
        if ch != "=":
            continue
        if i + 1 < len(text) and text[i + 1] == "=":
            continue
        if i and text[i - 1] in "=<>!":
            continue
        return text[:i].strip(), text[i + 1:].strip()
    return None


def _earn(fns, examples: List[str], anchors: List[str], depth: int,
          where: str) -> tuple:
    """Turn Examples into confidence and anchors into earned depth.

    Neither is source syntax. The forge settled the reserved words at
    eight, and SEMANTICS.md states both as operations on a thread rather
    than as things a program says about itself -- so they arrive the way
    a verification harness would supply them, from outside the program.
    """
    trust = Trust()
    tally: Dict[str, List[int]] = {}

    for spec in examples:
        parts = _split_example(spec)
        if parts is None:
            print(f"ezrun: --example {spec!r}: expected 'call = value'",
                  file=sys.stderr)
            return None, EXIT_BAD_INPUT
        call_src, want_src = parts
        cc = compile_ever(call_src, {k: len(v.params) for k, v in fns.items()})
        wc = compile_ever(want_src)
        if not cc.ok or not wc.ok:
            bad = call_src if not cc.ok else want_src
            print(f"ezrun: --example {spec!r}: {bad!r} does not compile",
                  file=sys.stderr)
            return None, EXIT_BAD_INPUT

        name = _called_name(cc.ast)
        if name is None or name not in fns:
            print(f"ezrun: --example {spec!r}: names no defined function",
                  file=sys.stderr)
            return None, EXIT_BAD_INPUT

        # An Example is checked at the confidence earned so far, which is
        # how the third Example is allowed to be the one that clears the
        # floor. A depth-exceeded Example counts as a failure; otherwise
        # the ceiling would be free.
        got = eval_ast(cc.ast, {}, dict(fns), 0, depth, trust)
        want = eval_ast(wc.ast, {}, {}, 0, depth, Trust())
        ok = (not got.is_z) and (not want.is_z) and got.value == want.value

        p, t = tally.get(name, [0, 0])
        tally[name] = [p + (1 if ok else 0), t + 1]
        trust.confidence[name] = confidence_from_examples(*tally[name])

    for name in anchors:
        fn = fns.get(name)
        if fn is None:
            print(f"ezrun: --anchor {name}: not defined in {where}",
                  file=sys.stderr)
            return None, EXIT_BAD_INPUT
        conf = trust.of(name)
        if conf < E_EXECUTE_FLOOR:
            # [ANCHOR-FN] requires a cleared thread. Anchoring an
            # unverified function would grant depth on no evidence.
            print(f"ezrun: --anchor {name}: refused, {conf}/256 is below "
                  f"the execute floor ({E_EXECUTE_FLOOR}). Give it "
                  f"Examples first.", file=sys.stderr)
            return None, EXIT_REFUSED
        measure = Semantic._measure(fn) if _recursive(fn) else ""
        if measure is None:
            # [ANCHOR-BOT], the rule that keeps the language honest: a
            # function can sit at 240/256 and still loop forever.
            print(f"ezrun: --anchor {name}: refused, no decreasing measure "
                  f"-- confidence proves trust, not termination.",
                  file=sys.stderr)
            return None, EXIT_REFUSED
        trust.anchored.add(name)

    return trust, EXIT_OK


def _called_name(ast) -> Optional[str]:
    node = ast.expr if isinstance(ast, Program) and ast.expr is not None else ast
    return node.name if isinstance(node, Call) else None


def _recursive(fn) -> bool:
    def walk(n) -> bool:
        if isinstance(n, Call) and n.name == fn.name:
            return True
        return any(walk(k) for k in n.children())
    return walk(fn.body)


def run(src: str, call: Optional[str] = None, depth: int = 100,
        quiet: bool = False, where: str = "<input>",
        examples: Optional[List[str]] = None,
        anchors: Optional[List[str]] = None) -> int:
    c = compile_ever(src)
    if not c.ok:
        _report_compile(c, where)
        return EXIT_BAD_INPUT

    fns = definitions(c.ast)
    arity = {k: len(v.params) for k, v in fns.items()}

    trust, code = _earn(fns, examples or [], anchors or [], depth, where)
    if trust is None:
        return code

    # A program that is one expression is its own entry point.
    if isinstance(c.ast, Program) and c.ast.expr is not None and call is None:
        result = eval_ast(c.ast, {}, dict(fns), 0, depth, trust)
        _show(result, quiet)
        # A Z is a refusal on this path too. Returning OK here meant
        # `ezrun -e 'head([])'` printed Z and exited 0, so anything
        # scripting it read a refusal as a success.
        return EXIT_REFUSED if result.is_z else EXIT_OK

    # Definitions: register them, then find something to evaluate.
    eval_ast(c.ast, {}, fns, 0, depth, trust)

    entry = call
    if entry is None:
        if "main" in fns and not fns["main"].params:
            entry = "main()"
        else:
            names = ", ".join(sorted(fns)) or "nothing"
            print(f"ezrun: {where} defines {names} and does not say what to "
                  f"run.\n       Define main(), or pass --call 'expr'.",
                  file=sys.stderr)
            return EXIT_BAD_INPUT

    cc = compile_ever(entry, arity)
    if not cc.ok:
        _report_compile(cc, f"--call {entry!r}")
        return EXIT_BAD_INPUT

    result = eval_ast(cc.ast, {}, dict(fns), 0, depth, trust)
    _show(result, quiet)
    return EXIT_REFUSED if result.is_z else EXIT_OK


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="ezrun", description="Run an EZR program.",
        epilog="A file of definitions needs an entry point: define "
               "main(), or pass --call.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("file", nargs="?", help="program to run, or - for stdin")
    src.add_argument("-e", "--eval", metavar="EXPR",
                     help="run one expression instead of a file")
    ap.add_argument("-c", "--call", metavar="EXPR",
                    help="what to evaluate once the definitions are loaded")
    ap.add_argument("-d", "--depth", type=int, default=100,
                    help="recursion ceiling (default 100; see the module "
                         "docstring on why this is not 3)")
    ap.add_argument("-q", "--quiet", action="store_true",
                    help="print the value alone, without its confidence")
    ap.add_argument("-x", "--example", metavar="CASE", action="append",
                    default=[],
                    help="evidence, as 'f(1) = 1'. Repeatable. Passing "
                         "cases raise the function's confidence by "
                         "[EXAMPLE]: 1/1 is 120, 2/2 clears the floor at "
                         "183, 3/3 is 217")
    ap.add_argument("-a", "--anchor", metavar="NAME", action="append",
                    default=[],
                    help="anchor a function, which buys depth. Refused "
                         "unless it has cleared the execute floor and, if "
                         "recursive, has a decreasing measure")
    args = ap.parse_args(argv)

    if args.eval is not None:
        return run(args.eval, args.call, args.depth, args.quiet, "-e",
                   args.example, args.anchor)

    text = _read(args.file)
    if text is None:
        return EXIT_BAD_INPUT
    return run(text, args.call, args.depth, args.quiet, args.file,
               args.example, args.anchor)


if __name__ == "__main__":
    sys.exit(main())
