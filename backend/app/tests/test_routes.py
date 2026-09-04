"""Route CRUD tests."""

import pytest


@pytest.mark.asyncio
async def test_create_route_rejects_same_origin_destination(client, auth_headers, branch):
    """origin_branch_id == destination_branch_id is rejected (no-op route)."""
    r = await client.post(
        "/routes",
        headers=auth_headers,
        json={
            "name": "No-op route",
            "branch_id": str(branch["_id"]),
            "type": "intrastate",
            "origin_branch_id": str(branch["_id"]),
            "destination_branch_id": str(branch["_id"]),
            "origin_city": "Same",
            "destination_city": "Same",
            "distance_km": 0.0,
            "base_fare_passenger": 0.0,
            "base_fare_cargo_per_kg": 0.0,
            "estimated_duration_hours": 0.0,
            "intermediate_stops": [],
            "required_permits": [],
            "is_active": True,
        },
    )
    assert r.status_code == 400
    assert "destination_branch_id" in r.text or "differ" in r.text


@pytest.mark.asyncio
async def test_create_route_happy(client, auth_headers, branch):
    from bson import ObjectId
    from datetime import datetime, timezone

    # create a second branch
    now = datetime.now(timezone.utc)
    second = await client.post(
        "/branches",
        headers=auth_headers,
        json={
            "name": "Branch 2",
            "code": "BR-02",
            "city": "Ibadan",
            "state": "Oyo",
            "address": "1 Bodija Rd",
            "status": "active",
        },
    )
    branch2_id = second.json()["data"]["_id"] if "_id" in second.json()["data"] else second.json()["data"]["id"]

    r = await client.post(
        "/routes",
        headers=auth_headers,
        json={
            "name": "Lagos → Ibadan",
            "branch_id": str(branch["_id"]),
            "type": "interstate",
            "origin_branch_id": str(branch["_id"]),
            "destination_branch_id": branch2_id,
            "origin_city": "Lagos",
            "destination_city": "Ibadan",
            "distance_km": 120.0,
            "base_fare_passenger": 2500.0,
            "base_fare_cargo_per_kg": 50.0,
            "estimated_duration_hours": 2.5,
            "intermediate_stops": [
                {
                    "name": "Sagamu",
                    "lat": 6.84,
                    "lng": 3.64,
                    "eta_minutes": 45,
                }
            ],
            "required_permits": ["interstate_license"],
            "is_active": True,
        },
    )
    assert r.status_code == 201
    body = r.json()["data"]
    assert body["name"] == "Lagos → Ibadan"
    assert len(body["intermediate_stops"]) == 1


@pytest.mark.asyncio
async def test_list_routes_paginated(client, auth_headers, branch):
    r = await client.get("/routes?page=1&page_size=10", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["page"] == 1


@pytest.mark.asyncio
async def test_route_rbac_driver_forbidden(client, driver_user):
    r = await client.post(
        "/auth/login",
        json={"email": "driver@transitos.app", "password": "Dr#1234567"},
    )
    token = r.json()["data"]["access_token"]
    r2 = await client.get("/routes", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 403
