"""The gate: run server.py as a real subprocess and drive its tools over stdio, like any
MCP client would -- not just import it. `pip install -e .` first (mcp, pydantic)."""

import asyncio
import sys

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

CLAMP = """To clamp given x, low and high, answering an Int:
  x is an Int, trusted 256 of 256.
  low is an Int, trusted 256 of 256.
  high is an Int, trusted 256 of 256.
  It never repeats.
  Make sure x is not void.
  Make sure low is not void.
  Make sure high is not void.
  If x is less than low:
    Answer low.
  Otherwise:
    If x is greater than high:
      Answer high.
    Otherwise:
      Answer x.
Check: clamp of 5 and 0 and 10 gives 5, trusted 120.
Check: clamp of negative 3 and 0 and 10 gives 0, trusted 120.
Check: clamp of 12 and 0 and 10 gives 10, trusted 120.
Check: clamp of 0 and 0 and 10 gives 0, trusted 120.
Check: clamp of 10 and 0 and 10 gives 10, trusted 120.
"""

BROKEN = CLAMP.replace("Answer low.", "Answer high.")


def text(result):
    return "".join(getattr(c, "text", "") for c in result.content)


async def main():
    params = StdioServerParameters(command=sys.executable, args=["server.py"])
    fails = []
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()

        tools = (await session.list_tools()).tools
        names = sorted(t.name for t in tools)
        print("tools:", names)
        if names != ["accord_build", "accord_check", "accord_run", "accord_tac"]:
            fails.append(f"unexpected tool set: {names}")
        for t in tools:
            if t.annotations is None or not t.annotations.read_only_hint:
                fails.append(f"{t.name}: missing/wrong readOnlyHint annotation")

        r = await session.call_tool("accord_check", {"params": {"program": CLAMP}})
        out = text(r)
        print("check ->", out.splitlines()[0])
        if "accepted: clamp" not in out or "245" not in out:
            fails.append(f"accord_check on a good program: {out!r}")

        r = await session.call_tool(
            "accord_run",
            {"params": {"program": CLAMP, "args": "negative 3 and 0 and 10"}},
        )
        out = text(r)
        print("run(-3,0,10) ->", out)
        if out != "0, trusted 120 of 256":
            fails.append(f"accord_run clamp(-3,0,10): {out!r}")

        r = await session.call_tool("accord_check", {"params": {"program": BROKEN}})
        out = text(r)
        print("check(broken) ->", out.splitlines()[0])
        if "refused" not in out or "checks" not in out.lower():
            fails.append(f"accord_check should refuse the broken program: {out!r}")

        r = await session.call_tool("accord_tac", {"params": {"program": CLAMP}})
        out = text(r)
        print("tac ->", out.splitlines()[0])
        if not out.startswith("# clamp") or "sha256" not in out:
            fails.append(f"accord_tac: {out!r}")

        r = await session.call_tool("accord_build", {"params": {"program": CLAMP}})
        out = text(r)
        print("build -> first line:", out.splitlines()[0])
        ok_build = "import" not in out.split("\n\n")[0] and "def clamp(" in out
        if not ok_build:
            fails.append(f"accord_build did not look like a built module: {out[:200]!r}")

        r = await session.call_tool(
            "accord_run", {"params": {"program": CLAMP, "function": "nope", "args": "1"}}
        )
        out = text(r)
        print("run(bad fn) ->", out)
        if "is not a function" not in out:
            fails.append(f"accord_run with an unknown function: {out!r}")

    if fails:
        print("FAILED:")
        for f in fails:
            print(" -", f)
        raise SystemExit(1)
    print("accord-mcp: all end-to-end MCP calls passed")


if __name__ == "__main__":
    asyncio.run(main())
