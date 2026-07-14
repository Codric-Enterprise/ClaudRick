"""Runtime configuration for the ReVision server.

All values can be overridden with environment variables so the same code runs
locally and in production without changes.
"""

import os
from dataclasses import dataclass

#: Default Claude model. Override with ``REVISION_MODEL``.
DEFAULT_MODEL = "claude-sonnet-5"

#: Anthropic Messages API endpoint the server proxies to.
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

#: Anthropic API version header value.
ANTHROPIC_VERSION = "2023-06-01"


@dataclass
class Config:
    """Server configuration resolved from the environment.

    The API key lives here (and only server-side) so it is never shipped to the
    browser.
    """

    api_key: str | None
    model: str
    host: str
    port: int

    @classmethod
    def from_env(cls) -> "Config":
        """Build a :class:`Config` from environment variables with sane defaults."""
        return cls(
            api_key=os.environ.get("ANTHROPIC_API_KEY"),
            model=os.environ.get("REVISION_MODEL", DEFAULT_MODEL),
            host=os.environ.get("REVISION_HOST", "127.0.0.1"),
            port=int(os.environ.get("REVISION_PORT", "8000")),
        )
