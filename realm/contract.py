"""Rime — tokens, vocabulary, trees, and the one idea the language has.

Rime is a postfix language whose *well-formedness condition is rhyme*.
A program is a sequence of couplets; a couplet is two lines; a line is
some operands followed by a verb. The verb ends the line, so the verb
is what the line rhymes on, and a couplet is well formed only when its
two verbs rhyme.

That would be decoration if rhyme classes were arbitrary. They are not.
The vocabulary is built so that **a rhyme class is exactly an operation
family**: everything rhyming on `-ow` moves numbers, everything rhyming
on `-eep` touches the store, and so on. So the rhyme rule is not a
pretty constraint bolted onto a normal language -- it is a typing
discipline written as verse. A couplet that rhymes is a couplet that
stayed on one topic, and the checker enforcing rhyme is enforcing
exactly that.

Two things follow, and they are the reason the language exists.

*Reading.* You can tell what a couplet does from how it sounds, before
you know what any individual word means.

*Writing.* The rhyme rule makes generation deterministic without a
random source. Once the first verb of a couplet is fixed, its class is
fixed, so the candidates for the second verb are a finite published
list -- and Rime takes the successor in that list. The second line of
every couplet is therefore a function of the first. Nothing is drawn.
See `rhyme.py`.

Codric Enterprise · 2026
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ══════════════════════════════════════════════════════════
# Tokens
# ══════════════════════════════════════════════════════════

#: Line structure is significant in Rime -- a couplet is two *lines* --
#: so the newline is a token and not whitespace. This is the single
#: most common place for independently written scanners to disagree,
#: which is precisely why the language is scanned three times over.
KINDS = ("NUM", "WORD", "NEWLINE", "EOF")

#: Rime's own defect classes. A front end never raises; it refuses,
#: and a refusal names one of these.
DEFECTS = (
    "unknown",    # a word that is not in the vocabulary
    "unrhymed",   # a couplet whose two verbs do not rhyme
    "orphaned",   # a line with no answering line
    "voiceless",  # a line with operands but no verb to end it
    "starved",    # the machine ran a verb with too little beneath it
)


@dataclass(frozen=True)
class Tok:
    kind: str
    text: str
    pos: int
    line: int

    def __repr__(self) -> str:
        return f"{self.kind}:{self.text!r}@{self.pos}"

    def canon(self) -> str:
        return f"{self.kind}({self.text})@{self.pos}L{self.line}"


@dataclass(frozen=True)
class Fail:
    """A refusal. A defect and a place, never prose."""

    stage: str          # "lex" | "parse" | "run"
    defect: str
    pos: int
    line: int

    def canon(self) -> str:
        return f"FAIL[{self.stage}/{self.defect}]@{self.pos}L{self.line}"


@dataclass
class LexOut:
    toks: list = field(default_factory=list)
    fail: Fail | None = None

    @property
    def ok(self) -> bool:
        return self.fail is None

    def canon(self) -> str:
        if self.fail:
            return self.fail.canon()
        return " ".join(t.canon() for t in self.toks)


# ══════════════════════════════════════════════════════════
# The vocabulary — rhyme class *is* operation family
# ══════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Verb:
    """One word. `arity` is what it takes off the stack, `gives` what
    it puts back -- both fixed, so a line's stack effect is known
    before it runs and the generator can avoid writing a program that
    starves."""

    word: str
    rhyme: str
    arity: int
    gives: int
    gloss: str


#: The four classes, each in its published order. The order is part of
#: the language: it is what "the next verb that rhymes" means, so it is
#: written once, here, and a change to it changes every generated
#: program. Nothing sorts this at runtime.
VOCABULARY: tuple[Verb, ...] = (
    # ── -ow · the numbers themselves ──
    Verb("grow",    "ow",   2, 1, "a b -- a+b"),
    Verb("slow",    "ow",   2, 1, "a b -- a-b"),
    Verb("throw",   "ow",   1, 1, "a -- -a"),
    Verb("mow",     "ow",   2, 1, "a b -- a mod b"),
    # ── -ine · two things becoming one, or one becoming two ──
    Verb("twine",   "ine",  2, 1, "a b -- a*b"),
    Verb("divine",  "ine",  2, 1, "a b -- a/b, truncating"),
    Verb("align",   "ine",  1, 2, "a -- a a"),
    Verb("combine", "ine",  2, 2, "a b -- b a"),
    # ── -eep · the store, and the shape of the stack ──
    Verb("keep",    "eep",  2, 0, "v a -- ; store v at cell a"),
    Verb("peep",    "eep",  1, 1, "a -- v ; load cell a"),
    Verb("heap",    "eep",  0, 1, "-- n ; how deep the stack is"),
    Verb("sweep",   "eep",  1, 0, "a -- ; forget cell a"),
    # ── -ight · anything the program says out loud ──
    Verb("light",   "ight", 1, 0, "a -- ; say a"),
    Verb("sight",   "ight", 1, 1, "a -- a ; say a, keep it"),
    Verb("write",   "ight", 1, 0, "a -- ; say a as a character"),
    Verb("cite",    "ight", 0, 0, "-- ; say the whole stack"),
)

WORDS: dict[str, Verb] = {v.word: v for v in VOCABULARY}

#: class -> the verbs in it, in published order.
CLASSES: dict[str, tuple[Verb, ...]] = {}
for _v in VOCABULARY:
    CLASSES[_v.rhyme] = CLASSES.get(_v.rhyme, ()) + (_v,)

#: The classes themselves, in published order.
CLASS_ORDER: tuple[str, ...] = tuple(CLASSES)


def rhyme_of(word: str) -> str | None:
    """The class a word belongs to, or None if the language has never
    heard of it. Deliberately a lookup and not a suffix rule: a suffix
    rule would happily accept `cow` or `sheep` and invent a meaning for
    them, and a language that guesses is a language that cannot refuse."""
    v = WORDS.get(word)
    return v.rhyme if v else None


def rhymes(first: str, second: str) -> bool:
    a, b = rhyme_of(first), rhyme_of(second)
    return a is not None and a == b


def successor(word: str) -> str:
    """The next verb in the same class, wrapping.

    This is the rhyming rule in its generative form. It is total over
    the vocabulary and it is a *function*, which is what lets a whole
    program be determined by its opening line.
    """
    v = WORDS[word]
    members = CLASSES[v.rhyme]
    return members[(members.index(v) + 1) % len(members)].word


# ══════════════════════════════════════════════════════════
# Trees
# ══════════════════════════════════════════════════════════

@dataclass
class Line:
    """Operands, then the verb that ends and names the line."""

    operands: list[int]
    verb: str
    line_no: int = 0

    def sexp(self) -> str:
        nums = "".join(f" {n}" for n in self.operands)
        return f"(line{nums} {self.verb})"

    def sound(self) -> str:
        return rhyme_of(self.verb) or "?"


@dataclass
class Couplet:
    first: Line
    second: Line

    def sexp(self) -> str:
        return f"(couplet {self.first.sexp()} {self.second.sexp()})"

    def sound(self) -> str:
        return self.first.sound()


@dataclass
class Poem:
    couplets: list[Couplet] = field(default_factory=list)

    def lines(self) -> list[Line]:
        return [ln for c in self.couplets for ln in (c.first, c.second)]

    def sexp(self) -> str:
        return "(poem " + " ".join(c.sexp() for c in self.couplets) + ")"

    def scheme(self) -> str:
        """The rhyme scheme, which is the program's shape at a glance:
        `ow.ow ine.ine` and so on."""
        return " ".join(f"{c.first.sound()}.{c.second.sound()}"
                        for c in self.couplets)


@dataclass
class ParseOut:
    ast: Poem | None = None
    fail: Fail | None = None

    @property
    def ok(self) -> bool:
        return self.fail is None and self.ast is not None

    def canon(self) -> str:
        if self.fail:
            return self.fail.canon()
        return self.ast.sexp() if self.ast else "(none)"


# ══════════════════════════════════════════════════════════
# Printing — the other half of the round trip
# ══════════════════════════════════════════════════════════

def unparse_line(ln: Line) -> str:
    return " ".join([str(n) for n in ln.operands] + [ln.verb])


def unparse(poem: Poem) -> str:
    """A poem back to source, couplets separated by a blank line.

    The blank line is cosmetic and the scanners are required to treat
    it as such; that requirement is worth stating because it is the
    kind of thing three independently written scanners will otherwise
    each decide for themselves.
    """
    return "\n\n".join(
        unparse_line(c.first) + "\n" + unparse_line(c.second)
        for c in poem.couplets
    )


def skeleton(poem: Poem) -> str:
    """The shape with the numbers erased: which verbs, in what order.

    Two poems with the same skeleton say the same thing about different
    values, so this is what to compare when asking whether a generator
    produced genuine variety or the same poem wearing new numbers.
    """
    return " ".join(
        f"{c.first.verb}/{c.second.verb}" for c in poem.couplets
    )


__all__ = [
    "CLASSES", "CLASS_ORDER", "DEFECTS", "KINDS", "VOCABULARY", "WORDS",
    "Couplet", "Fail", "LexOut", "Line", "ParseOut", "Poem", "Tok", "Verb",
    "rhyme_of", "rhymes", "skeleton", "successor", "unparse", "unparse_line",
]
