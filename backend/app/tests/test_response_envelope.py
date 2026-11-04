"""Response-envelope contract.

Every endpoint the app reads with ``getSingle`` must answer with the
standard ``{"data": ...}`` envelope, and every endpoint read with
``getPage`` must answer with ``{"items": [...], "total": n, ...}``.

Seven endpoints used to answer with a bare body — no ``data`` key —
while the frontend read them with ``getSingle`` (which returns
``response.data.data``). The result was silently ``undefined`` on the
dashboard, the fleet map, the QR scanner, the incident counters, the
role-permission matrix metadata and the audit actor list.

This module pins the envelope so the mismatch cannot come back.
"""

from __future__ import annotations

import pytest


async def _assert_envelope(r):
    """The response must be JSON with a ``data`` key."""
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, dict), f"expected an object, got {type(body)}"
    assert "data" in body, f"missing the 'data' envelope key: {list(body.keys())}"
    return body["data"]


@pytest.mark.asyncio
async def test_dashboard_summary_is_enveloped(client, auth_headers):
    data = await _assert_envelope(
        await client.get("/dashboard/summary", headers=auth_headers)
    )
    assert "vehicles_maintenance" in data
    assert "open_incidents" in data


@pytest.mark.asyncio
async def test_fleet_positions_is_enveloped(client, auth_headers):
    data = await _assert_envelope(
        await client.get("/fleet/positions", headers=auth_headers)
    )
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_qr_lookup_is_enveloped(client, auth_headers):
    """Generate a real QR token, then look it up."""
    from app.services.qr import generate_qr_token

    token = generate_qr_token("vehicle", "507f1f77bcf86cd799439011")
    data = await _assert_envelope(
        await client.get("/qr/lookup", params={"token": token}, headers=auth_headers)
    )
    assert data["entity_type"] == "vehicle"
    assert data["entity_id"] == "507f1f77bcf86cd799439011"


@pytest.mark.asyncio
async def test_qr_generate_is_enveloped(client, db, auth_headers):
    from bson import ObjectId

    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    await db.vehicles.insert_one(
        {
            "reg_number": "QR-001",
            "type": "bus",
            "make": "Toyota",
            "model": "Hiace",
            "year": 2022,
            "plate_number": "PLATE-QR",
            "status": "in_service",
            "branch_id": None,
            "current_odometer_km": 0,
            "current_fuel_level": 100,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    vehicle_id = str((await db.vehicles.find_one({"reg_number": "QR-001"}))["_id"])

    data = await _assert_envelope(
        await client.get(
            f"/qr/generate/vehicle/{vehicle_id}", headers=auth_headers
        )
    )
    assert data["entity_type"] == "vehicle"
    assert data["token"]


@pytest.mark.asyncio
async def test_incident_summary_is_enveloped(client, auth_headers):
    data = await _assert_envelope(
        await client.get("/incidents/summary", headers=auth_headers)
    )
    for key in ("severe", "moderate", "minor", "closed"):
        assert key in data


@pytest.mark.asyncio
async def test_incident_categories_is_enveloped(client, auth_headers):
    data = await _assert_envelope(
        await client.get("/incidents/categories", headers=auth_headers)
    )
    assert isinstance(data, list)
    assert "mechanical" in data


@pytest.mark.asyncio
async def test_inspection_template_is_enveloped(client, auth_headers):
    data = await _assert_envelope(
        await client.get("/inspections/template", headers=auth_headers)
    )
    assert isinstance(data, list)
    assert data, "the checklist template must not be empty"
    assert "key" in data[0]
    assert "label" in data[0]
    assert data[0]["status"] == "pending"


@pytest.mark.asyncio
async def test_audit_actors_is_enveloped(client, auth_headers):
    data = await _assert_envelope(
        await client.get("/audit-log/actors", headers=auth_headers)
    )
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_events_status_is_enveloped(client, auth_headers):
    data = await _assert_envelope(
        await client.get("/events/status", headers=auth_headers)
    )
    assert "subscribers" in data
    assert "running" in data


@pytest.mark.asyncio
async def test_settlement_summary_is_enveloped(client, auth_headers):
    data = await _assert_envelope(
        await client.get("/settlements/summary", headers=auth_headers)
    )
    assert "by_status" in data
    assert "totals" in data


@pytest.mark.asyncio
async def test_audit_log_summary_is_enveloped(client, auth_headers):
    data = await _assert_envelope(
        await client.get("/audit-log/summary", headers=auth_headers)
    )
    assert "total" in data


@pytest.mark.asyncio
async def test_role_permissions_meta_is_enveloped(client, auth_headers):
    data = await _assert_envelope(
        await client.get("/role-permissions/meta", headers=auth_headers)
    )
    assert isinstance(data, dict)
