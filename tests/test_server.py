import json
import threading
import urllib.error
import urllib.request
from contextlib import contextmanager

import pytest

from revision.anthropic_client import AnthropicError
from revision.config import Config
from revision.server import create_server


class _FakeStream:
    """Stand-in for the streaming response returned by open_message_stream."""

    def __init__(self, lines):
        self._lines = iter(lines)
        self.closed = False

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._lines)

    def close(self):
        self.closed = True


class _FakeClient:
    """Stand-in for AnthropicClient; records calls and returns/raises on demand."""

    def __init__(self, result=None, error=None, stream_lines=None, stream_error=None):
        self.result = result
        self.error = error
        self.stream_lines = stream_lines
        self.stream_error = stream_error
        self.calls = []

    def create_message(self, prompt, max_tokens=3000):
        self.calls.append((prompt, max_tokens))
        if self.error:
            raise self.error
        return self.result

    def open_message_stream(self, prompt, max_tokens=3000):
        self.calls.append((prompt, max_tokens))
        if self.stream_error:
            raise self.stream_error
        return _FakeStream(self.stream_lines or [])


@contextmanager
def running_server(client, **config_kwargs):
    kwargs = {
        "api_key": "sk-test",
        "model": "claude-sonnet-5",
        "host": "127.0.0.1",
        "port": 0,
    }
    kwargs.update(config_kwargs)
    config = Config(**kwargs)
    httpd = create_server(config, client=client)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address[:2]
    try:
        yield f"http://{host}:{port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def _post(url, payload, headers=None):
    data = json.dumps(payload).encode()
    hdrs = {"content-type": "application/json"}
    hdrs.update(headers or {})
    req = urllib.request.Request(url, data=data, method="POST", headers=hdrs)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read()), dict(resp.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read()), dict(exc.headers)


def test_get_index_served():
    client = _FakeClient(result={"content": []})
    with running_server(client) as base:
        with urllib.request.urlopen(base + "/") as resp:
            body = resp.read().decode()
        assert resp.status == 200
        assert "✨ ReVision" in body
        assert "/api/messages" in body


def test_healthz():
    client = _FakeClient(result={"content": []})
    with (
        running_server(client) as base,
        urllib.request.urlopen(base + "/healthz") as resp,
    ):
        assert resp.status == 200
        assert json.loads(resp.read()) == {"status": "ok"}


def test_api_messages_proxies_to_client():
    client = _FakeClient(result={"content": [{"type": "text", "text": "ok"}]})
    with running_server(client) as base:
        status, data, _ = _post(base + "/api/messages", {"prompt": "hi", "max_tokens": 500})
    assert status == 200
    assert data["content"][0]["text"] == "ok"
    assert client.calls == [("hi", 500)]


def test_api_messages_requires_prompt():
    client = _FakeClient(result={"content": []})
    with running_server(client) as base:
        status, data, _ = _post(base + "/api/messages", {"max_tokens": 500})
    assert status == 400
    assert "prompt" in data["error"]["message"].lower()
    assert client.calls == []


def test_api_messages_wraps_anthropic_error():
    client = _FakeClient(error=AnthropicError("boom"))
    with running_server(client) as base:
        status, data, _ = _post(base + "/api/messages", {"prompt": "hi"})
    assert status == 502
    assert data["error"]["message"] == "boom"


def test_unknown_path_404():
    client = _FakeClient(result={"content": []})
    with running_server(client) as base:
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(base + "/../etc/passwd")
        assert exc.value.code == 404


def test_auth_required_when_token_set():
    client = _FakeClient(result={"content": []})
    with running_server(client, api_token="secret") as base:
        # No header -> 401
        status, _, _ = _post(base + "/api/messages", {"prompt": "hi"})
        assert status == 401
        # Wrong token -> 401
        status, _, _ = _post(
            base + "/api/messages", {"prompt": "hi"}, headers={"Authorization": "Bearer nope"}
        )
        assert status == 401
        # Correct token -> 200
        status, _, _ = _post(
            base + "/api/messages", {"prompt": "hi"}, headers={"Authorization": "Bearer secret"}
        )
        assert status == 200
    assert client.calls == [("hi", 3000)]


def test_api_messages_streams_sse():
    lines = [
        b"event: content_block_delta\n",
        b'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"Hi"}}\n',
        b"\n",
        b"event: message_stop\n",
        b'data: {"type":"message_stop"}\n',
        b"\n",
    ]
    client = _FakeClient(stream_lines=lines)
    with running_server(client) as base:
        req = urllib.request.Request(
            base + "/api/messages",
            data=json.dumps({"prompt": "hi", "stream": True}).encode(),
            headers={"content-type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            content_type = resp.headers["content-type"]
            body = resp.read()
    assert content_type == "text/event-stream"
    assert b"content_block_delta" in body
    assert client.calls == [("hi", 3000)]


def test_api_messages_stream_error_returns_502_json():
    client = _FakeClient(stream_error=AnthropicError("boom"))
    with running_server(client) as base:
        status, data, _ = _post(base + "/api/messages", {"prompt": "hi", "stream": True})
    assert status == 502
    assert data["error"]["message"] == "boom"


def test_global_rate_limit_returns_429_with_retry_after():
    client = _FakeClient(result={"content": []})
    # Global budget is tighter than the per-client limit, so it's the one that trips.
    with running_server(
        client, rate_limit=30, global_rate_limit=2, global_rate_window=60.0
    ) as base:
        assert _post(base + "/api/messages", {"prompt": "a"})[0] == 200
        assert _post(base + "/api/messages", {"prompt": "b"})[0] == 200
        status, data, headers = _post(base + "/api/messages", {"prompt": "c"})
    assert status == 429
    assert "budget" in data["error"]["message"].lower()
    assert int(headers["Retry-After"]) >= 1
    assert client.calls == [("a", 3000), ("b", 3000)]


def test_rate_limit_returns_429_with_retry_after():
    client = _FakeClient(result={"content": []})
    with running_server(client, rate_limit=2, rate_window=60.0) as base:
        assert _post(base + "/api/messages", {"prompt": "a"})[0] == 200
        assert _post(base + "/api/messages", {"prompt": "b"})[0] == 200
        status, data, headers = _post(base + "/api/messages", {"prompt": "c"})
    assert status == 429
    assert "rate limit" in data["error"]["message"].lower()
    assert int(headers["Retry-After"]) >= 1
    # Only the two allowed requests reached the client.
    assert client.calls == [("a", 3000), ("b", 3000)]
