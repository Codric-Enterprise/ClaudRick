"""The Rime machine: a stack, a store, and a voice.

Evaluation is total. Nothing here raises -- a program that cannot be
run is *refused*, and a refusal is an ordinary value carrying a defect
and a place, exactly like a scanning or parsing refusal. That is worth
insisting on because the alternative is a language whose totality is a
property of whoever remembered to write a try block.

Two decisions follow from it and are worth stating plainly, since both
are places another language would have thrown:

* **Division and modulo by zero give zero.** Arithmetic in Rime is
  total. The alternative is a fifth defect class that exists only to
  describe one arithmetic edge, and a verb whose result type depends on
  its operand's value.
* **Reading a cell that was never written gives zero.** The store is a
  function from addresses to numbers, defined everywhere. `peep` cannot
  fail, so no couplet has to be written defensively around it.

The one thing the machine does refuse is running a verb with less
beneath it than the verb takes: `starved`. That is not an arithmetic
edge, it is a program that does not mean anything.

## Starving is decidable before the program runs

Every verb has a fixed arity and a fixed number of results, so the
depth of the stack at every point in a poem is known from the text
alone. `depth_of` computes it, and `rhyme.py` uses it to write poems
that cannot starve. The machine still checks at run time -- a poem can
arrive from somewhere other than the generator -- but the check is a
backstop for hand-written poems, not the primary guarantee.

Codric Enterprise · 2026
"""

from __future__ import annotations

from dataclasses import dataclass, field

from contract import WORDS, Fail, Poem


@dataclass
class RunOut:
    said: list[str] = field(default_factory=list)
    stack: list[int] = field(default_factory=list)
    store: dict[int, int] = field(default_factory=dict)
    fail: Fail | None = None

    @property
    def ok(self) -> bool:
        return self.fail is None

    def canon(self) -> str:
        if self.fail:
            return self.fail.canon()
        return f"said[{'|'.join(self.said)}] stack{self.stack}"


def depth_of(poem: Poem) -> int | None:
    """The stack depth after the poem, or None if it would starve.

    Pure bookkeeping over the published arities -- it never looks at a
    number in the program, which is why it can be trusted before
    anything runs.
    """
    depth = 0
    for ln in poem.lines():
        depth += len(ln.operands)
        v = WORDS[ln.verb]
        if depth < v.arity:
            return None
        depth = depth - v.arity + v.gives
    return depth


def run(poem: Poem, *, say_limit: int = 10_000) -> RunOut:
    """Evaluate a poem, line by line, in reading order."""
    out = RunOut()
    stack: list[int] = out.stack
    store: dict[int, int] = out.store

    def say(text: str) -> None:
        if len(out.said) < say_limit:
            out.said.append(text)

    for ln in poem.lines():
        stack.extend(ln.operands)
        v = WORDS[ln.verb]
        if len(stack) < v.arity:
            out.fail = Fail("run", "starved", 0, ln.line_no)
            return out

        w = ln.verb
        if w == "grow":
            b, a = stack.pop(), stack.pop()
            stack.append(a + b)
        elif w == "slow":
            b, a = stack.pop(), stack.pop()
            stack.append(a - b)
        elif w == "throw":
            stack.append(-stack.pop())
        elif w == "mow":
            b, a = stack.pop(), stack.pop()
            stack.append(0 if b == 0 else a % b)
        elif w == "twine":
            b, a = stack.pop(), stack.pop()
            stack.append(a * b)
        elif w == "divine":
            b, a = stack.pop(), stack.pop()
            stack.append(0 if b == 0 else int(a / b))
        elif w == "align":
            stack.append(stack[-1])
        elif w == "combine":
            stack[-1], stack[-2] = stack[-2], stack[-1]
        elif w == "keep":
            a, val = stack.pop(), stack.pop()
            store[a] = val
        elif w == "peep":
            stack.append(store.get(stack.pop(), 0))
        elif w == "heap":
            stack.append(len(stack))
        elif w == "sweep":
            store.pop(stack.pop(), None)
        elif w == "light":
            say(str(stack.pop()))
        elif w == "sight":
            say(str(stack[-1]))
        elif w == "write":
            a = stack.pop()
            say(chr(a) if 0 <= a < 0x110000 else "?")
        elif w == "cite":
            say("[" + " ".join(str(x) for x in stack) + "]")

    return out


__all__ = ["RunOut", "depth_of", "run"]
