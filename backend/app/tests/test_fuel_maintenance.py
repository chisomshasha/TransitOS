"""Fuel + Maintenance + Expense + Reports tests."""

from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId


async def _seed_branch_with_vehicle(client, headers, branch):
    r = await client.post(
        "/vehicles",
        headers=headers,
        json={
            "reg_number": "FUE-V-1",
            "type": "bus",
            "capacity_seats": 40,
            "capacity_kg": 3000,
            "branch_id": str(branch["_id"]),
        },
    )
    return r.json()["data"]["id"]


# ─── FuelLog ────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_fuel_log_create_and_efficiency(client, auth_headers, branch):
    vehicle_id = await _seed_branch_with_vehicle(client, auth_headers, branch)
    now = datetime.now(timezone.utc)

    # First log: 10000km, 40L
    r = await client.post(
        "/fuel-logs",
        headers=auth_headers,
        json={
            "vehicle_id": vehicle_id,
            "branch_id": str(branch["_id"]),
            "occurred_at": (now - timedelta(days=2)).isoformat(),
            "liters": 40.0,
            "cost_total": 8000.0,
            "cost_per_liter": 200.0,
            "odometer_km": 10000,
        },
    )
    assert r.status_code == 201, r.text

    # Second log: 10500km, 20L
    r = await client.post(
        "/fuel-logs",
        headers=auth_headers,
        json={
            "vehicle_id": vehicle_id,
            "branch_id": str(branch["_id"]),
            "occurred_at": now.isoformat(),
            "liters": 20.0,
            "cost_total": 4000.0,
            "cost_per_liter": 200.0,
            "odometer_km": 10500,
        },
    )
    assert r.status_code == 201, r.text

    # Efficiency
    r = await client.get(
        f"/fuel-logs/vehicle/{vehicle_id}/efficiency", headers=auth_headers
    )
    assert r.status_code == 200
    data = r.json()["data"]
    # 500km / 60L ≈ 8.33 km/L
    assert data["km_per_liter"] is not None
    assert abs(data["km_per_liter"] - 500 / 60) < 0.5
    assert data["total_liters"] == 60.0
    assert data["total_cost"] == 12000.0


# ─── Maintenance ────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_maintenance_lifecycle(client, auth_headers, branch):
    vehicle_id = await _seed_branch_with_vehicle(client, auth_headers, branch)
    now = datetime.now(timezone.utc)

    r = await client.post(
        "/maintenance",
        headers=auth_headers,
        json={
            "vehicle_id": vehicle_id,
            "branch_id": str(branch["_id"]),
            "type": "routine",
            "status": "scheduled",
            "title": "Oil change",
            "scheduled_for": (now + timedelta(days=7)).isoformat(),
        },
    )
    assert r.status_code == 201
    m_id = r.json()["data"]["id"]

    # Mark in progress
    r = await client.patch(
        f"/maintenance/{m_id}",
        headers=auth_headers,
        json={"status": "in_progress"},
    )
    assert r.status_code == 200

    # Vehicle should be in maintenance
    r = await client.get(f"/vehicles/{vehicle_id}", headers=auth_headers)
    assert r.json()["data"]["status"] == "maintenance"

    # Complete it
    r = await client.patch(
        f"/maintenance/{m_id}",
        headers=auth_headers,
        json={"status": "completed", "cost_parts": 5000.0, "cost_labor": 3000.0},
    )
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "completed"
    assert r.json()["data"]["cost_total"] == 8000.0

    # Vehicle back to available
    r = await client.get(f"/vehicles/{vehicle_id}", headers=auth_headers)
    assert r.json()["data"]["status"] == "available"


# ─── Expenses ───────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_expense_crud(client, auth_headers, branch):
    vehicle_id = await _seed_branch_with_vehicle(client, auth_headers, branch)
    now = datetime.now(timezone.utc)
    r = await client.post(
        "/expenses",
        headers=auth_headers,
        json={
            "vehicle_id": vehicle_id,
            "branch_id": str(branch["_id"]),
            "scope": "standalone",
            "category": "toll",
            "amount": 1500.0,
            "occurred_at": now.isoformat(),
            "vendor_name": "Toll Gate 5",
        },
    )
    assert r.status_code == 201
    e_id = r.json()["data"]["id"]
    r = await client.get(f"/expenses/{e_id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["data"]["amount"] == 1500.0

    # List
    r = await client.get("/expenses", headers=auth_headers)
    assert r.json()["total"] >= 1

    # Soft delete
    r = await client.delete(f"/expenses/{e_id}", headers=auth_headers)
    assert r.status_code == 204
    r = await client.get(f"/expenses/{e_id}", headers=auth_headers)
    assert r.status_code == 404


# ─── Reports ────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_reports_operations_summary(client, auth_headers, branch):
    """Summary returns the expected structure even with no trips."""
    r = await client.get(
        "/reports/operations/summary", headers=auth_headers
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert "totals" in data
    assert "by_status" in data
    assert "window" in data


@pytest.mark.asyncio
async def test_reports_daily_timeline(client, auth_headers, branch):
    r = await client.get(
        "/reports/operations/daily", headers=auth_headers
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert "series" in data
    assert data["bucket"] == "day"


@pytest.mark.asyncio
async def test_reports_fuel_summary(client, auth_headers, branch):
    r = await client.get("/reports/fuel/summary", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()["data"]
    assert "total_liters" in data
    assert "total_cost" in data


@pytest.mark.asyncio
async def test_reports_branch_performance(client, auth_headers, branch):
    r = await client.get(
        "/reports/branches/performance", headers=auth_headers
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert "branches" in data
