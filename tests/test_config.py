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
