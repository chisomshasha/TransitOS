"""
Regression tests for the role/access defects found by the contract
checker while building the User Manual mockups.

Each test here pins one defect that shipped in a green build with a green
test suite:

1. The fleet manager was shown a Fuel screen, but ``GET /fuel-logs``
   refused them (403). The UI offered the screen; the API said no.
2. The fleet manager was given the Trips tab, but ``GET /trips`` refused
   them (403).
3. The driver was given the pre-trip checklist, but ``GET /inspections``
   refused them (403).
4. The general manager was given the Role permissions screen, which
   rendered a "Reset ALL roles" button that only Super Admin and Owner
   may use. Tapping it produced a 403.
5. The cash-ups screen looked up each conductor with
   ``GET /conductors/{id}``. A conductor may not read the conductor
   directory, so every cash-up card showed the literal word
   "Conductor" instead of the crew member's name.

The contract checker (``tools/contract/check.py``) now catches this
class automatically; these tests are the permanent guards.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.services.auth import hash_password


# ── helpers ──────────────────────────────────────────────────────────────────
async def _make_user(db, client, *, email, role, branch_id=None,
                      password="Test#12345"):
    """Create a user and return an Authorization header for them."""
    now = datetime.now(timezone.utc)
    await db.users.insert_one({
        "email": email.lower(),
        "full_name": email.split("@")[0].title(),
        "phone": None,
        "role": role,
        "branch_id": branch_id,
        "status": "active",
        "hire_date": None,
        "photo_url": None,
        "password_hash": hash_password(password),
        "is_active": True,
        "last_login_at": None,
        "created_at": now,
        "updated_at": now,
    })
    resp = await client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def fleet_manager(db, client):
    return await _make_user(db, client, email="fm@transitos.app",
                            role="fleet_manager")


@pytest.fixture
async def general_manager(db, client):
    return await _make_user(db, client, email="gm@transitos.app",
                            role="general_manager")


@pytest.fixture
async def conductor(db, client, branch):
    return await _make_user(db, client, email="conductor@transitos.app",
                            role="conductor", branch_id=str(branch["_id"]))


# ── 1 & 2. Fleet manager can read fuel logs and trips ───────────────────────
@pytest.mark.asyncio
async def test_fleet_manager_can_read_fuel_logs(client, fleet_manager):
    """The UI shows fleet managers a Fuel screen; the API must allow it."""
    resp = await client.get("/fuel-logs", headers=fleet_manager)
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_fleet_manager_can_log_fuel(client, fleet_manager):
    """The Fuel screen's 'Log fuel' button must work for fleet managers."""
    resp = await client.post(
        "/fuel-logs",
        headers=fleet_manager,
        json={
            "vehicle_id": "652f3a1b9c4d2e0011aabb101",
            "branch_id": "652f3a1b9c4d2e0011aabb001",
            "occurred_at": "2026-01-05T09:00:00Z",
            "liters": 50.0,
            "cost_total": 25000.0,
            "cost_per_liter": 500.0,
            "odometer_km": 12000,
        },
    )
    # A 201 means the write was accepted. A 400/422 is also fine here —
    # what must never happen is a 403 (the role was refused).
    assert resp.status_code != 403, resp.text
    assert resp.status_code in (201, 400, 404, 422), resp.text


@pytest.mark.asyncio
async def test_fleet_manager_can_read_trips(client, fleet_manager):
    """The fleet manager has a Trips tab; the API must serve it."""
    resp = await client.get("/trips", headers=fleet_manager)
    assert resp.status_code == 200, resp.text


# ── 3. Driver can read inspections ──────────────────────────────────────────
@pytest.mark.asyncio
async def test_driver_can_read_inspections(client, driver_user):
    """The pre-trip checklist lists inspections; the driver must be allowed."""
    resp = await client.post(
        "/auth/login",
        json={"email": "driver@transitos.app", "password": "Dr#1234567"},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["data"]["access_token"]
    resp = await client.get("/inspections",
                            headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text


# ── 4. Only Super Admin and Owner may reset every role ──────────────────────
@pytest.mark.asyncio
async def test_general_manager_cannot_reset_all_role_permissions(
    client, general_manager
):
    """The API already refuses this; the point is that the rule holds."""
    resp = await client.post("/role-permissions/reset-all",
                              headers=general_manager)
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_owner_can_reset_all_role_permissions(client, owner):
    resp = await client.post("/role-permissions/reset-all",
                              headers={"Authorization":
                                       f"Bearer {owner['access_token']}"})
    assert resp.status_code == 204, resp.text


def test_reset_all_roles_allow_list_matches_the_api():
    """The frontend's RESET_ALL_ROLES must equal the API's require_roles.

    The defect was a button rendered for every role who could open the
    screen, while the API allowed only Super Admin and Owner. This test
    keeps the two lists from drifting apart again.
    """
    backend = Path(__file__).resolve().parents[2]
    screen = backend.parent / "frontend" / "app" / "(app)" / "role-permissions.tsx"
    if not screen.exists():
        pytest.skip("frontend not present in this checkout")

    api_src = (backend / "app" / "routers" / "role_permissions.py").read_text(
        encoding="utf-8"
    )
    tail = api_src[api_src.index("reset-all"):]
    m = re.search(r"require_roles\(([^)]*)\)", tail)
    assert m, "could not find require_roles for reset-all"
    aliases = {"SA": "super_admin", "OWNER": "owner", "GM": "general_manager"}
    api_roles = {
        aliases.get(r.strip().lstrip("*").strip(), r.strip().lstrip("*").strip())
        for r in m.group(1).split(",")
        if r.strip().lstrip("*").strip()
    }

    screen_src = screen.read_text(encoding="utf-8")
    g = re.search(r"const\s+RESET_ALL_ROLES[^=]*=\s*\[([^\]]*)\]", screen_src)
    assert g, "RESET_ALL_ROLES not found in role-permissions.tsx"
    ui_roles = set(re.findall(r"'([a-z_]+)'", g.group(1)))

    assert ui_roles == api_roles, (
        f"the UI offers reset-all to {sorted(ui_roles)} but the API allows "
        f"{sorted(api_roles)}"
    )


# ── 5. Cash-up carries the conductor's name ─────────────────────────────────
@pytest.mark.asyncio
async def test_cash_up_response_includes_conductor_name(client, conductor):
    """A conductor may not read the conductor directory.

    The cash-ups list therefore has to carry the name of the crew member
    who declared it, otherwise every card renders the literal word
    "Conductor" instead of a person's name.
    """
    resp = await client.get("/cash-ups", headers=conductor)
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    for item in items:
        assert "conductor_name" in item, (
            "the cash-up response must carry conductor_name"
        )


def test_cash_up_response_model_declares_conductor_name():
    from app.models.cash_up import CashUp

    assert "conductor_name" in CashUp.model_fields


@pytest.mark.asyncio
async def test_cash_up_carries_the_actual_crew_name(client, db, conductor):
    """The name is resolved, not merely present as an empty field."""
    from bson import ObjectId

    now = datetime.now(timezone.utc)
    conductor_doc_id = ObjectId()
    user_id = ObjectId()
    await db.users.insert_one({
        "_id": user_id,
        "email": "crew@transitos.app",
        "full_name": "Funke Adebayo",
        "phone": None,
        "role": "conductor",
        "branch_id": None,
        "status": "active",
        "hire_date": None,
        "photo_url": None,
        "password_hash": hash_password("Test#12345"),
        "is_active": True,
        "last_login_at": None,
        "created_at": now,
        "updated_at": now,
    })
    await db.conductors.insert_one({
        "_id": conductor_doc_id,
        "user_id": str(user_id),
        "badge_no": "LAG-CD-9999",
        "status": "active",
        "branch_id": None,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    })
    await db.cash_ups.insert_one({
        "_id": ObjectId(),
        "trip_id": "652f3a1b9c4d2e0011aabb503",
        "conductor_id": str(conductor_doc_id),
        "branch_id": "652f3a1b9c4d2e0011aabb001",
        "method": "cash",
        "amount": 1000.0,
        "reference": None,
        "breakdown": [{"method": "cash", "amount": 1000.0}],
        "declared_total": 1000.0,
        "status": "submitted",
        "expected_total": 1000.0,
        "variance": 0.0,
        "notes": "",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    })

    resp = await client.get("/cash-ups", headers=conductor)
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    names = {i.get("conductor_name") for i in items}
    assert "Funke Adebayo" in names, (
        f"expected the crew member's name on the cash-up; got {names}"
    )
