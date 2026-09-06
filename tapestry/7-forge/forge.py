#!/usr/bin/env python3
"""
forge.py — the loop that turns four front ends into one language.

Every lexer is paired with every parser and the whole matrix is run
against the same cases. Where the pairs agree, the answer belongs to
the language. Where they disagree, the language never actually said,
and the disagreement is the finding.

Arbitration is three-tiered, most authoritative first:

  1. DOCTRINE   a published document already settles it. A vote cannot
                overturn SEMANTICS.md or PIPELINE.md, so this tier runs
                before counting anybody.

  2. COVERAGE   the documents are silent, but stage 4 demonstrably
                holds something stages 1-3 cannot express. This tier
                exists because a vote cannot see it: all four front
                ends can agree, sincerely, on a limitation the rest of
                the language does not have, and consensus would then
                write that limitation into the specification.

  3. FINDING    the forge's own laws settle it. A law violation is
                evidence about the language, not about one
                implementation, so it outranks a vote among
                implementations that share the defect.

  4. CONSENSUS  the documents are silent, so the independent witnesses
                are polled — VOWELS.md's oracle, unchanged: at least
                pi = 3 agreeing and at least two thirds of those that
                answered. Below that it withholds rather than guessing.

  5. ESCALATE   nothing settles it. The forge says so and stops
                short. Inventing an answer here would teach the corpus
                a fact nobody verified, which is the one thing the
                language exists to prevent.

Counterexamples found by fuzzing are written to disk and carried by
every later generation, so criticism writes the next specification
rather than merely scoring this one (VOWELS.md, "The loop").

Convergence has to be earned: the fuzz budget doubles after every
clean generation, so "no counterexample found" is a statement about a
search that keeps getting harder, not about a search that got lucky.

Codric Enterprise · Ricky (Dreid) · 2026
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from contract import unparse                                   # noqa: E402
from corpus import (ACCEPT, GOLDEN, PROBES, REFUSE_LEX,         # noqa: E402
                    REFUSE_PARSE, Case, Fuzzer)
from coverage import Gap, probe_all                             # noqa: E402
from laws import (Run, Violation, law_agreement,                # noqa: E402
                  law_determinism, law_position, law_roundtrip,
                  law_token_stream, law_total, law_unambiguous)
from lexers import LEXERS                                       # noqa: E402
from parsers import PARSERS                                     # noqa: E402
from spec import SPEC                                           # noqa: E402

COUNTEREXAMPLES = os.path.join(HERE, "counterexamples.json")
LEDGER = os.path.join(HERE, "ledger.json")

PI = 3                    # SEMANTICS.md 1.1, ASCEND_POINTS = floor(pi)
TWO_THIRDS = 2.0 / 3.0


# ═════════════════════════════════════════════
# Tier 1 — what the documents already settle
# ═════════════════════════════════════════════

@dataclass
class Doctrine:
    answer: Any
    source: str
    quote: str


DOCTRINE: Dict[str, Doctrine] = {
    "cmp_kind": Doctrine(
        "CMP", "PIPELINE.md, section 2",
        "compare := additive [ CMP additive ] — the published grammar "
        "names CMP as the class of the comparison operator, so a bare "
        "'<' that scans as OP cannot satisfy the rule the project "
        "already printed."),

    "unterminated_string_defect": Doctrine(
        "unbounded", "PIPELINE.md and SEMANTICS.md 1",
        "PIPELINE.md classifies running out of input ('1 +') as "
        "Z(unbounded) and an illegal character ('a $ b') as "
        "Z(misbound). A string with no closing quote ran out of input; "
        "it is not a character the language rejects."),

    "reserved_words": Doctrine(
        ["def", "else", "false", "if", "then", "true"],
        "PIPELINE.md, section 2",
        "'This is the whole language. Anything not derivable here is "
        "outside the grammar.' Thirteen of the incumbent's nineteen "
        "reserved words appear in no rule, so they reserve names "
        "against a syntax that does not exist."),

    "chained_comparison": Doctrine(
        False, "PIPELINE.md, section 2",
        "compare := additive [ CMP additive ] — the brackets are "
        "optional-once, not repeated, so 'a < b < c' is outside the "
        "published grammar."),
}


@dataclass
class Finding:
    """A ruling the forge derived from one of its own laws."""
    answer: Any
    law: str
    evidence: str


FINDINGS: Dict[str, Finding] = {
    "trailing_expression": Finding(
        False, "unambiguous",
        "Allowing 'program := deflist [expr]' makes the grammar "
        "ambiguous. 'def f(n) = 1 - 1' has two derivations: a body of "
        "'1 - 1', or a body of '1' followed by the expression '- 1' "
        "under prefix minus. The chart parser reports overbound; the "
        "three deterministic parsers resolve it greedily and never "
        "mention it. Dropping the trailing expression removes the "
        "ambiguity and still closes the coverage gap, which was about "
        "holding several definitions in one namespace and never about "
        "a trailing expression."),
}


# ═════════════════════════════════════════════
# Pairs
# ═════════════════════════════════════════════

@dataclass
class Pair:
    name: str
    lexer: str
    parser: str
    lex: Callable
    parse: Callable


def build_pairs() -> List[Pair]:
    return [Pair(f"{ln} x {pn}", ln, pn, lf, pf)
            for ln, lf in LEXERS.items()
            for pn, pf in PARSERS.items()]


# ═════════════════════════════════════════════
# Reports
# ═════════════════════════════════════════════

@dataclass
class Divergence:
    src: str
    aspect: str
    answers: Dict[str, str]
    question: Optional[str] = None

    def groups(self) -> Dict[str, List[str]]:
        g: Dict[str, List[str]] = {}
        for who, ans in self.answers.items():
            g.setdefault(str(ans), []).append(who)
        return g


@dataclass
class GenReport:
    generation: int
    cases: int = 0
    fuzzed: int = 0
    golden_failures: List[str] = field(default_factory=list)
    violations: List[Violation] = field(default_factory=list)
    divergences: List[Divergence] = field(default_factory=list)
    ratified: List[str] = field(default_factory=list)
    escalated: List[str] = field(default_factory=list)
    gaps: List[Any] = field(default_factory=list)
    promoted: int = 0
    seconds: float = 0.0

    @property
    def clean(self) -> bool:
        return (not self.golden_failures and not self.violations
                and not self.divergences)

    def line(self) -> str:
        mark = "clean" if self.clean else "findings"
        return (f"gen {self.generation:>3} | {self.cases:>6} cases "
                f"({self.fuzzed:>6} fuzzed) | "
                f"gold {len(self.golden_failures):>3} "
                f"law {len(self.violations):>3} "
                f"diverge {len(self.divergences):>3} | "
                f"ratified {len(self.ratified)} promoted {self.promoted:>3} "
                f"| {mark} | {self.seconds:.1f}s")


# ═════════════════════════════════════════════
# The forge
# ═════════════════════════════════════════════

class Forge:
    def __init__(self, seed: int = 1, budget: int = 400,
                 quiet_needed: int = 3, floor: int = 50_000,
                 max_gens: int = 60, verbose: bool = True):
        self.pairs = build_pairs()
        self.seed = seed
        self.budget = budget
        self.quiet_needed = quiet_needed
        self.floor = floor
        self.max_gens = max_gens
        self.verbose = verbose
        self.reports: List[GenReport] = []
        self.total_fuzzed = 0
        self.promoted: List[Case] = []
        self.escalations: Dict[str, str] = {}
        self.gaps: List[Gap] = []
        self._load_promoted()

    # ── persistence of counterexamples ──
    def _load_promoted(self) -> None:
        if not os.path.exists(COUNTEREXAMPLES):
            return
        with open(COUNTEREXAMPLES) as fh:
            raw = json.load(fh)
        self.promoted = [Case(r["cid"], r["src"], r.get("outcome"),
                              r.get("sexp"), r.get("note", ""), "promoted")
                         for r in raw.get("cases", [])]

    def _save_promoted(self) -> None:
        with open(COUNTEREXAMPLES, "w") as fh:
            json.dump({
                "note": "Counterexamples found by the forge. Every "
                        "generation after the one that found them must "
                        "satisfy them (VOWELS.md: criticism writes the "
                        "next specification).",
                "cases": [{"cid": c.cid, "src": c.src, "outcome": c.outcome,
                           "sexp": c.sexp, "note": c.note}
                          for c in self.promoted],
            }, fh, indent=2)
            fh.write("\n")

    # ── one pair, one source ──
    def run_one(self, pair: Pair, src: str) -> Run:
        r = Run(pair=pair.name, lex_canon="", parse_canon="")
        try:
            lo = pair.lex(src)
        except Exception as exc:                       # totality, tier one
            r.crash = f"{type(exc).__name__}: {exc}"
            return r
        r.lex_canon = lo.canon()
        r.lex_ok = lo.ok
        r.toks = tuple(lo.toks)
        if not lo.ok:
            r.parse_canon = lo.canon()
            r.fail_pos = lo.fail.pos
            r.fail_defect = lo.fail.defect
            r.verdict = f"FAIL[lex/{lo.fail.defect}]"
            return r
        try:
            po = pair.parse(lo.toks)
        except Exception as exc:                       # totality, tier two
            r.crash = f"{type(exc).__name__}: {exc}"
            return r
        r.parse_canon = po.canon()
        r.parse_ok = po.ok
        r.ast = po.ast
        if po.fail:
            r.fail_pos = po.fail.pos
            r.fail_defect = po.fail.defect
            r.verdict = f"FAIL[parse/{po.fail.defect}]"
        else:
            r.verdict = po.canon()
        return r

    def canon_of(self, pair_name: str, src: str) -> Optional[str]:
        pair = next(p for p in self.pairs if p.name == pair_name)
        r = self.run_one(pair, src)
        if r.crash:
            return None
        return r.verdict

    # ── outcome classification, for golden checks ──
    @staticmethod
    def outcome_of(r: Run) -> str:
        if r.crash:
            return "crash"
        if not r.lex_ok:
            return REFUSE_LEX
        if not r.parse_ok:
            return REFUSE_PARSE
        return ACCEPT

    # ── a generation ──
    def generation(self, n: int) -> GenReport:
        t0 = time.time()
        rep = GenReport(generation=n)

        fz = Fuzzer(seed=self.seed * 10_000 + n)
        fuzz_cases = fz.batch(self.budget)
        rep.fuzzed = len(fuzz_cases)
        self.total_fuzzed += len(fuzz_cases)

        cases: List[Case] = list(GOLDEN) + list(PROBES) + \
            list(self.promoted) + fuzz_cases
        rep.cases = len(cases)

        new_promotions: List[Case] = []

        for case in cases:
            runs = {p.name: self.run_one(p, case.src) for p in self.pairs}

            # ── laws ──
            vs: List[Violation] = []
            vs += law_total(case.src, runs)
            vs += law_agreement(case.src, runs)
            vs += law_unambiguous(case.src, runs)
            vs += law_position(case.src, runs)
            vs += law_token_stream(case.src, runs)
            vs += law_roundtrip(case.src, runs, self.canon_of)
            if case.origin in ("golden", "probe", "promoted"):
                vs += law_determinism(case.src, runs, self.canon_of)
            rep.violations.extend(vs)

            # ── golden claims ──
            if case.origin in ("golden", "promoted") and case.outcome:
                for r in runs.values():
                    got = self.outcome_of(r)
                    if got != case.outcome:
                        rep.golden_failures.append(
                            f"{case.cid}: {r.pair} gave {got}, "
                            f"required {case.outcome}")
                if case.sexp:
                    for r in runs.values():
                        if r.parse_ok and r.parse_canon != case.sexp:
                            rep.golden_failures.append(
                                f"{case.cid}: {r.pair} built "
                                f"{r.parse_canon!r}, required {case.sexp!r}")

            # ── divergence ──
            answers = {k: r.verdict for k, r in runs.items()
                       if not r.crash}
            if len(set(answers.values())) > 1:
                d = Divergence(case.src, "parse", answers, case.question)
                rep.divergences.append(d)
                if case.origin == "fuzz":
                    new_promotions.append(Case(
                        f"cx-{len(self.promoted) + len(new_promotions)}",
                        case.src, None, None,
                        "promoted: pairs disagreed", "promoted"))
            elif vs and case.origin == "fuzz":
                new_promotions.append(Case(
                    f"cx-{len(self.promoted) + len(new_promotions)}",
                    case.src, None, None,
                    f"promoted: {vs[0].law}", "promoted"))

        # de-duplicate promotions by source text
        known = {c.src for c in self.promoted}
        for c in new_promotions:
            if c.src not in known:
                self.promoted.append(c)
                known.add(c.src)
                rep.promoted += 1
        if rep.promoted:
            self._save_promoted()

        rep.seconds = time.time() - t0
        return rep

    # ── arbitration ──
    def accepts_everywhere(self, src: str) -> bool:
        """True only when every pair accepts. A capability half the
        matrix can express is not a capability the language has."""
        return all(self.run_one(p, src).parse_ok for p in self.pairs)

    def find_gaps(self) -> List[Gap]:
        return probe_all(self.accepts_everywhere)

    def poll(self, question: str) -> Dict[str, Any]:
        """Ask every witness what it currently answers. The answer for
        a scanner question comes from the scanners; for a grammar
        question, from the pairs."""
        answers: Dict[str, Any] = {}

        if question == "cmp_kind":
            for name, fn in LEXERS.items():
                out = fn("1 < 2")
                hit = [t for t in out.toks if t.text == "<"]
                answers[name] = hit[0].kind if hit else "none"
            return answers

        if question == "unterminated_string_defect":
            for name, fn in LEXERS.items():
                out = fn('"no close')
                answers[name] = out.fail.defect if out.fail else "accepted"
            return answers

        if question == "reserved_words":
            for name, fn in LEXERS.items():
                out = fn("to by show learn")
                answers[name] = ",".join(sorted(
                    {t.text for t in out.toks if t.kind == "KW"}))
            return answers

        probe_src = {
            "multi_definition": "def f(n) = n\ndef g(n) = n + 1",
            "chained_comparison": "1 < 2 < 3",
            "trailing_comma": "f(1,)",
            "trailing_expression": "def d(n) = n * 2\nd(21)",
        }.get(question)
        if probe_src is not None:
            for p in self.pairs:
                r = self.run_one(p, probe_src)
                answers[p.name] = "yes" if r.parse_ok else "no"
        return answers

    def arbitrate(self, gen: int, rep: GenReport) -> None:
        for q in list(SPEC.open_questions):
            key = q.key

            # tier 1 — doctrine
            doc = DOCTRINE.get(key)
            if doc is not None:
                SPEC.ratify(key, doc.answer, gen,
                            witnesses=[doc.source],
                            rationale=f"doctrine ({doc.source}): {doc.quote}")
                rep.ratified.append(f"{key} := {doc.answer!r}  [doctrine]")
                continue

            # tier 2 — a capability the syntax cannot reach
            gap = next((g for g in self.find_gaps() if g.question == key),
                       None)
            if gap is not None:
                SPEC.ratify(key, True, gen,
                            witnesses=["stage-4 runtime"],
                            rationale=(f"coverage gap: {gap.capability}. "
                                       f"Runtime: {gap.runtime_evidence}. "
                                       f"Syntax: {gap.syntax_evidence}. "
                                       f"{gap.citation}"))
                self.gaps.append(gap)
                rep.gaps.append(gap)
                rep.ratified.append(f"{key} := True  [coverage gap]")
                continue

            # tier 3 — the forge's own laws
            found = FINDINGS.get(key)
            if found is not None:
                SPEC.ratify(key, found.answer, gen,
                            witnesses=[f"law:{found.law}"],
                            rationale=(f"finding (law {found.law}): "
                                       f"{found.evidence}"))
                rep.ratified.append(
                    f"{key} := {found.answer!r}  [finding/{found.law}]")
                continue

            # tier 4 — consensus among independent witnesses
            answers = self.poll(key)
            if not answers:
                continue
            groups: Dict[str, List[str]] = {}
            for who, ans in answers.items():
                groups.setdefault(str(ans), []).append(who)
            best_key, best = max(groups.items(), key=lambda kv: len(kv[1]))
            if len(best) >= PI and len(best) >= TWO_THIRDS * len(answers):
                value: Any = best_key
                if best_key in ("yes", "no"):
                    value = (best_key == "yes")
                SPEC.ratify(key, value, gen, witnesses=best,
                            rationale=(f"consensus: {len(best)} of "
                                       f"{len(answers)} independent "
                                       f"witnesses, threshold pi={PI} and "
                                       f"two thirds"))
                rep.ratified.append(
                    f"{key} := {value!r}  [consensus {len(best)}/"
                    f"{len(answers)}]")
                continue

            # tier 5 — withhold, and say why
            detail = "; ".join(f"{k}: {len(v)}" for k, v in groups.items())
            self.escalations[key] = (
                f"{q.asks}  no document settles it and the witnesses "
                f"split {detail} — below pi={PI} agreeing, so the forge "
                f"withholds.")
            rep.escalated.append(key)

        SPEC.save()

    # ── convergence ──
    def converge(self) -> bool:
        quiet = 0
        gen = 0
        if self.verbose:
            print(f"\n{'=' * 78}\nTHE FORGE — {len(self.pairs)} front ends "
                  f"({len(LEXERS)} lexers x {len(PARSERS)} parsers)\n"
                  f"{'=' * 78}\n")
            print(f"open questions at start: "
                  f"{len(SPEC.open_questions)}\n")

        while gen < self.max_gens:
            rep = self.generation(gen)
            self.arbitrate(gen, rep)
            self.reports.append(rep)
            if self.verbose:
                print(rep.line())
                for r in rep.ratified:
                    print(f"        ratified  {r}")
                for e in rep.escalated:
                    print(f"        ESCALATED {e}")

            if rep.clean:
                quiet += 1
                self.budget = min(self.budget * 2, 25_000)
            else:
                quiet = 0
                self.budget = max(self.budget, 400)

            done = (quiet >= self.quiet_needed
                    and self.total_fuzzed >= self.floor
                    and not [q for q in SPEC.open_questions
                             if q.key not in self.escalations])
            if done:
                if self.verbose:
                    print(f"\nconverged after {gen + 1} generations, "
                          f"{self.total_fuzzed:,} programs fuzzed, "
                          f"{quiet} consecutive clean generations")
                self._write_ledger(True, gen + 1)
                return True
            gen += 1

        if self.verbose:
            print(f"\nDID NOT CONVERGE in {self.max_gens} generations")
        self._write_ledger(False, gen)
        return False

    def _write_ledger(self, converged: bool, gens: int) -> None:
        with open(LEDGER, "w") as fh:
            json.dump({
                "converged": converged,
                "generations": gens,
                "pairs": len(self.pairs),
                "lexers": sorted(LEXERS),
                "parsers": sorted(PARSERS),
                "programs_fuzzed": self.total_fuzzed,
                "counterexamples_carried": len(self.promoted),
                "settled": {q.key: {"answer": q.answer,
                                    "generation": q.generation,
                                    "rationale": q.rationale}
                            for q in SPEC.settled_questions},
                "escalated": self.escalations,
                "coverage_gaps": [
                    {"question": g.question, "capability": g.capability,
                     "runtime": g.runtime_evidence,
                     "syntax": g.syntax_evidence, "citation": g.citation}
                    for g in self.gaps],
                "generations_log": [
                    {"gen": r.generation, "cases": r.cases,
                     "fuzzed": r.fuzzed,
                     "golden_failures": len(r.golden_failures),
                     "violations": len(r.violations),
                     "divergences": len(r.divergences),
                     "ratified": r.ratified, "promoted": r.promoted,
                     "seconds": round(r.seconds, 2)}
                    for r in self.reports],
            }, fh, indent=2)
            fh.write("\n")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Run the language forge.")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--budget", type=int, default=400)
    ap.add_argument("--floor", type=int, default=50_000)
    ap.add_argument("--max-gens", type=int, default=60)
    ap.add_argument("--quiet", type=int, default=3)
    ap.add_argument("--reset", action="store_true",
                    help="clear every ruling and start from unratified")
    args = ap.parse_args()

    if args.reset:
        SPEC.reset()
        SPEC.save()
        for path in (COUNTEREXAMPLES, LEDGER):
            if os.path.exists(path):
                os.remove(path)

    forge = Forge(seed=args.seed, budget=args.budget, floor=args.floor,
                  max_gens=args.max_gens, quiet_needed=args.quiet)
    ok = forge.converge()
    sys.exit(0 if ok else 1)
