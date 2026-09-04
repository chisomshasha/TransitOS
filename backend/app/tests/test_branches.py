"""Branch CRUD tests + RBAC scoping."""

import pytest


@pytest.mark.asyncio
async def test_create_branch(client, auth_headers):
    r = await client.post(
        "/branches",
        headers=auth_headers,
        json={
            "name": "New Branch",
            "code": "NEW-01",
            "city": "Lagos",
            "state": "Lagos",
            "address": "2 Marina Road",
            "status": "active",
        },
    )
    assert r.status_code == 201
    body = r.json()["data"]
    assert body["code"] == "NEW-01"
    assert body["is_active"] is True


@pytest.mark.asyncio
async def test_create_branch_duplicate_code(client, auth_headers, branch):
    r = await client.post(
        "/branches",
        headers=auth_headers,
        json={
            "name": "Dup Branch",
            "code": "TST-01",  # already exists
            "city": "XC",
            "state": "YK",
            "address": "123 Test Street",
            "status": "active",
        },
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_list_branches_paginated(client, auth_headers, branch):
    r = await client.get("/branches?page=1&page_size=10", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert body["total"] >= 1
    assert body["page"] == 1


@pytest.mark.asyncio
async def test_get_branch(client, auth_headers, branch):
    r = await client.get(f"/branches/{branch['_id']}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["data"]["code"] == "TST-01"


@pytest.mark.asyncio
async def test_update_branch(client, auth_headers, branch):
    r = await client.patch(
        f"/branches/{branch['_id']}",
        headers=auth_headers,
        json={"contact_phone": "+234-800-9999"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["contact_phone"] == "+234-800-9999"


@pytest.mark.asyncio
async def test_delete_branch_blocked_when_linked(
    client, auth_headers, branch, branch_manager
):
    r = await client.delete(f"/branches/{branch['_id']}", headers=auth_headers)
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_set_branch_manager(client, auth_headers, branch, branch_manager):
    r = await client.post(
        f"/branches/{branch['_id']}/manager",
        headers=auth_headers,
        json={"manager_id": str(branch_manager["_id"])},
    )
    assert r.status_code == 200
    assert r.json()["data"]["manager_id"] == str(branch_manager["_id"])


@pytest.mark.asyncio
async def test_branch_rbac_blocked_for_driver(client, driver_user):
    r = await client.post(
        "/auth/login",
        json={"email": "driver@transitos.app", "password": "Dr#1234567"},
    )
    token = r.json()["data"]["access_token"]
    r2 = await client.get("/branches", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 403
