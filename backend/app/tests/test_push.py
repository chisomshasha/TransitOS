"""Tests for the push-token router (registration, listing, unregister)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


async def test_register_requires_auth(client):
    r = await client.post("/push/register", json={"token": "a" * 20, "platform": "android"})
    assert r.status_code in (401, 403)


async def test_register_and_list_token(client, auth_headers):
    r = await client.post(
        "/push/register",
        json={"token": "expo-push-token-abc123", "platform": "android", "device_id": "dev-1"},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["token"] == "expo-push-token-abc123"
    assert data["platform"] == "android"
    assert data["is_active"] is True

    r2 = await client.get("/push", headers=auth_headers)
    assert r2.status_code == 200, r2.text
    items = r2.json()["items"]
    assert len(items) == 1
    assert items[0]["token"] == "expo-push-token-abc123"


async def test_register_is_idempotent_upsert(client, auth_headers):
    payload = {"token": "expo-push-token-same", "platform": "ios", "device_id": "dev-2"}
    r1 = await client.post("/push/register", json=payload, headers=auth_headers)
    r2 = await client.post("/push/register", json=payload, headers=auth_headers)
    assert r1.status_code == 200 and r2.status_code == 200

    listing = await client.get("/push", headers=auth_headers)
    items = listing.json()["items"]
    # Same (user, token) pair must not create a duplicate row.
    assert len(items) == 1


async def test_unregister_token(client, auth_headers):
    payload = {"token": "expo-push-token-unreg", "platform": "web"}
    await client.post("/push/register", json=payload, headers=auth_headers)

    r = await client.post("/push/unregister", json=payload, headers=auth_headers)
    assert r.status_code == 204

    listing = await client.get("/push", headers=auth_headers)
    assert listing.json()["items"] == []


async def test_unregister_unknown_token_404(client, auth_headers):
    r = await client.post(
        "/push/unregister",
        json={"token": "never-registered-token", "platform": "android"},
        headers=auth_headers,
    )
    assert r.status_code == 404
