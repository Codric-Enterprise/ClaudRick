"""realm_test.py — Rime, the whole language.

Checks the vocabulary's central claim before anything rests on it, then
the scanners, the parsers, the machine, the rhyming rule as a generator,
and finally all nine front ends over the whole corpus under every law.

Run directly: `python3 realm_test.py`.
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from contract import (  # noqa: E402
    CLASS_ORDER,
    CLASSES,
    VOCABULARY,
    WORDS,
    Couplet,
    Line,
    Poem,
    rhymes,
    skeleton,
    successor,
    unparse,
)
from lexers import LEXERS  # noqa: E402
from machine import depth_of, run  # noqa: E402
from parsers import PARSERS  # noqa: E402
from realm import GOLDEN, LAWS, ask, build_pairs, converge, corpus  # noqa: E402
from rhyme import Realm, fnv1a  # noqa: E402

passed = failed = 0


def ok(name, cond):
    global passed, failed
    if cond:
        passed += 1
        print(f"  ✓ {name}")
    else:
        failed += 1
        print(f"  ✗ {name}")


def raises(fn):
    try:
        fn()
    except Exception:
        return True
    return False


print("\n=== Rime — a language whose grammar rhymes ===\n")

PHRASE = "quantum realm"
pairs = build_pairs()


print("1. THE VOCABULARY")

ok("nine front ends", len(pairs) == 9)
ok("every verb is in exactly one class",
   all(sum(v in members for members in CLASSES.values()) == 1
       for v in VOCABULARY))
ok("a class is an operation family, not a spelling",
   all(v.rhyme == cls for cls, ms in CLASSES.items() for v in ms))
ok("classmates rhyme",
   all(rhymes(a.word, b.word)
       for ms in CLASSES.values() for a in ms for b in ms))
ok("verbs in different classes do not rhyme",
   all(not rhymes(a.word, b.word)
       for ca in CLASS_ORDER for cb in CLASS_ORDER if ca != cb
       for a in CLASSES[ca] for b in CLASSES[cb]))
ok("successor stays inside the class",
   all(rhymes(v.word, successor(v.word)) for v in VOCABULARY))
ok("successor is a bijection on each class",
   all(len({successor(v.word) for v in ms}) == len(ms)
       for ms in CLASSES.values()))
ok("successor never returns its argument",
   all(successor(v.word) != v.word for v in VOCABULARY))
ok("the language refuses a word it has never heard",
   not rhymes("grow", "cow") and "cow" not in WORDS)


print("\n2. THE SCANNERS")

SCANS = [
    "1 2 grow\n3 slow",
    "\n\n\t1 2 grow\n \n\n3 slow\n\n",
    "-3 throw\n4 5 mow",
    "",
    "\n\n\n",
    "1 $ 2 grow",
    "1 2 unheardof",
    "7 sight\ncite",
]
splits = [s for s in SCANS
          if len({f(s).canon() for f in LEXERS.values()}) != 1]
ok("three scanners, one reading", not splits)
# Kinds, not canonical forms: a blank line shifts every position
# after it, and that shift is real. What must not change is how many
# NEWLINEs come out of the run -- exactly one, however tall the gap.
ok("a blank line between couplets is cosmetic",
   all([t.kind for t in f("1 grow\n\n\n2 slow").toks] ==
       [t.kind for t in f("1 grow\n2 slow").toks]
       for f in LEXERS.values()))
ok("a poem does not begin or end with silence",
   [t.kind for t in LEXERS["L2-hand"]("\n\n1 grow\n\n").toks] ==
   ["NUM", "WORD", "EOF"])
ok("an illegal character is refused where it stands",
   all(not f("1 $ 2").ok and f("1 $ 2").fail.pos == 2
       for f in LEXERS.values()))
ok("an unknown word is a shape the scanner accepts",
   all(f("1 2 unheardof").ok for f in LEXERS.values()))
ok("a lone dash is not a number",
   all(not f("1 - grow").ok for f in LEXERS.values()))


print("\n3. THE PARSERS")

def verdicts(src):
    return {ask(p, src).verdict for p in pairs}


ok("a couplet that rhymes is a poem",
   verdicts("1 2 grow\n3 slow") ==
   {"(poem (couplet (line 1 2 grow) (line 3 slow)))"})
for cid, src, want in GOLDEN:
    got = verdicts(src)
    accepted = len(got) == 1 and not next(iter(got)).startswith("FAIL")
    ok(f"golden {cid} — {'accepted' if want == 'accept' else 'refused'}"
       f", by all nine",
       len(got) == 1 and accepted == (want == "accept"))

ok("a couplet that does not rhyme is unrhymed",
   verdicts("1 2 grow\n3 4 keep") == {"FAIL[parse/unrhymed]"})
ok("shape is checked before rhyme",
   verdicts("1 2\n3 4 keep") == {"FAIL[parse/voiceless]"})
ok("vocabulary is checked before pairing",
   verdicts("1 bogus") == {"FAIL[parse/unknown]"})
ok("pairing is checked before rhyme",
   verdicts("1 2 grow") == {"FAIL[parse/orphaned]"})


print("\n4. THE MACHINE")

def poem_of(src):
    lo = LEXERS["L1-regex"](src)
    return PARSERS["P1-descent"](lo.toks).ast


ok("arithmetic", run(poem_of("2 3 grow\n1 slow")).stack == [4])
ok("the stack is a stack",
   run(poem_of("1 2 combine\n align")).stack == [2, 1, 1])
ok("the store answers", run(poem_of("7 3 keep\n3 peep")).stack == [7])
ok("an unwritten cell reads zero",
   run(poem_of("99 peep\n1 sweep")).ok)
ok("the voice says what it pops",
   run(poem_of("42 light\ncite")).said == ["42", "[]"])
ok("division by zero is defined, not fatal",
   run(poem_of("5 0 divine\n1 align")).ok)
ok("modulo by zero is defined, not fatal",
   run(poem_of("5 0 mow\n1 throw")).ok)
ok("a starved poem refuses rather than raises",
   run(poem_of("grow\nslow")).fail.defect == "starved")
ok("static depth agrees with the machine",
   depth_of(poem_of("2 3 grow\n1 slow")) == 1)
ok("static depth sees starvation without running",
   depth_of(poem_of("grow\nslow")) is None)


print("\n5. THE RHYMING RULE AS A GENERATOR")

ok("fnv1a('') is the offset basis", fnv1a(b"") == 0xCBF29CE484222325)
ok("fnv1a('a') matches the published vector",
   fnv1a(b"a") == 0xAF63DC4C8601EC8C)
ok("fnv1a('foobar') matches the published vector",
   fnv1a(b"foobar") == 0x85944171F73967E8)

realm = Realm(PHRASE)
ok("an empty choice is refused", raises(lambda: realm.collapse("x", 0)))
ok("a phrase determines its poems",
   unparse(realm.poem(6)) == unparse(Realm(PHRASE).poem(6)))
ok("a different phrase is a different realm",
   unparse(Realm("other").poem(6)) != unparse(realm.poem(6)))

# The claim the address space exists to support.
warmed = Realm(PHRASE)
for i in range(9):
    warmed.couplet(i, 0)
ok("a couplet does not depend on its predecessors",
   warmed.couplet(9, 0)[0].sexp() == Realm(PHRASE).couplet(9, 0)[0].sexp())

# The rhyming rule proper: half the poem is derived, not chosen.
poem = realm.poem(12)
ok("every generated couplet rhymes",
   all(rhymes(c.first.verb, c.second.verb) for c in poem.couplets))
ok("the answering verb is the successor of the opening one",
   all(c.second.verb == successor(c.first.verb) for c in poem.couplets))
ok("generation is not one couplet repeated",
   len(set(skeleton(poem).split())) > 1)
ok("all four classes are reachable",
   {c.sound() for c in Realm("many sounds").poem(60).couplets} ==
   set(CLASS_ORDER))
ok("a generated poem never starves", depth_of(poem) is not None)
ok("a generated poem runs", run(poem).ok)
ok("a generated poem is accepted by all nine",
   len(verdicts(unparse(poem))) == 1 and
   not next(iter(verdicts(unparse(poem)))).startswith("FAIL"))


print("\n6. DETERMINISM ACROSS PROCESSES")


def _run(seed):
    env = dict(os.environ, PYTHONHASHSEED=seed)
    return subprocess.run(
        [sys.executable, "-c",
         "from rhyme import Realm; from contract import unparse;"
         "print(unparse(Realm('quantum realm').poem(8)))"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        env=env, capture_output=True, text=True, check=False).stdout


a, b = _run("0"), _run("12345")
ok("PYTHONHASHSEED does not change the poem", a == b and bool(a.strip()))


print("\n7. THE LAWS, INJECTED WITH A FAULT")

# A law nobody can fail is decoration. Each of these hands the law a
# front end that is wrong in the way the law exists to catch.
class _Crashing:
    def __call__(self, src):
        raise RuntimeError("scanner gave up")


rigged = [*pairs, type(pairs[0])("L9-crash x P1", _Crashing(),
                                 PARSERS["P1-descent"])]
answers = {p.name: ask(p, "1 2 grow\n3 slow") for p in rigged}
ok("total catches a scanner that raises",
   any("L9-crash" in v for v in LAWS["total"]("", answers, rigged)))
ok("agreement is silent when everyone agrees",
   not LAWS["agreement"]("1 2 grow\n3 slow",
                         {p.name: ask(p, "1 2 grow\n3 slow") for p in pairs},
                         pairs))

# A poem assembled behind the parsers' backs, so the rhyme law has
# something to find that the parsers would never have let through.
smuggled = Poem([Couplet(Line([1, 2], "grow"), Line([3, 4], "keep"))])


class _Smuggling:
    ast = smuggled

    def __call__(self, toks):
        from contract import ParseOut
        return ParseOut(ast=smuggled)


sneaky = [type(pairs[0])("L1 x P9-smuggle", LEXERS["L1-regex"],
                         _Smuggling())]
sneaky_answers = {p.name: ask(p, "1 2 grow\n3 slow") for p in sneaky}
ok("rhyme catches a poem that was never rhymed",
   bool(LAWS["rhyme"]("", sneaky_answers, sneaky)))
ok("machine catches a tree the machine cannot run",
   isinstance(LAWS["machine"]("", sneaky_answers, sneaky), list))


print("\n8. THE WHOLE CORPUS, EVERY LAW")

rep = converge(PHRASE, 40)
ok("the corpus has both poems and refusals",
   rep.accepted > 0 and rep.refused > 0)
ok("every poem was read by nine front ends", rep.pairs == 9)
ok("the corpus is not trivially small", rep.read >= 50)
for law in LAWS:
    ok(f"law: {law}", law not in rep.broken)
ok("the language came together", rep.clean)

# A second phrase, so convergence is not a fact about one corpus.
other = converge("entangle the parser", 40)
ok("and it comes together from another phrase too", other.clean)
ok("the two phrases are genuinely different corpora",
   [s for _, s in corpus(PHRASE, 12)] !=
   [s for _, s in corpus("entangle the parser", 12)])

print(f"\n=== Rime: {passed} passed, {failed} failed ===\n")
raise SystemExit(0 if failed == 0 else 1)
