"""Contract integrity — the OpenAPI schema must build, and every route
must accept a JSON body where the frontend sends one.

Why this file exists
---------------------
``app/routers/auth.py`` referenced ``ForgotUsernameRequest`` in the
``/auth/forgot-username`` signature without ever importing or defining
it. Because the module uses ``from __future__ import annotations`` the
annotation stayed a lazy string, so nothing failed at import time and
every test still passed — but:

  * ``POST /auth/forgot-username`` treated the unresolvable annotation
    as a *query* parameter and answered
    ``400 {"loc": "query → body", "msg": "Field required"}`` for every
    request, and
  * ``GET /openapi.json`` raised ``PydanticUserError`` and returned 500,
    breaking the docs for the entire API.

Both symptoms are invisible to a test that only exercises a handful of
routes. Building the whole OpenAPI schema, on the other hand, forces
FastAPI to resolve every annotation on every route — so it catches this
class of bug in one shot.
"""

from __future__ import annotations

import pytest

from app.main import app


@pytest.mark.asyncio
async def test_openapi_schema_builds():
    """The full OpenAPI document must generate without raising."""
    schema = app.openapi()
    assert schema is not None
    assert "paths" in schema

    # Count operations (a path can hold several methods).
    http_methods = {"get", "post", "put", "patch", "delete", "head", "options"}
    operations = sum(
        1
        for methods in schema["paths"].values()
        for method in methods
        if method in http_methods
    )

    # A non-trivial number of routes — if this ever drops to a handful,
    # routers failed to mount and the app is silently crippled.
    assert operations > 120, (
        f"only {operations} operations in the OpenAPI document "
        f"({len(schema['paths'])} paths) — did some routers fail to mount?"
    )


@pytest.mark.asyncio
async def test_openapi_covers_known_router_prefixes():
    """Every mounted router must appear in the schema."""
    schema = app.openapi()
    paths = set(schema["paths"].keys())

    for prefix in (
        "/auth",
        "/branches",
        "/users",
        "/vehicles",
        "/drivers",
        "/conductors",
        "/routes",
        "/trips",
        "/cash-ups",
        "/expenses",
        "/fuel-logs",
        "/maintenance",
        "/reports",
        "/notifications",
        "/push",
        "/alerts",
        "/audit-log",
        "/role-permissions",
        "/incidents",
        "/inspections",
        "/vehicle-transfers",
        "/vehicle-documents",
        "/sync",
        "/qr",
        "/dashboard",
        "/fleet",
        "/admin",
    ):
        assert any(p.startswith(prefix) for p in paths), (
            f"no route found under {prefix!r} in the OpenAPI document"
        )


@pytest.mark.asyncio
async def test_forgot_username_accepts_a_json_body(client):
    """Regression: the body must be read from the JSON payload.

    Before the fix the body was parsed as a query parameter, so every
    request came back 400 with ``loc: "query → body"``.
    """
    r = await client.post(
        "/auth/forgot-username", json={"email": "nobody@example.com"}
    )
    assert r.status_code == 202, r.text
    # The endpoint must never reveal whether the account exists.
    r2 = await client.post(
        "/auth/forgot-username", json={"email": "admin@transitos.app"}
    )
    assert r2.status_code == 202, r2.text


@pytest.mark.asyncio
async def test_forgot_username_rejects_a_malformed_body(client):
    r = await client.post("/auth/forgot-username", json={"email": "not-an-email"})
    assert r.status_code == 422, r.text
    assert r.json()["type"] == "validation_error", r.text


@pytest.mark.asyncio
async def test_openapi_json_endpoint_serves_the_schema(client):
    """``/openapi.json`` must return 200, not 500."""
    r = await client.get("/openapi.json")
    assert r.status_code == 200, r.text
    assert r.json()["openapi"].startswith("3.")
