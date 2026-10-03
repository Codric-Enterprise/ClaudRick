from revision.config import DEFAULT_MODEL, Config


def test_from_env_defaults(monkeypatch):
    for var in ("ANTHROPIC_API_KEY", "REVISION_MODEL", "REVISION_HOST", "REVISION_PORT"):
        monkeypatch.delenv(var, raising=False)

    config = Config.from_env()

    assert config.api_key is None
    assert config.model == DEFAULT_MODEL
    assert config.host == "127.0.0.1"
    assert config.port == 8000


def test_from_env_overrides(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("REVISION_MODEL", "claude-opus-4-8")
    monkeypatch.setenv("REVISION_HOST", "0.0.0.0")
    monkeypatch.setenv("REVISION_PORT", "9999")

    config = Config.from_env()

    assert config.api_key == "sk-test"
    assert config.model == "claude-opus-4-8"
    assert config.host == "0.0.0.0"
    assert config.port == 9999


def test_request_limits_default_and_override(monkeypatch):
    for var in ("REVISION_MAX_TOKENS", "REVISION_MAX_BODY_BYTES"):
        monkeypatch.delenv(var, raising=False)
    config = Config.from_env()
    assert config.max_tokens == 8192
    assert config.max_body_bytes == 1_048_576

    monkeypatch.setenv("REVISION_MAX_TOKENS", "2048")
    monkeypatch.setenv("REVISION_MAX_BODY_BYTES", "4096")
    config = Config.from_env()
    assert config.max_tokens == 2048
    assert config.max_body_bytes == 4096
