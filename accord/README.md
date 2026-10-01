# Accord

One language for a person and an AI to write one program together. See
`LANGUAGE.md` for what it is and `SEMANTICS.md` for exactly what it means.

## Using it on its own

This directory is not tied to the rest of its repository, and needs
nothing installed:

```
cp -r accord /somewhere/else   # or: git clone --filter=blob:none --sparse ... ; sparse-checkout set accord
cd /somewhere/else
python3 accord.py check examples/classify.accord
python3 finish.py               # the full gate, standalone: verified to pass with nothing else present
```

Every module (`parse.py`, `core.py`, `build.py`, `fill.py`, `accord.py`)
imports only the Python standard library and its siblings in this
directory — never anything from the rest of the repository it may have
shipped in. `ruff.toml` carries its own lint settings for the same
reason: `finish.py`'s lint step works whether or not a `pyproject.toml`
exists above this directory. `fill.py` additionally needs the
`anthropic` package and a credential (`ANTHROPIC_API_KEY` or
`ant auth login`) — only if you use `fill`; nothing else in Accord
touches the network.

The comments and `SEMANTICS.md` credit `ezr/SEMANTICS.md` and
`ezr/CORE.md` as the source of several rules (literal trust, the chain
rule, list semantics, and more). That is a citation, not a dependency:
nothing here imports, reads, or requires `ezr/` to exist.
