"""accord fill: you write the header, trust and Checks; Claude writes the body; Accord decides.

Headless. The program goes to stdout, progress to stderr, and the exit code says who acts next:
0 accepted, 1 Claude could not satisfy the Checks, 2 usage, 3 environment, 4 your turn.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

import parse
from core import AccordError, Report, verify

MODEL = "claude-opus-5"
ATTEMPTS = 4
YOURS = ("coverage", "floor")  # only more Checks can fix these: the person decides

CARD = """You write the body of one function in Accord, a small language.
A person wrote the header, the trust given to each input, and the Checks. You must not change
them, and you do not repeat them. Reply with only the body, indented two spaces, inside one
```accord fenced block. Your body is a claim. Accord runs the person's Checks against it and
refuses the program unless every Check holds, every decision is tried both ways, and every
comparison is tried at its edge.

The body, in order:
  It never repeats.                                  (or, if it calls itself:)
  It shrinks by n.                                   (n: an Int or List parameter that gets smaller)
  Make sure x is not void.                           (one per parameter, before it is used)
  Let limit be an Int, trusted 256 of 256, equal to 10.
  If <condition>:
    <statements, ending in an Answer or an If>
  Otherwise:
    <statements, ending in an Answer or an If>
  Answer <expression>.

Every path ends in exactly one Answer. An If must be the last statement of its block and must
have an Otherwise. A Let's trust is written "trusted N of 256".

Expressions:
  comparison   a is greater than b | is less than | is at least | is at most | is equal to
               | is not equal to
  arithmetic   a plus b | a minus b | a times b | a divided by b | negative 3
  lists        the list of 1, 2 and 3 | the empty list | the length of xs | the first of xs
               | the rest of xs | xs plus ys (joins two lists)
  calls        f of a | f of a and b     (only the function itself; parenthesize a list argument)
  literals     12 | 1.5 | "text" | true | false
  grouping     (a plus b) times c
There is no and/or/not, no remainder, no loops, and no other functions. Types: Int, Float, Text,
Bool, and List of any of them. Reserved words (never names): list, empty, length, first, rest,
trusted.

Example body, for "To fact given n, answering an Int:" with n an Int:
```accord
  It shrinks by n.
  Make sure n is not void.
  If n is at most 0:
    Answer 1.
  Otherwise:
    Answer n times fact of (n minus 1).
```"""


class FillError(Exception):
    """The environment, not the program, stopped the run: no SDK, no credentials, the API."""


@dataclass
class Intent:
    """The person's part, kept as their exact text so the AI can never rewrite it."""

    header: list[str]
    declarations: list[str]
    checks: list[str]

    @property
    def text(self) -> str:
        return "\n".join(self.header + self.declarations + self.checks) + "\n"


@dataclass
class Outcome:
    code: int
    program: str = ""
    report: Report | None = None
    attempts: int = 0
    log: list[str] = field(default_factory=list)


def intent(source: str) -> Intent:
    """Split a person's file: the header, one trust line per parameter, then the Checks."""
    lines = [ln for ln in source.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    if not lines or not lines[0].startswith("To "):
        raise AccordError(
            1, "the file must start with a header: 'To name given ..., answering ...:'"
        )
    names = _parameters(lines[0])
    indented = [ln for ln in lines[1:] if ln.startswith(" ")]
    top = [ln for ln in lines[1:] if not ln.startswith(" ")]
    if len(indented) > len(names):
        raise AccordError(1, "this file already has a body; fill writes the body")
    if len(indented) < len(names):
        raise AccordError(1, f"R1: declare the trust of every parameter: {', '.join(names)}")
    if not all(ln.startswith("Check:") for ln in top):
        raise AccordError(1, "after the declarations, only Check lines belong to you")
    return Intent([lines[0]], indented, top)


def _parameters(header: str) -> list[str]:
    match = re.match(r"To \S+ given (.+), answering ", header)
    if not match:
        return []
    return [n for n in re.split(r",\s*|\s+and\s+", match.group(1)) if n]


def body_of(reply: str) -> list[str]:
    """The body lines from a reply, re-indented under the header. Rejects header or Check lines."""
    fenced = re.search(r"```(?:accord)?\n(.*?)```", reply, re.S)
    text = fenced.group(1) if fenced else reply
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        raise AccordError(1, "the reply had no body")
    for ln in lines:
        word = ln.lstrip()
        if word.startswith(("Check:", "To ")):
            raise AccordError(
                1, "the body may not change the header or the Checks; write the body only"
            )
    shift = min(len(ln) - len(ln.lstrip()) for ln in lines)
    return ["  " + ln[shift:] for ln in lines]


def assemble(person: Intent, body: list[str]) -> str:
    return "\n".join(person.header + person.declarations + body + person.checks) + "\n"


def prompt(person: Intent) -> str:
    return f"Write the body for this program.\n\n```accord\n{person.text}```"


def fill(source: str, ask: Callable, attempts: int = ATTEMPTS, explain=None) -> Outcome:
    """The loop. `ask(system, messages) -> (text, content)` is all that talks to a model."""
    if explain is None:
        from accord import explain
    person = intent(source)
    messages: list = [{"role": "user", "content": prompt(person)}]
    outcome = Outcome(code=1)
    for n in range(1, attempts + 1):
        outcome.attempts = n
        text, content = ask(CARD, messages)
        messages.append({"role": "assistant", "content": content})
        try:
            program = assemble(person, body_of(text))
            report = verify(parse.parse(program))
        except AccordError as err:
            verdict = f"refused: {err}"
            outcome.log.append(f"attempt {n}: {verdict}")
            messages.append({"role": "user", "content": _again(verdict)})
            continue
        outcome.program, outcome.report = program, report
        verdict = explain(report)
        outcome.log.append(f"attempt {n}: {verdict.splitlines()[0]}")
        if report.accepted:
            outcome.code = 0
            return outcome
        if report.stage in YOURS:
            outcome.code = 4
            outcome.log.append("your turn: " + verdict)
            return outcome
        messages.append({"role": "user", "content": _again(verdict)})
    return outcome


def _again(verdict: str) -> str:
    return f"Accord refused that body:\n\n{verdict}\n\nWrite the whole body again."


# ── the one place that talks to Claude ───────────────────────────────────────


def request(model: str, fast: bool, system: str, messages: list) -> dict:
    """The request, built without the network so it can be tested."""
    kwargs = {
        "model": model,
        "max_tokens": 16000,
        "system": system,
        "messages": messages,
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": "high"},
        "betas": ["server-side-fallback-2026-07-01"],
        "fallbacks": "default",
    }
    if fast:
        kwargs["speed"] = "fast"
        kwargs["betas"] = [*kwargs["betas"], "fast-mode-2026-02-01"]
    return kwargs


def claude(model: str = MODEL, fast: bool = False) -> Callable:
    try:
        import anthropic
    except ImportError as err:
        raise FillError("fill needs the Anthropic SDK: pip install anthropic") from err
    client = anthropic.Anthropic()

    def ask(system: str, messages: list):
        kwargs = request(model, fast, system, messages)
        try:
            response = client.beta.messages.create(**kwargs)
        except anthropic.RateLimitError:
            if not fast:
                raise
            kwargs = request(model, False, system, messages)  # fast mode has its own limit
            response = client.beta.messages.create(**kwargs)
        except anthropic.AuthenticationError as err:
            raise FillError(
                "no credentials: set ANTHROPIC_API_KEY or run `ant auth login`"
            ) from err
        except anthropic.APIStatusError as err:
            raise FillError(
                f"the API refused the request ({err.status_code}): {err.message}"
            ) from err
        except anthropic.APIConnectionError as err:
            raise FillError("could not reach the API") from err
        except TypeError as err:  # the SDK raises this before sending when no credential resolves
            if "authentication" not in str(err):
                raise
            raise FillError(
                "no credentials: set ANTHROPIC_API_KEY or run `ant auth login`"
            ) from err
        if response.stop_reason == "refusal":
            raise FillError("Claude declined to write this body")
        text = "".join(b.text for b in response.content if b.type == "text")
        return text, response.content

    return ask
