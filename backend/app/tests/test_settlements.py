"""Settlements — the Sprint D financial close.

Covers the computation (what gets paid, to whom) and the state machine
(draft → submitted → approved → paid), including the rule that an
approved settlement is locked.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.services.settlements import compute_settlement


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _seed_branch(db, name="Lagos"):
    now = _now()
    doc = {
        "name": name,
        "code": f"BR-{name[:3].upper()}",
        "city": name,
        "state": "State",
        "address": "1 Road",
        "contact_phone": "+1-555-0000",
        "contact_email": "branch@example.com",
        "status": "active",
        "manager_id": None,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.branches.insert_one(doc)
    doc["_id"] = result.inserted_id
    doc["id"] = str(result.inserted_id)
    return doc


async def _seed_trip(
    db,
    *,
    branch_id,
    status="cashed_up",
    total_revenue=0.0,
    days_ago=1,
    driver_id=None,
    conductor_id=None,
    route_id=None,
):
    now = _now()
    dep = now - timedelta(days=days_ago)
    doc = {
        "branch_id": branch_id,
        "route_id": route_id,
        "vehicle_id": "veh-1",
        "driver_id": driver_id,
        "conductor_id": conductor_id,
        "status": status,
        "scheduled_departure": dep,
        "scheduled_arrival": dep + timedelta(hours=4),
        "actual_departure": dep,
        "total_revenue": total_revenue,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.trips.insert_one(doc)
    doc["_id"] = result.inserted_id
    doc["id"] = str(result.inserted_id)
    return doc


async def _seed_cash_up(db, *, trip_id, expected_total, variance=0.0):
    now = _now()
    doc = {
        "trip_id": trip_id,
        "conductor_id": "cond-1",
        "branch_id": "b1",
        "breakdown": [],
        "declared_total": expected_total + variance,
        "expected_total": expected_total,
        "variance": variance,
        "status": "approved",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.cash_ups.insert_one(doc)
    doc["_id"] = result.inserted_id
    doc["id"] = str(result.inserted_id)
    return doc


async def _seed_expense(
    db, *, branch_id, amount, scope="on_trip", trip_id=None, days_ago=1
):
    now = _now()
    doc = {
        "vehicle_id": "veh-1",
        "branch_id": branch_id,
        "scope": scope,
        "trip_id": trip_id,
        "category": "fuel",
        "amount": amount,
        "occurred_at": now - timedelta(days=days_ago),
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.expenses.insert_one(doc)
    doc["_id"] = result.inserted_id
    doc["id"] = str(result.inserted_id)
    return doc


# ─────────────────────────────────────────────────────────────────────────────
# Computation
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_compute_uses_cash_up_revenue(db):
    branch = await _seed_branch(db)
    trip = await _seed_trip(db, branch_id=branch["id"], total_revenue=999.0)
    await _seed_cash_up(db, trip_id=trip["id"], expected_total=50000.0)

    result = await compute_settlement(
        db,
        branch_id=branch["id"],
        period_start=_now() - timedelta(days=7),
        period_end=_now() + timedelta(days=1),
    )

    # The cash-up wins over the trip's manifest total.
    assert result["gross_revenue"] == 50000.0
    assert result["trip_count"] == 1
    assert result["net_payable"] == 50000.0


@pytest.mark.asyncio
async def test_compute_falls_back_to_trip_revenue_without_cash_up(db):
    branch = await _seed_branch(db)
    await _seed_trip(db, branch_id=branch["id"], total_revenue=12000.0)

    result = await compute_settlement(
        db,
        branch_id=branch["id"],
        period_start=_now() - timedelta(days=7),
        period_end=_now() + timedelta(days=1),
    )

    assert result["gross_revenue"] == 12000.0


@pytest.mark.asyncio
async def test_compute_excludes_unfinished_trips(db):
    branch = await _seed_branch(db)
    await _seed_trip(db, branch_id=branch["id"], status="planned", total_revenue=9000.0)
    await _seed_trip(db, branch_id=branch["id"], status="departed", total_revenue=8000.0)

    result = await compute_settlement(
        db,
        branch_id=branch["id"],
        period_start=_now() - timedelta(days=7),
        period_end=_now() + timedelta(days=1),
    )

    assert result["trip_count"] == 0
    assert result["gross_revenue"] == 0.0


@pytest.mark.asyncio
async def test_compute_excludes_trips_outside_the_period(db):
    branch = await _seed_branch(db)
    await _seed_trip(db, branch_id=branch["id"], total_revenue=5000.0, days_ago=60)

    result = await compute_settlement(
        db,
        branch_id=branch["id"],
        period_start=_now() - timedelta(days=7),
        period_end=_now() + timedelta(days=1),
    )

    assert result["trip_count"] == 0


@pytest.mark.asyncio
async def test_compute_subtracts_trip_expenses(db):
    branch = await _seed_branch(db)
    trip = await _seed_trip(db, branch_id=branch["id"], total_revenue=10000.0)
    await _seed_expense(db, branch_id=branch["id"], amount=2500.0, trip_id=trip["id"])

    result = await compute_settlement(
        db,
        branch_id=branch["id"],
        period_start=_now() - timedelta(days=7),
        period_end=_now() + timedelta(days=1),
    )

    assert result["trip_expenses"] == 2500.0
    assert result["net_payable"] == 7500.0


@pytest.mark.asyncio
async def test_compute_subtracts_standalone_expenses(db):
    branch = await _seed_branch(db)
    await _seed_trip(db, branch_id=branch["id"], total_revenue=10000.0)
    await _seed_expense(
        db, branch_id=branch["id"], amount=1000.0, scope="standalone", trip_id=None
    )

    result = await compute_settlement(
        db,
        branch_id=branch["id"],
        period_start=_now() - timedelta(days=7),
        period_end=_now() + timedelta(days=1),
    )

    assert result["standalone_expenses"] == 1000.0
    assert result["net_payable"] == 9000.0


@pytest.mark.asyncio
async def test_compute_applies_pay_rates_per_trip(db):
    branch = await _seed_branch(db)
    await _seed_trip(db, branch_id=branch["id"], total_revenue=1000.0, days_ago=1)
    await _seed_trip(db, branch_id=branch["id"], total_revenue=2000.0, days_ago=2)

    result = await compute_settlement(
        db,
        branch_id=branch["id"],
        period_start=_now() - timedelta(days=7),
        period_end=_now() + timedelta(days=1),
        driver_rate=5000.0,
        conductor_rate=3000.0,
    )

    assert result["trip_count"] == 2
    assert result["driver_payroll"] == 10000.0
    assert result["conductor_payroll"] == 6000.0
    assert len(result["lines"]) == 2


@pytest.mark.asyncio
async def test_compute_is_branch_scoped(db):
    branch_a = await _seed_branch(db, "Alpha")
    branch_b = await _seed_branch(db, "Beta")
    await _seed_trip(db, branch_id=branch_a["id"], total_revenue=1000.0)
    await _seed_trip(db, branch_id=branch_b["id"], total_revenue=9000.0)

    result = await compute_settlement(
        db,
        branch_id=branch_a["id"],
        period_start=_now() - timedelta(days=7),
        period_end=_now() + timedelta(days=1),
    )

    assert result["gross_revenue"] == 1000.0


# ─────────────────────────────────────────────────────────────────────────────
# API
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_generate_settlement_endpoint(client, db, auth_headers):
    branch = await _seed_branch(db)
    await _seed_trip(db, branch_id=branch["id"], total_revenue=40000.0)

    r = await client.post(
        "/settlements/generate",
        headers=auth_headers,
        json={
            "branch_id": branch["id"],
            "period_start": (_now() - timedelta(days=30)).isoformat(),
            "period_end": (_now() + timedelta(days=1)).isoformat(),
            "driver_rate": 5000,
            "conductor_rate": 2000,
        },
    )
    assert r.status_code == 201, r.text
    data = r.json()["data"]
    assert data["status"] == "draft"
    assert data["gross_revenue"] == 40000.0
    assert data["driver_payroll"] == 5000.0
    assert data["trip_count"] == 1
    assert data["id"]


@pytest.mark.asyncio
async def test_generate_rejects_inverted_period(client, db, auth_headers):
    branch = await _seed_branch(db)
    r = await client.post(
        "/settlements/generate",
        headers=auth_headers,
        json={
            "branch_id": branch["id"],
            "period_start": (_now()).isoformat(),
            "period_end": (_now() - timedelta(days=5)).isoformat(),
        },
    )
    assert r.status_code == 400, r.text


@pytest.mark.asyncio
async def test_settlement_lifecycle(client, db, auth_headers):
    branch = await _seed_branch(db)
    await _seed_trip(db, branch_id=branch["id"], total_revenue=10000.0)

    r = await client.post(
        "/settlements/generate",
        headers=auth_headers,
        json={
            "branch_id": branch["id"],
            "period_start": (_now() - timedelta(days=30)).isoformat(),
            "period_end": (_now() + timedelta(days=1)).isoformat(),
        },
    )
    sid = r.json()["data"]["id"]

    # submit
    r = await client.post(f"/settlements/{sid}/submit", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["status"] == "submitted"

    # approve
    r = await client.post(f"/settlements/{sid}/approve", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["status"] == "approved"

    # pay
    r = await client.post(
        f"/settlements/{sid}/pay",
        headers=auth_headers,
        json={"payment_reference": "TRF-001"},
    )
    assert r.status_code == 200, r.text
    body = r.json()["data"]
    assert body["status"] == "paid"
    assert body["payment_reference"] == "TRF-001"
    assert body["paid_at"] is not None


@pytest.mark.asyncio
async def test_approved_settlement_is_locked(client, db, auth_headers):
    branch = await _seed_branch(db)
    await _seed_trip(db, branch_id=branch["id"], total_revenue=10000.0)

    r = await client.post(
        "/settlements/generate",
        headers=auth_headers,
        json={
            "branch_id": branch["id"],
            "period_start": (_now() - timedelta(days=30)).isoformat(),
            "period_end": (_now() + timedelta(days=1)).isoformat(),
        },
    )
    sid = r.json()["data"]["id"]

    await client.post(f"/settlements/{sid}/submit", headers=auth_headers)
    await client.post(f"/settlements/{sid}/approve", headers=auth_headers)

    # Editing an approved settlement must be refused.
    r = await client.patch(
        f"/settlements/{sid}", headers=auth_headers, json={"driver_rate": 99999}
    )
    assert r.status_code == 409, r.text

    # Submitting it again is refused too.
    r = await client.post(f"/settlements/{sid}/submit", headers=auth_headers)
    assert r.status_code == 409, r.text


@pytest.mark.asyncio
async def test_cannot_pay_an_unapproved_settlement(client, db, auth_headers):
    branch = await _seed_branch(db)
    await _seed_trip(db, branch_id=branch["id"], total_revenue=10000.0)

    r = await client.post(
        "/settlements/generate",
        headers=auth_headers,
        json={
            "branch_id": branch["id"],
            "period_start": (_now() - timedelta(days=30)).isoformat(),
            "period_end": (_now() + timedelta(days=1)).isoformat(),
        },
    )
    sid = r.json()["data"]["id"]

    r = await client.post(f"/settlements/{sid}/pay", headers=auth_headers, json={})
    assert r.status_code == 409, r.text


@pytest.mark.asyncio
async def test_rejected_settlement_becomes_editable_again(client, db, auth_headers):
    branch = await _seed_branch(db)
    await _seed_trip(db, branch_id=branch["id"], total_revenue=10000.0)

    r = await client.post(
        "/settlements/generate",
        headers=auth_headers,
        json={
            "branch_id": branch["id"],
            "period_start": (_now() - timedelta(days=30)).isoformat(),
            "period_end": (_now() + timedelta(days=1)).isoformat(),
        },
    )
    sid = r.json()["data"]["id"]

    await client.post(f"/settlements/{sid}/submit", headers=auth_headers)
    r = await client.post(
        f"/settlements/{sid}/reject",
        headers=auth_headers,
        json={"reason": "wrong rate"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["status"] == "rejected"

    r = await client.patch(
        f"/settlements/{sid}", headers=auth_headers, json={"driver_rate": 1234}
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["driver_rate"] == 1234


@pytest.mark.asyncio
async def test_update_rate_recomputes_payroll(client, db, auth_headers):
    branch = await _seed_branch(db)
    await _seed_trip(db, branch_id=branch["id"], total_revenue=10000.0)
    await _seed_trip(db, branch_id=branch["id"], total_revenue=20000.0, days_ago=2)

    r = await client.post(
        "/settlements/generate",
        headers=auth_headers,
        json={
            "branch_id": branch["id"],
            "period_start": (_now() - timedelta(days=30)).isoformat(),
            "period_end": (_now() + timedelta(days=1)).isoformat(),
            "driver_rate": 1000,
        },
    )
    sid = r.json()["data"]["id"]
    assert r.json()["data"]["driver_payroll"] == 2000.0

    r = await client.patch(
        f"/settlements/{sid}", headers=auth_headers, json={"driver_rate": 5000}
    )
    assert r.status_code == 200, r.text
    body = r.json()["data"]
    assert body["driver_payroll"] == 10000.0
    # Revenue is a historical record — it must not move.
    assert body["gross_revenue"] == 30000.0


@pytest.mark.asyncio
async def test_settlement_list_and_summary(client, db, auth_headers):
    branch = await _seed_branch(db)
    await _seed_trip(db, branch_id=branch["id"], total_revenue=10000.0)

    await client.post(
        "/settlements/generate",
        headers=auth_headers,
        json={
            "branch_id": branch["id"],
            "period_start": (_now() - timedelta(days=30)).isoformat(),
            "period_end": (_now() + timedelta(days=1)).isoformat(),
        },
    )

    r = await client.get("/settlements", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["total"] == 1

    r = await client.get("/settlements/summary", headers=auth_headers)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["by_status"]["draft"]["count"] == 1
    assert data["totals"]["net_payable"] == 10000.0


@pytest.mark.asyncio
async def test_settlement_endpoints_require_auth(client):
    for method, path in [
        ("get", "/settlements"),
        ("get", "/settlements/summary"),
        ("post", "/settlements/generate"),
    ]:
        r = await client.request(method.upper(), path, json={})
        assert r.status_code == 401, f"{method} {path} -> {r.status_code}"


@pytest.mark.asyncio
async def test_settlement_404s_on_bad_id(client, auth_headers):
    r = await client.get("/settlements/not-an-id", headers=auth_headers)
    assert r.status_code == 400, r.text
