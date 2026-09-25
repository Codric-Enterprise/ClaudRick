"""accord fill: you write the header, trust and Checks; Claude writes the body; Accord decides.

Headless. The program goes to stdout, progress to stderr, and the exit code says who acts next:
0 accepted, 1 Claude could not satisfy the Checks, 2 usage, 3 environment, 4 your turn.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

import parse
from core import AccordError, ProgramReport, verify_program

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
  calls        f of a | f of a and b     (this or another function; parenthesize a list argument)
  literals     12 | 1.5 | "text" | true | false
  grouping     (a plus b) times c
There is no and/or/not, no remainder and no loops. A program may have several functions: call
another by name, as "total of xs", but no functions may call each other in a cycle.
Types: Int, Float, Text, Bool, and List of any of them.
Reserved words (never names): list, empty, length, first, rest, trusted.

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
    """One function's part, kept as the person's exact text so the AI can never rewrite it."""

    header: list[str]
    declarations: list[str]
    checks: list[str]

    @property
    def name(self) -> str:
        return self.header[0].split()[1]

    @property
    def text(self) -> str:
        return "\n".join(self.header + self.declarations + self.checks) + "\n"


@dataclass
class Outcome:
    code: int
    program: str = ""
    report: ProgramReport | None = None
    attempts: int = 0
    log: list[str] = field(default_factory=list)


def intents(source: str) -> list[Intent]:
    """Every function's part: its header, one trust line per parameter, then its Checks."""
    lines = [ln for ln in source.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    if not lines or not lines[0].startswith("To "):
        raise AccordError(
            1, "the file must start with a header: 'To name given ..., answering ...:'"
        )
    groups: list[list[str]] = []
    for ln in lines:
        if ln.startswith("To "):
            groups.append([])
        groups[-1].append(ln)
    parts = [_intent(group) for group in groups]
    names = [p.name for p in parts]
    for n in sorted({n for n in names if names.count(n) > 1}):
        raise AccordError(1, f"R3: two functions are named {n}")
    return parts


def intent(source: str) -> Intent:
    parts = intents(source)
    if len(parts) != 1:
        raise AccordError(1, f"expected one function, found {len(parts)}: use intents()")
    return parts[0]


def _intent(lines: list[str]) -> Intent:
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


FENCE = re.compile(r"```accord(?:[ \t]+(\w+))?[ \t]*\n(.*?)```", re.S)


def body_of(reply: str) -> list[str]:
    """The body lines from a reply, re-indented under the header. Rejects header or Check lines."""
    fenced = re.search(r"```(?:accord)?(?:[ \t]+\w+)?[ \t]*\n(.*?)```", reply, re.S)
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


def bodies(reply: str, names: list[str]) -> dict[str, list[str]]:
    """One body per function. With one function, an unlabelled reply is that function's body."""
    if len(names) == 1:
        return {names[0]: body_of(reply)}
    found: dict[str, list[str]] = {}
    for label, text in FENCE.findall(reply):
        if not label:
            raise AccordError(1, "label each body with its function: ```accord NAME")
        if label not in names:
            raise AccordError(1, f"there is no function named {label}")
        if label in found:
            raise AccordError(1, f"two bodies for {label}")
        found[label] = body_of(text)
    missing = [n for n in names if n not in found]
    if missing:
        raise AccordError(1, f"no body for {', '.join(missing)}")
    return found


def assemble(parts: list[Intent] | Intent, body) -> str:
    if isinstance(parts, Intent):
        parts, body = [parts], {parts.name: body}
    return "".join(
        "\n".join(p.header + p.declarations + body[p.name] + p.checks) + "\n" for p in parts
    )


def prompt(parts: list[Intent]) -> str:
    text = "".join(p.text for p in parts)
    if len(parts) == 1:
        return f"Write the body for this program.\n\n```accord\n{text}```"
    names = ", ".join(p.name for p in parts)
    return (
        f"Write the body of each function: {names}. Reply with one fenced block per function,"
        f" labelled with its name, like ```accord {parts[0].name}.\n\n```accord\n{text}```"
    )


def fill(source: str, ask: Callable, attempts: int = ATTEMPTS, explain=None) -> Outcome:
    """The loop. `ask(system, messages) -> (text, content)` is all that talks to a model."""
    if explain is None:
        from accord import explain_program as explain
    parts = intents(source)
    names = [p.name for p in parts]
    messages: list = [{"role": "user", "content": prompt(parts)}]
    outcome = Outcome(code=1)
    for n in range(1, attempts + 1):
        outcome.attempts = n
        text, content = ask(CARD, messages)
        messages.append({"role": "assistant", "content": content})
        try:
            program = assemble(parts, bodies(text, names))
            report = verify_program(parse.program(program))
        except AccordError as err:
            verdict = f"refused: {err}"
            outcome.log.append(f"attempt {n}: {verdict}")
            messages.append({"role": "user", "content": _again(verdict, len(parts))})
            continue
        outcome.program, outcome.report = program, report
        verdict = explain(report)
        outcome.log.append(f"attempt {n}: {verdict.splitlines()[0]}")
        if report.accepted:
            outcome.code = 0
            return outcome
        stages = [
            r.stage for r in report.reports.values() if r.stage not in ("accepted", "depends")
        ]
        if not report.errors and stages and all(s in YOURS for s in stages):
            outcome.code = 4
            outcome.log.append("your turn: " + verdict)
            return outcome
        messages.append({"role": "user", "content": _again(verdict, len(parts))})
    return outcome


def _again(verdict: str, functions: int) -> str:
    ask = "Write the whole body again." if functions == 1 else "Write every body again."
    return f"Accord refused that:\n\n{verdict}\n\n{ask}"


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
