from revision.ratelimit import RateLimiter


def test_disabled_when_limit_zero():
    limiter = RateLimiter(limit=0, window=60.0)
    for _ in range(1000):
        allowed, retry = limiter.check("k")
        assert allowed
        assert retry == 0


def test_allows_up_to_limit_then_blocks():
    limiter = RateLimiter(limit=3, window=60.0)
    assert limiter.check("k")[0] is True
    assert limiter.check("k")[0] is True
    assert limiter.check("k")[0] is True
    allowed, retry = limiter.check("k")
    assert allowed is False
    assert retry >= 1


def test_keys_are_independent():
    limiter = RateLimiter(limit=1, window=60.0)
    assert limiter.check("a")[0] is True
    assert limiter.check("b")[0] is True
    assert limiter.check("a")[0] is False


def test_window_expiry(monkeypatch):
    fake = {"t": 1000.0}
    monkeypatch.setattr("revision.ratelimit.time.monotonic", lambda: fake["t"])
    limiter = RateLimiter(limit=1, window=10.0)

    assert limiter.check("k")[0] is True
    assert limiter.check("k")[0] is False
    # Advance beyond the window; the old hit should expire.
    fake["t"] += 11
    assert limiter.check("k")[0] is True


def test_expired_keys_are_forgotten(monkeypatch):
    fake = {"t": 1000.0}
    monkeypatch.setattr("revision.ratelimit.time.monotonic", lambda: fake["t"])
    limiter = RateLimiter(limit=5, window=10.0)

    for i in range(100):
        limiter.check(f"client-{i}")
    assert len(limiter._hits) == 100

    # Past the window every one of those hits has expired; none of those clients
    # returns, so the next call (from someone else) must sweep them away.
    fake["t"] += 11
    limiter.check("newcomer")
    assert list(limiter._hits) == ["newcomer"]


def test_active_keys_survive_a_sweep(monkeypatch):
    fake = {"t": 1000.0}
    monkeypatch.setattr("revision.ratelimit.time.monotonic", lambda: fake["t"])
    limiter = RateLimiter(limit=1, window=10.0)

    assert limiter.check("busy")[0] is True
    fake["t"] += 5
    limiter.check("other")  # inside the window, so "busy" is still being limited
    fake["t"] += 6  # first sweep deadline has passed; "busy" has now expired
    limiter.check("other")
    assert limiter.check("busy")[0] is True
