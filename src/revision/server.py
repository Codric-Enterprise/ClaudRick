"""HTTP server for ReVision.

Serves the static single-page UI and proxies browser requests to the Anthropic
API through ``/api/messages`` so the API key stays server-side. Optional bearer
auth and per-client rate limiting protect that endpoint. Built on the
standard-library ``http.server`` to avoid runtime dependencies.
"""

import hmac
import http.client
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from revision.anthropic_client import AnthropicClient, AnthropicError
from revision.config import Config
from revision.ratelimit import RateLimiter

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
    """Request handler bound to config/client/limiter via :func:`make_handler`."""

    client: AnthropicClient
    static_dir: Path
    config: Config
    limiter: RateLimiter

    server_version = "ReVision"

    def _send_json(self, status: int, obj: dict, extra_headers: dict | None = None) -> None:
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _client_key(self) -> str:
        """Best-effort client identifier for rate limiting."""
        if self.config.trust_proxy:
            forwarded = self.headers.get("X-Forwarded-For")
            if forwarded:
                # Left-most entry is the original client.
                return forwarded.split(",")[0].strip()
        return self.client_address[0]

    def _authorized(self) -> bool:
        token = self.config.api_token
        if not token:
            return True
        header = self.headers.get("Authorization", "")
        prefix = "Bearer "
        if not header.startswith(prefix):
            return False
        return hmac.compare_digest(header[len(prefix) :], token)

    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        path = self.path.split("?", 1)[0]
        if path == "/healthz":
            self._send_json(200, {"status": "ok"})
            return
        self._serve_static("/index.html" if path == "/" else path)

    def _serve_static(self, path: str) -> None:
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

        if not self._authorized():
            self._send_json(401, {"error": {"message": "Unauthorized."}})
            return

        allowed, retry_after = self.limiter.check(self._client_key())
        if not allowed:
            self._send_json(
                429,
                {"error": {"message": "Rate limit exceeded. Please retry shortly."}},
                extra_headers={"Retry-After": str(retry_after)},
            )
            return

        data = self._read_json_body()
        if data is None:
            return

        params = self._extract_message_params(data)
        if params is None:
            return
        prompt, max_tokens, stream = params

        if stream:
            self._handle_stream(prompt, max_tokens)
            return

        try:
            result = self.client.create_message(prompt, max_tokens=max_tokens)
        except AnthropicError as exc:
            self._send_json(502, {"error": {"message": str(exc)}})
            return

        self._send_json(200, result)

    def _read_json_body(self) -> dict | None:
        """Read and parse the request body into a JSON object.

        Sends a 400 (bad ``Content-Length``, bad JSON, or not an object) or a
        413 (body over ``max_body_bytes``) and returns None if it can't.
        """
        raw_length = self.headers.get("content-length", "0").strip() or "0"
        try:
            length = int(raw_length)
        except ValueError:
            length = -1
        if length < 0:
            self._send_json(400, {"error": {"message": "Invalid Content-Length header."}})
            return None
        if length > self.config.max_body_bytes:
            self._send_json(
                413,
                {"error": {"message": f"Request body exceeds {self.config.max_body_bytes} bytes."}},
            )
            return None

        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw)
        except ValueError:  # JSONDecodeError and UnicodeDecodeError (invalid UTF-8)
            self._send_json(400, {"error": {"message": "Request body is not valid JSON."}})
            return None
        if not isinstance(data, dict):
            self._send_json(400, {"error": {"message": "Request body must be a JSON object."}})
            return None
        return data

    def _extract_message_params(self, data: dict) -> tuple[str, int, bool] | None:
        """Validate the prompt/max_tokens fields; sends a 400 and returns None if invalid."""
        prompt = data.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            self._send_json(400, {"error": {"message": "Missing or empty 'prompt'."}})
            return None

        max_tokens = data.get("max_tokens", 3000)
        # bool is an int subclass, so `true` would otherwise pass as 1.
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens <= 0:
            self._send_json(400, {"error": {"message": "'max_tokens' must be a positive integer."}})
            return None

        return prompt, min(max_tokens, self.config.max_tokens), bool(data.get("stream"))

    def _handle_stream(self, prompt: str, max_tokens: int) -> None:
        """Proxy an Anthropic SSE stream straight through to the browser."""
        try:
            upstream = self.client.open_message_stream(prompt, max_tokens=max_tokens)
        except AnthropicError as exc:
            self._send_json(502, {"error": {"message": str(exc)}})
            return

        self.send_response(200)
        self.send_header("content-type", "text/event-stream")
        self.send_header("cache-control", "no-cache")
        self.end_headers()
        try:
            for line in upstream:
                self.wfile.write(line)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass  # the browser went away; nothing left to tell it
        except (OSError, http.client.HTTPException) as exc:
            # Headers are already sent, so a status code is no longer possible;
            # tell the client in-band instead of leaving it a silently truncated stream.
            self._send_stream_error(f"Upstream stream failed: {exc}")
        finally:
            upstream.close()

    def _send_stream_error(self, message: str) -> None:
        payload = json.dumps({"type": "error", "error": {"message": message}})
        try:
            self.wfile.write(f"event: error\ndata: {payload}\n\n".encode())
            self.wfile.flush()
        except OSError:
            pass

    def log_message(self, *args) -> None:  # noqa: A002 (silence default stderr logging)
        """Suppress the default per-request stderr logging."""


def make_handler(
    client: AnthropicClient, static_dir: Path, config: Config, limiter: RateLimiter
) -> type[RevisionHandler]:
    """Return a handler subclass bound to its dependencies."""
    return type(
        "BoundRevisionHandler",
        (RevisionHandler,),
        {
            "client": client,
            "static_dir": static_dir,
            "config": config,
            "limiter": limiter,
        },
    )


def create_server(
    config: Config | None = None, client: AnthropicClient | None = None
) -> ThreadingHTTPServer:
    """Build (but do not start) the ReVision HTTP server."""
    config = config or Config.from_env()
    client = client or AnthropicClient(config.api_key, config.model)
    limiter = RateLimiter(config.rate_limit, config.rate_window)
    handler = make_handler(client, STATIC_DIR, config, limiter)
    return ThreadingHTTPServer((config.host, config.port), handler)


def serve(config: Config | None = None) -> None:
    """Start the ReVision server and block until interrupted."""
    config = config or Config.from_env()
    httpd = create_server(config)
    host, port = httpd.server_address[:2]
    print(f"ReVision serving on http://{host}:{port}  (model: {config.model})")
    if not config.api_key:
        print("WARNING: ANTHROPIC_API_KEY is not set — API calls will fail until it is.")
    if config.api_token:
        print("Auth: bearer token required on /api/messages.")
    if config.rate_limit > 0:
        print(f"Rate limit: {config.rate_limit} requests / {config.rate_window:g}s per client.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
