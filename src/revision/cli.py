"""Command-line interface for ReVision — starts the web server."""

import argparse
from collections.abc import Sequence

from revision import __version__
from revision.config import Config
from revision.server import serve


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ``revision`` console script."""
    parser = argparse.ArgumentParser(
        prog="revision",
        description="Start the ReVision document-toolkit web server.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--host", default=None, help="host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=None, help="port to bind (default: 8000)")
    parser.add_argument("--model", default=None, help="Claude model id to use")
    args = parser.parse_args(argv)

    config = Config.from_env()
    if args.host:
        config.host = args.host
    if args.port:
        config.port = args.port
    if args.model:
        config.model = args.model

    serve(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
