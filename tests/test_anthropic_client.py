import io
import json
import urllib.error

import pytest

from revision.anthropic_client import AnthropicClient, AnthropicError


class _FakeResponse:
    def __init__(self, payload: dict):
        self._data = json.dumps(payload).encode()

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_missing_api_key_raises():
    client = AnthropicClient(api_key=None, model="claude-sonnet-5")
    with pytest.raises(AnthropicError, match="ANTHROPIC_API_KEY"):
        client.create_message("hello")


def test_create_message_success(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout=None, context=None):
        captured["url"] = request.full_url
        captured["headers"] = request.headers
        captured["body"] = json.loads(request.data)
        return _FakeResponse({"content": [{"type": "text", "text": "hi"}]})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    client = AnthropicClient(api_key="sk-test", model="claude-sonnet-5")
    result = client.create_message("hello", max_tokens=1234)

    assert result["content"][0]["text"] == "hi"
    assert captured["body"]["model"] == "claude-sonnet-5"
    assert captured["body"]["max_tokens"] == 1234
    assert captured["body"]["messages"] == [{"role": "user", "content": "hello"}]
    # urllib title-cases header keys
    assert captured["headers"]["X-api-key"] == "sk-test"


def test_http_error_is_wrapped(monkeypatch):
    def fake_urlopen(request, timeout=None, context=None):
        body = io.BytesIO(json.dumps({"error": {"message": "bad key"}}).encode())
        raise urllib.error.HTTPError(request.full_url, 401, "Unauthorized", {}, body)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    client = AnthropicClient(api_key="sk-test", model="claude-sonnet-5")
    with pytest.raises(AnthropicError, match="401.*bad key"):
        client.create_message("hello")


def test_url_error_is_wrapped(monkeypatch):
    def fake_urlopen(request, timeout=None, context=None):
        raise urllib.error.URLError("no route to host")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    client = AnthropicClient(api_key="sk-test", model="claude-sonnet-5")
    with pytest.raises(AnthropicError, match="Could not reach"):
        client.create_message("hello")


class _FakeSSEResponse:
    """Iterable fake mimicking urllib's response for an SSE stream."""

    def __init__(self, lines: list[str]):
        self._lines = [line.encode() for line in lines]

    def __iter__(self):
        return iter(self._lines)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _sse_lines(*events: dict) -> list[str]:
    lines = []
    for event in events:
        lines.append(f"event: {event['type']}\n")
        lines.append(f"data: {json.dumps(event)}\n")
        lines.append("\n")
    return lines


def test_stream_message_missing_key_raises():
    client = AnthropicClient(api_key=None, model="claude-sonnet-5")
    with pytest.raises(AnthropicError, match="ANTHROPIC_API_KEY"):
        next(client.stream_message("hello"))


def test_stream_message_yields_text_deltas(monkeypatch):
    captured = {}
    events = _sse_lines(
        {"type": "message_start", "message": {}},
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text"}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Hel"}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "lo"}},
        {"type": "content_block_stop", "index": 0},
        {"type": "message_delta", "delta": {"stop_reason": "end_turn"}},
        {"type": "message_stop"},
    )

    def fake_urlopen(request, timeout=None, context=None):
        captured["body"] = json.loads(request.data)
        return _FakeSSEResponse(events)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    client = AnthropicClient(api_key="sk-test", model="claude-sonnet-5")
    assert list(client.stream_message("hello", max_tokens=99)) == ["Hel", "lo"]
    assert captured["body"]["stream"] is True
    assert captured["body"]["max_tokens"] == 99


def test_stream_message_error_event_raises(monkeypatch):
    events = _sse_lines(
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "x"}},
        {"type": "error", "error": {"type": "overloaded_error", "message": "Overloaded"}},
    )

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout=None, context=None: _FakeSSEResponse(events),
    )

    client = AnthropicClient(api_key="sk-test", model="claude-sonnet-5")
    stream = client.stream_message("hello")
    assert next(stream) == "x"
    with pytest.raises(AnthropicError, match="Overloaded"):
        next(stream)
