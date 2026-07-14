"""Command-line interface for ClaudRick."""

import argparse
from collections.abc import Sequence

from claudrick import __version__
from claudrick.core import greet


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ``claudrick`` console script."""
    parser = argparse.ArgumentParser(prog="claudrick", description="ClaudRick CLI.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("name", nargs="?", default="world", help="who to greet")
    args = parser.parse_args(argv)

    print(greet(args.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
