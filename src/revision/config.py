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


def _env_int(name: str, default: int) -> int:
    """Read an int env var, falling back to ``default`` if unset or invalid."""
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


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
    #: Optional bearer token required on ``/api/messages`` (auth disabled if None).
    api_token: str | None = None
    #: Max ``/api/messages`` requests per client within ``rate_window`` (0 = off).
    rate_limit: int = 30
    #: Rate-limit sliding window in seconds.
    rate_window: float = 60.0
    #: Trust ``X-Forwarded-For`` for the client IP (enable only behind a proxy).
    trust_proxy: bool = False

    @classmethod
    def from_env(cls) -> "Config":
        """Build a :class:`Config` from environment variables with sane defaults."""
        return cls(
            api_key=os.environ.get("ANTHROPIC_API_KEY"),
            model=os.environ.get("REVISION_MODEL", DEFAULT_MODEL),
            host=os.environ.get("REVISION_HOST", "127.0.0.1"),
            port=_env_int("REVISION_PORT", 8000),
            api_token=os.environ.get("REVISION_API_TOKEN") or None,
            rate_limit=_env_int("REVISION_RATE_LIMIT", 30),
            rate_window=float(_env_int("REVISION_RATE_WINDOW", 60)),
            trust_proxy=_env_bool("REVISION_TRUST_PROXY", False),
        )
