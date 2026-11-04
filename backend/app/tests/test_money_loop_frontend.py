"""The money loop must be reachable from the app, not only from curl.

The 4th audit pass found that the backend could advance a trip and submit
a cash-up perfectly well — and that the app had **no button for either**.
The hooks existed (``useChangeTripStatus``, ``useSubmitCashUp``), the
endpoints existed, the API worked; but no screen called the hooks, so a
trip could never reach ``closed``, a cash-up could never leave ``draft``,
and the whole money loop was a feature that only ``curl`` could reach.

Every static check passed while that was true. That is what this file is
for. It proves, from the source and from the running API, that

* the trip detail screen can advance a trip through its lifecycle;
* a cash-up can be submitted for approval from the app;
* the manifest can be filled in and corrected from the app, so the
  "expected" figure a cash-up is measured against is a real number;
* the role lists the app uses are the ones the backend enforces.

The negative tests matter as much as the positive ones: they prove the
guards still bite. A guard that cannot fail is worse than no guard,
because it is trusted.
"""

from __future__ import annotations

import pathlib
import re
import sys
from datetime import datetime, timedelta, timezone

import pytest

BACKEND = pathlib.Path(__file__).resolve().parents[2]
FRONTEND = BACKEND.parent / "frontend"
REPO = BACKEND.parent

sys.path.insert(0, str(REPO / "tools" / "contract"))

import check  # noqa: E402
import payloads  # noqa: E402


# ── the money-loop endpoints the app has to be able to reach ────────────────

MONEY_LOOP_ENDPOINTS = {
    ("PATCH", "/trips/{}/status"),
    ("POST", "/trips/{}/manifest"),
    ("DELETE", "/trips/{}/manifest/{}"),
    ("POST", "/cash-ups"),
    ("PATCH", "/cash-ups/{}"),
    ("POST", "/cash-ups/{}/submit"),
    ("POST", "/cash-ups/{}/approve"),
    ("POST", "/cash-ups/{}/reject"),
}


def _frontend_calls() -> set[tuple[str, str]]:
    return {(c["method"], c["path"]) for c in check.frontend_calls()}


# ── the app really calls them ───────────────────────────────────────────────


@pytest.mark.parametrize("endpoint", sorted(MONEY_LOOP_ENDPOINTS))
def test_the_app_calls_every_money_loop_endpoint(endpoint):
    """Each money-loop endpoint is called from a screen or a component.

    If a button is deleted, the call disappears and this fails — which
    is exactly when the feature has to be noticed.
    """
    assert endpoint in _frontend_calls(), (
        f"{endpoint[0]} {endpoint[1]} is no longer called from the app. The money loop "
        "needs a button for it."
    )


@pytest.mark.parametrize("endpoint", sorted(MONEY_LOOP_ENDPOINTS))
def test_no_money_loop_endpoint_is_baselined_as_unreachable(endpoint):
    """The endpoints are reachable, so they must not sit in the baseline.

    ``KNOWN_UNREACHABLE`` is the list of endpoints the app cannot reach.
    An entry there means "we know this is missing". Leaving an entry in
    place after the screen has landed would silently switch the guard
    off — the next regression would no longer be reported.
    """
    assert endpoint not in check.KNOWN_UNREACHABLE, (
        f"{endpoint[0]} {endpoint[1]} is in KNOWN_UNREACHABLE but the app can reach it; "
        "remove the baseline entry so the guard covers it again"
    )


def test_the_trip_detail_screen_advances_the_trip():
    """The trip screen (or a component it renders) can change the status."""
    symbol_map = check._symbol_to_screens()
    calls = [c for c in check.frontend_calls()
             if (c["method"], c["path"]) == ("PATCH", "/trips/{}/status")]
    assert calls, "no call to the trip-status endpoint"

    screens = set()
    for call in calls:
        screens |= check._screens_for_call(call, symbol_map)
    assert any("trips" in s for s in screens), (
        "the trip-status endpoint is not reachable from any trip screen"
    )


def test_a_cash_up_can_be_submitted_from_the_app():
    """A draft cash-up can be moved to ``submitted`` from the app."""
    symbol_map = check._symbol_to_screens()
    calls = [c for c in check.frontend_calls()
             if (c["method"], c["path"]) == ("POST", "/cash-ups/{}/submit")]
    assert calls, "no call to the cash-up submit endpoint"

    screens = set()
    for call in calls:
        screens |= check._screens_for_call(call, symbol_map)
    assert screens, "the cash-up submit endpoint is not reachable from any screen"


# ── the app and the backend agree on the rules ─────────────────────────────


def _frontend_role_constants() -> dict[str, list[str]]:
    return check._role_constants()


def test_the_role_lists_match_the_backend():
    """The frontend role lists are the backend's role lists.

    ``frontend/lib/money-loop.ts`` mirrors the constants in
    ``app/routers/trips.py`` and ``app/routers/cash_ups.py``. If either
    side changes, the app would offer a button the backend refuses (or
    hide one it allows), so the two are compared here.
    """
    from app.routers.cash_ups import CASHUP_APPROVE, CASHUP_MUTATE
    from app.routers.trips import TRIPS_MANIFEST_MUTATE, TRIPS_MUTATE

    constants = _frontend_role_constants()
    expected = {
        "TRIP_MUTATE_ROLES": [r.value for r in TRIPS_MUTATE],
        "TRIP_MANIFEST_MUTATE_ROLES": [r.value for r in TRIPS_MANIFEST_MUTATE],
        "CASH_UP_MUTATE_ROLES": [r.value for r in CASHUP_MUTATE],
        "CASH_UP_APPROVE_ROLES": [r.value for r in CASHUP_APPROVE],
    }
    for name, roles in expected.items():
        assert name in constants, f"{name} is missing from the frontend"
        assert sorted(constants[name]) == sorted(roles), (
            f"{name} is {constants[name]} in the frontend but {roles} in the backend"
        )


def test_the_transition_table_matches_the_backend():
    """The frontend state machine is the backend state machine."""
    from app.models.trip import TRIP_TRANSITIONS

    src = (FRONTEND / "lib" / "money-loop.ts").read_text(encoding="utf-8")
    block = re.search(r"TRIP_TRANSITIONS[^=]*=\s*\{(.*?)\n\};", src, re.S)
    assert block, "TRIP_TRANSITIONS is missing from frontend/lib/money-loop.ts"

    frontend_map: dict[str, list[str]] = {}
    for status, targets in re.findall(
        r"(\w+):\s*\[([^\]]*)\]", block.group(1)
    ):
        frontend_map[status] = re.findall(r"'([a-z_]+)'", targets)

    backend_map = {
        key.value: sorted(v.value for v in values)
        for key, values in TRIP_TRANSITIONS.items()
    }
    for status, targets in backend_map.items():
        assert status in frontend_map, f"{status} is missing from the frontend table"
        assert sorted(frontend_map[status]) == targets, (
            f"the frontend allows {frontend_map[status]} from '{status}'; the backend "
            f"allows {targets}"
        )


def test_the_endpoint_guard_table_agrees_with_the_backend():
    """``ENDPOINT_GUARDS`` never offers an action to a refused role."""
    guards = check._endpoint_guards()
    assert guards, "ENDPOINT_GUARDS is missing from frontend/lib/rbac.ts"

    roles = check.endpoint_roles()
    ops = check.openapi_ops()
    by_norm = {
        (o["method"], check._norm(o["path"])): roles.get((o["method"], o["path"]))
        for o in ops
    }
    for (method, path), guard_roles in guards.items():
        info = by_norm.get((method, path))
        assert info is not None, f"{method} {path} is not a backend route"
        extra = sorted(set(guard_roles) - set(info["roles"]))
        assert not extra, (
            f"the app offers {method} {path} to {extra}, but the backend allows only "
            f"{sorted(info['roles'])}"
        )


def test_the_cash_up_needs_a_closed_trip():
    """The app only offers a cash-up once the trip is closed.

    The backend refuses a cash-up for any other status with
    ``Trip must be 'closed' before cash-up``. The app states the same
    requirement rather than letting the user press a button that fails.
    """
    src = (FRONTEND / "lib" / "money-loop.ts").read_text(encoding="utf-8")
    match = re.search(r"CASH_UP_REQUIRES_TRIP_STATUS:\s*TripStatus\s*=\s*'([a-z_]+)'", src)
    assert match, "CASH_UP_REQUIRES_TRIP_STATUS is missing from frontend/lib/money-loop.ts"
    assert match.group(1) == "closed"


# ── the guards still bite ──────────────────────────────────────────────────


def test_the_reachability_guard_fails_when_the_status_button_is_removed(monkeypatch):
    """Delete the button and the guard must notice.

    This is the whole point of the file: the defect that started the
    audit — a feature that exists in the backend and not in the app —
    has to be impossible to reintroduce silently.

    The simulation removes the component that renders the button, so
    the hook in ``lib/queries.ts`` survives but nothing calls it any
    more. That is exactly the shape of the original defect: the
    endpoint and the hook were both there, and no screen reached them.
    """
    real_files = payloads.reachable_files

    def without_the_panel():
        return real_files() - {"components/TripStatusPanel.tsx"}

    monkeypatch.setattr(payloads, "reachable_files", without_the_panel)
    problems = check.check_reachable(check.openapi_ops(), check.frontend_calls())
    assert any("/trips/{}/status" in p for p in problems), (
        "the reachability guard did not notice that the trip-status call disappeared"
    )


def test_the_guard_check_fails_when_the_table_grants_too_much():
    """A guard table that offers a refused role must fail the check."""
    original = check._endpoint_guards

    def wrong_table():
        # 'driver' may not change a trip's status.
        return {("PATCH", "/trips/{}/status"): ["super_admin", "driver"]}

    check._endpoint_guards = wrong_table
    try:
        problems = check.check_guards(
            check.openapi_ops(), check.frontend_calls(), check.endpoint_roles()
        )
    finally:
        check._endpoint_guards = original
    assert problems, "the guard check accepted a table that offers a refused role"
    assert any("driver" in p for p in problems)


def test_the_rbac_check_fails_when_the_table_grants_too_much():
    """The RBAC check must use the table, not just the screen's gate."""
    original = check._endpoint_guards

    def wrong_table():
        return {("PATCH", "/trips/{}/status"): ["super_admin", "driver"]}

    check._endpoint_guards = wrong_table
    try:
        problems = check.check_rbac(
            check.openapi_ops(), check.frontend_calls(), check.endpoint_roles()
        )
    finally:
        check._endpoint_guards = original
    assert problems, "the RBAC check accepted a role the backend refuses"


# ── the API really does what the app says it does ──────────────────────────


@pytest.mark.asyncio
async def test_the_money_loop_runs_end_to_end(client, auth_headers, branch):
    """The whole loop, with the exact bodies the app sends.

    Manifest → advance → cash-up → submit → approve. The cash-up's
    ``expected_total`` is the manifest's fare sum, which is the number
    the conductor is judged against — so the app's manifest editor is
    what makes the variance meaningful.
    """
    from app.tests.test_trips import _seed_trip_context

    ctx = await _seed_trip_context(client, None, None, branch, auth_headers)
    now = datetime.now(timezone.utc)
    created = await client.post(
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
    assert created.status_code == 201, created.text
    trip_id = created.json()["data"]["id"]

    # The body the app's manifest editor sends.
    r = await client.post(
        f"/trips/{trip_id}/manifest",
        headers=auth_headers,
        json={
            "trip_id": trip_id,
            "type": "passenger",
            "passenger_name": "Ada Bello",
            "passenger_phone": "08030000001",
            "seat_number": "12",
            "fare": 2500.0,
            "payment_status": "on_board",
        },
    )
    assert r.status_code == 201, r.text
    entry_id = r.json()["data"]["id"]

    # A cargo entry, as the app's cargo form sends it.
    r = await client.post(
        f"/trips/{trip_id}/manifest",
        headers=auth_headers,
        json={
            "trip_id": trip_id,
            "type": "cargo",
            "cargo_description": "2 cartons of drinks",
            "cargo_weight_kg": 40.0,
            "cargo_sender_name": "Kola Stores",
            "cargo_receiver_phone": "08030000002",
            "fare": 1000.0,
            "payment_status": "paid",
        },
    )
    assert r.status_code == 201, r.text

    # The trip now knows its revenue.
    r = await client.get(f"/trips/{trip_id}", headers=auth_headers)
    assert r.json()["data"]["total_revenue"] == 3500.0
    assert r.json()["data"]["passenger_count"] == 1
    assert r.json()["data"]["cargo_weight_kg"] == 40.0

    # The app lets the manifest be corrected — the trash button.
    r = await client.delete(
        f"/trips/{trip_id}/manifest/{entry_id}", headers=auth_headers
    )
    assert r.status_code == 204, r.text
    r = await client.get(f"/trips/{trip_id}", headers=auth_headers)
    assert r.json()["data"]["total_revenue"] == 1000.0

    # The status panel: planned → boarding → departed → arrived → closed.
    for status in ("boarding", "departed", "arrived", "closed"):
        r = await client.patch(
            f"/trips/{trip_id}/status", headers=auth_headers, json={"status": status}
        )
        assert r.status_code == 200, f"{status}: {r.text}"
    assert r.json()["data"]["actual_departure"] is not None
    assert r.json()["data"]["actual_arrival"] is not None

    # The cash-up: saved as a draft first.
    r = await client.post(
        "/cash-ups",
        headers=auth_headers,
        json={
            "trip_id": trip_id,
            "conductor_id": ctx["conductor_id"],
            "branch_id": str(branch["_id"]),
            "breakdown": [{"method": "cash", "amount": 1000.0}],
            "declared_total": 1000.0,
        },
    )
    assert r.status_code == 201, r.text
    cash_up = r.json()["data"]
    assert cash_up["status"] == "draft"

    # Editing the draft — the app's "Update cash-up" button.
    r = await client.patch(
        f"/cash-ups/{cash_up['id']}",
        headers=auth_headers,
        json={
            "breakdown": [{"method": "cash", "amount": 950.0}],
            "declared_total": 950.0,
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["declared_total"] == 950.0

    # Submitting it — the button that was missing.
    r = await client.post(f"/cash-ups/{cash_up['id']}/submit", headers=auth_headers)
    assert r.status_code == 200, r.text
    submitted = r.json()["data"]
    assert submitted["status"] == "submitted"
    assert submitted["expected_total"] == 1000.0
    assert submitted["variance"] == -50.0

    # A second submit is refused — the button must not be double-firing.
    r = await client.post(f"/cash-ups/{cash_up['id']}/submit", headers=auth_headers)
    assert r.status_code == 409

    # Approval flips the trip to cashed_up.
    r = await client.post(
        f"/cash-ups/{cash_up['id']}/approve", headers=auth_headers, json={}
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["status"] == "approved"

    r = await client.get(f"/trips/{trip_id}", headers=auth_headers)
    assert r.json()["data"]["status"] == "cashed_up"
    assert r.json()["data"]["cash_up_id"] == cash_up["id"]
