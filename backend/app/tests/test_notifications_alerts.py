"""Alerts engine + notifications inbox.

These cover the path the Notifications screen depends on end to end:

    alerts scan → notification rows → GET /notifications → unread count
    → mark read / mark all read

The scan used to be reachable only by manually hitting
``POST /alerts/scan``. It is now also run by the background worker in
``app/main.py``, so the inbox is populated without anyone poking the
endpoint. These tests pin the behaviour the UI relies on.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.services.alerts import run_alerts_scan


def _days_ago(days: float) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=days)


async def _seed_vehicle(db, *, reg_number="AAA-001", fuel_level=None):
    now = datetime.now(timezone.utc)
    doc = {
        "reg_number": reg_number,
        "type": "bus",
        "make": "Toyota",
        "model": "Hiace",
        "year": 2022,
        "plate_number": f"PLATE-{reg_number}",
        "status": "in_service",
        "branch_id": None,
        "current_fuel_level": fuel_level,
        "odometer_km": 1000,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.vehicles.insert_one(doc)
    doc["_id"] = result.inserted_id
    doc["id"] = str(result.inserted_id)
    return doc


async def _seed_driver(db, *, license_expiry=None, name="Ada Driver"):
    now = datetime.now(timezone.utc)
    doc = {
        "full_name": name,
        "phone": "+1-555-0000",
        "license_no": "LIC-001",
        "license_expiry": license_expiry,
        "branch_id": None,
        "status": "active",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.drivers.insert_one(doc)
    doc["_id"] = result.inserted_id
    doc["id"] = str(result.inserted_id)
    return doc


async def _seed_vehicle_document(db, *, vehicle_id, expires_at, doc_type="insurance"):
    now = datetime.now(timezone.utc)
    doc = {
        "vehicle_id": vehicle_id,
        "doc_type": doc_type,
        "issuer": "Assurance Co",
        "ref_number": "REF-9001",
        "issued_at": now,
        "expires_at": expires_at,
        "alert_days": 30,
        "branch_id": None,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.vehicle_documents.insert_one(doc)
    doc["_id"] = result.inserted_id
    doc["id"] = str(result.inserted_id)
    return doc


# ─────────────────────────────────────────────────────────────────────────────
# The scan
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_scan_raises_alert_for_expiring_document(db):
    vehicle = await _seed_vehicle(db)
    await _seed_vehicle_document(
        db, vehicle_id=vehicle["id"], expires_at=_days_ago(5)  # 5 days out
    )

    counts = await run_alerts_scan(db)

    assert counts["documents"] == 1
    assert counts["total"] >= 1

    notifications = await db.notifications.find({}).to_list(100)
    assert len(notifications) == 1
    assert notifications[0]["type"] == "documents"
    assert notifications[0]["severity"] == "warn"
    assert "expires" in notifications[0]["title"].lower()


@pytest.mark.asyncio
async def test_scan_raises_alert_for_expiring_driver_license(db):
    await _seed_driver(db, license_expiry=_days_ago(3))

    counts = await run_alerts_scan(db)

    assert counts["licenses"] == 1
    notifications = await db.notifications.find({}).to_list(100)
    assert notifications[0]["type"] == "licenses"


@pytest.mark.asyncio
async def test_scan_raises_low_fuel_alert(db):
    await _seed_vehicle(db, reg_number="LOW-001", fuel_level=8.0)

    counts = await run_alerts_scan(db)

    assert counts["low_fuel"] == 1
    notifications = await db.notifications.find({}).to_list(100)
    assert notifications[0]["type"] == "low_fuel"
    assert notifications[0]["severity"] == "danger"


@pytest.mark.asyncio
async def test_scan_is_idempotent(db):
    """Re-running the scan must not pile up duplicate notifications."""
    vehicle = await _seed_vehicle(db)
    await _seed_vehicle_document(
        db, vehicle_id=vehicle["id"], expires_at=_days_ago(5)
    )

    await run_alerts_scan(db)
    await run_alerts_scan(db)
    await run_alerts_scan(db)

    notifications = await db.notifications.find({}).to_list(100)
    assert len(notifications) == 1


@pytest.mark.asyncio
async def test_scan_ignores_far_future_expiry(db):
    vehicle = await _seed_vehicle(db)
    await _seed_vehicle_document(
        db, vehicle_id=vehicle["id"], expires_at=_days_ago(365)  # a year out
    )

    counts = await run_alerts_scan(db)

    assert counts["documents"] == 0
    assert await db.notifications.count_documents({}) == 0


# ─────────────────────────────────────────────────────────────────────────────
# The inbox endpoints the Notifications screen calls
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_notifications_inbox_flow(client, db, auth_headers):
    vehicle = await _seed_vehicle(db)
    await _seed_vehicle_document(
        db, vehicle_id=vehicle["id"], expires_at=_days_ago(5)
    )
    await run_alerts_scan(db)

    # ── list ──
    r = await client.get("/notifications", headers=auth_headers)
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["total"] == 1
    assert payload["items"][0]["type"] == "documents"

    # ── unread count ──
    r = await client.get("/notifications/unread-count", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["count"] == 1

    # ── mark one read ──
    notification_id = payload["items"][0]["id"]
    r = await client.post(
        f"/notifications/{notification_id}/mark-read", headers=auth_headers
    )
    assert r.status_code == 204, r.text

    r = await client.get("/notifications/unread-count", headers=auth_headers)
    assert r.json()["data"]["count"] == 0

    # ── unread filter excludes it ──
    r = await client.get(
        "/notifications", params={"unread": "true"}, headers=auth_headers
    )
    assert r.json()["total"] == 0


@pytest.mark.asyncio
async def test_mark_all_read_clears_unread_count(client, db, auth_headers):
    vehicle = await _seed_vehicle(db)
    await _seed_vehicle_document(
        db, vehicle_id=vehicle["id"], expires_at=_days_ago(5)
    )
    await _seed_driver(db, license_expiry=_days_ago(3))
    await run_alerts_scan(db)

    r = await client.get("/notifications/unread-count", headers=auth_headers)
    assert r.json()["data"]["count"] == 2

    r = await client.post("/notifications/mark-all-read", headers=auth_headers)
    assert r.status_code == 204, r.text

    r = await client.get("/notifications/unread-count", headers=auth_headers)
    assert r.json()["data"]["count"] == 0


@pytest.mark.asyncio
async def test_alerts_scan_endpoint_requires_auth(client, db):
    r = await client.post("/alerts/scan")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_alerts_scan_endpoint_runs_scan(client, db, auth_headers):
    vehicle = await _seed_vehicle(db)
    await _seed_vehicle_document(
        db, vehicle_id=vehicle["id"], expires_at=_days_ago(5)
    )

    r = await client.post("/alerts/scan", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["documents"] == 1
