"""Trip lifecycle + manifest + cash-up flow tests."""

from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId

# Helpers
async def _seed_trip_context(client, db, super_admin, branch, headers):
    """Create a route, vehicle, driver, conductor in the same branch.
    Returns dict with their ids."""
    # Create a second branch so route is valid
    second = await client.post(
        "/branches",
        headers=headers,
        json={
            "name": "Dest",
            "code": "DST-01",
            "city": "DC",
            "state": "DS",
            "address": "1 Dest Rd",
            "status": "active",
        },
    )
    second_id = second.json()["data"]["id"]

    route = await client.post(
        "/routes",
        headers=headers,
        json={
            "name": "Origin → Dest",
            "branch_id": str(branch["_id"]),
            "type": "interstate",
            "origin_branch_id": str(branch["_id"]),
            "destination_branch_id": second_id,
            "origin_city": "OC",
            "destination_city": "DC",
            "distance_km": 100.0,
            "base_fare_passenger": 1000.0,
            "base_fare_cargo_per_kg": 50.0,
            "estimated_duration_hours": 2.0,
            "intermediate_stops": [],
            "required_permits": [],
        },
    )
    route_id = route.json()["data"]["id"]

    vehicle = await client.post(
        "/vehicles",
        headers=headers,
        json={
            "reg_number": "TRP-V-1",
            "type": "bus",
            "capacity_seats": 40,
            "capacity_kg": 3000,
            "branch_id": str(branch["_id"]),
        },
    )
    vehicle_id = vehicle.json()["data"]["id"]

    driver_user = await client.post(
        "/users",
        headers=headers,
        json={
            "email": "tripd@transitos.app",
            "full_name": "Trip Driver",
            "role": "driver",
            "branch_id": str(branch["_id"]),
            "password": "DrvPass#12345",
        },
    )
    driver_user_id = driver_user.json()["data"]["id"]
    driver = await client.post(
        "/drivers",
        headers=headers,
        json={
            "user_id": driver_user_id,
            "license_no": "TRP-LIC-1",
            "license_expiry": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
            "years_experience": 3,
        },
    )
    driver_id = driver.json()["data"]["id"]

    conductor_user = await client.post(
        "/users",
        headers=headers,
        json={
            "email": "tripc@transitos.app",
            "full_name": "Trip Conductor",
            "role": "conductor",
            "branch_id": str(branch["_id"]),
            "password": "CndPass#12345",
        },
    )
    conductor_user_id = conductor_user.json()["data"]["id"]
    conductor = await client.post(
        "/conductors",
        headers=headers,
        json={
            "user_id": conductor_user_id,
            "badge_no": "TRP-BDG-1",
        },
    )
    conductor_id = conductor.json()["data"]["id"]

    return {
        "route_id": route_id,
        "vehicle_id": vehicle_id,
        "driver_id": driver_id,
        "conductor_id": conductor_id,
    }


@pytest.mark.asyncio
async def test_create_trip_happy(client, auth_headers, branch):
    ctx = await _seed_trip_context(client, None, None, branch, auth_headers)
    now = datetime.now(timezone.utc)
    r = await client.post(
        "/trips",
        headers=auth_headers,
        json={
            "route_id": ctx["route_id"],
            "vehicle_id": ctx["vehicle_id"],
            "driver_id": ctx["driver_id"],
            "conductor_id": ctx["conductor_id"],
            "branch_id": str(branch["_id"]),
            "scheduled_departure": (now + timedelta(hours=1)).isoformat(),
            "scheduled_arrival": (now + timedelta(hours=3)).isoformat(),
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()["data"]
    assert body["status"] == "planned"


@pytest.mark.asyncio
async def test_create_trip_arrival_before_departure_fails(client, auth_headers, branch):
    ctx = await _seed_trip_context(client, None, None, branch, auth_headers)
    now = datetime.now(timezone.utc)
    r = await client.post(
        "/trips",
        headers=auth_headers,
        json={
            "route_id": ctx["route_id"],
            "vehicle_id": ctx["vehicle_id"],
            "driver_id": ctx["driver_id"],
            "conductor_id": ctx["conductor_id"],
            "branch_id": str(branch["_id"]),
            "scheduled_departure": (now + timedelta(hours=3)).isoformat(),
            "scheduled_arrival": (now + timedelta(hours=1)).isoformat(),
        },
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_trip_state_machine_full_flow(client, auth_headers, branch):
    ctx = await _seed_trip_context(client, None, None, branch, auth_headers)
    now = datetime.now(timezone.utc)
    r = await client.post(
        "/trips",
        headers=auth_headers,
        json={
            "route_id": ctx["route_id"],
            "vehicle_id": ctx["vehicle_id"],
            "driver_id": ctx["driver_id"],
            "conductor_id": ctx["conductor_id"],
            "branch_id": str(branch["_id"]),
            "scheduled_departure": (now + timedelta(hours=1)).isoformat(),
            "scheduled_arrival": (now + timedelta(hours=3)).isoformat(),
        },
    )
    trip_id = r.json()["data"]["id"]

    # Add manifest entries
    for i, fare in enumerate([1000.0, 1500.0, 2000.0]):
        r = await client.post(
            f"/trips/{trip_id}/manifest",
            headers=auth_headers,
            json={
                "trip_id": trip_id,
                "type": "passenger",
                "passenger_name": f"Pax {i+1}",
                "fare": fare,
                "payment_status": "paid",
            },
        )
        assert r.status_code == 201

    # Trip totals
    r = await client.get(f"/trips/{trip_id}", headers=auth_headers)
    body = r.json()["data"]
    assert body["passenger_count"] == 3
    assert body["total_revenue"] == 4500.0

    # Transition: planned → boarding → departed
    r = await client.patch(
        f"/trips/{trip_id}/status",
        headers=auth_headers,
        json={"status": "boarding"},
    )
    assert r.status_code == 200
    r = await client.patch(
        f"/trips/{trip_id}/status",
        headers=auth_headers,
        json={"status": "departed"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["actual_departure"] is not None

    # Departed → arrived → closed
    r = await client.patch(
        f"/trips/{trip_id}/status", headers=auth_headers, json={"status": "arrived"}
    )
    assert r.status_code == 200
    r = await client.patch(
        f"/trips/{trip_id}/status", headers=auth_headers, json={"status": "closed"}
    )
    assert r.status_code == 200

    # Now create a cash-up
    r = await client.post(
        "/cash-ups",
        headers=auth_headers,
        json={
            "trip_id": trip_id,
            "conductor_id": ctx["conductor_id"],
            "branch_id": str(branch["_id"]),
            "breakdown": [{"method": "cash", "amount": 4500.0}],
            "declared_total": 4500.0,
        },
    )
    assert r.status_code == 201, r.text
    cu_id = r.json()["data"]["id"]

    # Submit it
    r = await client.post(f"/cash-ups/{cu_id}/submit", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["status"] == "submitted"
    assert body["expected_total"] == 4500.0
    assert body["variance"] == 0.0

    # Approve it
    r = await client.post(f"/cash-ups/{cu_id}/approve", headers=auth_headers, json={})
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "approved"

    # Trip should now be cashed_up
    r = await client.get(f"/trips/{trip_id}", headers=auth_headers)
    assert r.json()["data"]["status"] == "cashed_up"


@pytest.mark.asyncio
async def test_invalid_state_transition_rejected(client, auth_headers, branch):
    ctx = await _seed_trip_context(client, None, None, branch, auth_headers)
    now = datetime.now(timezone.utc)
    r = await client.post(
        "/trips",
        headers=auth_headers,
        json={
            "route_id": ctx["route_id"],
            "vehicle_id": ctx["vehicle_id"],
            "driver_id": ctx["driver_id"],
            "conductor_id": ctx["conductor_id"],
            "branch_id": str(branch["_id"]),
            "scheduled_departure": (now + timedelta(hours=1)).isoformat(),
            "scheduled_arrival": (now + timedelta(hours=3)).isoformat(),
        },
    )
    trip_id = r.json()["data"]["id"]
    # Can't go from planned directly to departed
    r = await client.patch(
        f"/trips/{trip_id}/status", headers=auth_headers, json={"status": "departed"}
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_cash_up_with_variance(client, auth_headers, branch):
    ctx = await _seed_trip_context(client, None, None, branch, auth_headers)
    now = datetime.now(timezone.utc)
    r = await client.post(
        "/trips",
        headers=auth_headers,
        json={
            "route_id": ctx["route_id"],
            "vehicle_id": ctx["vehicle_id"],
            "driver_id": ctx["driver_id"],
            "conductor_id": ctx["conductor_id"],
            "branch_id": str(branch["_id"]),
            "scheduled_departure": (now + timedelta(hours=1)).isoformat(),
            "scheduled_arrival": (now + timedelta(hours=3)).isoformat(),
        },
    )
    trip_id = r.json()["data"]["id"]
    # Add manifest totalling 4000
    for i, fare in enumerate([1000.0, 1500.0, 1500.0]):
        await client.post(
            f"/trips/{trip_id}/manifest",
            headers=auth_headers,
            json={
                "trip_id": trip_id,
                "type": "passenger",
                "passenger_name": f"P{i}",
                "fare": fare,
                "payment_status": "paid",
            },
        )
    # Move to closed
    for s in ("boarding", "departed", "arrived", "closed"):
        r = await client.patch(
            f"/trips/{trip_id}/status", headers=auth_headers, json={"status": s}
        )
        assert r.status_code == 200, f"{s}: {r.text}"

    # Conductor declares 3700 (shortage of 300)
    r = await client.post(
        "/cash-ups",
        headers=auth_headers,
        json={
            "trip_id": trip_id,
            "conductor_id": ctx["conductor_id"],
            "branch_id": str(branch["_id"]),
            "breakdown": [{"method": "cash", "amount": 3700.0}],
            "declared_total": 3700.0,
        },
    )
    cu_id = r.json()["data"]["id"]
    r = await client.post(f"/cash-ups/{cu_id}/submit", headers=auth_headers)
    body = r.json()["data"]
    assert body["expected_total"] == 4000.0
    assert body["variance"] == -300.0


@pytest.mark.asyncio
async def test_breakdown_sum_mismatch_rejected(client, auth_headers, branch):
    ctx = await _seed_trip_context(client, None, None, branch, auth_headers)
    now = datetime.now(timezone.utc)
    r = await client.post(
        "/trips",
        headers=auth_headers,
        json={
            "route_id": ctx["route_id"],
            "vehicle_id": ctx["vehicle_id"],
            "driver_id": ctx["driver_id"],
            "conductor_id": ctx["conductor_id"],
            "branch_id": str(branch["_id"]),
            "scheduled_departure": (now + timedelta(hours=1)).isoformat(),
            "scheduled_arrival": (now + timedelta(hours=3)).isoformat(),
        },
    )
    trip_id = r.json()["data"]["id"]
    for s in ("boarding", "departed", "arrived", "closed"):
        r = await client.patch(
            f"/trips/{trip_id}/status", headers=auth_headers, json={"status": s}
        )
        assert r.status_code == 200
    r = await client.post(
        "/cash-ups",
        headers=auth_headers,
        json={
            "trip_id": trip_id,
            "conductor_id": ctx["conductor_id"],
            "branch_id": str(branch["_id"]),
            "breakdown": [{"method": "cash", "amount": 1000.0}],
            "declared_total": 2000.0,  # mismatch
        },
    )
    assert r.status_code == 400
