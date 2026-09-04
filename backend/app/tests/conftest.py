"""Pytest fixtures using ``mongomock-motor`` (in-memory async Mongo).

This means tests don't need a running mongod. For prod we use the real
Motor client; the test app swaps the dependency to mongomock via
``app.dependency_overrides[get_db]``.
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import AsyncIterator

# Bootstrap path BEFORE app import.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Force test settings BEFORE app import.
os.environ.setdefault("MONGODB_DB_NAME", "transitos_test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only-not-for-prod")

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from mongomock_motor import AsyncMongoMockClient  # noqa: E402

from app.core.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402
limiter.enabled = False  # disable in-process limits during tests
from app.services.auth import hash_password  # noqa: E402


# ─── event loop ──────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ─── mock client + DB override ───────────────────────────────────────────────
_mock_client = AsyncMongoMockClient()


def _mock_get_db():
    return _mock_client[os.environ["MONGODB_DB_NAME"]]


# Override before any test client is created.
app.dependency_overrides[get_db] = _mock_get_db


# ─── DB fixture (clean per test) ─────────────────────────────────────────────
@pytest_asyncio.fixture(autouse=True)
async def _clean_db():
    db = _mock_get_db()
    for coll in await db.list_collection_names():
        await db.drop_collection(coll)
    yield
    for coll in await db.list_collection_names():
        await db.drop_collection(coll)


# ─── client ──────────────────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ─── direct DB handle for fixtures ──────────────────────────────────────────
@pytest_asyncio.fixture
async def db():
    return _mock_get_db()


# ─── user / branch helpers ───────────────────────────────────────────────────
async def _create_user(db, *, email, role, branch_id=None, password="Test#12345"):
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    doc = {
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
    }
    result = await db.users.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


@pytest_asyncio.fixture
async def super_admin(db):
    return await _create_user(
        db, email="admin@transitos.app", role="super_admin", password="Admin#12345"
    )


@pytest_asyncio.fixture
async def branch(db):
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    doc = {
        "name": "Test Branch",
        "code": "TST-01",
        "city": "Test City",
        "state": "Test State",
        "address": "1 Test Street",
        "contact_phone": "+1-555-0000",
        "contact_email": "test@transitos.app",
        "status": "active",
        "manager_id": None,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.branches.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


@pytest_asyncio.fixture
async def branch_manager(db, branch):
    return await _create_user(
        db,
        email="bm@transitos.app",
        role="branch_manager",
        branch_id=str(branch["_id"]),
        password="Bm#1234567",
    )


@pytest_asyncio.fixture
async def driver_user(db, branch):
    return await _create_user(
        db,
        email="driver@transitos.app",
        role="driver",
        branch_id=str(branch["_id"]),
        password="Dr#1234567",
    )


@pytest_asyncio.fixture
async def auth_headers(client, super_admin):
    r = await client.post(
        "/auth/login", json={"email": "admin@transitos.app", "password": "Admin#12345"}
    )
    assert r.status_code == 200, r.text
    token = r.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def bm_auth_headers(client, branch_manager):
    r = await client.post(
        "/auth/login", json={"email": "bm@transitos.app", "password": "Bm#1234567"}
    )
    assert r.status_code == 200, r.text
    token = r.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ─── multi-branch scoping fixtures (test_branch_scoping.py) ──────────────────

async def _login(client, email: str, password: str) -> dict:
    r = await client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login failed for {email}: {r.text}"
    tokens = r.json()["data"]
    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
    }


@pytest_asyncio.fixture
async def other_branch(db):
    """A second branch used to prove isolation."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    doc = {
        "name": "Other Branch",
        "code": "OTH-01",
        "city": "Other City",
        "state": "Other State",
        "address": "99 Other Street",
        "contact_phone": "+1-555-9999",
        "contact_email": "other@transitos.app",
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


@pytest_asyncio.fixture
async def branch_a(db):
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    doc = {
        "name": "Branch Alpha",
        "code": "ALP-01",
        "city": "Alpha City",
        "state": "State A",
        "address": "1 Alpha Ave",
        "contact_phone": "+1-555-1000",
        "contact_email": "alpha@transitos.app",
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


@pytest_asyncio.fixture
async def branch_b(db):
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    doc = {
        "name": "Branch Beta",
        "code": "BET-01",
        "city": "Beta City",
        "state": "State B",
        "address": "2 Beta Blvd",
        "contact_phone": "+1-555-2000",
        "contact_email": "beta@transitos.app",
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


@pytest_asyncio.fixture
async def other_branch_user(db, other_branch):
    """User that belongs to ``other_branch`` (not the BM's branch)."""
    user = await _create_user(
        db,
        email="other.bm@transitos.app",
        role="driver",
        branch_id=str(other_branch["_id"]),
        password="Other#12345",
    )
    user["id"] = str(user["_id"])
    user["email"] = "other.bm@transitos.app"
    return user


@pytest_asyncio.fixture
async def other_branch_trip(db, other_branch):
    """Minimal trip doc on the other branch for list-scoping assertions."""
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    doc = {
        "branch_id": str(other_branch["_id"]),
        "route_id": None,
        "vehicle_id": None,
        "driver_id": None,
        "conductor_id": None,
        "status": "planned",
        "scheduled_departure": now + timedelta(hours=2),
        "scheduled_arrival": now + timedelta(hours=6),
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.trips.insert_one(doc)
    doc["_id"] = result.inserted_id
    doc["id"] = str(result.inserted_id)
    return doc


@pytest_asyncio.fixture
async def owner(db, client):
    """Owner user + access token for global-visibility tests."""
    user = await _create_user(
        db,
        email="owner@transitos.app",
        role="owner",
        password="Owner#12345",
    )
    tokens = await _login(client, "owner@transitos.app", "Owner#12345")
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "role": "owner",
        **tokens,
    }


# Enrich branch_manager fixture consumers that expect access_token.
# The original fixture returns the raw user doc; tests also need a token.
@pytest_asyncio.fixture
async def branch_manager_authed(client, branch_manager):
    """Branch manager with access_token attached (preferred for scoping tests)."""
    tokens = await _login(client, "bm@transitos.app", "Bm#1234567")
    return {
        "id": str(branch_manager["_id"]),
        "email": branch_manager["email"],
        "role": "branch_manager",
        "branch_id": branch_manager.get("branch_id"),
        **tokens,
    }
