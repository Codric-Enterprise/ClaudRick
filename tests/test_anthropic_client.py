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
