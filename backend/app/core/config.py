"""Application configuration loaded from environment variables.

CRITICAL NOTE on CORS_ORIGINS
=============================
The field is NOT declared on the pydantic ``Settings`` class. It's read
directly from ``os.environ`` at import time.

Why: pydantic-settings v2 auto-JSON-decodes any field typed as ``list[...]``,
which crashes on plain strings like ``"*"`` or ``"https://a.com,https://b.com"``
that are the natural way to write env values. The fix is to never let
pydantic-settings see this field as a complex type.

If you need to add another list-typed env var, use the same pattern — read it
manually in this module rather than declaring it on ``Settings``.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_cors_origins(raw: str | list[str] | None) -> list[str]:
    """Normalise a CORS origins value into a list of strings.

    Accepts:
      - ``"*"`` or ``None`` or ``""`` → ``["*"]`` (open to all)
      - ``"https://a.com,https://b.com"`` → split + trim
      - ``'["https://a.com", "https://b.com"]'`` → JSON-decoded, then normalised
      - ``["https://a.com", "https://b.com"]`` (already a list) → as-is
    """
    if raw is None or raw == "" or (isinstance(raw, str) and raw.strip() == "*"):
        return ["*"]
    if isinstance(raw, str):
        s = raw.strip()
        if s.startswith("["):
            import json
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed if str(x).strip()]
            except (ValueError, json.JSONDecodeError):
                pass
        return [item.strip() for item in s.split(",") if item.strip()]
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    return ["*"]


# ─── CORS — read directly from env, bypass pydantic-settings entirely ──────
# This is the only safe way. Pydantic-settings will JSON-decode list fields
# and crash on plain strings. So we don't give it the field at all.
_CORS_RAW = os.environ.get("CORS_ORIGINS", "*")
CORS_ORIGINS_LIST: list[str] = parse_cors_origins(_CORS_RAW)

# Known insecure default — must never be used outside local dev.
_INSECURE_JWT_DEFAULT = "dev-only-not-for-production-please-change-me"
_MIN_JWT_SECRET_LEN = 32


class Settings(BaseSettings):
    """Env-driven configuration. See ``.env.example`` for documentation.

    Note: ``cors_origins`` is intentionally NOT a field here. Read it from
    the module-level :data:`CORS_ORIGINS_LIST` constant instead.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- runtime ---
    env: Literal["dev", "staging", "prod"] = "dev"
    log_level: str = "INFO"

    # --- database ---
    # Accept either our own naming (MONGODB_URL / MONGODB_DB_NAME) or
    # Railway's MongoDB plugin naming (MONGO_URL / MONGO_DB).
    mongodb_url: str = Field(
        default="mongodb://localhost:27017",
        validation_alias=AliasChoices(
            "MONGODB_URL",
            "MONGO_URL",
            "MONGO_URI",
        ),
    )
    mongodb_db_name: str = Field(
        default="transitos",
        validation_alias=AliasChoices(
            "MONGODB_DB_NAME",
            "MONGO_DB",
            "MONGO_DATABASE",
            "MONGODB_DATABASE",
        ),
    )

    # --- security / JWT ---
    jwt_secret_key: str = Field(
        default=_INSECURE_JWT_DEFAULT,
        description="HS256 signing key for access + refresh tokens.",
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # ── Resend email delivery (preferred over SMTP) ─────────────────────────
    RESEND_API_KEY: str | None = None
    EMAIL_FROM: str = "TransitOS <no-reply@transitos.app>"

    # --- password-reset delivery ---
    # When SMTP_HOST is set, forgot-password emails are sent via SMTP.
    # Otherwise the token is only logged in ENV=dev (never in staging/prod).
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@transitos.app"
    smtp_use_tls: bool = True
    # Public frontend URL used to build the reset link in the email body.
    # Example: https://app.transitos.example
    frontend_url: str = "http://localhost:8081"

    # --- admin bootstrap (one-shot) ---
    # Optional. When set to a non-empty string, POST /admin/seed is enabled.
    # When empty/unset, the endpoint is permanently disabled (returns 403).
    admin_bootstrap_token: str = Field(
        default="",
        description=(
            "Optional secret that enables the one-shot POST /admin/seed endpoint. "
            "Set via ADMIN_BOOTSTRAP_TOKEN env var. Unset after first use to lock."
        ),
    )

    @model_validator(mode="after")
    def _reject_insecure_settings_in_non_dev(self) -> "Settings":
        """Refuse to start in staging/prod with weak secrets or open CORS."""
        if self.env not in ("staging", "prod"):
            return self

        # ── JWT secret ──────────────────────────────────────────────────
        key = (self.jwt_secret_key or "").strip()
        if not key or key == _INSECURE_JWT_DEFAULT:
            raise RuntimeError(
                "JWT_SECRET_KEY must be set to a strong random value when "
                f"ENV={self.env}. Generate one with: "
                'python -c "import secrets; print(secrets.token_urlsafe(64))"'
            )
        if len(key) < _MIN_JWT_SECRET_LEN:
            raise RuntimeError(
                f"JWT_SECRET_KEY is too short ({len(key)} chars). "
                f"Use at least {_MIN_JWT_SECRET_LEN} characters in "
                f"ENV={self.env}."
            )

        # ── CORS origins ────────────────────────────────────────────────
        # In non-dev we never allow the wildcard. Explicit origins required.
        origins = CORS_ORIGINS_LIST
        if not origins or origins == ["*"] or "*" in origins:
            raise RuntimeError(
                "CORS_ORIGINS must be set to one or more explicit origins "
                f"(not '*') when ENV={self.env}. Example: "
                'CORS_ORIGINS="https://app.example.com,https://admin.example.com"'
            )

        return self

    @property
    def cors_origins_list(self) -> list[str]:
        """Proxy to module-level parsed CORS list (always available)."""
        return CORS_ORIGINS_LIST


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings factory. Prefer importing ``settings`` directly."""
    return Settings()


# Module-level singleton. Use this everywhere.
settings = get_settings()
