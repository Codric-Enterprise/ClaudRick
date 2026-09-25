"""The gate. Every rule is shown to refuse something, not only to accept the examples."""

from __future__ import annotations

from pathlib import Path

import parse
from accord import explain
from core import (
    INT_BOUND,
    LITERAL,
    AccordError,
    Call,
    Example,
    Function,
    Name,
    Param,
    Require,
    Return,
    Thread,
    apply,
    check,
    earned,
    equal,
    lower,
    run,
    verify,
)

HERE = Path(__file__).parent
EX = HERE / "examples"
passed, failed = 0, []


def ok(cond: bool, label: str):
    global passed
    if cond:
        passed += 1
    else:
        failed.append(label)


def src(name: str) -> str:
    return (EX / f"{name}.accord").read_text()


def program(header: str, *lines: str, checks: tuple = ()) -> str:
    body = "".join(f"  {line}\n" for line in lines)
    return f"{header}\n{body}" + "".join(f"Check: {c}\n" for c in checks)


def parse_error(source: str) -> str:
    try:
        parse.parse(source)
    except AccordError as err:
        return err.message
    return ""


def call(source: str, *args, trust: int = LITERAL) -> Thread:
    return run(lower(parse.parse(source)), tuple(Thread(a, trust) for a in args))


def verdict(source: str):
    return verify(parse.parse(source))


# ── the four examples are accepted, and say so in the language ──────────────
for stem, trust in (("classify", 217), ("fact", 183), ("total", 183), ("reverse", 183)):
    report = verdict(src(stem))
    ok(report.accepted and report.trust == trust, f"{stem}: accepted at {trust} ({report.stage})")
ok(explain(verdict(src("classify"))).startswith("accepted: classify"), "acceptance is explained")

# ── the bridge: the body is a claim, and the Checks decide how far to trust it ──
table = [earned(p, t) for p, t in ((1, 1), (2, 2), (3, 3), (4, 4), (2, 3))]
ok(table == [120, 183, 217, 235, 122], "earned trust reproduces SEMANTICS.md 4.2's table")
edge_check = 'Check: classify of 128 gives "Uncertain", trusted 100.\n'
no_edge = src("classify").replace(edge_check, "")
report = verdict(no_edge)
ok(report.stage == "coverage", "Checks that never try the edge are refused")
ok("no Check tries signal equal to threshold" in explain(report), "the edge is named, in Accord")
ge = src("classify").replace("is greater than the threshold", "is at least the threshold")
report = verdict(ge)
ok(report.stage == "checks", "the AI's >= for > is caught by the edge Check")
ok('classify of 128 should give "Uncertain"' in explain(report), "and the failing Check is quoted")
report = verdict(ge.replace(edge_check, ""))
ok(report.stage == "coverage", "without the edge Check, the same bug is still not accepted")
one_sided = no_edge.replace('classify of 50 gives "Uncertain"', 'classify of 250 gives "Certain"')
report = verdict(one_sided)
ok(report.stage == "coverage", "a decision never taken is refused")
ok(
    "no Check makes 'signal is greater than threshold' false" in explain(report),
    "untaken side named",
)
deep = verdict(src("total").replace("Check: total of the empty list gives 0, trusted 120.\n", ""))
ok(deep.stage != "coverage", "a base case reached through recursion counts as tried")
flag = program(
    "To keep given flagged, answering an Int:",
    "flagged is a Bool, trusted 256 of 256.",
    "It never repeats.",
    "Make sure flagged is not void.",
    "If flagged:",
    "  Answer 1.",
    "Otherwise:",
    "  Answer 0.",
    checks=("keep of true gives 1, trusted 120.", "keep of true gives 1, trusted 120."),
)
report = verdict(flag)
ok(report.stage == "coverage", "a Bool decision must be seen both ways")
ok("no Check makes 'flagged' false" in explain(report), "and the missing way is named")
seven = program(
    "To seven given x, answering an Int:",
    "x is an Int, trusted 256 of 256.",
    "It never repeats.",
    "Make sure x is not void.",
    "Answer 7.",
    checks=("seven of 1 gives 7, trusted 120.",),
)
report = verdict(seven)
ok(report.stage == "floor" and report.trust == 120, "one Check earns 120: below the floor")
ok("one case proves nothing" in explain(report), "and the refusal says why")
report = verdict(seven + "Check: seven of 2 gives 7, trusted 120.\n")
ok(report.accepted and report.trust == 183, "a second Check lifts it over the floor")
pick = program(
    "To pick given x, answering an Int:",
    "x is an Int, trusted 256 of 256.",
    "It never repeats.",
    "Make sure x is not void.",
    "Answer x.",
    checks=("pick of 1 gives 1, trusted 120.", "pick of 2 gives 2, trusted 120."),
)
report = verdict(pick)
ok(apply(report, (9,), trust=256).trust == 183, "an answer never exceeds what the Checks earned")
ok(apply(report, (9,)).trust == 120, "typed-in arguments stay at literal trust")
got = apply(verdict(no_edge), (200,))
ok(got.void and "refused at coverage" in got.reason, "a refused program does not run")
round_trip = True
for stem in ("classify", "fact", "total", "reverse"):
    notes: dict = {}
    lower(parse.parse(src(stem)), notes)
    for node in notes.values():
        text = parse.render(node)
        round_trip &= parse.expr(parse.Sentence(1, 0, parse.lex(text, 1))) == node
ok(round_trip, "every quoted decision is real Accord: parse(render(e)) == e")
ok(parse.values("the list of 1, 2 and 3") == ((1, 2, 3),), "arguments are typed in the language")

# ── R1: trust must be written ───────────────────────────────────────────────
e = parse_error(src("classify").replace(", trusted 100 of 256.", "."))
ok(e.startswith("R1"), f"a parameter without trust is refused ({e})")
e = parse_error(src("classify").replace("a Float, trusted 256 of 256, equal", "a Float equal"))
ok(e.startswith("R1"), "a let without trust is refused")
e = parse_error(src("classify").replace("  signal is a Float, trusted 100 of 256.\n", ""))
ok(e != "", "an undeclared parameter is refused")

# ── R2: a parameter is checked before it is used ────────────────────────────
errors = check(parse.parse(src("classify").replace("  Make sure signal is not void.\n", "")))
ok(any(x.startswith("R2: signal is used before") for x in errors), "use before require")
errors = check(parse.parse(src("classify").replace("than the threshold", "than the limit")))
ok(any("limit is never bound" in x for x in errors), "an unbound name is refused")
guard = program(
    "To keep given x, answering an Int:",
    "x is an Int, trusted 256 of 256.",
    "It never repeats.",
    "Make sure x is not void.",
    "Answer 7.",
)
held = run(lower(parse.parse(guard)), (Thread(None, 0, "unbound: x"),))
ok(held.void and held.reason == "unbound: x", "require stops a void input the answer never reads")

# ── R3: types are closed and Int is bounded where runtimes stop agreeing ────
errors = check(parse.parse(src("classify").replace("signal is a Float", "signal is a Number")))
ok(any(x.startswith("R3") for x in errors), "an unknown type is refused")
got = call(src("fact"), INT_BOUND + 1)
ok(got.void and "Int bound" in got.reason, "an Int past 2^53 is refused, not rounded")
got = call(src("fact"), 19)
ok(got.void and "Int bound" in got.reason, "19! overflows the bound and is refused")
ok(call(src("fact"), 18).value == 6402373705728000, "18! is inside the bound and exact")
got = call(src("classify"), "loud")
ok(got.void and "misbound" in got.reason, "Text where a Float is declared is refused")

# ── R4: no Checks, no program ───────────────────────────────────────────────
bare = "\n".join(x for x in src("fact").splitlines() if not x.startswith("Check"))
ok(any(x.startswith("R4") for x in check(parse.parse(bare))), "a function with no Checks")

# ── R5: every path answers, and recursion carries a shrinking measure ───────
errors = check(parse.parse(src("fact").replace("It shrinks by n.", "It never repeats.")))
ok(any("calls itself but names no measure" in x for x in errors), "recursion without a measure")
e = parse_error(src("fact").replace("  Otherwise:\n    Answer n times fact of (n minus 1).\n", ""))
ok(e.startswith("R5"), "an If without Otherwise is refused")
got = call(src("fact").replace("fact of (n minus 1)", "fact of n"), 3)
ok(got.void and "did not decrease" in got.reason, "a measure that does not shrink is stopped")
ok(call(src("fact").replace("n minus 1", "n plus 1"), 3).void, "a measure that grows is stopped")
got = call(src("fact"), 5000)
ok(got.void and "calls deep" in got.reason, "deep but shrinking recursion is refused, not crashed")

# ── trust follows SEMANTICS.md: literals 120, chain is min, [IF-T] ──────────
got = call(src("classify"), 200)
ok(got.value == "Certain" and got.trust == 100, "an answer is no more trusted than its decision")
ok(call(seven, 1).trust == 120, "a literal answer carries literal trust 120, not 256")
ok(call(src("fact"), 0).value == 1, "the base case answers without the recursive arm")
got = call(src("classify").replace("equal to 128.", "equal to 128 divided by 0."), 200)
ok(got.void and "division by zero" in got.reason, "Z from a division reaches the answer")

# ── lists: CORE.md 1.2, with every refusal it names ─────────────────────────
first = program(
    "To front given xs, answering an Int:",
    "xs is a List of Int, trusted 256 of 256.",
    "It never repeats.",
    "Make sure xs is not void.",
    "Answer the first of xs.",
)
got = call(first, ())
ok(got.void and got.reason == "unbound: head of an empty list", "head of [] is a refusal")
rest = first.replace("answering an Int", "answering a List of Int").replace("first of", "rest of")
got = call(rest, ())
ok(got.void and got.reason == "unbound: tail of an empty list", "tail of [] is a refusal")
ok(equal(call(rest, (1, 2, 3)).value, (2, 3)), "tail drops exactly the first")
got = call(first.replace("a List of Int, trusted", "an Int, trusted"), 5)
ok(got.void and "needs a list" in got.reason, "head of a number is refused")
got = call(src("total"), ("a",))
ok(got.void and "element 0" in got.reason, "a Text element in a List of Int is refused")
got = call(src("total"), (1, INT_BOUND + 1))
ok(got.void and "Int bound" in got.reason, "an element past 2^53 is refused, not rounded")
ok(call(src("total"), 5).void, "a number where a list is declared is refused")
pair = program(
    "To pair given a and b, answering a List of Int:",
    "a is an Int, trusted 100 of 256.",
    "b is an Int, trusted 256 of 256.",
    "It never repeats.",
    "Make sure a is not void.",
    "Make sure b is not void.",
    "Answer the list of a and b.",
)
got = call(pair, 1, 2)
ok(equal(got.value, (1, 2)) and got.trust == 100, "a list is as trusted as its weakest element")
got = call(pair.replace("the list of a and b", "the empty list"), 1, 2)
ok(got.value == () and got.trust == 120, "the empty list is a written literal: 120")
got = call(pair.replace("the list of a and b", "the list of a and (b divided by 0)"), 1, 2)
ok(got.void and "division by zero" in got.reason, "a Z element makes the whole list Z")
second = pair.replace("answering a List of Int", "answering an Int").replace(
    "Answer the list of a and b.", "Answer the first of the rest of the list of a and b."
)
got = call(second, 1, 2)
ok(got.value == 2 and got.trust == 100, "tail keeps the whole list's trust, as CORE does")
same = pair.replace("answering a List of Int", "answering a Bool").replace(
    "Answer the list of a and b.", "Answer (the list of a) is equal to (the list of true)."
)
ok(call(same, 1, 2).value is False, "[1] == [true] is false at any depth")
got = call(src("total").replace("total of the rest of xs", "total of xs"), (1, 2))
ok(got.void and "did not decrease" in got.reason, "a list measure must shrink too")
text_measure = program(
    "To t given s, answering an Int:",
    "s is a Text, trusted 256 of 256.",
    "It shrinks by s.",
    "Make sure s is not void.",
    "Answer 1.",
    checks=("t of 1 gives 1, trusted 120.",),
)
ok(any("must be an Int or List" in x for x in check(parse.parse(text_measure))), "Text measure")
two_args = Function(
    "f",
    (Param("xs", "List[Int]", 256),),
    "Int",
    None,
    (Require("not_void", "xs"), Return(Call("len", (Name("xs"), Name("xs"))))),
    (Example(((1,),), 1, 120),),
)
ok(any("len takes 1 argument" in x for x in check(two_args)), "a builtin given two arguments")
redefined = check(parse.parse(first.replace("To front", "To len")))
ok(any("cannot be redefined" in x for x in redefined), "a function may not be named len")
nested = program(
    "To count given xss, answering an Int:",
    "xss is a List of List of Int, trusted 256 of 256.",
    "It never repeats.",
    "Make sure xss is not void.",
    "Answer the length of xss.",
)
ok(call(nested, ((1,), ())).value == 2, "nested lists: a List of List of Int")

# ── joining lists: Accord's own rule, extending ezr's Text concatenation ────
got = call(pair.replace("the list of a and b", "(the list of a) plus (the list of b)"), 1, 2)
ok(equal(got.value, (1, 2)) and got.trust == 100, "a join takes the weaker side's trust")
got = call(pair.replace("the list of a and b", "(the list of b) plus (the list of a)"), 1, 2)
ok(equal(got.value, (2, 1)), "a join keeps the left list first")
wide = pair.replace("trusted 100 of 256", "trusted 256 of 256")
got = call(
    wide.replace("the list of a and b", "the empty list plus (the list of a)"), 1, 2, trust=256
)
ok(equal(got.value, (1,)) and got.trust == 120, "joining a written empty list costs trust 120")
got = call(pair.replace("the list of a and b", "(the list of a) plus b"), 1, 2)
ok(got.void and "needs numbers" in got.reason, "a list plus a number is refused")
got = call(pair.replace("the list of a and b", '"a" plus (the list of b)'), 1, 2)
ok(got.void and "needs numbers" in got.reason, "Text plus a list is refused")
got = call(pair.replace("the list of a and b", '(the list of a) plus (the list of "x")'), 1, 2)
ok(got.void and "element 1" in got.reason, "a joined Text element is refused at List of Int")
grow = program(
    "To grow given xs, answering an Int:",
    "xs is a List of Int, trusted 256 of 256.",
    "It shrinks by xs.",
    "Make sure xs is not void.",
    "If the length of xs is greater than 5:",
    "  Answer 0.",
    "Otherwise:",
    "  Answer grow of (xs plus (the list of 1)).",
)
got = call(grow, ())
ok(got.void and "did not decrease (0 -> 1)" in got.reason, "a growing list cannot be a measure")

# ── the one syntax: one form per construct ──────────────────────────────────
e = parse_error(src("total").replace("1, 2 and 3", "1, 2, and 3"))
ok("final 'and'" in e, "one list form only, so no comma before 'and'")
e = parse_error(src("total").replace("a List of Int,", "a List,"))
ok(e.startswith("R3"), "a List without an element type is refused")
drop = program(
    "To drop given xs, answering a List of Int:",
    "xs is a List of Int, trusted 256 of 256.",
    "It never repeats.",
    "Make sure xs is not void.",
    "Answer the rest of xs.",
    checks=("drop of the list of 2 and 3 gives the list of 3, trusted 120.",),
)
ok(parse.parse(drop).examples[0].value == (3,), "a one-item list ends at ', trusted'")
ok(parse_error(drop.replace("drop", "rest")) != "", "'rest' is reserved: no function named rest")

# ── the pieces stay apart: semantics never imports syntax ───────────────────
ok("import parse" not in (HERE / "core.py").read_text(), "core.py does not depend on the syntax")

total = passed + len(failed)
for label in failed:
    print(f"FAIL  {label}")
print(f"accord: {passed}/{total} passed")
raise SystemExit(0 if not failed else 1)
