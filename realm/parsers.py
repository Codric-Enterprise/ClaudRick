"""Three parsers for Rime, derived three different ways.

P1 walks the tokens recursively, P2 shifts and reduces, P3 cuts the
stream into lines first and only then looks at what is in them. The
strategies share nothing but the tree they build and the order in which
they are required to complain.

## The order of complaint, published

Three parsers that accept the same programs can still be three
different languages, because a program can be wrong in more than one
way at once and whichever fault a parser happens to notice first is the
fault it reports. `3 4 bogus` followed by `1 keep` is unknown *and*
unrhymed. Left to themselves the three would each pick a favourite and
the matrix would read that as a disagreement about Rime, which it is
not -- it is a disagreement about reading order, and reading order is
part of the language whether or not anybody writes it down.

So it is written down. Every parser here checks, in this order:

1. **Shape**, line by line in order. A line is `NUM* WORD`: any number
   of operands, then exactly one verb to end it. A line that does not
   end in a verb -- `1 2`, or `3 grow 4` -- is `voiceless`.
2. **Vocabulary**, line by line in order. The ending word must be a
   verb Rime knows, else `unknown`.
3. **Pairing**. Lines come two by two. A last line with nobody to
   answer it is `orphaned`.
4. **Rhyme**, couplet by couplet in order. The two verbs must share a
   class, else `unrhymed`.

Phases run to completion in sequence, so a shape fault anywhere beats a
rhyme fault everywhere. Within a phase the first fault in reading order
wins.

A refusal carries the position of the token that caused it. That
position is honest but it is not a claim about Rime -- see
`laws.py::verdict`, which compares stage and defect and deliberately
leaves position out.

Codric Enterprise · 2026
"""

from __future__ import annotations

from contract import WORDS, Couplet, Fail, Line, ParseOut, Poem, rhymes

# ══════════════════════════════════════════════════════════
# The four phases, as one shared statement of the rules
# ══════════════════════════════════════════════════════════
#
# Each parser below produces its own list of raw lines by its own
# means -- that is where the independence lives. What they must not do
# is each invent their own order of complaint, so the phases that turn
# raw lines into a verdict are stated once here. A parser that reached
# a different *set* of raw lines will still be caught: the phases will
# be handed different input and the matrix will split.


def _check(groups: list[list]) -> ParseOut:
    """Phases 1-4 over already-segmented lines. `groups` is a list of
    token lists, one per line, NEWLINE and EOF already removed."""
    # ── 1. shape ──
    for g in groups:
        if not g or g[-1].kind != "WORD":
            bad = g[-1] if g else None
            return ParseOut(fail=Fail("parse", "voiceless",
                                      bad.pos if bad else 0,
                                      bad.line if bad else 1))
        for t in g[:-1]:
            if t.kind != "NUM":
                return ParseOut(fail=Fail("parse", "voiceless",
                                          t.pos, t.line))

    # ── 2. vocabulary ──
    for g in groups:
        if g[-1].text not in WORDS:
            return ParseOut(fail=Fail("parse", "unknown",
                                      g[-1].pos, g[-1].line))

    lines = [Line([int(t.text) for t in g[:-1]], g[-1].text, g[-1].line)
             for g in groups]

    # ── 3. pairing ──
    if len(lines) % 2:
        last = groups[-1][-1]
        return ParseOut(fail=Fail("parse", "orphaned", last.pos, last.line))

    # ── 4. rhyme ──
    couplets = []
    for i in range(0, len(lines), 2):
        a, b = lines[i], lines[i + 1]
        if not rhymes(a.verb, b.verb):
            tok = groups[i + 1][-1]
            return ParseOut(fail=Fail("parse", "unrhymed", tok.pos, tok.line))
        couplets.append(Couplet(a, b))

    return ParseOut(ast=Poem(couplets))


# ══════════════════════════════════════════════════════════
# P1 — recursive descent
# ══════════════════════════════════════════════════════════

def parse_descent(toks) -> ParseOut:
    """A cursor and a function per level. Segmentation falls out of
    `_line` returning when it sees a boundary."""
    body = [t for t in toks if t.kind != "EOF"]
    groups: list[list] = []
    i = 0

    def _line(at: int):
        got = []
        while at < len(body) and body[at].kind != "NEWLINE":
            got.append(body[at])
            at += 1
        if at < len(body):
            at += 1                       # step over the NEWLINE
        return got, at

    while i < len(body):
        group, i = _line(i)
        if group:
            groups.append(group)

    return _check(groups)


# ══════════════════════════════════════════════════════════
# P2 — shift/reduce
# ══════════════════════════════════════════════════════════

def parse_shift(toks) -> ParseOut:
    """One pass, a buffer, and a reduction on every boundary. There is
    no recursion and no lookahead: the decision to close a line is made
    from the token in hand."""
    groups: list[list] = []
    buf: list = []

    for t in toks:
        if t.kind in ("NEWLINE", "EOF"):
            if buf:
                groups.append(buf)
                buf = []
            continue
        buf.append(t)

    if buf:                                # no EOF in the stream
        groups.append(buf)

    return _check(groups)


# ══════════════════════════════════════════════════════════
# P3 — segment first, inspect second
# ══════════════════════════════════════════════════════════

def parse_segment(toks) -> ParseOut:
    """Cut on the separators, then look. The opposite order to P1: this
    one knows how many lines there are before it knows whether any of
    them is a line at all, which is a genuinely different way to be
    wrong and therefore worth having."""
    body = [t for t in toks if t.kind != "EOF"]
    groups: list[list] = [[]]
    for t in body:
        if t.kind == "NEWLINE":
            groups.append([])
        else:
            groups[-1].append(t)
    return _check([g for g in groups if g])


PARSERS = {
    "P1-descent": parse_descent,
    "P2-shift": parse_shift,
    "P3-segment": parse_segment,
}

__all__ = ["PARSERS", "parse_descent", "parse_segment", "parse_shift"]
