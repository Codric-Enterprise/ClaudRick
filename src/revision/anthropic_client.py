"""Thin server-side client for the Anthropic Messages API.

Uses only the standard library (``urllib``) so ReVision has no runtime
dependencies. The API key is injected here, server-side, and never exposed to
the browser.
"""

import json
import ssl
import urllib.error
import urllib.request

from revision.config import ANTHROPIC_API_URL, ANTHROPIC_VERSION


class AnthropicError(Exception):
    """Raised when the Anthropic API returns an error or cannot be reached."""


class AnthropicClient:
    """Minimal client that sends a single-user-message request to Claude."""

    def __init__(
        self,
        api_key: str | None,
        model: str,
        *,
        api_url: str = ANTHROPIC_API_URL,
        timeout: float = 60.0,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.api_url = api_url
        self.timeout = timeout

    def create_message(self, prompt: str, max_tokens: int = 3000) -> dict:
        """Send ``prompt`` to Claude and return the parsed Anthropic response.

        Raises :class:`AnthropicError` if the key is missing, the API returns a
        non-2xx status, or the endpoint is unreachable.
        """
        if not self.api_key:
            raise AnthropicError(
                "ANTHROPIC_API_KEY is not set on the server. "
                "Set it in the environment before starting ReVision."
            )

        payload = json.dumps(
            {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            }
        ).encode("utf-8")

        request = urllib.request.Request(
            self.api_url,
            data=payload,
            method="POST",
            headers={
                "content-type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": ANTHROPIC_VERSION,
            },
        )

        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout, context=ssl.create_default_context()
            ) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise AnthropicError(
                f"Anthropic API error ({exc.code}): {_extract_error(exc)}"
            ) from exc
        except urllib.error.URLError as exc:
            raise AnthropicError(f"Could not reach the Anthropic API: {exc.reason}") from exc


def _extract_error(exc: urllib.error.HTTPError) -> str:
    """Pull a human-readable message out of an Anthropic error response."""
    body = exc.read().decode("utf-8", errors="replace")
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return body or exc.reason
    error = data.get("error")
    if isinstance(error, dict):
        return error.get("message", body)
    return str(error or body)
