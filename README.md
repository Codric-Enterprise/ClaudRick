# ClaudRick

A Python project using a modern `src/` layout.

## Requirements

- Python >= 3.11

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

```bash
claudrick           # -> Hello, world!
claudrick Rick      # -> Hello, Rick!
```

Or run without installing:

```bash
python -m claudrick.cli Rick
```

## Development

```bash
pytest              # run tests
ruff check .        # lint
ruff format .       # format
```

## Project layout

```
.
├── src/claudrick/     # package source
│   ├── __init__.py
│   ├── cli.py         # console entry point (claudrick)
│   └── core.py        # library code
├── tests/             # pytest suite
└── pyproject.toml     # build config, deps, tool settings
```
