"""The demo seed must produce a working account for **every** role.

`backend/scripts/seed.py` is what a developer (or a GitHub Codespace)
runs to get a usable app: it creates the demo accounts, a branch, a
vehicle, a route and the driver/conductor profiles.

It used to seed only seven of the ten roles — `operations_manager`,
`chief_accountant` and `branch_accountant` had no demo account at all,
so those three screens could not be demoed without hand-creating a user
through the admin UI (which needs an account you do not have yet).

These tests seed an in-memory Mongo and then **actually log in** as each
account, so a demo login that is broken — a weak password, a missing
branch, a role the API will not accept — fails here rather than in
front of a demo.
"""

from __future__ import annotations

import pytest

from app.models.user import BRANCH_SCOPED_ROLES, UserRole
from app.core.security import validate_password_strength
from scripts.seed import DEMO_ACCOUNTS, seed_database


# ─── coverage ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_seed_creates_an_account_for_every_role(db):
    """Every role the permission system knows must have a demo account."""
    seeded_roles = {account["role"] for account, _ in DEMO_ACCOUNTS}
    every_role = {role.value for role in UserRole}

    missing = every_role - seeded_roles
    assert not missing, f"no demo account for: {sorted(missing)}"
    assert seeded_roles == every_role, (
        f"demo accounts cover roles the app does not have: "
        f"{sorted(seeded_roles - every_role)}"
    )


@pytest.mark.asyncio
async def test_seed_creates_one_user_per_role_in_the_database(db):
    accounts = await seed_database(db)
    assert len(accounts) == len(DEMO_ACCOUNTS)

    users = await db.users.find({}).to_list(length=None)
    assert len(users) == len(DEMO_ACCOUNTS), "duplicate demo users created"
    assert {u["role"] for u in users} == {r.value for r in UserRole}


# ─── the accounts actually work ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_every_demo_account_can_log_in_and_gets_its_own_role(db, client):
    """Log in as each demo account and confirm the role that comes back."""
    accounts = await seed_database(db)

    for account in accounts:
        r = await client.post(
            "/auth/login",
            json={"email": account["email"], "password": account["password"]},
        )
        assert r.status_code == 200, (
            f"{account['role']} could not log in: HTTP {r.status_code} {r.text}"
        )
        token = r.json()["data"]["access_token"]

        me = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200, f"/auth/me failed for {account['role']}"
        assert me.json()["data"]["role"] == account["role"], (
            f"{account['email']} logged in as {me.json()['data']['role']}, "
            f"expected {account['role']}"
        )


@pytest.mark.asyncio
async def test_demo_passwords_satisfy_the_strength_policy():
    """The seed must not ship a password the API would reject."""
    for account, _ in DEMO_ACCOUNTS:
        validate_password_strength(account["password"])  # raises on failure


# ─── branch scoping ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_branch_scoped_accounts_have_a_branch(db):
    """Every role whose *visibility* is limited by a branch gets one.

    Two different sets are involved:

    * ``BRANCH_SCOPED_ROLES`` — the API **requires** a ``branch_id`` at
      create time (branch_manager, branch_accountant, driver,
      conductor).
    * ``BRANCH_OPS_SCOPED`` — the roles whose branch-ops reads and
      writes (cash-ups, reports, expenses, fleet entities) are filtered
      by ``branch_id``. It adds ``fleet_manager``.

    A role in either set with no ``branch_id`` is not scoped at all:
    ``branch_scope_query()`` returns ``None`` and the actor sees every
    branch. Seeding a fleet manager *with* a branch is therefore the
    safe choice — it keeps their visibility narrowed to Lagos instead
    of company-wide.
    """
    from app.routers._common import BRANCH_OPS_SCOPED

    accounts = await seed_database(db)
    must_have_branch = {role.value for role in BRANCH_SCOPED_ROLES} | set(
        BRANCH_OPS_SCOPED
    )

    for account in accounts:
        user = await db.users.find_one({"email": account["email"]})
        if account["role"] in must_have_branch:
            assert user.get("branch_id"), (
                f"{account['role']} has no branch_id — its visibility would not "
                f"be scoped to a branch"
            )
        else:
            assert not user.get("branch_id"), (
                f"{account['role']} should not be branch-scoped"
            )


@pytest.mark.asyncio
async def test_seed_creates_the_supporting_demo_data(db):
    """The branch, vehicle, route and profiles the app expects."""
    await seed_database(db)

    assert await db.branches.count_documents({}) == 1
    assert await db.vehicles.count_documents({}) == 1
    assert await db.routes.count_documents({}) == 1
    assert await db.drivers.count_documents({}) == 1
    assert await db.conductors.count_documents({}) == 1

    branch = await db.branches.find_one({})
    assert branch["manager_id"], "the seeded branch has no manager"


# ─── idempotency ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_running_the_seed_twice_creates_no_duplicates(db):
    await seed_database(db)
    await seed_database(db)

    assert await db.users.count_documents({}) == len(DEMO_ACCOUNTS)
    assert await db.branches.count_documents({}) == 1
    assert await db.vehicles.count_documents({}) == 1


@pytest.mark.asyncio
async def test_rerunning_repairs_a_missing_branch_id(db):
    """An account created without a branch gets one on the next run."""
    await seed_database(db)
    await db.users.update_one(
        {"email": "ba.lagos@transitos.app"}, {"$set": {"branch_id": None}}
    )

    await seed_database(db)

    user = await db.users.find_one({"email": "ba.lagos@transitos.app"})
    assert user.get("branch_id"), "the re-run did not repair the branch_id"
