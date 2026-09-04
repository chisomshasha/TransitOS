"""Driver/conductor may list and get only trips they are assigned to."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient


async def _login(client: AsyncClient, email: str, password: str) -> str:
    r = await client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["data"]["access_token"]


@pytest.fixture
async def driver_profile(db, branch, driver_user):
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    doc = {
        "user_id": str(driver_user["_id"]),
        "license_no": "DRV-TEST-001",
        "license_expiry": now + timedelta(days=365),
        "status": "available",
        "branch_id": str(branch["_id"]),
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.drivers.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


@pytest.fixture
async def conductor_user(db, branch):
    from app.services.auth import hash_password
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    doc = {
        "email": "conductor@transitos.app",
        "full_name": "Conductor",
        "phone": None,
        "role": "conductor",
        "branch_id": str(branch["_id"]),
        "status": "active",
        "hire_date": None,
        "photo_url": None,
        "password_hash": hash_password("Co#1234567"),
        "is_active": True,
        "last_login_at": None,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.users.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


@pytest.fixture
async def conductor_profile(db, branch, conductor_user):
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    doc = {
        "user_id": str(conductor_user["_id"]),
        "badge_no": "BADGE-001",
        "status": "available",
        "branch_id": str(branch["_id"]),
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.conductors.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


@pytest.fixture
async def fleet_manager(db, branch):
    from app.services.auth import hash_password
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    doc = {
        "email": "fm@transitos.app",
        "full_name": "Fleet Manager",
        "phone": None,
        "role": "fleet_manager",
        "branch_id": str(branch["_id"]),
        "status": "active",
        "hire_date": None,
        "photo_url": None,
        "password_hash": hash_password("Fm#1234567"),
        "is_active": True,
        "last_login_at": None,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.users.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


@pytest.fixture
async def assigned_trip(db, branch, driver_profile, conductor_profile):
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    doc = {
        "route_id": "000000000000000000000001",
        "vehicle_id": "000000000000000000000002",
        "driver_id": str(driver_profile["_id"]),
        "conductor_id": str(conductor_profile["_id"]),
        "branch_id": str(branch["_id"]),
        "scheduled_departure": now + timedelta(hours=1),
        "scheduled_arrival": now + timedelta(hours=5),
        "status": "planned",
        "passenger_count": 0,
        "cargo_weight_kg": 0.0,
        "total_revenue": 0.0,
        "total_expenses": 0.0,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.trips.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


@pytest.fixture
async def other_trip(db, other_branch):
    """Trip on a different branch with different crew ids."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    doc = {
        "route_id": "000000000000000000000099",
        "vehicle_id": "000000000000000000000098",
        "driver_id": "000000000000000000000097",
        "conductor_id": "000000000000000000000096",
        "branch_id": str(other_branch["_id"]),
        "scheduled_departure": now + timedelta(hours=2),
        "scheduled_arrival": now + timedelta(hours=6),
        "status": "planned",
        "passenger_count": 0,
        "cargo_weight_kg": 0.0,
        "total_revenue": 0.0,
        "total_expenses": 0.0,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.trips.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


@pytest.mark.asyncio
async def test_driver_sees_only_assigned_trips(
    client, driver_user, driver_profile, assigned_trip, other_trip
):
    token = await _login(client, "driver@transitos.app", "Dr#1234567")
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.get("/trips", headers=headers)
    assert r.status_code == 200, r.text
    ids = {t["id"] for t in r.json()["items"]}
    assert str(assigned_trip["_id"]) in ids
    assert str(other_trip["_id"]) not in ids


@pytest.mark.asyncio
async def test_driver_get_assigned_trip_ok(
    client, driver_user, driver_profile, assigned_trip
):
    token = await _login(client, "driver@transitos.app", "Dr#1234567")
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.get(f"/trips/{assigned_trip['_id']}", headers=headers)
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_driver_get_other_trip_404(
    client, driver_user, driver_profile, other_trip
):
    token = await _login(client, "driver@transitos.app", "Dr#1234567")
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.get(f"/trips/{other_trip['_id']}", headers=headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_conductor_sees_only_assigned_trips(
    client, conductor_user, conductor_profile, assigned_trip, other_trip
):
    token = await _login(client, "conductor@transitos.app", "Co#1234567")
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.get("/trips", headers=headers)
    assert r.status_code == 200, r.text
    ids = {t["id"] for t in r.json()["items"]}
    assert str(assigned_trip["_id"]) in ids
    assert str(other_trip["_id"]) not in ids


@pytest.mark.asyncio
async def test_driver_cannot_mutate_trip(
    client, driver_user, driver_profile, assigned_trip
):
    token = await _login(client, "driver@transitos.app", "Dr#1234567")
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.patch(
        f"/trips/{assigned_trip['_id']}/status",
        headers=headers,
        json={"status": "boarding"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_fleet_manager_cannot_see_other_branch_vehicles(
    client, fleet_manager, other_branch
):
    from datetime import datetime, timezone

    db = client  # noqa — use fixture via login only
    # insert vehicle on other branch via mock db
    from app.tests.conftest import _mock_get_db

    dbh = _mock_get_db()
    now = datetime.now(timezone.utc)
    other_vehicle = {
        "reg_number": "OTH-VEH-1",
        "type": "bus",
        "branch_id": str(other_branch["_id"]),
        "status": "available",
        "capacity_seats": 40,
        "capacity_kg": 500.0,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    res = await dbh.vehicles.insert_one(other_vehicle)
    other_vehicle["_id"] = res.inserted_id

    own_vehicle = {
        "reg_number": "OWN-VEH-1",
        "type": "bus",
        "branch_id": fleet_manager["branch_id"],
        "status": "available",
        "capacity_seats": 40,
        "capacity_kg": 500.0,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    res2 = await dbh.vehicles.insert_one(own_vehicle)
    own_vehicle["_id"] = res2.inserted_id

    token = await _login(client, "fm@transitos.app", "Fm#1234567")
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.get("/vehicles", headers=headers)
    assert r.status_code == 200, r.text
    regs = {v["reg_number"] for v in r.json()["items"]}
    assert "OWN-VEH-1" in regs
    assert "OTH-VEH-1" not in regs


@pytest.mark.asyncio
async def test_fleet_manager_get_other_branch_vehicle_404(
    client, fleet_manager, other_branch
):
    from datetime import datetime, timezone
    from app.tests.conftest import _mock_get_db

    dbh = _mock_get_db()
    now = datetime.now(timezone.utc)
    other_vehicle = {
        "reg_number": "OTH-VEH-2",
        "type": "bus",
        "branch_id": str(other_branch["_id"]),
        "status": "available",
        "capacity_seats": 40,
        "capacity_kg": 500.0,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    res = await dbh.vehicles.insert_one(other_vehicle)
    vid = str(res.inserted_id)

    token = await _login(client, "fm@transitos.app", "Fm#1234567")
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.get(f"/vehicles/{vid}", headers=headers)
    assert r.status_code == 404
