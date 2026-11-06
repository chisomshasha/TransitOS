"""The dashboard must not show one role another's business.

The home screen used to render the platform administrator's view for
everybody: the same four company-wide figures, the same eight counters,
the same fleet map. Two things were wrong with that, and this file
covers both.

**The screens were wrong.** A driver's dashboard is their next trip; a
branch manager's is their branch; a chief accountant's is the money.
The front end now decides that from one table
(``frontend/lib/dashboard-view.ts``), and the test at the bottom checks
that table rather than the pixels.

**The data was wrong.** The endpoints behind those cards were not
scoped to crew, so the app was asking for company-wide figures it was
never entitled to see — and getting them:

* ``GET /dashboard/summary`` scoped only the management tiers, so a
  driver opening the dashboard was shown the whole company's fleet,
  incidents and cash-ups.
* ``GET /cash-ups`` scoped only the management tiers too, so a
  conductor was shown every cash-up in the business — other branches'
  takings included.

The fix is scoping, and a 404 rather than a 403 for a cash-up that is
not the reader's: another conductor's cash-up must not be
discoverable by guessing an id.
"""

from __future__ import annotations

import pathlib
import re

import pytest
from httpx import AsyncClient

BACKEND = pathlib.Path(__file__).resolve().parents[2]
REPO = BACKEND.parent
FRONTEND = REPO / "frontend"


# ── fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
async def conductor_user(db, branch):
    """A conductor with a crew profile, in ``branch``."""
    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    doc = {
        "email": "conductor.dash@transitos.app",
        "full_name": "Dashboard Conductor",
        "role": "conductor",
        "branch_id": str(branch["_id"]),
        "status": "active",
        "password_hash": __import__(
            "app.services.auth", fromlist=["hash_password"]
        ).hash_password("Cnd#1234567"),
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
    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    doc = {
        "user_id": str(conductor_user["_id"]),
        "badge_no": "DASH-001",
        "status": "active",
        "branch_id": str(branch["_id"]),
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.conductors.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


@pytest.fixture
async def conductor_token(client, conductor_user):
    r = await client.post(
        "/auth/login",
        json={
            "email": "conductor.dash@transitos.app",
            "password": "Cnd#1234567",
        },
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]["access_token"]


@pytest.fixture
async def other_conductor_profile(db, other_branch):
    """A conductor in another branch."""
    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    doc = {
        "user_id": str(other_branch["_id"]),
        "badge_no": "DASH-999",
        "status": "active",
        "branch_id": str(other_branch["_id"]),
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.conductors.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


@pytest.fixture
async def cash_ups(db, branch, other_branch, conductor_profile, other_conductor_profile):
    """One cash-up per conductor, in two different branches."""
    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    mine = {
        "trip_id": "00000000000000000000000a",
        "conductor_id": str(conductor_profile["_id"]),
        "branch_id": str(branch["_id"]),
        "method": "cash",
        "amount": 1000.0,
        "reference": None,
        "breakdown": [{"method": "cash", "amount": 1000.0}],
        "declared_total": 1000.0,
        "status": "draft",
        "expected_total": 0.0,
        "variance": 0.0,
        "notes": "",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    theirs = {
        "trip_id": "00000000000000000000000b",
        "conductor_id": str(other_conductor_profile["_id"]),
        "branch_id": str(other_branch["_id"]),
        "method": "cash",
        "amount": 5000.0,
        "reference": None,
        "breakdown": [{"method": "cash", "amount": 5000.0}],
        "declared_total": 5000.0,
        "status": "draft",
        "expected_total": 0.0,
        "variance": 0.0,
        "notes": "",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    a = await db.cash_ups.insert_one(mine)
    b = await db.cash_ups.insert_one(theirs)
    mine["_id"] = a.inserted_id
    theirs["_id"] = b.inserted_id
    return mine, theirs


# ── the dashboard counters must be scoped ──────────────────────────────────


@pytest.mark.asyncio
async def test_a_conductor_dashboard_summary_is_branch_scoped(
    client: AsyncClient, conductor_token, db, branch, other_branch
):
    """The dashboard counters must not be company-wide for a crew member.

    Before the fix the branch scope only covered the management tiers,
    so a driver's dashboard showed the whole company's fleet.
    """
    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    await db.vehicles.insert_many([
        {"_id": __import__("bson").ObjectId(), "reg_number": "V-MINE-1",
         "type": "bus", "capacity_seats": 40, "capacity_kg": 1000.0,
         "branch_id": str(branch["_id"]), "status": "maintenance",
         "current_odometer_km": 0, "current_fuel_level": 50.0, "documents": [],
         "is_active": True, "created_at": now, "updated_at": now},
        {"_id": __import__("bson").ObjectId(), "reg_number": "V-THEIRS-1",
         "type": "bus", "capacity_seats": 40, "capacity_kg": 1000.0,
         "branch_id": str(other_branch["_id"]), "status": "maintenance",
         "current_odometer_km": 0, "current_fuel_level": 50.0, "documents": [],
         "is_active": True, "created_at": now, "updated_at": now},
    ])

    headers = {"Authorization": f"Bearer {conductor_token}"}
    r = await client.get("/dashboard/summary", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()["data"]

    # One vehicle is in maintenance in the conductor's branch; the other
    # belongs to another branch and must not be counted.
    assert body["vehicles_maintenance"] == 1, (
        "the dashboard counters are not scoped to the reader's branch"
    )


@pytest.mark.asyncio
async def test_a_manager_dashboard_summary_is_still_company_wide(
    client: AsyncClient, owner
):
    """The platform view keeps its company-wide figures."""
    headers = {"Authorization": f"Bearer {owner['access_token']}"}
    r = await client.get("/dashboard/summary", headers=headers)
    assert r.status_code == 200, r.text
    assert "vehicles_maintenance" in r.json()["data"]


# ── a conductor sees only their own cash-ups ──────────────────────────────


@pytest.mark.asyncio
async def test_a_conductor_sees_only_their_own_cash_ups(
    client: AsyncClient, conductor_token, cash_ups
):
    """The cash-ups list is the conductor's own, not the company's.

    The list endpoint scoped only the management tiers, so a conductor
    was shown every cash-up in the business — other branches' takings
    included.
    """
    mine, theirs = cash_ups
    headers = {"Authorization": f"Bearer {conductor_token}"}
    r = await client.get("/cash-ups", headers=headers)
    assert r.status_code == 200, r.text
    ids = {c["id"] for c in r.json()["items"]}
    assert str(mine["_id"]) in ids
    assert str(theirs["_id"]) not in ids, (
        "a conductor can see another branch's cash-up"
    )


@pytest.mark.asyncio
async def test_a_conductor_cannot_read_another_conductors_cash_up(
    client: AsyncClient, conductor_token, cash_ups
):
    """404, not 403 — the record must not be discoverable."""
    _mine, theirs = cash_ups
    headers = {"Authorization": f"Bearer {conductor_token}"}
    r = await client.get(f"/cash-ups/{theirs['_id']}", headers=headers)
    assert r.status_code == 404, r.text


@pytest.mark.asyncio
async def test_a_conductor_cannot_export_another_conductors_cash_up(
    client: AsyncClient, conductor_token, cash_ups
):
    _mine, theirs = cash_ups
    headers = {"Authorization": f"Bearer {conductor_token}"}
    r = await client.get(f"/cash-ups/{theirs['_id']}/pdf", headers=headers)
    assert r.status_code == 404, r.text


@pytest.mark.asyncio
async def test_a_manager_still_sees_every_cash_up(
    client: AsyncClient, owner, cash_ups
):
    """The scoping fix must not take the management view away."""
    mine, theirs = cash_ups
    headers = {"Authorization": f"Bearer {owner['access_token']}"}
    r = await client.get("/cash-ups", headers=headers)
    assert r.status_code == 200, r.text
    ids = {c["id"] for c in r.json()["items"]}
    assert {str(mine["_id"]), str(theirs["_id"])} <= ids


# ── the front end's per-role view ──────────────────────────────────────────


def _dashboard_view_source() -> str:
    return (FRONTEND / "lib" / "dashboard-view.ts").read_text(encoding="utf-8")


def test_every_role_has_a_dashboard_view():
    """No role is left on the platform view by accident."""
    from app.core.roles import Role

    src = _dashboard_view_source()
    block = re.search(r"DASHBOARD_VIEWS[^=]*=\s*\{(.*?)\n\};", src, re.S)
    assert block, "DASHBOARD_VIEWS is missing from frontend/lib/dashboard-view.ts"
    listed = set(re.findall(r"^\s{2}(\w+):", block.group(1), re.M))
    expected = {r.value for r in Role}
    assert listed == expected, (
        f"the dashboard view covers {sorted(listed)} but the roles are {sorted(expected)}"
    )


def test_the_crew_dashboard_shows_no_company_figures():
    """A driver or a conductor must not be shown the company's numbers.

    The company-wide figures — revenue, cash variance, the fleet, the
    branch map — belong to the management and finance tiers. The crew
    view is their own trips.
    """
    src = _dashboard_view_source()
    for view_name in ("DRIVER_VIEW", "CONDUCTOR_VIEW"):
        block = re.search(
            rf"const {view_name}[^=]*=\s*\{{(.*?)\n\}};", src, re.S
        )
        assert block, f"{view_name} is missing"
        body = block.group(1)
        for company_figure in (
            "revenue",
            "cash_variance",
            "active_fleet",
            "total_vehicles",
            "pending_cashups",
            "open_incidents",
        ):
            assert f"'{company_figure}'" not in body, (
                f"{view_name} shows {company_figure}, which is not the crew's business"
            )
        assert "fleetMap: false" in body, f"{view_name} shows the company fleet map"


def test_the_crew_dashboard_does_not_ask_for_the_fleet():
    """The app must not request what the backend would refuse."""
    src = _dashboard_view_source()
    for view_name in ("DRIVER_VIEW", "CONDUCTOR_VIEW"):
        block = re.search(
            rf"const {view_name}[^=]*=\s*\{{(.*?)\n\}};", src, re.S
        )
        assert block
        body = block.group(1)
        assert "needsFleet: false" in body, (
            f"{view_name} asks for the fleet, which the backend refuses a crew member"
        )
        assert "needsBranches: false" in body
        assert "needsSummary: false" in body


def test_the_finance_views_see_the_money():
    """The accountants must still see the money."""
    src = _dashboard_view_source()
    for view_name in ("CHIEF_ACCOUNTANT_VIEW", "BRANCH_ACCOUNTANT_VIEW"):
        block = re.search(
            rf"const {view_name}[^=]*=\s*\{{(.*?)\n\}};", src, re.S
        )
        assert block, f"{view_name} is missing"
        body = block.group(1)
        assert "'revenue'" in body, f"{view_name} cannot see the revenue"
        assert "'cash_variance'" in body, f"{view_name} cannot see the variance"


@pytest.mark.asyncio
async def test_a_conductor_cannot_edit_another_conductors_cash_up(
    client: AsyncClient, conductor_token, cash_ups
):
    """The write endpoints must be scoped the same way as the reads."""
    _mine, theirs = cash_ups
    headers = {"Authorization": f"Bearer {conductor_token}"}
    r = await client.patch(
        f"/cash-ups/{theirs['_id']}",
        headers=headers,
        json={"declared_total": 1.0, "breakdown": [{"method": "cash", "amount": 1.0}]},
    )
    assert r.status_code == 404, r.text


@pytest.mark.asyncio
async def test_a_conductor_cannot_submit_another_conductors_cash_up(
    client: AsyncClient, conductor_token, cash_ups
):
    _mine, theirs = cash_ups
    headers = {"Authorization": f"Bearer {conductor_token}"}
    r = await client.post(f"/cash-ups/{theirs['_id']}/submit", headers=headers)
    assert r.status_code == 404, r.text


@pytest.mark.asyncio
async def test_a_conductor_cannot_declare_a_cash_up_for_someone_else(
    client: AsyncClient, conductor_token, db, branch, conductor_profile,
    other_conductor_profile,
):
    """A cash-up is filed in the declarer's own name."""
    from bson import ObjectId

    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    trip = {
        "route_id": "00000000000000000000000c",
        "vehicle_id": "00000000000000000000000d",
        "driver_id": "00000000000000000000000e",
        "conductor_id": str(conductor_profile["_id"]),
        "branch_id": str(branch["_id"]),
        "scheduled_departure": now,
        "scheduled_arrival": now,
        "status": "closed",
        "passenger_count": 0,
        "cargo_weight_kg": 0.0,
        "total_revenue": 0.0,
        "total_expenses": 0.0,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.trips.insert_one(trip)
    trip_id = str(result.inserted_id)

    headers = {"Authorization": f"Bearer {conductor_token}"}
    r = await client.post(
        "/cash-ups",
        headers=headers,
        json={
            "trip_id": trip_id,
            "conductor_id": str(other_conductor_profile["_id"]),
            "branch_id": str(branch["_id"]),
            "breakdown": [{"method": "cash", "amount": 10.0}],
            "declared_total": 10.0,
        },
    )
    assert r.status_code == 403, r.text
