"""accord build: an accepted program, compiled from its verified TAC to a standalone Python module.

The module imports nothing from Accord. Its semantics are core's own functions, copied in by
source, so the built code and the interpreter cannot mean different things by `plus` or `min`.
A build is only handed back after every Check has been run through the built code and has
answered exactly what the interpreter answers: value, trust and reason.
"""

from __future__ import annotations

import inspect
import keyword
import sys
import types

import core
from core import CERTAIN, LITERAL, ProgramReport, Thread, apply_program, equal, run

# Everything the built code runs, in dependency order. Nothing else from core is copied.
CONSTANTS = ("CERTAIN", "LITERAL", "INT_BOUND", "DEPTH_LIMIT")
SEMANTICS = (
    core.Thread, core.Z, core.element_type, core._admit, core._num, core._whole, core.equal,
    core._binop, core._builtin, core._size, core._list, core._truth, core._short, core._join,
    core._not, core._bind, core._cap, core._answer, core._enter,
)  # fmt: skip

INTERFACE = '''

class Refused(Exception):
    """Accord refused to answer: the value was void. The message says why."""


def _intake(value):
    return tuple(_intake(v) for v in value) if isinstance(value, (list, tuple)) else value


def trusted(name, *values, trust=LITERAL):
    """(answer, trust) from one function, capped at the trust its Checks earned. Raises Refused."""
    fn, arity, cap = FUNCTIONS[name]
    if len(values) != arity:
        raise TypeError(f"{name} takes {arity} arguments, given {len(values)}")
    got = _cap(fn(*(Thread(_intake(v), trust) for v in values)), cap)
    if got.void:
        raise Refused(got.reason)
    return got.value, got.trust
'''


class BuildError(Exception):
    pass


def generate(report: ProgramReport) -> str:
    """The module's source. The program must have been accepted."""
    if not report.accepted:
        raise BuildError(f"the program was refused at {report.stage}; only accepted programs build")
    internal = {n: f"_f_{n}" for n in report.reports}
    taken = {*CONSTANTS, *(o.__name__ for o in SEMANTICS), *internal.values()}
    taken |= {"Refused", "trusted", "FUNCTIONS", "dataclass", "annotations"}
    public = {}
    for n in report.reports:
        name = n
        while keyword.iskeyword(name) or name in taken:
            name += "_"
        public[n] = name
        taken.add(name)

    names = ", ".join(report.reports)
    lines = [
        f'"""Built by accord from a program of {len(report.reports)} function(s): {names}.',
        "",
        "Do not edit: change the .accord source and build again. Each function answers at most",
        "the trust its Checks earned, and raises Refused instead of answering void:",
    ]
    for n, r in report.reports.items():
        digest = core.tac_hash(r.tac)[:16]
        lines.append(f"  {public[n]}: trusted at most {r.trust} of 256, tac sha256 {digest}")
    lines += [
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "from dataclasses import dataclass",
        "",
    ]
    lines += [f"{c} = {getattr(core, c)!r}" for c in CONSTANTS]
    for obj in SEMANTICS:
        lines += ["", "", inspect.getsource(obj).rstrip()]
    lines.append(INTERFACE.rstrip())
    for r in report.reports.values():
        lines += ["", ""] + _function(
            r.tac, internal, {m: x.trust for m, x in report.reports.items()}
        )
    lines += ["", "", "FUNCTIONS = {"]
    for n, r in report.reports.items():
        lines.append(f"    {n!r}: ({internal[n]}, {len(r.fn.params)}, {r.trust}),")
    lines.append("}")
    for n, r in report.reports.items():
        header = ", ".join(f"{p.name}: {p.type} trusted {p.trust}" for p in r.fn.params)
        lines += [
            "",
            "",
            f"def {public[n]}(*values):",
            f'    """{n}({header}) -> {r.fn.returns}; `trusted` adds its trust."""',
            f"    return trusted({n!r}, *values)[0]",
        ]
    return "\n".join(lines) + "\n"


def _function(tac: list[tuple], internal: dict, caps: dict) -> list[str]:
    name = tac[0][1]
    params = tuple(ins[1:] for ins in tac if ins[0] == "param")
    measure = next(ins[1] for ins in tac if ins[0] == "measure")
    labels = {ins[1]: i for i, ins in enumerate(tac) if ins[0] in ("label", "mark")}
    start = next(i for i, ins in enumerate(tac) if ins[0] == "measure") + 1
    out = [
        f"def {internal[name]}(*args, _measure=None, _depth=0):",
        f"    v = _enter({name!r}, {params!r}, {measure!r}, args, _measure, _depth)",
        "    if isinstance(v, Thread):",
        "        return v",
        "    path = CERTAIN",
    ]

    def region(i: int, end: int, pad: str, answers: bool = True):
        while i < end:
            ins, op = tac[i], tac[i][0]
            if op == "const":
                out.append(f"{pad}{ins[1]} = Thread({ins[3]!r}, LITERAL)")
            elif op == "load":
                out.append(f'{pad}{ins[1]} = v.get({ins[2]!r}) or Z("unbound: {ins[2]}")')
            elif op == "bin":
                out.append(f"{pad}{ins[1]} = _binop({ins[2]!r}, {ins[3]}, {ins[4]})")
            elif op == "list":
                out.append(f"{pad}{ins[1]} = _list([{', '.join(ins[2])}])")
            elif op == "builtin":
                out.append(f"{pad}{ins[1]} = _builtin({ins[2]!r}, {ins[3]})")
            elif op == "call":
                args = "".join(f"{a}, " for a in ins[3])
                if ins[2] == name:
                    here = f"_size(v[{measure!r}].value)" if measure is not None else "None"
                    call = f"{internal[name]}({args}_measure={here}, _depth=_depth + 1)"
                    out.append(f"{pad}{ins[1]} = {call}")
                else:
                    call = f"{internal[ins[2]]}({args}_depth=_depth + 1)"
                    out.append(f"{pad}{ins[1]} = _cap({call}, {caps[ins[2]]})")
            elif op == "require":
                out.extend([f"{pad}if v[{ins[2]!r}].void:", f"{pad}    return v[{ins[2]!r}]"])
            elif op == "let":
                out.append(f"{pad}v[{ins[1]!r}] = _bind({ins[4]}, {ins[2]!r}, {ins[3]})")
            elif op == "not":
                out.append(f"{pad}{ins[1]} = _not({ins[2]})")
            elif op == "short":
                out.extend(
                    [
                        f"{pad}{ins[1]} = _short({ins[2]!r}, {ins[3]})",
                        f"{pad}if {ins[1]} is None:",
                    ]
                )
                mark = labels[ins[4]]
                region(i + 1, mark, pad + "    ", answers=False)
                i = mark
            elif op == "join":
                out.append(f"{pad}{ins[1]} = _join({ins[2]!r}, {ins[3]}, {ins[4]})")
            elif op == "br":
                then, orelse = labels[ins[2]], labels[ins[3]]
                if then != i + 1:
                    raise BuildError(f"{name}: a branch at {i} is not followed by its label")
                c = ins[1]
                out.extend(
                    [
                        f'{pad}_r = _truth("a condition", {c})',
                        f"{pad}if _r is not None:",
                        f"{pad}    return _r",
                        f"{pad}path = min(path, {c}.trust)",
                        f"{pad}if {c}.value:",
                    ]
                )
                region(then + 1, orelse, pad + "    ")
                out.append(f"{pad}else:")
                region(orelse + 1, end, pad + "    ")
                return
            elif op == "ret":
                out.append(f"{pad}return _answer({ins[1]}, {tac[0][2]!r}, path)")
                return
            else:
                raise BuildError(f"{name}: no Python for {op} at {i}")
            i += 1
        if answers:
            raise BuildError(f"{name}: a path through the TAC ends without answering")

    region(start, len(tac), "    ")
    return out


def load(source: str) -> types.ModuleType:
    """Execute a built module in isolation. It is never imported from, or cached in, sys.modules."""
    module = types.ModuleType("accord_built")
    sys.modules[module.__name__] = module  # @dataclass looks its module up while decorating
    try:
        exec(compile(source, "<accord build>", "exec"), module.__dict__)
    finally:
        del sys.modules[module.__name__]
    return module


def differences(report: ProgramReport, source: str) -> list[str]:
    """Every Check, through the built module and through Accord. Empty: they agree.

    Each Check runs twice: at a literal's trust, as written, and at full trust, where the
    caps on helpers and on answers are what decide the result.
    """
    module = load(source)
    program = {n: (r.tac, r.trust) for n, r in report.reports.items()}
    found = []
    for n, r in report.reports.items():
        if module.FUNCTIONS[n][1:] != (len(r.fn.params), r.trust):
            found.append(f"{n}: the module says {module.FUNCTIONS[n][1:]}, Accord says "
                         f"{(len(r.fn.params), r.trust)} (arguments, trust)")  # fmt: skip
        fn = module.FUNCTIONS[n][0]
        for ex in r.fn.examples:
            for trust in (LITERAL, CERTAIN):
                shown = f"{n} of {', '.join(map(repr, ex.args))} at trust {trust}"
                want = run(r.tac, tuple(Thread(a, trust) for a in ex.args), program=program)
                got = fn(*(module.Thread(a, trust) for a in ex.args))
                if not _same(got, want):
                    found.append(f"{shown}: built gave {_show(got)}, Accord gave {_show(want)}")
                elif trust == LITERAL and not (
                    equal(got.value, ex.value) and got.trust == ex.trust
                ):
                    found.append(f"{shown}: built gave {_show(got)}; the Check says "
                                 f"{ex.value!r}@{ex.trust}")  # fmt: skip
                capped = apply_program(report, n, ex.args, trust)
                try:
                    public = module.trusted(n, *ex.args, trust=trust)
                except module.Refused as refusal:
                    public = (None, 0, str(refusal))
                if not _same(Thread(*public), capped):
                    found.append(f"{shown}: trusted() gave {public!r}, Accord gave {_show(capped)}")
    return found


def _same(a, b) -> bool:
    return equal(a.value, b.value) and a.trust == b.trust and a.reason == b.reason


def _show(t) -> str:
    return f"void ({t.reason})" if t.void else f"{t.value!r}@{t.trust}"


def build(report: ProgramReport) -> str:
    """The module, but only once its Checks agree with the interpreter's."""
    source = generate(report)
    found = differences(report, source)
    if found:
        raise BuildError("the built module disagrees with Accord:\n  " + "\n  ".join(found))
    return source
