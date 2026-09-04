"""User CRUD + RBAC branch-scoping tests."""

import pytest


@pytest.mark.asyncio
async def test_create_user_duplicate_email(client, auth_headers, super_admin):
    r = await client.post(
        "/users",
        headers=auth_headers,
        json={
            "email": "admin@transitos.app",
            "full_name": "Another Admin",
            "role": "owner",
            "password": "NewPass#12345",
        },
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_create_user_branch_required_for_branch_role(
    client, auth_headers
):
    r = await client.post(
        "/users",
        headers=auth_headers,
        json={
            "email": "bm1@transitos.app",
            "full_name": "Branch Manager",
            "role": "branch_manager",
            # no branch_id — should fail validation
            "password": "Pass#12345",
        },
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_create_user_happy_path(client, auth_headers, branch):
    r = await client.post(
        "/users",
        headers=auth_headers,
        json={
            "email": "newbm@transitos.app",
            "full_name": "New BM",
            "role": "branch_manager",
            "branch_id": str(branch["_id"]),
            "password": "Pass#12345",
        },
    )
    assert r.status_code == 201
    body = r.json()["data"]
    assert body["email"] == "newbm@transitos.app"
    assert body["branch_id"] == str(branch["_id"])


@pytest.mark.asyncio
async def test_list_users_paginated(client, auth_headers, super_admin, branch_manager):
    r = await client.get("/users?page=1&page_size=10", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 2  # sa + bm


@pytest.mark.asyncio
async def test_bm_only_sees_own_branch_users(
    client, bm_auth_headers, branch, super_admin
):
    # Create a user in another branch
    from app.services.auth import hash_password
    from datetime import datetime, timezone

    from bson import ObjectId

    other_branch_id = ObjectId()
    await client.post(
        "/users",
        headers={
            "Authorization": f"Bearer {(await client.post('/auth/login', json={'email': 'admin@transitos.app', 'password': 'Admin#12345'})).json()['data']['access_token']}"
        },
        json={
            "email": "other@transitos.app",
            "full_name": "Other User",
            "role": "branch_manager",
            "branch_id": str(other_branch_id),
            "password": "Pass#12345",
        },
    )
    # BM lists users → should not see the other-branch one
    r = await client.get("/users", headers=bm_auth_headers)
    assert r.status_code == 200
    emails = [u["email"] for u in r.json()["items"]]
    assert "other@transitos.app" not in emails
    assert "bm@transitos.app" in emails


@pytest.mark.asyncio
async def test_update_user(client, auth_headers, branch_manager):
    r = await client.patch(
        f"/users/{branch_manager['_id']}",
        headers=auth_headers,
        json={"phone": "+234-800-7777"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["phone"] == "+234-800-7777"


@pytest.mark.asyncio
async def test_admin_reset_password_via_patch(client, auth_headers, branch_manager):
    """PATCH /users/{id} with new_password must accept StrongPassword and revoke tokens."""
    # Weak password rejected by schema
    r_weak = await client.patch(
        f"/users/{branch_manager['_id']}",
        headers=auth_headers,
        json={"new_password": "weak"},
    )
    assert r_weak.status_code == 400

    # Strong password accepted
    r = await client.patch(
        f"/users/{branch_manager['_id']}",
        headers=auth_headers,
        json={"new_password": "ResetPass#98765"},
    )
    assert r.status_code == 200

    # Old password no longer works
    r_old = await client.post(
        "/auth/login",
        json={"email": "bm@transitos.app", "password": "Bm#1234567"},
    )
    assert r_old.status_code == 401

    # New password works
    r_new = await client.post(
        "/auth/login",
        json={"email": "bm@transitos.app", "password": "ResetPass#98765"},
    )
    assert r_new.status_code == 200
    assert "access_token" in r_new.json()["data"]


@pytest.mark.asyncio
async def test_cannot_delete_self(client, auth_headers, super_admin):
    r = await client.delete(f"/users/{super_admin['_id']}", headers=auth_headers)
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_soft_delete_user(client, auth_headers, branch_manager):
    r = await client.delete(f"/users/{branch_manager['_id']}", headers=auth_headers)
    assert r.status_code == 204
    # Login should now fail
    r2 = await client.post(
        "/auth/login",
        json={"email": "bm@transitos.app", "password": "Bm#1234567"},
    )
    assert r2.status_code == 403  # account is deactivated
