import json
import threading
import urllib.error
import urllib.request
from contextlib import contextmanager

import pytest

from revision.anthropic_client import AnthropicError
from revision.config import Config
from revision.server import create_server


class _FakeClient:
    """Stand-in for AnthropicClient; records calls and returns/raises on demand."""

    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def create_message(self, prompt, max_tokens=3000):
        self.calls.append((prompt, max_tokens))
        if self.error:
            raise self.error
        return self.result


@contextmanager
def running_server(client):
    config = Config(api_key="sk-test", model="claude-sonnet-5", host="127.0.0.1", port=0)
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


def _post(url, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, method="POST", headers={"content-type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_get_index_served():
    client = _FakeClient(result={"content": []})
    with running_server(client) as base:
        with urllib.request.urlopen(base + "/") as resp:
            body = resp.read().decode()
        assert resp.status == 200
        assert "✨ ReVision" in body
        assert "/api/messages" in body


def test_api_messages_proxies_to_client():
    client = _FakeClient(result={"content": [{"type": "text", "text": "ok"}]})
    with running_server(client) as base:
        status, data = _post(base + "/api/messages", {"prompt": "hi", "max_tokens": 500})
    assert status == 200
    assert data["content"][0]["text"] == "ok"
    assert client.calls == [("hi", 500)]


def test_api_messages_requires_prompt():
    client = _FakeClient(result={"content": []})
    with running_server(client) as base:
        status, data = _post(base + "/api/messages", {"max_tokens": 500})
    assert status == 400
    assert "prompt" in data["error"]["message"].lower()
    assert client.calls == []


def test_api_messages_wraps_anthropic_error():
    client = _FakeClient(error=AnthropicError("boom"))
    with running_server(client) as base:
        status, data = _post(base + "/api/messages", {"prompt": "hi"})
    assert status == 502
    assert data["error"]["message"] == "boom"


def test_unknown_path_404():
    client = _FakeClient(result={"content": []})
    with running_server(client) as base:
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(base + "/../etc/passwd")
        assert exc.value.code == 404
