"""Three scanners for Rime, written three different ways.

They exist to disagree. Rime makes the line break significant -- a
couplet is two *lines* -- and "where exactly does a newline stop being
whitespace" is the question independently written scanners answer
differently without noticing, because each one's answer looks obviously
correct from inside. One scanner cannot be evidence about that; three
derived from different mechanisms can.

The rule they are all held to, stated once so none of them gets to
decide it privately:

* Spaces, tabs and carriage returns separate tokens and are otherwise
  nothing.
* A maximal run of line feeds -- blanks and tabs in between do not
  break the run -- yields exactly one NEWLINE, placed at the first line
  feed of the run. So a blank line between couplets is cosmetic, which
  is what lets `unparse` put one there for legibility.
* A run at the very start of the text, or the very end, yields nothing.
  A poem does not begin or end with silence.
* NUM is an optional minus and then digits. WORD is lower-case letters.
* Any other character is refused, at its own position, as `unknown`.

A word that is spelled legally but is not in the vocabulary is *not* a
scanning error. It is a WORD token, and `parsers.py` refuses it. The
scanner's job is shapes, not meaning.

Codric Enterprise · 2026
"""

from __future__ import annotations

import re

from contract import Fail, LexOut, Tok

_DIGITS = "0123456789"
_LOWER = "abcdefghijklmnopqrstuvwxyz"
_INLINE = " \t\r"


def _finish(toks: list[Tok]) -> LexOut:
    """Drop a trailing NEWLINE and cap with EOF.

    Shared because it is bookkeeping, not scanning. If the three
    scanners disagreed about whether to emit a final EOF that would be
    a fact about this function, not about Rime, and the matrix would
    report a split that means nothing.
    """
    while toks and toks[-1].kind == "NEWLINE":
        toks.pop()
    end = toks[-1].pos + len(toks[-1].text) if toks else 0
    line = toks[-1].line if toks else 1
    toks.append(Tok("EOF", "", end, line))
    return LexOut(toks)


# ══════════════════════════════════════════════════════════
# L1 — one master regex
# ══════════════════════════════════════════════════════════

_MASTER = re.compile(
    r"""(?P<BREAK>  [ \t\r]* \n (?: [ \t\r]* \n )* )
      | (?P<SPACE>  [ \t\r]+ )
      | (?P<NUM>    -?[0-9]+ )
      | (?P<WORD>   [a-z]+ )
    """,
    re.VERBOSE,
)


def lex_regex(src: str) -> LexOut:
    """Alternation, in order. The break rule is expressed as a pattern,
    so the "maximal run" part is the regex engine's greediness rather
    than a loop somebody has to remember to write."""
    toks: list[Tok] = []
    i, line = 0, 1
    while i < len(src):
        m = _MASTER.match(src, i)
        if not m:
            return LexOut(toks, Fail("lex", "unknown", i, line))
        kind = m.lastgroup
        text = m.group()
        if kind == "BREAK":
            at = i + text.index("\n")
            if toks:
                toks.append(Tok("NEWLINE", "\n", at, line))
            line += text.count("\n")
        elif kind != "SPACE":
            toks.append(Tok(kind, text, i, line))
        i = m.end()
    return _finish(toks)


# ══════════════════════════════════════════════════════════
# L2 — a hand-rolled character walk
# ══════════════════════════════════════════════════════════

def lex_hand(src: str) -> LexOut:
    """No regex anywhere. Each token kind is a loop that knows how to
    stop, which is the most direct statement of the rule and the one
    easiest to check against the prose above by eye."""
    toks: list[Tok] = []
    i, line, n = 0, 1, len(src)

    while i < n:
        ch = src[i]

        if ch in _INLINE:
            i += 1
            continue

        if ch == "\n":
            at = i
            started = line
            while i < n and (src[i] == "\n" or src[i] in _INLINE):
                if src[i] == "\n":
                    line += 1
                i += 1
            if toks:
                toks.append(Tok("NEWLINE", "\n", at, started))
            continue

        if ch in _DIGITS or (ch == "-" and i + 1 < n and src[i + 1] in _DIGITS):
            start = i
            i += 1
            while i < n and src[i] in _DIGITS:
                i += 1
            toks.append(Tok("NUM", src[start:i], start, line))
            continue

        if ch in _LOWER:
            start = i
            while i < n and src[i] in _LOWER:
                i += 1
            toks.append(Tok("WORD", src[start:i], start, line))
            continue

        return LexOut(toks, Fail("lex", "unknown", i, line))

    return _finish(toks)


# ══════════════════════════════════════════════════════════
# L3 — a table-driven machine
# ══════════════════════════════════════════════════════════

def _class_of(ch: str) -> str:
    if ch == "\n":
        return "nl"
    if ch in _INLINE:
        return "sp"
    if ch in _DIGITS:
        return "dig"
    if ch == "-":
        return "dash"
    if ch in _LOWER:
        return "low"
    return "bad"


#: state x character-class -> (next state, emit?)
_TABLE: dict[tuple[str, str], tuple[str, bool]] = {
    ("start", "sp"):   ("start", False),
    ("start", "nl"):   ("break", False),
    ("start", "dig"):  ("num", False),
    ("start", "dash"): ("dash", False),
    ("start", "low"):  ("word", False),
    ("break", "nl"):   ("break", False),
    ("break", "sp"):   ("break", False),
    ("num", "dig"):    ("num", False),
    ("word", "low"):   ("word", False),
    ("dash", "dig"):   ("num", False),
}


def lex_table(src: str) -> LexOut:
    """The same language as a transition table. Where L1 and L2 carry
    the rule in control flow, here it is data: the run-collapsing is the
    `break -> break` self-loop and nothing else."""
    toks: list[Tok] = []
    state, start, line, start_line = "start", 0, 1, 1
    i, n = 0, len(src)

    def emit(kind: str, upto: int) -> None:
        toks.append(Tok(kind, src[start:upto], start, start_line))

    while i <= n:
        cls = _class_of(src[i]) if i < n else "end"
        step = _TABLE.get((state, cls))

        if step is not None:
            if state == "start":
                start, start_line = i, line
            state = step[0]
            if cls == "nl":
                line += 1
            i += 1
            continue

        # No transition: the current token, if any, ends here.
        if state == "num":
            emit("NUM", i)
        elif state == "word":
            emit("WORD", i)
        elif state == "dash":
            return LexOut(toks, Fail("lex", "unknown", start, start_line))
        elif state == "break":
            if toks:
                toks.append(Tok("NEWLINE", "\n", start, start_line))

        if cls == "end":
            break
        if cls == "bad":
            return LexOut(toks, Fail("lex", "unknown", i, line))
        state = "start"

    return _finish(toks)


LEXERS = {
    "L1-regex": lex_regex,
    "L2-hand": lex_hand,
    "L3-table": lex_table,
}

__all__ = ["LEXERS", "lex_hand", "lex_regex", "lex_table"]
