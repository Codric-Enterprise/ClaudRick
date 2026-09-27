# accord-mcp

An MCP server exposing [Accord](../accord/) — check, run, inspect the TAC of, and build an
Accord program — to any MCP client (Claude Desktop, Claude Code, or your own).

## Tools

| Tool | Does |
|---|---|
| `accord_check` | Verify a program; report accepted/refused and why, in Accord's own words |
| `accord_run` | Verify a program, then run one of its functions on given arguments |
| `accord_tac` | Show the three-address code an accepted program lowers to, and its hash |
| `accord_build` | Compile an accepted program to a standalone Python module's source |

All four are read-only, deterministic and offline: each takes the program's full source text
as input and never touches the network. They call `accord/`'s own `parse.py`, `core.py`,
`build.py` and `accord.py` directly — nothing here reimplements Accord's semantics, so this
can't drift from what `python3 accord.py` does on the command line.

**`fill` is not exposed.** It is the one part of Accord that calls the Anthropic API, needs a
credential, and costs money per call — none of which belongs behind an MCP tool a client can
invoke without warning. Use `python3 accord.py fill` directly for that.

## Running it

```
pip install -e .          # installs mcp + pydantic; accord/ itself needs neither
python3 server.py         # stdio transport, for a local client
```

To register it with Claude Desktop (or another stdio MCP client), point its config at this
`server.py` with `python3` (or this environment's interpreter) as the command, e.g.:

```json
{
  "mcpServers": {
    "accord": { "command": "python3", "args": ["/path/to/accord-mcp/server.py"] }
  }
}
```

## Verifying it

```
python3 test_server.py    # the gate: runs server.py as a real subprocess over stdio
```

This is a genuine end-to-end check, not an import test: it starts the server, lists its
tools, and calls each one, asserting on a correct program, a program broken so its Checks
fail, an unknown function name, and the built module's shape.
