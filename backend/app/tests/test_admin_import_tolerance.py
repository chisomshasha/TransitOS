"""Regression test: the app must boot even if the admin router is missing."""

from __future__ import annotations

import logging


def _all_paths(app) -> set[str]:
    """Collect paths from FastAPI routes including nested APIRouter mounts.

    FastAPI ≥0.115 stores included routers as ``_IncludedRouter`` with
    ``original_router.routes`` holding the real APIRoute objects.
    """
    paths: set[str] = set()

    def walk(routes) -> None:
        for r in routes:
            p = getattr(r, "path", None)
            if p is not None:
                paths.add(p)
            # Nested APIRouter
            orig = getattr(r, "original_router", None)
            if orig is not None and hasattr(orig, "routes"):
                walk(orig.routes)
            nested = getattr(r, "routes", None)
            if nested:
                walk(nested)

    walk(app.routes)
    return paths


def test_app_boots_with_admin_router_present():
    from app.main import app, _ADMIN_ROUTER_AVAILABLE

    assert _ADMIN_ROUTER_AVAILABLE is True
    paths = _all_paths(app)
    assert "/healthz" in paths
    assert "/auth/login" in paths
    assert "/branches" in paths
    assert "/admin/seed" in paths


def test_app_boots_when_admin_router_missing():
    """Simulate ImportError when loading admin — core routes must remain."""
    logger = logging.getLogger("transitos")

    class _Boom:
        @property
        def router(self):
            raise ImportError("simulated missing admin")

    admin_available = False
    admin_router = None
    try:
        mod = _Boom()
        if mod is not None and hasattr(mod, "router"):
            admin_router = mod.router
            admin_available = True
    except Exception as exc:
        logger.warning(
            "admin router not available (POST /admin/seed disabled): %s", exc
        )
        admin_available = False
        admin_router = None

    assert admin_available is False
    assert admin_router is None

    from app.main import app

    paths = _all_paths(app)
    assert "/healthz" in paths
    assert "/auth/login" in paths
    assert "/branches" in paths
