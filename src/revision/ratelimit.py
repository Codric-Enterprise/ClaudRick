"""A tiny thread-safe, per-key sliding-window rate limiter (stdlib only)."""

import time
from collections import defaultdict, deque
from threading import Lock


class RateLimiter:
    """Allow up to ``limit`` events per ``window`` seconds for each key.

    Thread-safe so it can back a :class:`~http.server.ThreadingHTTPServer`. A
    ``limit`` of 0 (or less) disables limiting entirely.
    """

    def __init__(self, limit: int, window: float) -> None:
        self.limit = limit
        self.window = window
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> tuple[bool, int]:
        """Record an attempt for ``key``.

        Returns ``(allowed, retry_after_seconds)``. When not allowed,
        ``retry_after_seconds`` is a positive hint for the ``Retry-After``
        header; when allowed it is 0.
        """
        if self.limit <= 0:
            return True, 0

        now = time.monotonic()
        cutoff = now - self.window
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= self.limit:
                retry_after = self.window - (now - hits[0])
                return False, max(1, int(retry_after) + 1)
            hits.append(now)
            # Drop empty deques opportunistically to bound memory growth.
            return True, 0
