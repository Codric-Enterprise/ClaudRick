"""The rhyming rule, in its generative form.

Rime checks rhyme to decide whether a poem is well formed. This module
runs the same rule backwards and uses it to *write* poems -- which is
the whole reason the vocabulary was built the way it was.

## Why rhyme makes generation deterministic

Pick the first verb of a couplet and you have picked its rhyme class,
because in Rime a verb belongs to exactly one. The class is a finite,
published, ordered list. So the candidates for the answering verb are
not a space to sample from; they are four items in a known order, and
Rime's rule is simply: **the next one**. `contract.successor` is total
over the vocabulary and is a function, so the second line of every
couplet is determined by the first. Half the program writes itself, and
that half involves no choice at all.

The remaining choices -- which class, which opening verb, which numbers
-- come from the phrase, through FNV-1a, addressed by position. There
is no random source anywhere in this file.

## Addressed, not sequential

Each choice is keyed by a path: `"3/verb"`, `"3/b/op1"`. So a choice
depends on the phrase and where it sits, and on nothing else -- not on
call order, not on how many couplets were written before it. Couplet 9
can be generated on its own, without generating couplets 0 through 8
first, and it comes out the same either way. A seeded random generator
cannot say that: reproducing its hundredth draw means replaying the
ninety-nine before it.

## Generated poems do not starve

Every verb's arity is published, so the generator tracks the stack as
it writes and pushes exactly the operands a verb needs and no more.
What comes out parses and runs, which is what makes it usable as
material for the matrix in `realm.py`: a corpus of refusals would
exercise the front ends' agreement about failure, but never their
agreement about what a program *means*.

Codric Enterprise · 2026
"""

from __future__ import annotations

from contract import (
    CLASS_ORDER,
    CLASSES,
    WORDS,
    Couplet,
    Line,
    Poem,
    successor,
)

_FNV_OFFSET = 0xCBF29CE484222325
_FNV_PRIME = 0x100000001B3
_MASK64 = 0xFFFFFFFFFFFFFFFF


def fnv1a(data: bytes) -> int:
    """FNV-1a, 64-bit, written out rather than imported.

    Python's `hash()` is salted per process, so a generator resting on
    it would emit a different corpus every run and still call itself
    deterministic. This is four lines and can be checked by eye against
    the published constants, which matters more here than speed: the
    claim this module makes is that a poem is a function of a phrase.
    """
    h = _FNV_OFFSET
    for byte in data:
        h ^= byte
        h = (h * _FNV_PRIME) & _MASK64
    return h


class Realm:
    """A phrase, and every poem it determines."""

    def __init__(self, phrase: str) -> None:
        self.phrase = phrase

    def collapse(self, addr: str, n: int) -> int:
        """Choose one of `n`, by phrase and address alone."""
        if n <= 0:
            raise ValueError("no candidates to choose between")
        return fnv1a(f"{self.phrase}\x00{addr}".encode()) % n

    # ── one couplet ──
    def couplet(self, index: int, depth: int) -> tuple[Couplet, int]:
        """Write couplet `index`, given the stack depth it starts at.

        Returns the couplet and the depth it leaves behind. The opening
        verb is chosen; the answering verb is *derived* -- that asymmetry
        is the rhyming rule and it is the only reason this is a couplet
        rather than two unrelated lines.
        """
        cls = CLASS_ORDER[self.collapse(f"{index}/class", len(CLASS_ORDER))]
        members = CLASSES[cls]
        opener = members[self.collapse(f"{index}/verb", len(members))].word
        answer = successor(opener)

        first, depth = self._line(f"{index}/a", opener, depth)
        second, depth = self._line(f"{index}/b", answer, depth)
        return Couplet(first, second), depth

    def _line(self, addr: str, verb: str, depth: int) -> tuple[Line, int]:
        """Push exactly what the verb needs and no more.

        Operands are 1..99, never 0: `divine` and `mow` by zero are
        defined, but a corpus full of them would be testing that one
        definition over and over instead of the language around it.
        """
        v = WORDS[verb]
        need = max(0, v.arity - depth)
        operands = [1 + self.collapse(f"{addr}/op{i}", 99)
                    for i in range(need)]
        depth = depth + need - v.arity + v.gives
        return Line(operands, verb), depth

    # ── a whole poem ──
    def poem(self, couplets: int = 8) -> Poem:
        out, depth = [], 0
        for i in range(couplets):
            cp, depth = self.couplet(i, depth)
            out.append(cp)
        return Poem(out)


__all__ = ["Realm", "fnv1a"]
