"""Tests for env-driven configuration.

Locks down the CORS parsing fix. Three different approaches have been tried
(before settling on the final one):

  1. ``cors_origins: list[str]`` with pydantic-settings auto-decode → crashes
  2. ``Annotated[list[str], NoDecode, BeforeValidator]`` → didn't help on Railway
  3. ``cors_origins: str`` with a property → better, but Settings still touched it
  4. **(current)** Read directly from ``os.environ`` at module import time,
     never declared on the Settings class. Pydantic-settings cannot crash on
     a field it never sees.
"""

import importlib


def _reload_config(monkeypatch):
    """Force the config module to re-read from the current env."""
    import sys
    if "app.core.config" in sys.modules:
        del sys.modules["app.core.config"]
    return importlib.import_module("app.core.config")


def test_cors_default_is_wildcard(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    cfg = _reload_config(monkeypatch)
    assert cfg.CORS_ORIGINS_LIST == ["*"]


def test_cors_accepts_wildcard_string(monkeypatch):
    """The original bug: CORS_ORIGINS='*' used to crash with JSONDecodeError."""
    monkeypatch.setenv("CORS_ORIGINS", "*")
    cfg = _reload_config(monkeypatch)
    assert cfg.CORS_ORIGINS_LIST == ["*"]


def test_cors_accepts_comma_separated_string(monkeypatch):
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "https://app.transitos.example,https://admin.transitos.example",
    )
    cfg = _reload_config(monkeypatch)
    assert cfg.CORS_ORIGINS_LIST == [
        "https://app.transitos.example",
        "https://admin.transitos.example",
    ]


def test_cors_trims_whitespace(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", " https://a.example , https://b.example ")
    cfg = _reload_config(monkeypatch)
    assert cfg.CORS_ORIGINS_LIST == ["https://a.example", "https://b.example"]


def test_cors_handles_empty_string(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "")
    cfg = _reload_config(monkeypatch)
    assert cfg.CORS_ORIGINS_LIST == ["*"]


def test_cors_handles_json_array(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", '["https://app.example","https://admin.example"]')
    cfg = _reload_config(monkeypatch)
    assert cfg.CORS_ORIGINS_LIST == [
        "https://app.example",
        "https://admin.example",
    ]


def test_cors_not_a_settings_field(monkeypatch):
    """Regression guard: cors_origins must never be a pydantic field again."""
    monkeypatch.setenv("CORS_ORIGINS", "*")
    cfg = _reload_config(monkeypatch)
    s = cfg.Settings(_env_file=None)
    # If this assertion ever fails, someone re-introduced cors_origins as a
    # pydantic field — the JSON-decode bug is back.
    assert "cors_origins" not in s.model_fields
    assert "cors_origins" not in dir(s)


def test_mongo_url_alias_choice_still_works(monkeypatch):
    """MONGO_URL (Railway plugin) still maps to mongodb_url."""
    monkeypatch.setenv("MONGO_URL", "mongodb://railway-test:27017")
    monkeypatch.delenv("MONGODB_URL", raising=False)
    monkeypatch.delenv("MONGO_URI", raising=False)
    cfg = _reload_config(monkeypatch)
    assert cfg.settings.mongodb_url == "mongodb://railway-test:27017"


def test_admin_bootstrap_token_default_is_empty(monkeypatch):
    monkeypatch.delenv("ADMIN_BOOTSTRAP_TOKEN", raising=False)
    cfg = _reload_config(monkeypatch)
    assert cfg.settings.admin_bootstrap_token == ""


def test_admin_bootstrap_token_reads_env(monkeypatch):
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "my-secret")
    cfg = _reload_config(monkeypatch)
    assert cfg.settings.admin_bootstrap_token == "my-secret"
