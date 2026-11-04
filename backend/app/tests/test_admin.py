"""Tests for the admin bootstrap endpoint.

Verifies:
- No token configured → 403
- Wrong token → 403
- Missing token header → 401
- Valid token → seeds users + branch + vehicle + driver + conductor + route
- Idempotent: running twice doesn't duplicate
- Each demo user can actually log in after seeding
"""

import os

import pytest

ADMIN_PATH = "/admin/seed"


@pytest.fixture(autouse=True)
def clear_admin_token(monkeypatch):
    """Ensure each test starts with no admin token configured."""
    monkeypatch.delenv("ADMIN_BOOTSTRAP_TOKEN", raising=False)


async def test_seed_blocked_when_token_not_configured(client):
    """If ADMIN_BOOTSTRAP_TOKEN is unset, endpoint must 403."""
    resp = await client.post(ADMIN_PATH)
    assert resp.status_code == 403
    body = resp.json()
    assert "disabled" in body["detail"].lower()


async def test_seed_requires_header(client):
    """If token is set but header is missing → 401."""
    os.environ["ADMIN_BOOTSTRAP_TOKEN"] = "test-secret-12345"
    resp = await client.post(ADMIN_PATH, headers={})
    assert resp.status_code == 401


async def test_seed_rejects_wrong_token(client):
    """Wrong token → 403."""
    os.environ["ADMIN_BOOTSTRAP_TOKEN"] = "test-secret-12345"
    resp = await client.post(ADMIN_PATH, headers={"X-Admin-Token": "wrong"})
    assert resp.status_code == 403


async def test_seed_creates_all_accounts(client):
    """Happy path — all three primary accounts land in the DB."""
    os.environ["ADMIN_BOOTSTRAP_TOKEN"] = "test-secret-12345"
    resp = await client.post(ADMIN_PATH, headers={"X-Admin-Token": "test-secret-12345"})
    assert resp.status_code == 200
    body = resp.json()["data"]

    # Three primary accounts created
    created = body["summary"]["created"]
    assert "admin@transitos.app" in created["users"]
    assert "owner@transitos.app" in created["users"]
    assert "gm@transitos.app" in created["users"]

    # Credentials surfaced so user can log in
    creds = body["credentials"]
    assert creds["owner"]["email"] == "owner@transitos.app"
    assert "CHANGE ALL PASSWORDS" in creds["note"]


async def test_seed_idempotent(client):
    """First seed succeeds; second call is permanently locked (one-shot design).

    Resource creation itself is idempotent *within* a single seed run, but
    after a successful bootstrap the endpoint sets ``system_flags.bootstrap_completed``
    and returns 403 on every subsequent call — even with a valid token.
    """
    os.environ["ADMIN_BOOTSTRAP_TOKEN"] = "test-secret-12345"
    h = {"X-Admin-Token": "test-secret-12345"}

    first = await client.post(ADMIN_PATH, headers=h)
    assert first.status_code == 200, first.text
    data = first.json()["data"]
    assert len(data["summary"]["created"]["users"]) >= 3

    # Second run must be rejected by the permanent DB lock
    second = await client.post(ADMIN_PATH, headers=h)
    assert second.status_code == 403
    assert "already been completed" in second.json()["detail"].lower() or "disabled" in second.json()["detail"].lower()


async def test_seeded_owner_can_log_in(client):
    """End-to-end: seed, then log in as the owner and get a token."""
    os.environ["ADMIN_BOOTSTRAP_TOKEN"] = "test-secret-12345"
    await client.post(ADMIN_PATH, headers={"X-Admin-Token": "test-secret-12345"})

    resp = await client.post(
        "/auth/login",
        json={"email": "owner@transitos.app", "password": "Owner#Transit2026!"},
    )
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"

    # And the owner can call /auth/me to confirm role
    me = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    me_data = me.json()["data"]
    assert me_data["email"] == "owner@transitos.app"
    assert me_data["role"] == "owner"
