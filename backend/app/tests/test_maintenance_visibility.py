"""Maintenance records must be visible to the alerts engine and reports.

The maintenance router writes to the ``maintenance`` collection, but the
alerts engine scanned ``maintenance_records`` and the profit-and-loss
report read ``maintenance_records`` too. Both were empty in practice,
so:

* "maintenance due" / "maintenance overdue" notifications never fired
* maintenance cost never appeared in the P&L report
* maintenance downtime never appeared in vehicle ROI

Nothing raised. No test had ever seeded either collection, so the whole
split stayed invisible.

These tests write a maintenance record the way the router writes it and
assert the alerts engine and the reports actually see it.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId


async def _seed_maintenance(db, *, due_in_days: int, cost_total: float = 5000.0):
    """Insert a maintenance record into the collection the router uses."""
    now = datetime.now(timezone.utc)
    branch_id = ObjectId()
    vehicle_id = ObjectId()
    record_id = ObjectId()

    await db.branches.insert_one({
        "_id": branch_id, "name": "Alert Branch", "code": "AL-1", "city": "C",
        "state": "S", "address": "A", "status": "active", "manager_id": None,
        "is_active": True, "created_at": now, "updated_at": now,
    })
    await db.vehicles.insert_one({
        "_id": vehicle_id, "reg_number": "AL-001", "type": "bus", "make": "Toyota",
        "model": "Hiace", "year": 2023, "plate_number": "AL-P",
        "status": "available", "capacity_seats": 50, "capacity_kg": 2000,
        "branch_id": str(branch_id), "current_odometer_km": 100,
        "current_fuel_level": 80, "is_active": True,
        "created_at": now, "updated_at": now,
    })
    # Written exactly as app/routers/maintenance.py writes it.
    await db["maintenance"].insert_one({
        "_id": record_id, "branch_id": str(branch_id),
        "vehicle_id": str(vehicle_id), "type": "routine", "status": "scheduled",
        "title": "Brake service", "description": "Replace pads",
        "cost_parts": 3000, "cost_labor": 2000, "cost_total": cost_total,
        "odometer_km": 100, "notes": None, "vendor_name": None,
        "next_due_date": None, "next_due_km": None,
        "scheduled_for": now + timedelta(days=due_in_days),
        "started_at": None, "completed_at": None,
        "is_active": True, "created_at": now, "updated_at": now,
    })
    return branch_id, vehicle_id, record_id


@pytest.mark.asyncio
async def test_alerts_scan_finds_maintenance_due(db):
    """A maintenance record due soon must raise a notification."""
    from app.services.alerts import run_alerts_scan

    await _seed_maintenance(db, due_in_days=5)

    counts = await run_alerts_scan(db)
    assert counts.get("maintenance", 0) >= 1, counts

    notes = [d async for d in db.notifications.find({"type": "maintenance"})]
    assert notes, "no maintenance notification was created"
    assert any("Brake service" in (n.get("title") or "") for n in notes), [
        n.get("title") for n in notes
    ]


@pytest.mark.asyncio
async def test_alerts_scan_ignores_distant_maintenance(db):
    """A record due far in the future must not raise an alert."""
    from app.services.alerts import run_alerts_scan

    await _seed_maintenance(db, due_in_days=400)

    counts = await run_alerts_scan(db)
    assert counts.get("maintenance", 0) == 0, counts


@pytest.mark.asyncio
async def test_profit_loss_includes_maintenance_cost(client, db, auth_headers):
    """Completed maintenance cost must reach the profit-and-loss report."""
    now = datetime.now(timezone.utc)
    branch_id, vehicle_id, _ = await _seed_maintenance(db, due_in_days=5)

    # A completed record, which is what the P&L sums over.
    await db["maintenance"].update_one(
        {"vehicle_id": str(vehicle_id)},
        {"$set": {
            "status": "completed",
            "cost_total": 5000.0,
            "cost_parts": 3000.0,
            "cost_labor": 2000.0,
            "completed_at": now,
            "started_at": now - timedelta(days=1),
        }},
    )

    start = (now - timedelta(days=7)).isoformat()
    end = (now + timedelta(days=1)).isoformat()
    r = await client.get(
        "/reports/financials/profit-loss",
        params={"from": start, "to": end},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]

    # The report sums db["maintenance"] — the collection the router writes.
    breakdown = data.get("expenses_breakdown") or {}
    maint = float(breakdown.get("maintenance") or data.get("maintenance") or 0)
    assert maint >= 5000.0, f"maintenance cost missing from the P&L: {data}"


@pytest.mark.asyncio
async def test_utilization_counts_maintenance_downtime(client, db, auth_headers):
    """Maintenance downtime must reduce the vehicle utilization figure.

    The utilization report subtracts completed-maintenance days from the
    window, so with the wrong collection name every vehicle looked 100%
    utilised.
    """
    now = datetime.now(timezone.utc)
    branch_id, vehicle_id, _ = await _seed_maintenance(db, due_in_days=5)

    await db["maintenance"].update_one(
        {"vehicle_id": str(vehicle_id)},
        {"$set": {
            "status": "completed",
            "started_at": now - timedelta(days=3),
            "completed_at": now - timedelta(days=1),
        }},
    )

    start = (now - timedelta(days=7)).isoformat()
    end = (now + timedelta(days=1)).isoformat()
    r = await client.get(
        "/reports/vehicles/utilization",
        params={"from": start, "to": end},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]

    # The report answers {"vehicles": [...]} — matching the frontend.
    items = data.get("vehicles") if isinstance(data, dict) else data
    assert items, "the utilization report returned no rows"
    row = next((i for i in items if str(i.get("vehicle_id")) == str(vehicle_id)), None)
    assert row is not None, f"the maintained vehicle is missing: {items}"
    assert float(row.get("downtime_days") or 0) >= 1.9, row
    assert float(row.get("utilization_pct") or 0) < 100, row
