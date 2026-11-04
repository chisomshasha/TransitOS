"""Every setting must be documented in ``.env.example``.

``backend/.env.example`` is what an operator copies to ``.env`` and
fills in. Ten of the twenty settings were **not** in it — including
``FRONTEND_URL``, which builds the password-reset link, and every
email-delivery setting. An operator reading the example file would not
know they existed, so they stayed unset: reset emails linked to
``localhost`` and no email was ever sent.

This test walks the ``Settings`` model and fails if any field has no
corresponding entry in ``.env.example``, so a new setting cannot be
added without documenting it.
"""

from __future__ import annotations

import pathlib
import re

from app.core.config import Settings

BACKEND = pathlib.Path(__file__).resolve().parents[2]
ENV_EXAMPLE = BACKEND / ".env.example"


def _documented_names(text: str) -> set[str]:
    """Every env var name mentioned in the example file."""
    assigned = set(re.findall(r"^([A-Za-z_][A-Za-z0-9_]*)=", text, re.M))
    commented = set(re.findall(r"^#\s*([A-Z_][A-Z0-9_]*)=", text, re.M))
    return {n.upper() for n in assigned | commented}


def _accepted_names(name: str, field) -> set[str]:
    """The env var names pydantic-settings accepts for a field."""
    names = {name.upper()}
    alias = field.validation_alias
    if isinstance(alias, str):
        names.add(alias.upper())
    elif alias is not None and hasattr(alias, "choices"):
        names |= {str(c).upper() for c in alias.choices}
    return names


def test_every_setting_is_documented_in_env_example():
    assert ENV_EXAMPLE.exists(), f"{ENV_EXAMPLE} is missing"

    documented = _documented_names(ENV_EXAMPLE.read_text(encoding="utf-8"))

    missing = []
    for name, field in Settings.model_fields.items():
        if not (_accepted_names(name, field) & documented):
            missing.append(name)

    assert not missing, (
        "these settings are not documented in backend/.env.example: "
        f"{missing}\n  An operator cannot set what they cannot see."
    )


def test_env_example_does_not_mention_settings_that_do_not_exist():
    """A stale entry is as confusing as a missing one."""
    documented = _documented_names(ENV_EXAMPLE.read_text(encoding="utf-8"))
    known: set[str] = set()
    for name, field in Settings.model_fields.items():
        known |= _accepted_names(name, field)

    # These are read directly from os.environ, not from Settings.
    known |= {"CORS_ORIGINS", "ADMIN_BOOTSTRAP_TOKEN", "RATE_LIMIT_REDIS_URL",
              "REDIS_URL", "RATE_LIMIT_FAIL_CLOSED", "MAX_REQUEST_BODY_BYTES"}

    unknown = documented - known
    assert not unknown, f"backend/.env.example mentions unknown settings: {sorted(unknown)}"
