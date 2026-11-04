"""The password-reset link must point at a route that actually exists.

The reset email used to link to::

    {FRONTEND_URL}/(auth)/reset-password?token=…

Two things were wrong with it:

1. **Expo Router groups are not part of a URL.** The ``(auth)`` folder is
   a *group*; ``app/(auth)/reset-password.tsx`` is served at
   ``/reset-password``. A URL containing ``/(auth)/`` 404s.
2. **There was no ``reset-password`` route at all.** The app only had a
   "forgot password" screen that could complete the flow if the user
   pasted the code by hand — the link in the email was dead.

The link is now built by :func:`build_reset_link`, and the route exists.
These tests pin both halves: the format, and the promise that the path
in the email resolves to a screen that exists in the app.
"""

from __future__ import annotations

import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[3]
FRONTEND = REPO / "frontend"

sys.path.insert(0, str(REPO / "backend"))

from app.services.auth import build_reset_link  # noqa: E402


# ─── the link format ───────────────────────────────────────────────────────

def test_reset_link_strips_the_expo_router_group():
    """``(auth)`` is a group, not a URL segment."""
    link = build_reset_link("https://app.example.com", "abc123")
    assert link == "https://app.example.com/reset-password?token=abc123"
    assert "(auth)" not in link


def test_reset_link_does_not_double_the_slash():
    link = build_reset_link("https://app.example.com/", "abc123")
    assert link == "https://app.example.com/reset-password?token=abc123"


def test_reset_link_keeps_a_deep_link_scheme_intact():
    """``transitos://`` must keep its double slash."""
    link = build_reset_link("transitos://", "abc123")
    assert link == "transitos://reset-password?token=abc123"


def test_reset_link_without_a_base_url_is_empty():
    assert build_reset_link("", "abc123") == ""
    assert build_reset_link("   ", "abc123") == ""


def test_reset_link_carries_the_token():
    link = build_reset_link("https://app.example.com", "s3cr3t")
    assert "token=s3cr3t" in link


# ─── the promise: the path exists as a screen ─────────────────────────────

def _frontend_routes() -> set[str]:
    """Every URL the app serves, with Expo Router groups stripped."""
    routes: set[str] = set()
    app_dir = FRONTEND / "app"
    if not app_dir.exists():
        return routes
    for path in app_dir.rglob("*.tsx"):
        rel = path.relative_to(app_dir)
        parts = [p for p in rel.parts[:-1] if not (p.startswith("(") and p.endswith(")"))]
        route = "/" + "/".join([*parts, rel.stem])
        route = route.replace("/index", "").rstrip("/") or "/"
        routes.add(route)
    return routes


def test_the_emailed_path_is_a_screen_that_exists():
    """The path in the reset email must resolve to a real screen.

    This is the check that would have caught the original bug: the email
    named a route that the app never served.
    """
    link = build_reset_link("https://app.example.com", "abc123")
    path = link.split("?", 1)[0]
    route = re.sub(r"^https?://[^/]+", "", path)

    routes = _frontend_routes()
    assert routes, "no front-end routes found — is the front end present?"
    assert route in routes, (
        f"the reset email links to {route!r} but the app serves "
        f"{sorted(routes)}"
    )


def test_the_reset_screen_reads_the_token_from_the_link():
    """The route must actually consume ``?token=``."""
    screen = FRONTEND / "app" / "(auth)" / "reset-password.tsx"
    assert screen.exists(), "app/(auth)/reset-password.tsx is missing"
    src = screen.read_text(encoding="utf-8")
    assert "useLocalSearchParams" in src
    assert "token" in src
    assert "initialToken" in src
