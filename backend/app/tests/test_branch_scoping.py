"""Multi-branch isolation tests.

Guarantees that a branch_manager (and branch_accountant) can only see / mutate
resources that belong to their own branch, while owner / GM retain global access.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.fixture
async def bm_token(client, branch_manager) -> str:
    """Login as the branch_manager fixture user and return the access token."""
    r = await client.post(
        "/auth/login",
        json={"email": "bm@transitos.app", "password": "Bm#1234567"},
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_bm_cannot_list_other_branch_users(
    client: AsyncClient, bm_token, branch_manager, other_branch_user
):
    """BM list is forced to their own branch_id."""
    headers = {"Authorization": f"Bearer {bm_token}"}
    r = await client.get("/users", headers=headers)
    assert r.status_code == 200
    emails = {u["email"] for u in r.json()["items"]}
    assert other_branch_user["email"] not in emails


@pytest.mark.asyncio
async def test_bm_cannot_get_other_branch_user(
    client: AsyncClient, bm_token, other_branch_user
):
    headers = {"Authorization": f"Bearer {bm_token}"}
    r = await client.get(f"/users/{other_branch_user['id']}", headers=headers)
    assert r.status_code in (403, 404)


@pytest.mark.asyncio
async def test_bm_cannot_create_user_in_other_branch(
    client: AsyncClient, bm_token, other_branch
):
    headers = {"Authorization": f"Bearer {bm_token}"}
    r = await client.post(
        "/users",
        headers=headers,
        json={
            "email": "intruder@transitos.app",
            "full_name": "Intruder",
            "role": "driver",
            "branch_id": other_branch["id"],
            "password": "Driver#Transit2026!",
        },
    )
    assert r.status_code in (400, 403)


@pytest.mark.asyncio
async def test_bm_trip_list_scoped(
    client: AsyncClient, bm_token, other_branch_trip
):
    headers = {"Authorization": f"Bearer {bm_token}"}
    r = await client.get("/trips", headers=headers)
    assert r.status_code == 200
    trip_ids = {t["id"] for t in r.json()["items"]}
    assert other_branch_trip["id"] not in trip_ids


@pytest.mark.asyncio
async def test_owner_sees_all_branches(client: AsyncClient, owner, branch_a, branch_b):
    headers = {"Authorization": f"Bearer {owner['access_token']}"}
    r = await client.get("/branches", headers=headers)
    assert r.status_code == 200
    codes = {b["code"] for b in r.json()["items"]}
    assert branch_a["code"] in codes
    assert branch_b["code"] in codes


@pytest.mark.asyncio
async def test_lockout_after_repeated_failures(client: AsyncClient, super_admin):
    """5 bad passwords → temporary lock (403)."""
    email = super_admin["email"] if isinstance(super_admin, dict) else "admin@transitos.app"
    # super_admin fixture returns the user doc with email
    email = super_admin.get("email", "admin@transitos.app") if isinstance(super_admin, dict) else "admin@transitos.app"
    for _ in range(5):
        r = await client.post(
            "/auth/login",
            json={"email": email, "password": "definitely-wrong-password"},
        )
        assert r.status_code in (401, 403)
    r = await client.post(
        "/auth/login",
        json={"email": email, "password": "definitely-wrong-password"},
    )
    assert r.status_code == 403
    assert "locked" in r.json()["detail"].lower()
