#!/usr/bin/env python3
"""accord_mcp: MCP tools over Accord (../accord) -- check, run, tac and build a program.

Every tool is pure and offline: it parses and verifies Accord source handed to it in full,
using accord/'s own parse.py, core.py, build.py and accord.py (never reimplemented here, so
this can't drift from what `python3 accord.py` actually does). Nothing here touches the
network. `fill` -- the one part of Accord that calls the Anthropic API and costs money -- is
deliberately not exposed as a tool; see README.md.

Run directly for stdio (the default, for a local client like Claude Desktop):
    python3 server.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# accord/ is a sibling directory kept dependency-free on purpose (see accord/README.md): its
# modules use plain names (parse, core, build) meant for `cd accord && python3 accord.py`, not
# for installation as top-level packages. Adding it to sys.path keeps that true -- this process
# alone resolves `import parse`/`import core`/etc. to accord/'s files, and nothing is installed.
ACCORD_DIR = Path(__file__).resolve().parent.parent / "accord"
sys.path.insert(0, str(ACCORD_DIR))

import accord as accord_cli  # noqa: E402  accord.py: explain_program (doesn't import anthropic)
import build  # noqa: E402  accord/build.py
import parse  # noqa: E402  accord/parse.py
from core import AccordError, apply_program, format_tac, tac_hash, verify_program  # noqa: E402
from mcp.server.mcpserver import MCPServer  # noqa: E402
from mcp.types import ToolAnnotations  # noqa: E402
from pydantic import BaseModel, ConfigDict, Field  # noqa: E402

mcp = MCPServer("accord_mcp")


# Every tool here only parses, verifies, runs or compiles the source it is handed -- it changes
# nothing outside the call, is safe to call repeatedly, and never reaches the network.
def _annotations(title: str) -> ToolAnnotations:
    return ToolAnnotations(
        title=title,
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )


PROGRAM_DESCRIPTION = (
    "Complete Accord source: one or more functions, each starting at a 'To name given ..., "
    "answering a Type:' header in column 0, its body indented two spaces under it, and its "
    "'Check:' lines back at column 0. See accord/LANGUAGE.md for the full syntax."
)


class ProgramInput(BaseModel):
    """Accord source text, verbatim -- the same text `python3 accord.py check FILE` reads."""

    model_config = ConfigDict(extra="forbid")

    program: str = Field(..., description=PROGRAM_DESCRIPTION, min_length=1)


class RunInput(ProgramInput):
    """A program to verify, plus which function to run it as and what to run it on."""

    function: str | None = Field(
        default=None,
        description="Which function to run, by name. Defaults to the last one in the program.",
    )
    args: str = Field(
        default="",
        description=(
            "The arguments, written in Accord, e.g. '200', 'negative 3', or "
            "'the list of 1, 2 and 3'. Separate more than one with ', ' or ' and '."
        ),
    )


def _parse(program: str):
    """accord/parse.py's own program(), with its refusal turned into tool output, not a crash."""
    try:
        return parse.program(program), None
    except AccordError as err:
        return None, f"refused: {err}"


@mcp.tool(
    name="accord_check",
    annotations=_annotations("Check an Accord program"),
)
def accord_check(params: ProgramInput) -> str:
    """Verify an Accord program and report its verdict, exactly as `accord.py check` would.

    Runs the full pipeline (parse -> R1-R5 -> Checks -> coverage/R6 -> the 128 trust floor)
    and returns the verdict in Accord's own words: which stage refused it and why, or that it
    is accepted and at what trust. Never runs the program's answers; use accord_run for that.

    Args:
        params (ProgramInput): params.program is the Accord source (one or more functions).

    Returns:
        str: "accepted: <name>\\n  <N> Checks hold, so its answers are trusted at most <T> of
        256\\n  ..." for one accepted function; "accepted: all <N> functions" or "refused: <k>
        of <N> functions" plus one line per function for several; otherwise "refused: ..."
        naming the stage (check/checks/coverage/floor) and quoting the offending Check or
        decision back in Accord.

    Examples:
        - Use when: "does this Accord program type-check and hold?" -> params.program is the
          whole file's text.
        - Don't use when: you want the program's answer for specific inputs -> use accord_run.
    """
    functions, error = _parse(params.program)
    if error:
        return error
    report = verify_program(functions)
    return accord_cli.explain_program(report)


@mcp.tool(
    name="accord_run",
    annotations=_annotations("Run an accepted Accord function"),
)
def accord_run(params: RunInput) -> str:
    """Verify an Accord program, then run one of its functions on the given arguments.

    Refuses to run anything the checker, Checks, coverage or trust floor would refuse --
    exactly the verdict accord_check would give -- rather than executing an unverified body.

    Args:
        params (RunInput): params.program is the Accord source; params.function selects which
            function to run (default: the program's last function); params.args is the
            argument list, written in Accord (e.g. "negative 3 and 0 and 10").

    Returns:
        str: "<value>, trusted <T> of 256" on success (value rendered in Accord's own
        notation, e.g. "true", "6", "the list of 1 and 2"); "refused: <name> is not a function
        of this program" if params.function names nothing in the program; the program's full
        refusal verdict (as accord_check) if it was not accepted; "refused: the arguments:
        <message>" if params.args does not parse; "refused: <reason>" if the run itself
        answers void (misbound/unbound/unbounded, per accord/SEMANTICS.md).

    Examples:
        - Use when: "what does clamp give for -3, 0, 10?" -> params.args = "negative 3 and 0
          and 10".
        - Don't use when: you only want to know if the program holds -> use accord_check.
    """
    functions, error = _parse(params.program)
    if error:
        return error
    report = verify_program(functions)
    name = params.function or functions[-1].name
    target = report.reports.get(name)
    if target is None:
        return f"refused: {name} is not a function of this program"
    if not target.accepted:
        return accord_cli.explain_program(report)
    try:
        args = parse.values(params.args)
    except AccordError as err:
        return f"refused: the arguments: {err.message}"
    got = apply_program(report, name, args)
    if got.void:
        return f"refused: {got.reason}"
    return f"{parse.render_value(got.value)}, trusted {got.trust} of 256"


@mcp.tool(
    name="accord_tac",
    annotations=_annotations("Show an Accord program's compiled TAC"),
)
def accord_tac(params: ProgramInput) -> str:
    """Show the three-address code Accord lowers an accepted program's functions to.

    Args:
        params (ProgramInput): params.program is the Accord source.

    Returns:
        str: for each accepted function, "# <name>\\n<one TAC instruction per line>\\n#
        sha256 <hash>", functions separated by a blank line; the program's refusal verdict
        (as accord_check) if nothing in it was accepted.
    """
    functions, error = _parse(params.program)
    if error:
        return error
    report = verify_program(functions)
    lowered = [(n, r.tac) for n, r in report.reports.items() if r.tac]
    if not lowered:
        return accord_cli.explain_program(report)
    return "\n\n".join(f"# {n}\n{format_tac(tac)}\n# sha256 {tac_hash(tac)}" for n, tac in lowered)


@mcp.tool(
    name="accord_build",
    annotations=_annotations("Compile an Accord program to standalone Python"),
)
def accord_build(params: ProgramInput) -> str:
    """Compile an accepted Accord program into one standalone Python module's source.

    The module imports nothing from Accord: its semantics are core.py's own functions, copied
    in by source. Every Check is re-run through it at trust 120 and at 256 and must match the
    interpreter's value, trust and reason exactly, or nothing is returned (see accord/SEMANTICS.md
    S8). This can take a few seconds for a program with several functions.

    Args:
        params (ProgramInput): params.program is the Accord source; it must be accepted (see
            accord_check) or nothing is built.

    Returns:
        str: the built module's full Python source on success; the program's refusal verdict
        (as accord_check) if it was not accepted; "refused: the built module disagrees with
        Accord: ..." in the (should-be-impossible) case that self-verification fails.
    """
    functions, error = _parse(params.program)
    if error:
        return error
    report = verify_program(functions)
    if not report.accepted:
        return accord_cli.explain_program(report)
    try:
        return build.build(report)
    except build.BuildError as err:
        return f"refused: {err}"


if __name__ == "__main__":
    mcp.run()
