"""PDF export — cash-up receipts and trip waybills.

There was no test for either endpoint, and both were broken: the PDF
service formatted dates with ``iso.replace("Z", "+00:00")``, which is
correct for an ISO string but means ``datetime.replace(year, month, ...)``
when the value comes straight out of MongoDB as a native datetime. The
result was ``TypeError: 'str' object cannot be interpreted as an
integer`` and a 500 on every single receipt and waybill.

These tests pin the fix.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId

from app.services.pdf import _fmt_date


# ── the formatter ───────────────────────────────────────────────────────────

def test_fmt_date_handles_a_native_datetime():
    """A datetime straight out of Mongo — the case that used to raise."""
    dt = datetime(2026, 3, 14, 15, 9, 26, tzinfo=timezone.utc)
    out = _fmt_date(dt)
    assert "14 Mar 2026" in out, out


def test_fmt_date_handles_a_naive_datetime():
    """A naive datetime is treated as UTC rather than crashing."""
    out = _fmt_date(datetime(2026, 3, 14, 15, 9, 26))
    assert "14 Mar 2026" in out, out


def test_fmt_date_handles_an_iso_string():
    out = _fmt_date("2026-03-14T15:09:26+00:00")
    assert "14 Mar 2026" in out, out


def test_fmt_date_handles_a_zulu_iso_string():
    out = _fmt_date("2026-03-14T15:09:26Z")
    assert "14 Mar 2026" in out, out


def test_fmt_date_handles_none_and_garbage():
    assert _fmt_date(None) == "—"
    assert _fmt_date("") == "—"
    # An unparseable string is echoed rather than raising.
    assert _fmt_date("not-a-date") == "not-a-date"
    # A non-date type is echoed too.
    assert _fmt_date(12345) == "12345"


# ── the endpoints ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cash_up_pdf_endpoint(client, db, auth_headers):
    """A cash-up receipt must download as a real PDF."""
    now = datetime.now(timezone.utc)
    trip_id = ObjectId()
    branch_id = ObjectId()
    conductor_id = ObjectId()

    await db.branches.insert_one({
        "_id": branch_id, "name": "PDF Branch", "code": "PDF-1", "city": "C",
        "state": "S", "address": "A", "status": "active", "manager_id": None,
        "is_active": True, "created_at": now, "updated_at": now,
    })
    await db.trips.insert_one({
        "_id": trip_id, "branch_id": str(branch_id), "route_id": None,
        "vehicle_id": None, "driver_id": None, "conductor_id": None,
        "status": "planned", "scheduled_departure": now + timedelta(hours=1),
        "scheduled_arrival": now + timedelta(hours=5), "is_active": True,
        "created_at": now, "updated_at": now,
    })
    await db.conductors.insert_one({
        "_id": conductor_id, "user_id": str(branch_id), "full_name": "PDF Conductor",
        "phone": None, "badge_no": "PDF-B1", "status": "active",
        "branch_id": str(branch_id), "is_active": True,
        "created_at": now, "updated_at": now,
    })
    cash_up_id = ObjectId()
    await db.cash_ups.insert_one({
        "_id": cash_up_id, "trip_id": str(trip_id), "branch_id": str(branch_id),
        "conductor_id": str(conductor_id), "declared_total": 1000,
        "expected_total": 950, "variance": 50, "status": "submitted",
        "breakdown": [{"method": "cash", "amount": 1000, "reference": None}],
        "notes": None, "is_active": True, "created_at": now, "updated_at": now,
    })

    r = await client.get(f"/cash-ups/{cash_up_id}/pdf", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content.startswith(b"%PDF"), r.content[:40]


@pytest.mark.asyncio
async def test_trip_waybill_pdf_endpoint(client, db, auth_headers):
    """A trip waybill must download as a real PDF."""
    now = datetime.now(timezone.utc)
    trip_id = ObjectId()
    branch_id = ObjectId()
    route_id = ObjectId()

    await db.branches.insert_one({
        "_id": branch_id, "name": "WB Branch", "code": "WB-1", "city": "C",
        "state": "S", "address": "A", "status": "active", "manager_id": None,
        "is_active": True, "created_at": now, "updated_at": now,
    })
    await db.routes.insert_one({
        "_id": route_id, "name": "WB Route", "code": "WB-R", "type": "intrastate",
        "origin_branch_id": str(branch_id), "destination_branch_id": str(branch_id),
        "origin_city": "A", "destination_city": "B", "distance_km": 20,
        "base_fare_passenger": 1000, "base_fare_cargo_per_kg": 50,
        "estimated_duration_hours": 1, "status": "active",
        "branch_id": str(branch_id), "is_active": True,
        "created_at": now, "updated_at": now,
    })
    await db.trips.insert_one({
        "_id": trip_id, "branch_id": str(branch_id), "route_id": str(route_id),
        "vehicle_id": None, "driver_id": None, "conductor_id": None,
        "status": "planned", "scheduled_departure": now + timedelta(hours=1),
        "scheduled_arrival": now + timedelta(hours=5), "is_active": True,
        "created_at": now, "updated_at": now,
    })
    await db["manifest"].insert_one({
        "trip_id": str(trip_id), "type": "passenger",
        "passenger_name": "PDF Passenger", "passenger_phone": "+1-555-0000",
        "passenger_id_number": None, "seat_number": "1A",
        "cargo_description": None, "cargo_weight_kg": None,
        "cargo_sender_name": None, "cargo_receiver_name": None,
        "cargo_receiver_phone": None, "fare": 500,
        "payment_status": "paid", "payment_method": "cash", "boarded": True,
        "is_active": True, "created_at": now, "updated_at": now,
    })

    r = await client.get(f"/trips/{trip_id}/waybill.pdf", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content.startswith(b"%PDF"), r.content[:40]
