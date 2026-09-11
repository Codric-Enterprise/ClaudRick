#!/usr/bin/env python3
"""
ezrun.py — run an EZR program.

The core language had no runner. `ezr.py <file>` exists and runs a
*different* language: the directive surface (`tax = 40`, `expect`,
`learn`) that the browser interface also speaks. Lists, `let`, `show`
and the builtins live in the AST pipeline in `syntax.py`, and until
this file the only way to reach any of them was to import the module
and call `compile_ezr` by hand. A language feature you can only use by
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

from ezr import E, E_CERTAIN
from syntax import Prog, compile_ezr, definitions, eval_ast

EXIT_OK = 0
EXIT_REFUSED = 1        # the program ran and produced Z
EXIT_BAD_INPUT = 2      # could not read it, or it did not compile


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


def run(src: str, call: Optional[str] = None, depth: int = 100,
        quiet: bool = False, where: str = "<input>") -> int:
    c = compile_ezr(src)
    if not c.ok:
        _report_compile(c, where)
        return EXIT_BAD_INPUT

    fns = definitions(c.ast)
    arity = {k: len(v.params) for k, v in fns.items()}

    # A program that is one expression is its own entry point.
    if isinstance(c.ast, Prog) and c.ast.expr is not None and call is None:
        result = eval_ast(c.ast, {}, dict(fns), 0, limit=depth)
        _show(result, quiet)
        # A Z is a refusal on this path too. Returning OK here meant
        # `ezrun -e 'head([])'` printed Z and exited 0, so anything
        # scripting it read a refusal as a success.
        return EXIT_REFUSED if result.is_z else EXIT_OK

    # Definitions: register them, then find something to evaluate.
    eval_ast(c.ast, {}, fns, 0, limit=depth)

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

    cc = compile_ezr(entry, arity)
    if not cc.ok:
        _report_compile(cc, f"--call {entry!r}")
        return EXIT_BAD_INPUT

    result = eval_ast(cc.ast, {}, dict(fns), 0, limit=depth)
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
    args = ap.parse_args(argv)

    if args.eval is not None:
        return run(args.eval, args.call, args.depth, args.quiet, "-e")

    text = _read(args.file)
    if text is None:
        return EXIT_BAD_INPUT
    return run(text, args.call, args.depth, args.quiet, args.file)


if __name__ == "__main__":
    sys.exit(main())
