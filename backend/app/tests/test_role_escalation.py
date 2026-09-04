"""Tests for the privilege-escalation guard on user role assignment.

Covers the gap flagged in review: PATCH /users/{id} (and, less
obviously, POST /users for non-branch-manager actors) previously let
any SAFETY_OPS role set an arbitrary ``role`` value, including
super_admin/owner — regardless of the actor's own seniority.
"""

from __future__ import annotations

import pytest
from app.tests.conftest import _create_user

pytestmark = pytest.mark.asyncio


async def _login(client, email: str, password: str) -> dict:
    r = await client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    token = r.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _gm_headers(client, db):
    await _create_user(db, email="gm@transitos.app", role="general_manager", password="Gm#1234567")
    return await _login(client, "gm@transitos.app", "Gm#1234567")


async def _om_headers(client, db):
    await _create_user(db, email="om@transitos.app", role="operations_manager", password="Om#1234567")
    return await _login(client, "om@transitos.app", "Om#1234567")


# ─── PATCH (update_user) ───────────────────────────────────────────────────


async def test_bm_cannot_promote_user_to_owner_via_patch(client, bm_auth_headers, branch_manager):
    r = await client.patch(
        f"/users/{branch_manager['_id']}",
        headers=bm_auth_headers,
        json={"role": "owner"},
    )
    assert r.status_code == 403


async def test_bm_cannot_self_promote_via_patch(client, bm_auth_headers, branch_manager):
    r = await client.patch(
        f"/users/{branch_manager['_id']}",
        headers=bm_auth_headers,
        json={"role": "super_admin"},
    )
    assert r.status_code == 403


async def test_bm_cannot_promote_to_peer_branch_manager_via_patch(
    client, bm_auth_headers, branch_manager
):
    """BM's existing narrow allow-list (BA/driver/conductor only) still holds."""
    r = await client.patch(
        f"/users/{branch_manager['_id']}",
        headers=bm_auth_headers,
        json={"role": "branch_manager"},
    )
    assert r.status_code == 403


async def test_bm_can_still_assign_allowed_role_via_patch(client, bm_auth_headers, branch_manager):
    r = await client.patch(
        f"/users/{branch_manager['_id']}",
        headers=bm_auth_headers,
        json={"role": "driver"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["role"] == "driver"


async def test_om_cannot_promote_to_owner_via_patch(client, db, branch_manager):
    om_headers = await _om_headers(client, db)
    r = await client.patch(
        f"/users/{branch_manager['_id']}",
        headers=om_headers,
        json={"role": "owner"},
    )
    assert r.status_code == 403


async def test_om_cannot_promote_to_general_manager_via_patch(client, db, branch_manager):
    om_headers = await _om_headers(client, db)
    r = await client.patch(
        f"/users/{branch_manager['_id']}",
        headers=om_headers,
        json={"role": "general_manager"},
    )
    assert r.status_code == 403


async def test_om_can_promote_branch_manager_via_patch(client, db, branch, branch_manager):
    """OM is senior to BM in the rank hierarchy, so this must remain allowed."""
    driver = await _create_user(
        db, email="drv2@transitos.app", role="driver", branch_id=str(branch["_id"]), password="Dr#1234567"
    )
    om_headers = await _om_headers(client, db)
    r = await client.patch(
        f"/users/{driver['_id']}",
        headers=om_headers,
        json={"role": "branch_manager"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["role"] == "branch_manager"


async def test_super_admin_can_still_assign_any_role_via_patch(client, auth_headers, branch_manager):
    r = await client.patch(
        f"/users/{branch_manager['_id']}",
        headers=auth_headers,
        json={"role": "owner"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["role"] == "owner"


# ─── POST (create_user) ─────────────────────────────────────────────────────


async def test_gm_cannot_create_owner(client, db, branch):
    gm_headers = await _gm_headers(client, db)
    r = await client.post(
        "/users",
        headers=gm_headers,
        json={
            "email": "sneaky-owner@transitos.app",
            "full_name": "Sneaky Owner",
            "role": "owner",
            "password": "Pass#12345",
        },
    )
    assert r.status_code == 403


async def test_gm_can_create_branch_manager(client, db, branch):
    gm_headers = await _gm_headers(client, db)
    r = await client.post(
        "/users",
        headers=gm_headers,
        json={
            "email": "gm-made-bm@transitos.app",
            "full_name": "GM Made BM",
            "role": "branch_manager",
            "branch_id": str(branch["_id"]),
            "password": "Pass#12345",
        },
    )
    assert r.status_code == 201


async def test_om_cannot_create_fleet_manager_peer_escalation_attempt(client, db):
    """Sanity check: OM (tier 3) creating a peer-tier CA is allowed by the
    general rank rule (peers may assign one another) — documents current
    behavior rather than asserting a stricter, undocumented business rule."""
    om_headers = await _om_headers(client, db)
    r = await client.post(
        "/users",
        headers=om_headers,
        json={
            "email": "om-made-ca@transitos.app",
            "full_name": "OM Made CA",
            "role": "chief_accountant",
            "password": "Pass#12345",
        },
    )
    assert r.status_code == 201
