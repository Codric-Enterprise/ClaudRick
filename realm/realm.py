"""The realm: every scanner against every parser, over everything.

Three scanners and three parsers make nine front ends. Each was derived
from a different mechanism, so where all nine agree the answer belongs
to Rime, and where they split, Rime never said and the split is the
finding. This is the same discipline `ezr/7-forge/` applies to EZR; the
languages share no code, no tokens and no trees, only the conviction
that one implementation cannot be evidence about itself.

## What a verdict is, and what it leaves out

Agreement is judged on the tree when a poem is accepted, and on the
stage and defect when it is refused. The *position* of a refusal is
excluded on purpose. P1 reports the token it choked on and P3 reports
the token that ended the line it was inspecting; both are honest,
neither is a claim about Rime, and folding them into the verdict would
manufacture disagreements about nothing.

## The laws

A golden case says what one poem does. A law says what every poem does,
which is the only kind of statement a generator can be pointed at.

* **total** -- no front end raises. A scanner that throws makes Rime's
  totality a property of whoever wrote the caller.
* **agreement** -- all nine reach the same verdict.
* **roundtrip** -- print an accepted poem and read it back: same poem.
  This is also the property an emitter needs first.
* **determinism** -- the same text twice gives the same answer.
* **rhyme** -- every couplet in an accepted poem rhymes. The parsers
  enforce this, so the law is asking whether they actually did rather
  than taking their word for it.
* **family** -- the two verbs of a couplet are in the same operation
  family. In Rime this is not a second fact: the vocabulary is built so
  that class *is* family, and this law is what holds the vocabulary to
  that. Add a verb to the wrong class and everything else still passes.
* **machine** -- running an accepted poem does not raise; it produces
  output or it refuses.

Codric Enterprise · 2026
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field

from contract import CLASSES, WORDS, rhyme_of, unparse
from lexers import LEXERS
from machine import depth_of, run
from parsers import PARSERS
from rhyme import Realm

# ══════════════════════════════════════════════════════════
# The matrix
# ══════════════════════════════════════════════════════════


@dataclass(frozen=True)
class Pair:
    name: str
    lex: object
    parse: object


def build_pairs() -> list[Pair]:
    return [Pair(f"{ln} x {pn}", lf, pf)
            for ln, lf in LEXERS.items()
            for pn, pf in PARSERS.items()]


@dataclass
class Answer:
    verdict: str
    ast: object = None
    crash: str | None = None


def ask(pair: Pair, src: str) -> Answer:
    """One pair, one poem. Never raises: a crash is an answer too, and
    a law below is waiting for it."""
    try:
        lo = pair.lex(src)
    except Exception as exc:                            # noqa: BLE001
        return Answer("CRASH", None, f"{type(exc).__name__}: {exc}")
    if not lo.ok:
        return Answer(f"FAIL[lex/{lo.fail.defect}]")
    try:
        po = pair.parse(lo.toks)
    except Exception as exc:                            # noqa: BLE001
        return Answer("CRASH", None, f"{type(exc).__name__}: {exc}")
    if not po.ok:
        return Answer(f"FAIL[parse/{po.fail.defect}]")
    return Answer(po.ast.sexp(), po.ast)


# ══════════════════════════════════════════════════════════
# The corpus
# ══════════════════════════════════════════════════════════

ACCEPT, REFUSE = "accept", "refuse"

#: Hand-written cases. Every defect Rime can name appears here, because
#: a corpus that only contains poems tests half a language.
GOLDEN: list[tuple[str, str, str]] = [
    ("say-one",      "1 2 grow\n3 slow",              ACCEPT),
    ("two-couplets", "1 2 grow\n3 slow\n\n2 twine\n align", ACCEPT),
    ("blank-lines",  "\n\n1 2 grow\n\n\n3 slow\n\n",  ACCEPT),
    ("negatives",    "-3 throw\n4 5 mow",             ACCEPT),
    ("empty",        "",                              ACCEPT),
    ("voice",        "7 sight\n cite",                ACCEPT),
    ("unrhymed",     "1 2 grow\n3 4 keep",            REFUSE),
    ("unknown",      "1 2 bogus\n3 slow",             REFUSE),
    ("orphaned",     "1 2 grow",                      REFUSE),
    ("voiceless",    "1 2\n3 4",                      REFUSE),
    ("verb-first",   "grow 1 2\n3 slow",              REFUSE),
    ("bad-char",     "1 $ 2 grow\n3 slow",            REFUSE),
]


def corpus(phrase: str, count: int) -> list[tuple[str, str]]:
    """The golden cases, then generated poems. Returns (id, source)."""
    out = [(cid, src) for cid, src, _ in GOLDEN]
    realm = Realm(phrase)
    for i in range(count):
        out.append((f"gen-{i}", unparse(realm.poem(1 + i % 6))))
    return out


# ══════════════════════════════════════════════════════════
# The laws
# ══════════════════════════════════════════════════════════

def law_total(src, answers, pairs):
    return [f"{n}: raised {a.crash}" for n, a in answers.items() if a.crash]


def law_agreement(src, answers, pairs):
    live = {n: a for n, a in answers.items() if not a.crash}
    groups: dict[str, list[str]] = {}
    for n, a in live.items():
        groups.setdefault(a.verdict, []).append(n)
    if len(groups) <= 1:
        return []
    winner = max(groups.values(), key=len)
    agreed = next(v for v, m in groups.items() if m is winner)
    return [f"{', '.join(m)} said {v[:60]!r}, {len(winner)} others said "
            f"{agreed[:60]!r}"
            for v, m in groups.items() if m is not winner]


def law_roundtrip(src, answers, pairs):
    out = []
    for pair in pairs:
        a = answers[pair.name]
        if a.ast is None:
            continue
        again = ask(pair, unparse(a.ast))
        if again.verdict != a.verdict:
            out.append(f"{pair.name}: printed and reread as "
                       f"{again.verdict[:50]!r}, was {a.verdict[:50]!r}")
    return out


def law_determinism(src, answers, pairs):
    return [f"{p.name}: second reading differed"
            for p in pairs if ask(p, src).verdict != answers[p.name].verdict]


def law_rhyme(src, answers, pairs):
    out = []
    for name, a in answers.items():
        if a.ast is None:
            continue
        for i, c in enumerate(a.ast.couplets):
            if rhyme_of(c.first.verb) != rhyme_of(c.second.verb):
                out.append(f"{name}: couplet {i} accepted but does not "
                           f"rhyme: {c.first.verb}/{c.second.verb}")
    return out


def law_family(src, answers, pairs):
    """Class is family, or the vocabulary has drifted from its own idea.

    Checked against the source of truth rather than the poem: every
    verb in a class must agree with its classmates about which class
    they are in. It reads as a tautology and is not -- it is what fails
    when somebody adds a verb to a list it does not belong in.
    """
    out = []
    for cls, members in CLASSES.items():
        for v in members:
            if v.rhyme != cls or WORDS[v.word] is not v:
                out.append(f"vocabulary: {v.word} is filed under {cls} "
                           f"but calls itself {v.rhyme}")
    return out


def law_machine(src, answers, pairs):
    out = []
    for name, a in answers.items():
        if a.ast is None:
            continue
        try:
            r = run(a.ast)
        except Exception as exc:                        # noqa: BLE001
            out.append(f"{name}: machine raised {type(exc).__name__}: {exc}")
            continue
        if r.ok and depth_of(a.ast) is None:
            out.append(f"{name}: ran, but static depth says it starves")
        if not r.ok and r.fail.defect != "starved":
            out.append(f"{name}: refused at run time as {r.fail.defect}")
    return out


LAWS = {
    "total": law_total,
    "agreement": law_agreement,
    "roundtrip": law_roundtrip,
    "determinism": law_determinism,
    "rhyme": law_rhyme,
    "family": law_family,
    "machine": law_machine,
}


# ══════════════════════════════════════════════════════════
# Convergence
# ══════════════════════════════════════════════════════════

@dataclass
class Report:
    phrase: str
    pairs: int = 0
    read: int = 0
    accepted: int = 0
    refused: int = 0
    broken: dict[str, list[str]] = field(default_factory=dict)

    @property
    def clean(self) -> bool:
        return not self.broken

    def summary(self) -> str:
        state = "the language came together" if self.clean else "SPLIT"
        return (f"{self.read} poems x {self.pairs} front ends  "
                f"({self.accepted} accepted, {self.refused} refused)"
                f"  — {state}")


def converge(phrase: str, count: int, verbose: bool = False) -> Report:
    pairs = build_pairs()
    rep = Report(phrase, pairs=len(pairs))

    for cid, src in corpus(phrase, count):
        answers = {p.name: ask(p, src) for p in pairs}
        rep.read += 1
        first = answers[pairs[0].name]
        if first.ast is not None:
            rep.accepted += 1
        else:
            rep.refused += 1

        for law, fn in LAWS.items():
            for bad in fn(src, answers, pairs):
                rep.broken.setdefault(law, []).append(f"{cid}: {bad}")

        if verbose:
            mark = "✓" if not any(
                fn(src, answers, pairs) for fn in LAWS.values()) else "✗"
            print(f"  {mark} {cid:<14} {first.verdict[:58]}")
    return rep


# ══════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════

def show_poem(phrase: str, couplets: int) -> None:
    realm = Realm(phrase)
    poem = realm.poem(couplets)
    src = unparse(poem)

    print(f"\n  realm {phrase!r}\n")
    for i, c in enumerate(poem.couplets):
        sound = rhyme_of(c.first.verb)
        print(f"    ── couplet {i}  rhyming on -{sound}")
        print(f"       {c.first.verb:<9} {WORDS[c.first.verb].gloss}")
        print(f"       {c.second.verb:<9} {WORDS[c.second.verb].gloss}")
    print("\n  the poem\n")
    for ln in src.splitlines():
        print(f"    {ln}")
    print(f"\n  scheme: {poem.scheme()}")

    out = run(poem)
    if out.ok:
        said = " ".join(out.said) if out.said else "(nothing)"
        print(f"  says:   {said}")
        print(f"  leaves: {out.stack}\n")
    else:
        print(f"  refused: {out.fail.canon()}\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Rime — a language that rhymes")
    ap.add_argument("--phrase", default="quantum realm",
                    help="the phrase every generated poem collapses from")
    ap.add_argument("--couplets", type=int, default=5)
    ap.add_argument("--poems", type=int, default=24,
                    help="how many generated poems to put to the matrix")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)

    show_poem(args.phrase, args.couplets)

    print("  putting it to nine front ends\n")
    rep = converge(args.phrase, args.poems, verbose=args.verbose)
    print(f"\n  {rep.summary()}\n")
    for law, bad in rep.broken.items():
        print(f"  [{law}]")
        for b in bad[:6]:
            print(f"    {b}")
    return 0 if rep.clean else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["GOLDEN", "LAWS", "Pair", "Report", "ask", "build_pairs",
           "converge", "corpus"]
