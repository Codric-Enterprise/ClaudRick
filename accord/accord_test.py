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

# ── programs: several functions, each witnessed by its own Checks ──────────
from accord import explain_program  # noqa: E402
from core import apply_program, verify_program  # noqa: E402


def prog(source: str):
    return verify_program(parse.program(source))


STATS = src("stats")
report = prog(STATS)
ok(report.accepted and list(report.reports) == ["total", "mean"], "a two-function program")
ok(apply_program(report, "mean", ((1, 2, 3),)).value == 2.0, "mean calls total and answers 2.0")
ok(apply_program(report, "mean", ((),)).void, "mean of the empty list is refused, not crashed")
mean_first = STATS[STATS.index("To mean") :] + "\n" + STATS[: STATS.index("To mean")]
ok(list(prog(mean_first).reports) == ["total", "mean"], "helpers are verified first")
ok(report.reports["mean"].accepted, "a caller's Checks need not cover its helper's decisions")
PICK = program(
    "To pick given x, answering an Int:",
    "x is an Int, trusted 256 of 256.",
    "It never repeats.",
    "Make sure x is not void.",
    "Answer x.",
    checks=("pick of 1 gives 1, trusted 120.", "pick of 2 gives 2, trusted 120."),
)
WRAP = program(
    "To wrap given x, answering an Int:",
    "x is an Int, trusted 256 of 256.",
    "It never repeats.",
    "Make sure x is not void.",
    "Answer pick of x.",
    checks=(
        "wrap of 1 gives 1, trusted 120.",
        "wrap of 2 gives 2, trusted 120.",
        "wrap of 3 gives 3, trusted 120.",
    ),
)
capped = prog(PICK + WRAP)
ok(capped.reports["wrap"].trust == 217 and capped.reports["pick"].trust == 183, "own trusts")
got = apply_program(capped, "wrap", (9,), trust=256)
ok(got.trust == 183, "a caller's answer is capped by what its helper's Checks earned (4.3)")
broken = prog(
    STATS.replace(
        "total of the list of 1, 2 and 3 gives 6", "total of the list of 1, 2 and 3 gives 7"
    )
)
ok(broken.reports["total"].stage == "checks", "a wrong helper is refused at its Checks")
ok(broken.reports["mean"].stage == "depends", "and its caller is refused because of it")
ok("mean uses total, which was refused" in explain_program(broken), "the dependency is named")
ok(apply_program(broken, "mean", ((1,),)).void, "a function resting on a refused one does not run")
PING = program(
    "To ping given n, answering an Int:",
    "n is an Int, trusted 256 of 256.",
    "It never repeats.",
    "Make sure n is not void.",
    "Answer pong of n.",
)
PONG = PING.replace("To ping", "To pong").replace("Answer pong of n.", "Answer ping of n.")
cycle = prog(PING + PONG)
ok(any("call each other" in e for e in cycle.errors), "mutual recursion is refused (R5)")
undefined = prog(STATS.replace("(total of xs) divided by", "(sum of xs) divided by"))
ok(any("'sum' is not defined in this program" in e for e in undefined.reports["mean"].errors),
   "a call to an undefined function is refused")  # fmt: skip
arity = prog(STATS.replace("(total of xs) divided by", "(total of xs and xs) divided by"))
ok(any("total called with 2 args, takes 1" in e for e in arity.reports["mean"].errors),
   "a call with the wrong number of arguments is refused")  # fmt: skip
ok(any("two functions are named pick" in e for e in prog(PICK + PICK).errors), "duplicate names")
EDGELESS = no_edge
USES = program(
    "To judge given s, answering a Text:",
    "s is a Float, trusted 256 of 256.",
    "It never repeats.",
    "Make sure s is not void.",
    "Answer classify of s.",
    checks=(
        'judge of 128 gives "Uncertain", trusted 100.',
        'judge of 200 gives "Certain", trusted 100.',
    ),
)
leaned = prog(EDGELESS + USES)
ok(leaned.reports["classify"].stage == "coverage", "a caller's Checks do not cover a helper")
ok(leaned.reports["judge"].stage == "depends", "so the caller waits on the helper's own Checks")
try:
    parse.parse(STATS)
    one = ""
except AccordError as err:
    one = err.message
ok("use program()" in one, "parse() is for one function; a program is read with program()")

# ── fill: the person writes the intent, Claude writes the body, Accord decides ─
import fill  # noqa: E402

INTENT = src("clamp.intent")
GOOD = """```accord
  It never repeats.
  Make sure x is not void.
  Make sure low is not void.
  Make sure high is not void.
  If x is less than low:
    Answer low.
  Otherwise:
    If x is greater than high:
      Answer high.
    Otherwise:
      Answer x.
```"""
SWAPPED = GOOD.replace("Answer low.", "Answer high.")


def scripted(*replies):
    calls = []

    def ask(system, messages):
        calls.append((system, list(messages)))
        reply = replies[min(len(calls), len(replies)) - 1]
        return reply, reply

    return ask, calls


person = fill.intent(INTENT)
ok(len(person.declarations) == 3 and len(person.checks) == 5, "the intent file is split by role")
ask, calls = scripted(GOOD)
out = fill.fill(INTENT, ask)
ok(out.code == 0 and out.attempts == 1, "a correct body is accepted on the first attempt")
ok(all(c in out.program for c in person.checks), "the person's Checks survive verbatim")
ok(verify(parse.parse(out.program)).trust == 245, "five Checks earn 245 (SEMANTICS.md 4.2)")
ok(calls[0][0] == fill.CARD and "Check: clamp of 12" in calls[0][1][0]["content"],
   "Claude is given the language card and the person's part")  # fmt: skip
ask, calls = scripted(SWAPPED, GOOD)
out = fill.fill(INTENT, ask)
ok(out.code == 0 and out.attempts == 2, "a wrong body is sent back and then fixed")
feedback = calls[1][1][-1]["content"]
ok("clamp of negative 3 and 0 and 10 should give 0" in feedback, "the refusal goes back in Accord")
tamper = GOOD.replace("```\n", "").replace(
    "      Answer x.", "      Answer x.\nCheck: clamp of 5 and 0 and 10 gives 99, trusted 120."
)
ask, calls = scripted(tamper, GOOD)
out = fill.fill(INTENT, ask)
ok(out.code == 0 and out.attempts == 2, "a reply that rewrites a Check is refused")
ok("gives 99" not in out.program, "and the person's Checks are never touched")
ok("may not change" in calls[1][1][-1]["content"], "Claude is told why")
ask, calls = scripted(SWAPPED)
out = fill.fill(INTENT, ask, attempts=3)
ok(out.code == 1 and out.attempts == 3, "a body that never satisfies the Checks runs out of tries")
no_edges = "\n".join(
    x for x in INTENT.splitlines() if "of 0 and 0" not in x and "of 10 and 0" not in x
)
ask, calls = scripted(GOOD)
out = fill.fill(no_edges, ask)
ok(out.code == 4 and len(calls) == 1, "an untried edge is the person's turn, not Claude's")
ok(any("no Check tries x equal to low" in line for line in out.log), "and the question is asked")
one = "To keep given x, answering an Int:\n  x is an Int, trusted 256 of 256.\n"
one += "Check: keep of 3 gives 3, trusted 120.\n"
ask, calls = scripted("  It never repeats.\n  Make sure x is not void.\n  Answer x.")
out = fill.fill(one, ask)
ok(out.code == 4 and out.report.stage == "floor", "too few Checks is the person's turn too")
try:
    fill.intent(src("classify"))
    has_body = ""
except AccordError as err:
    has_body = err.message
ok("already has a body" in has_body, "fill refuses a file that already has a body")
try:
    fill.intent(INTENT.replace("  high is an Int, trusted 256 of 256.\n", ""))
    missing = ""
except AccordError as err:
    missing = err.message
ok(missing.startswith("R1"), "every parameter's trust must be declared by the person")
flat = "It never repeats.\nIf x is less than low:\n  Answer low.\nOtherwise:\n  Answer x."
ok(fill.body_of(flat)[2] == "    Answer low.", "an unindented reply keeps its nesting")
fast = fill.request(fill.MODEL, True, "s", [])
ok(fast["speed"] == "fast" and "fast-mode-2026-02-01" in fast["betas"], "--fast asks for fast mode")
slow = fill.request(fill.MODEL, False, "s", [])
ok("speed" not in slow and slow["model"] == "claude-opus-5", "the default is standard Opus 5")
ok(slow["fallbacks"] == "default", "refusal fallbacks are on")

# ── fill and logic/modulo: the card documents them, and a filled body can use them ──
ok("a and b | a or b | not a" in fill.CARD and "a modulo b" in fill.CARD,
   "the card documents and/or/not/modulo")  # fmt: skip

LEAP_INTENT = src("leap.intent")
LEAP_ANSWER = (
    "  Answer (year modulo 4 is equal to 0 and year modulo 100 is not equal to 0)"
    " {op} year modulo 400 is equal to 0.\n"
)
LEAP_GOOD = "```accord\n  It never repeats.\n  Make sure year is not void.\n"
LEAP_GOOD += LEAP_ANSWER.format(op="or") + "```"
LEAP_WRONG = "```accord\n  It never repeats.\n  Make sure year is not void.\n"
LEAP_WRONG += LEAP_ANSWER.format(op="and") + "```"

leap_person = fill.intent(LEAP_INTENT)
ok(len(leap_person.declarations) == 1 and len(leap_person.checks) == 4,
   "the leap intent is split by role")  # fmt: skip
ask, calls = scripted(LEAP_GOOD)
out = fill.fill(LEAP_INTENT, ask)
ok(out.code == 0 and out.attempts == 1, "a body using and/or/modulo is accepted on the first try")
ok(verify(parse.parse(out.program)).trust == 235, "leap's four Checks earn 235 (SEMANTICS.md 4.2)")
ok(" and " in out.program and " or " in out.program and " modulo " in out.program,
   "and, or and modulo pass through the body unchanged")  # fmt: skip
ask, calls = scripted(LEAP_WRONG, LEAP_GOOD)
out = fill.fill(LEAP_INTENT, ask)
ok(out.code == 0 and out.attempts == 2, "an and/or slip is refused, then fixed")
feedback = calls[1][1][-1]["content"]
ok("leap of 2024 should give true" in feedback, "the refusal names the Check it broke, in Accord")

ODD_INTENT = "To odd given n, answering a Bool:\n  n is an Int, trusted 256 of 256.\n"
ODD_INTENT += (
    "Check: odd of 4 gives false, trusted 120.\nCheck: odd of 5 gives true, trusted 120.\n"
)
ODD_GOOD = "```accord\n  It never repeats.\n  Make sure n is not void.\n"
ODD_GOOD += "  Answer not (n modulo 2 is equal to 0).\n```"
ODD_MISSING_NOT = "```accord\n  It never repeats.\n  Make sure n is not void.\n"
ODD_MISSING_NOT += "  Answer n modulo 2 is equal to 0.\n```"

ask, calls = scripted(ODD_GOOD)
out = fill.fill(ODD_INTENT, ask)
ok(out.code == 0 and out.attempts == 1 and verify(parse.parse(out.program)).trust == 183,
   "a body using not is accepted, and its two Checks earn 183")  # fmt: skip
ok("not (" in out.program, "not passes through the body unchanged")
ask, calls = scripted(ODD_MISSING_NOT, ODD_GOOD)
out = fill.fill(ODD_INTENT, ask)
ok(out.code == 0 and out.attempts == 2, "a body missing not is refused, then fixed")

STATS_INTENT = """To total given xs, answering an Int:
  xs is a List of Int, trusted 256 of 256.
Check: total of the empty list gives 0, trusted 120.
Check: total of the list of 1, 2 and 3 gives 6, trusted 120.
To mean given xs, answering a Float:
  xs is a List of Int, trusted 256 of 256.
Check: mean of the list of 1, 2 and 3 gives 2.0, trusted 120.
Check: mean of the list of 4 gives 4.0, trusted 120.
"""
TOTAL_BODY = """```accord total
  It shrinks by xs.
  Make sure xs is not void.
  If the length of xs is equal to 0:
    Answer 0.
  Otherwise:
    Answer the first of xs plus total of the rest of xs.
```"""
MEAN_BODY = """```accord mean
  It never repeats.
  Make sure xs is not void.
  Answer (total of xs) divided by (the length of xs).
```"""
ok([p.name for p in fill.intents(STATS_INTENT)] == ["total", "mean"], "a multi-function intent")
ask, calls = scripted(TOTAL_BODY + "\n" + MEAN_BODY)
out = fill.fill(STATS_INTENT, ask)
ok(out.code == 0 and out.report.accepted, "fill writes every body of a program in one reply")
ok("mean" in calls[0][1][0]["content"] and "```accord total" in calls[0][1][0]["content"],
   "and asks for one labelled block per function")  # fmt: skip
ask, calls = scripted(TOTAL_BODY, TOTAL_BODY + "\n" + MEAN_BODY)
out = fill.fill(STATS_INTENT, ask)
ok(out.code == 0 and out.attempts == 2, "a missing body is sent back and then supplied")
ok("no body for mean" in calls[1][1][-1]["content"], "Claude is told which body is missing")
unlabelled = TOTAL_BODY.replace("```accord total", "```accord") + "\n" + MEAN_BODY
ask, calls = scripted(unlabelled, TOTAL_BODY + "\n" + MEAN_BODY)
ok(fill.fill(STATS_INTENT, ask).attempts == 2, "an unlabelled body in a program is refused")
ok("label each body" in calls[1][1][-1]["content"], "and Claude is told to label it")
one_check = STATS_INTENT.replace("Check: mean of the list of 4 gives 4.0, trusted 120.\n", "")
ask, calls = scripted(TOTAL_BODY + "\n" + MEAN_BODY)
out = fill.fill(one_check, ask)
ok(out.code == 4 and len(calls) == 1, "one function short of Checks is the person's turn")
ok(out.report.reports["mean"].stage == "floor", "and it names that function's floor")

# ── and, or, not: each is a decision, and a skipped side never counts ───────
from core import Bin, Not  # noqa: E402

report = verdict(src("leap"))
ok(report.accepted and report.trust == 235, f"leap: accepted at 235 ({report.stage})")
report = verdict(src("leap").replace("Check: leap of 2000 gives true, trusted 120.\n", ""))
ok(report.stage == "coverage", "an or whose second side is never true is refused")
ok("'(year modulo 400) is equal to 0' true" in explain(report), "and the refusal names that side")


def logic(answer: str, a: int = 200, b: int = 60, checks: tuple = ()) -> str:
    return program(
        "To both given a and b, answering a Bool:",
        f"a is a Bool, trusted {a} of 256.",
        f"b is a Bool, trusted {b} of 256.",
        "It never repeats.",
        "Make sure a is not void.",
        "Make sure b is not void.",
        f"Answer {answer}.",
        checks=checks,
    )


got = call(logic("a and b"), False, True)
ok((got.value, got.trust) == (False, 120), "a false 'and' answers with its first side's trust")
got = call(logic("a and b"), True, True)
ok((got.value, got.trust) == (True, 60), "a true 'and' ran both sides: the chain rule's min")
got = call(logic("a and b", a=60, b=200), True, True)
ok((got.value, got.trust) == (True, 60), "when both sides run, the first side's trust still counts")
got = call(logic("a or b"), True, False)
ok((got.value, got.trust) == (True, 120), "a true 'or' never runs its second side")
got = call(logic("a or b"), False, False)
ok((got.value, got.trust) == (False, 60), "a false 'or' ran both sides")
got = call(logic("not b"), True, True)
ok((got.value, got.trust) == (False, 60), "not flips the value and keeps the trust")
got = call(logic("a and (1 divided by 0 is equal to 1)"), False, True)
ok(got.value is False and not got.void, "the skipped side never runs, so it cannot fail")
got = call(logic("a and (1 divided by 0 is equal to 1)"), True, True)
ok(got.void and "division by zero" in got.reason, "the side that runs can")
got = call(logic("a and 1"), True, True)
ok(got.void and "and needs a Bool" in got.reason, "and takes Bools only")
got = call(logic("not 1"), True, True)
ok(got.void and "not needs a Bool" in got.reason, "not takes Bools only")
one_way = (
    "both of true and true gives true, trusted 60.",
    "both of false and true gives false, trusted 120.",
)
report = verdict(logic("a and b", checks=one_way))
ok(report.stage == "coverage", "a Bool side never seen false is refused")
ok("no Check makes 'b' false" in explain(report), "and named, in the language")
all_ways = (*one_way, "both of true and false gives false, trusted 60.")
ok(verdict(logic("a and b", checks=all_ways)).accepted, "with that Check added, it is accepted")

# ── modulo: whole numbers, and the answer takes the divisor's sign ──────────
mod = program(
    "To rem given a and b, answering an Int:",
    "a is an Int, trusted 256 of 256.",
    "b is an Int, trusted 256 of 256.",
    "It never repeats.",
    "Make sure a is not void.",
    "Make sure b is not void.",
    "Answer a modulo b.",
)
ok([call(mod, a, b).value for a, b in ((7, 3), (-7, 3), (7, -3), (6, 3))] == [1, 2, -2, 0],
   "modulo answers with the divisor's sign")  # fmt: skip
got = call(mod, 7, 0)
ok(got.void and "modulo by zero" in got.reason, "modulo by zero is refused")
fmod = mod.replace("an Int:", "a Float:").replace("a is an Int", "a is a Float")
got = run(lower(parse.parse(fmod)), (Thread(7.5, 120), Thread(2, 120)))
ok(got.void and "whole numbers" in got.reason, "modulo takes whole numbers only")


# ── the syntax of logic: or, then and, then not, then one comparison ────────
def read(text: str):
    return parse.expr(parse.Sentence(1, 0, parse.lex(text, 1)))


a, b, c, x, y = (Name(v) for v in "abcxy")
ok(read("a or b and c") == Bin("or", a, Bin("and", b, c)), "and binds tighter than or")
ok(read("not a is equal to b") == Not(Bin("==", a, b)), "not takes a whole comparison")
ok(read("f of x and y") == Call("f", (x, y)), "a call takes every 'and'")
ok(read("(f of x) and y") == Bin("and", Call("f", (x,)), y), "unless parenthesized")
ok(
    read("a modulo b times c") == Bin("*", Bin("%", a, b), c),
    "modulo binds like times, leftmost first",
)
texts = ("a and b or c", "not a and b", "not (a or b)", "not not a", "(f of x) and y")
texts += ("the list of (f of x) and y", "x modulo 3 is equal to 0 and y")
trees = [read(t) for t in texts]
ok(all(read(parse.render(t)) == t for t in trees), "every logic tree reads back from its rendering")
ok(parse_error(src("leap").replace("leap", "or")) != "", "'or' is reserved")
ok(parse_error(src("leap").replace("year", "modulo")) != "", "'modulo' is reserved")

# ── build: an accepted program becomes a standalone module, checked against Accord ──
import contextlib  # noqa: E402
import io  # noqa: E402
import sys  # noqa: E402

import accord  # noqa: E402
import build  # noqa: E402

built = {}
for stem in ("classify", "fact", "total", "reverse", "stats", "leap"):
    rep = prog(src(stem))
    built[stem] = (rep, build.build(rep))
ok(len(built) == 6, "every example builds")
imports = {line for _, code in built.values() for line in code.splitlines() if "import" in line
           and not line.startswith(" ")}  # fmt: skip
ok(imports == {"from __future__ import annotations", "from dataclasses import dataclass"},
   "a built module imports nothing from Accord")  # fmt: skip
ok("accord_built" not in sys.modules, "loading a build leaves nothing behind in sys.modules")
leap_rep, leap_code = built["leap"]
m = build.load(leap_code)
years = [(y, apply_program(leap_rep, "leap", (y,))) for y in range(1, 2401)]
ok(all(m.trusted("leap", y) == (t.value, t.trust) for y, t in years),
   "the built leap agrees with Accord on 2400 years, not only on its Checks")  # fmt: skip
fact_rep, fact_code = built["fact"]
m = build.load(fact_code)
agree = True
for n in (*range(0, 21), -3, 300):
    want = apply_program(fact_rep, "fact", (n,))
    try:
        got = m.trusted("fact", n)
        agree &= not want.void and got == (want.value, want.trust)
    except m.Refused as refusal:
        agree &= want.void and str(refusal) == want.reason
agree &= apply_program(fact_rep, "fact", (300,)).void
ok(agree, "the built fact agrees with Accord, refusals and their reasons included")
m = build.load(built["stats"][1])
ok(
    (m.mean([1, 2, 3]), m.trusted("mean", (4,))) == (2.0, (4.0, 120)),
    "a built program calls helpers",
)
QUAD = """To double given n, answering an Int:
  n is an Int, trusted 256 of 256.
  It never repeats.
  Make sure n is not void.
  Answer n plus n.
Check: double of 2 gives 4, trusted 120.
Check: double of 0 gives 0, trusted 120.

To quad given n, answering an Int:
  n is an Int, trusted 256 of 256.
  It never repeats.
  Make sure n is not void.
  Answer double of (double of n).
Check: quad of 1 gives 4, trusted 120.
Check: quad of 3 gives 12, trusted 120.
"""
quad_rep = prog(QUAD)
quad_code = build.build(quad_rep)
want = apply_program(quad_rep, "quad", (5,), 256)
got = build.load(quad_code).trusted("quad", 5, trust=256)
ok(
    got == (20, 183) == (want.value, want.trust),
    "at full trust a helper's cap decides, as in Accord",
)
try:
    m.mean([])
    ok(False, "an empty mean is refused by the built module")
except m.Refused as refusal:
    ok("division by zero" in str(refusal), "an empty mean is refused by the built module")
stats_rep, stats_code = built["stats"]
for rep, good, old, new, label in (
    (leap_rep, leap_code, "_binop('%', t13", "_binop('*', t13", "an operator"),
    (leap_rep, leap_code, "_short('or', t6)", "_short('and', t6)", "a short circuit"),
    (stats_rep, stats_code, "'mean': (_f_mean, 1, 183)", "'mean': (_f_mean, 1, 256)",
     "an answer cap"),
    (quad_rep, quad_code, "_depth=_depth + 1), 183)", "_depth=_depth + 1), 256)", "a helper's cap"),
):  # fmt: skip
    ok(old in good and build.differences(rep, good.replace(old, new)) != [],
       f"a build with {label} changed is caught")  # fmt: skip
ok(all(build.differences(r, code) == [] for r, code in built.values()), "and an honest one is not")
low_first = ("both of true and true gives true, trusted 60.", "both of false and true gives false,"
             " trusted 60.", "both of true and false gives false, trusted 60.")  # fmt: skip
both = build.load(build.build(prog(logic("a and b", a=60, b=200, checks=low_first))))
ok(both.trusted("both", True, True) == (True, 60), "a built 'and' keeps both sides' trust")
honest = build.generate
build.generate = lambda r: honest(r).replace("_binop('%', t13", "_binop('*', t13")
try:
    build.build(leap_rep)
    ok(False, "build refuses a module that disagrees with Accord")
except build.BuildError as err:
    ok("disagrees" in str(err), "build refuses a module that disagrees with Accord")
finally:
    build.generate = honest
try:
    build.build(prog(src("leap").replace("Check: leap of 2000 gives true, trusted 120.\n", "")))
    ok(False, "a refused program does not build")
except build.BuildError as err:
    ok("refused at coverage" in str(err), "a refused program does not build")
kw = src("fact").replace("fact", "lambda")
m = build.load(build.build(prog(kw)))
ok(m.lambda_(5) == 120, "a function named like a Python keyword builds under a safe name")


def main(*argv) -> tuple[int, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = accord.main(list(argv))
    return code, out.getvalue() + err.getvalue()


code, text = main("build", str(EX / "leap.accord"))
ok(code == 0 and text == leap_code, "accord build prints the module")
code, text = main("build", str(EX / "clamp.intent.accord"))
ok(code == 1 and text.startswith("refused"), "accord build refuses a program without bodies")
ok(main("build", str(EX / "leap.accord"), "--oops")[0] == 2, "accord build rejects stray arguments")

# ── the specs: GRAMMAR.ebnf and SEMANTICS.md are held to the code ─────────
import re  # noqa: E402

import core  # noqa: E402

grammar = (HERE / "GRAMMAR.ebnf").read_text()
quoted = {w.lower() for w in re.findall(r'"([A-Za-z]+)"', grammar)}
ok(quoted >= parse.RESERVED, f"every reserved word is in the grammar: {parse.RESERVED - quoted}")
code = ((HERE / "parse.py").read_text() + (HERE / "core.py").read_text()).lower()
unread = {w for w in quoted if f'"{w}"' not in code}
ok(not unread, f"every word in the grammar is one the reader matches: {unread}")
listed = re.search(r"A name may not be a reserved word:\n(.*?)\*\)", grammar, re.S)
ok(listed is not None and set(listed.group(1).split()) == parse.RESERVED,
   "the grammar's list of reserved words is parse.py's")  # fmt: skip
semantics = (HERE / "SEMANTICS.md").read_text()
cited = set(re.findall(r"`(_[a-z]+)`", semantics))
ok(cited and all(hasattr(core, name) for name in cited), "every function SEMANTICS.md cites exists")
copied = {obj.__name__ for obj in build.SEMANTICS if obj.__name__.startswith("_")}
ok(copied - {"_num", "_whole", "_size", "_builtin", "_admit"} <= cited,
   f"SEMANTICS.md names what a build copies: {copied - cited}")  # fmt: skip

# ── the pieces stay apart: semantics never imports syntax ───────────────────
ok("import parse" not in (HERE / "core.py").read_text(), "core.py does not depend on the syntax")

total = passed + len(failed)
for label in failed:
    print(f"FAIL  {label}")
print(f"accord: {passed}/{total} passed")
raise SystemExit(0 if not failed else 1)
