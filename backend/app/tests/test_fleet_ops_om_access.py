"""Tests for the FLEET_OPS fix: Operations Manager can create/update
vehicles, drivers, conductors, and routes, matching the access every
fleet-setup screen's frontend creator-role list already assumed (and
the local workaround vehicle_transfers.py had to carry until now).
"""

from __future__ import annotations

import pytest
from app.tests.conftest import _create_user

pytestmark = pytest.mark.asyncio


async def _om_headers(client, db):
    await _create_user(db, email="om-fleet@transitos.app", role="operations_manager", password="Om#1234567")
    r = await client.post("/auth/login", json={"email": "om-fleet@transitos.app", "password": "Om#1234567"})
    assert r.status_code == 200, r.text
    token = r.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_om_can_create_vehicle(client, db, branch):
    om_headers = await _om_headers(client, db)
    r = await client.post(
        "/vehicles",
        headers=om_headers,
        json={
            "reg_number": "OM-V-001",
            "type": "bus",
            "capacity_seats": 40,
            "capacity_kg": 3000,
            "branch_id": str(branch["_id"]),
            "status": "available",
        },
    )
    assert r.status_code == 201, r.text


async def test_om_can_update_vehicle(client, db, branch):
    om_headers = await _om_headers(client, db)
    create = await client.post(
        "/vehicles",
        headers=om_headers,
        json={
            "reg_number": "OM-V-002",
            "type": "bus",
            "capacity_seats": 40,
            "capacity_kg": 3000,
            "branch_id": str(branch["_id"]),
            "status": "available",
        },
    )
    vehicle_id = create.json()["data"]["id"]
    r = await client.patch(
        f"/vehicles/{vehicle_id}", headers=om_headers, json={"status": "maintenance"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["status"] == "maintenance"


async def test_om_can_create_route(client, db, branch):
    om_headers = await _om_headers(client, db)
    branch2_doc = {
        "name": "Second Branch", "code": "SB2", "city": "City B", "state": "State B",
        "address": "Addr", "contact_phone": None, "contact_email": None, "gps": None,
        "bank_account": None, "status": "active", "is_active": True,
    }
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    branch2_doc["created_at"] = now
    branch2_doc["updated_at"] = now
    result = await db.branches.insert_one(branch2_doc)

    r = await client.post(
        "/routes",
        headers=om_headers,
        json={
            "name": "OM Test Route",
            "branch_id": str(branch["_id"]),
            "type": "intrastate",
            "origin_branch_id": str(branch["_id"]),
            "destination_branch_id": str(result.inserted_id),
            "origin_city": "City A",
            "destination_city": "City B",
            "distance_km": 50,
            "base_fare_passenger": 1000,
            "base_fare_cargo_per_kg": 50,
            "estimated_duration_hours": 1.5,
        },
    )
    assert r.status_code == 201, r.text


async def test_om_can_create_driver(client, db, branch, driver_user):
    om_headers = await _om_headers(client, db)
    from datetime import datetime, timedelta, timezone
    r = await client.post(
        "/drivers",
        headers=om_headers,
        json={
            "user_id": str(driver_user["_id"]),
            "license_no": "OM-LIC-001",
            "license_expiry": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
            "years_experience": 2,
            "status": "active",
        },
    )
    assert r.status_code == 201, r.text
