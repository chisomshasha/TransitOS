"""Auth endpoint tests — login, refresh, /me, logout, RBAC basics."""

import pytest


@pytest.mark.asyncio
async def test_login_success(client, super_admin):
    r = await client.post(
        "/auth/login",
        json={"email": "admin@transitos.app", "password": "Admin#12345"},
    )
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["expires_in"] == 15 * 60


@pytest.mark.asyncio
async def test_login_bad_password(client, super_admin):
    r = await client.post(
        "/auth/login",
        json={"email": "admin@transitos.app", "password": "wrong"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email(client):
    r = await client.post(
        "/auth/login",
        json={"email": "ghost@transitos.app", "password": "anything"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_validation_short_password(client):
    r = await client.post(
        "/auth/login",
        json={"email": "x@y.com", "password": ""},
    )
    assert r.status_code == 400  # our handler converts 422 -> 400


@pytest.mark.asyncio
async def test_me_requires_token(client):
    r = await client.get("/auth/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_user(client, auth_headers):
    r = await client.get("/auth/me", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["email"] == "admin@transitos.app"
    assert body["role"] == "super_admin"
    assert "password_hash" not in body


@pytest.mark.asyncio
async def test_refresh_issues_new_tokens(client, super_admin):
    r = await client.post(
        "/auth/login",
        json={"email": "admin@transitos.app", "password": "Admin#12345"},
    )
    refresh = r.json()["data"]["refresh_token"]
    r2 = await client.post("/auth/refresh", headers={"Authorization": f"Bearer {refresh}"})
    assert r2.status_code == 200
    body = r2.json()["data"]
    assert body["access_token"]
    assert body["refresh_token"]
    # old refresh is revoked
    r3 = await client.post("/auth/refresh", headers={"Authorization": f"Bearer {refresh}"})
    assert r3.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_token(client, super_admin):
    r = await client.post(
        "/auth/login",
        json={"email": "admin@transitos.app", "password": "Admin#12345"},
    )
    refresh = r.json()["data"]["refresh_token"]
    access = r.json()["data"]["access_token"]
    r2 = await client.post(
        "/auth/logout",
        json={"refresh_token": refresh},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert r2.status_code == 204
    r3 = await client.post("/auth/refresh", headers={"Authorization": f"Bearer {refresh}"})
    assert r3.status_code == 401


@pytest.mark.asyncio
async def test_change_password_revokes_tokens(client, super_admin):
    r = await client.post(
        "/auth/login",
        json={"email": "admin@transitos.app", "password": "Admin#12345"},
    )
    refresh = r.json()["data"]["refresh_token"]
    r2 = await client.post(
        "/auth/change-password",
        headers={"Authorization": r.json()["data"]["access_token"].__class__ and f"Bearer {r.json()['data']['access_token']}"},
        json={"current_password": "Admin#12345", "new_password": "NewSecret#12345"},
    )
    assert r2.status_code == 204
    # refresh should be revoked
    r3 = await client.post("/auth/refresh", headers={"Authorization": f"Bearer {refresh}"})
    assert r3.status_code == 401
    # new password works
    r4 = await client.post(
        "/auth/login",
        json={"email": "admin@transitos.app", "password": "NewSecret#12345"},
    )
    assert r4.status_code == 200
