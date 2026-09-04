"""Vehicle / Driver / Conductor CRUD tests."""

from datetime import datetime, timedelta, timezone

import pytest


# ─── Vehicles ────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_create_vehicle(client, auth_headers, branch):
    r = await client.post(
        "/vehicles",
        headers=auth_headers,
        json={
            "reg_number": "TST-V-001",
            "type": "bus",
            "capacity_seats": 40,
            "capacity_kg": 3000,
            "branch_id": str(branch["_id"]),
            "status": "available",
            "current_odometer_km": 0,
            "current_fuel_level": 100.0,
        },
    )
    assert r.status_code == 201
    body = r.json()["data"]
    assert body["reg_number"] == "TST-V-001"


@pytest.mark.asyncio
async def test_create_vehicle_duplicate_reg(client, auth_headers, branch):
    payload = {
        "reg_number": "DUP-001",
        "type": "bus",
        "capacity_seats": 30,
        "capacity_kg": 2000,
        "branch_id": str(branch["_id"]),
    }
    r1 = await client.post("/vehicles", headers=auth_headers, json=payload)
    assert r1.status_code == 201
    r2 = await client.post("/vehicles", headers=auth_headers, json=payload)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_list_vehicles(client, auth_headers, branch):
    await client.post(
        "/vehicles",
        headers=auth_headers,
        json={
            "reg_number": "LST-1",
            "type": "bus",
            "capacity_seats": 30,
            "capacity_kg": 2000,
            "branch_id": str(branch["_id"]),
        },
    )
    r = await client.get("/vehicles", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["total"] >= 1


# ─── Drivers ─────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_create_driver(client, auth_headers, branch, driver_user):
    r = await client.post(
        "/drivers",
        headers=auth_headers,
        json={
            "user_id": str(driver_user["_id"]),
            "license_no": "TST-LIC-001",
            "license_expiry": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
            "years_experience": 5,
            "status": "active",
        },
    )
    assert r.status_code == 201
    body = r.json()["data"]
    assert body["branch_id"] == str(branch["_id"])


@pytest.mark.asyncio
async def test_create_driver_duplicate_license(client, auth_headers, branch, driver_user):
    from app.services.auth import hash_password
    from bson import ObjectId
    from datetime import datetime, timezone

    other_user = await client.post(
        "/users",
        headers=auth_headers,
        json={
            "email": "d2@transitos.app",
            "full_name": "Driver 2",
            "role": "driver",
            "branch_id": str(branch["_id"]),
            "password": "DrPass#12345",
        },
    )
    other_id = other_user.json()["data"]["id"]

    payload = {
        "user_id": str(driver_user["_id"]),
        "license_no": "SAME-LIC",
        "license_expiry": "2030-01-01T00:00:00Z",
    }
    r1 = await client.post("/drivers", headers=auth_headers, json=payload)
    assert r1.status_code == 201

    payload2 = {**payload, "user_id": other_id}
    r2 = await client.post("/drivers", headers=auth_headers, json=payload2)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_create_driver_wrong_user_role(client, auth_headers, branch):
    # super_admin is not driver/conductor
    r = await client.post(
        "/auth/login",
        json={"email": "admin@transitos.app", "password": "Admin#12345"},
    )
    sa_id = r.json()["data"]["access_token"]
    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {sa_id}"})
    sa_user_id = me.json()["data"]["id"]
    r2 = await client.post(
        "/drivers",
        headers=auth_headers,
        json={
            "user_id": sa_user_id,
            "license_no": "X-001",
            "license_expiry": "2030-01-01T00:00:00Z",
        },
    )
    assert r2.status_code == 400


# ─── Conductors ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_create_conductor(client, auth_headers, branch):
    # create a user with conductor role first
    r = await client.post(
        "/users",
        headers=auth_headers,
        json={
            "email": "cond1@transitos.app",
            "full_name": "Cond One",
            "role": "conductor",
            "branch_id": str(branch["_id"]),
            "password": "CondPass#12345",
        },
    )
    user_id = r.json()["data"]["id"]
    r2 = await client.post(
        "/conductors",
        headers=auth_headers,
        json={"user_id": user_id, "badge_no": "TST-B-001", "status": "active"},
    )
    assert r2.status_code == 201
    body = r2.json()["data"]
    assert body["badge_no"] == "TST-B-001"
    assert body["branch_id"] == str(branch["_id"])


@pytest.mark.asyncio
async def test_conductor_duplicate_badge(client, auth_headers, branch):
    r = await client.post(
        "/users",
        headers=auth_headers,
        json={
            "email": "c1@transitos.app",
            "full_name": "C1",
            "role": "conductor",
            "branch_id": str(branch["_id"]),
            "password": "CondPass#12345",
        },
    )
    u1 = r.json()["data"]["id"]
    r = await client.post(
        "/users",
        headers=auth_headers,
        json={
            "email": "c2@transitos.app",
            "full_name": "C2",
            "role": "conductor",
            "branch_id": str(branch["_id"]),
            "password": "CondPass#12346",
        },
    )
    u2 = r.json()["data"]["id"]
    await client.post(
        "/conductors", headers=auth_headers,
        json={"user_id": u1, "badge_no": "DUP-BDG"},
    )
    r2 = await client.post(
        "/conductors", headers=auth_headers,
        json={"user_id": u2, "badge_no": "DUP-BDG"},
    )
    assert r2.status_code == 409
