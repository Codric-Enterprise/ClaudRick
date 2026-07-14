"""HTTP server for ReVision.

Serves the static single-page UI and proxies browser requests to the Anthropic
API through ``/api/messages`` so the API key stays server-side. Built on the
standard-library ``http.server`` to avoid runtime dependencies.
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from revision.anthropic_client import AnthropicClient, AnthropicError
from revision.config import Config

STATIC_DIR = Path(__file__).parent / "static"

#: Minimal content-type map for the few static assets ReVision ships.
_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


class RevisionHandler(BaseHTTPRequestHandler):
    """Request handler bound to a client and static dir via :func:`make_handler`."""

    client: AnthropicClient
    static_dir: Path

    server_version = "ReVision"

    def _send_json(self, status: int, obj: dict) -> None:
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        path = self.path.split("?", 1)[0]
        if path == "/":
            path = "/index.html"

        target = (self.static_dir / path.lstrip("/")).resolve()
        root = self.static_dir.resolve()
        # Guard against path traversal outside the static directory.
        if root not in target.parents and target != root:
            self.send_error(404, "Not found")
            return
        if not target.is_file():
            self.send_error(404, "Not found")
            return

        content = target.read_bytes()
        ctype = _CONTENT_TYPES.get(target.suffix, "application/octet-stream")
        self.send_response(200)
        self.send_header("content-type", ctype)
        self.send_header("content-length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:  # noqa: N802 (http.server API)
        path = self.path.split("?", 1)[0]
        if path != "/api/messages":
            self.send_error(404, "Not found")
            return

        length = int(self.headers.get("content-length", 0) or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            self._send_json(400, {"error": {"message": "Request body is not valid JSON."}})
            return

        prompt = data.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            self._send_json(400, {"error": {"message": "Missing or empty 'prompt'."}})
            return

        max_tokens = data.get("max_tokens", 3000)
        if not isinstance(max_tokens, int) or max_tokens <= 0:
            max_tokens = 3000

        try:
            result = self.client.create_message(prompt, max_tokens=max_tokens)
        except AnthropicError as exc:
            self._send_json(502, {"error": {"message": str(exc)}})
            return

        self._send_json(200, result)

    def log_message(self, *args) -> None:  # noqa: A002 (silence default stderr logging)
        """Suppress the default per-request stderr logging."""


def make_handler(client: AnthropicClient, static_dir: Path) -> type[RevisionHandler]:
    """Return a handler subclass bound to ``client`` and ``static_dir``."""
    return type(
        "BoundRevisionHandler",
        (RevisionHandler,),
        {"client": client, "static_dir": static_dir},
    )


def create_server(
    config: Config | None = None, client: AnthropicClient | None = None
) -> ThreadingHTTPServer:
    """Build (but do not start) the ReVision HTTP server."""
    config = config or Config.from_env()
    client = client or AnthropicClient(config.api_key, config.model)
    handler = make_handler(client, STATIC_DIR)
    return ThreadingHTTPServer((config.host, config.port), handler)


def serve(config: Config | None = None) -> None:
    """Start the ReVision server and block until interrupted."""
    config = config or Config.from_env()
    httpd = create_server(config)
    host, port = httpd.server_address[:2]
    print(f"ReVision serving on http://{host}:{port}  (model: {config.model})")
    if not config.api_key:
        print("WARNING: ANTHROPIC_API_KEY is not set — API calls will fail until it is.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
