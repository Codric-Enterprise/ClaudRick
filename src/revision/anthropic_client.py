"""Thin server-side client for the Anthropic Messages API.

Uses only the standard library (``urllib``) so ReVision has no runtime
dependencies. The API key is injected here, server-side, and never exposed to
the browser.
"""

import json
import ssl
import urllib.error
import urllib.request
from collections.abc import Iterator

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

    def stream_message(self, prompt: str, max_tokens: int = 3000) -> Iterator[str]:
        """Stream ``prompt`` to Claude, yielding text deltas as they arrive.

        Sends the request with ``"stream": true`` and parses the SSE response
        line by line, yielding the text of each ``content_block_delta`` event.

        Raises :class:`AnthropicError` if the key is missing, the request is
        rejected, the endpoint is unreachable, or an ``error`` event arrives
        mid-stream. This is a generator: connection errors surface on the
        first ``next()``, so callers should pull the first chunk before
        committing to a streaming response.
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
                "stream": True,
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
            response = urllib.request.urlopen(
                request, timeout=self.timeout, context=ssl.create_default_context()
            )
        except urllib.error.HTTPError as exc:
            raise AnthropicError(
                f"Anthropic API error ({exc.code}): {_extract_error(exc)}"
            ) from exc
        except urllib.error.URLError as exc:
            raise AnthropicError(f"Could not reach the Anthropic API: {exc.reason}") from exc

        with response:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[len("data:") :].strip()
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    continue
                kind = event.get("type")
                if kind == "content_block_delta":
                    delta = event.get("delta") or {}
                    if delta.get("type") == "text_delta" and delta.get("text"):
                        yield delta["text"]
                elif kind == "error":
                    error = event.get("error") or {}
                    message = error.get("message", "unknown streaming error")
                    raise AnthropicError(f"Anthropic API error: {message}")
                elif kind == "message_stop":
                    return


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
