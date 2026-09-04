"""Seed script — bootstrap a super-admin + demo data for local dev.

Usage:
    cd /workspace/transitos/backend
    python -m scripts.seed

Idempotent: re-running won't duplicate. Reads connection from
``MONGODB_URL`` / ``MONGODB_DB_NAME`` env (default localhost:27017,
db ``transitos``).
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

# Allow running as ``python -m scripts.seed`` from the backend root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bson import ObjectId  # noqa: E402
from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import create_indexes  # noqa: E402
from app.services.auth import hash_password  # noqa: E402

logging.basicConfig(level="INFO", format="%(levelname)s %(message)s")
log = logging.getLogger("seed")


# ─── seed data ───────────────────────────────────────────────────────────────
SUPER_ADMIN = {
    "email": "chisomarinzeshasha@gmail.com",
    "password": "Admin#Transit2026!",
    "full_name": "Platform Admin",
    "phone": "+234-803-574-2789",
    "role": "super_admin",
}

OWNER = {
    "email": "owner@transitos.app",
    "password": "Owner#Transit2026!",
    "full_name": "Company Owner",
    "phone": "+1-555-0200",
    "role": "owner",
}

GENERAL_MANAGER = {
    "email": "gm@transitos.app",
    "password": "Gm#Transit2026!",
    "full_name": "General Manager",
    "phone": "+1-555-0300",
    "role": "general_manager",
}

BRANCH = {
    "name": "Lagos Main Branch",
    "code": "LOS-01",
    "city": "Lagos",
    "state": "Lagos",
    "address": "1 Marina Road, Lagos Island",
    "contact_phone": "+234-800-000-0001",
    "contact_email": "lagos@transit-os.app",
    "status": "active",
}

BRANCH_MANAGER_USER = {
    "email": "bm.lagos@transitos.app",
    "password": "Bm#Transit2026!",
    "full_name": "Lagos Branch Manager",
    "phone": "+234-800-000-0002",
    "role": "branch_manager",
}

FLEET_MANAGER_USER = {
    "email": "fm.lagos@transitos.app",
    "password": "Fm#Transit2026!",
    "full_name": "Lagos Fleet Manager",
    "phone": "+234-800-000-0003",
    "role": "fleet_manager",
}

DRIVER_USER = {
    "email": "driver1@transitos.app",
    "password": "Driver#Transit2026!",
    "full_name": "Adebayo Ogunlesi",
    "phone": "+234-800-000-0010",
    "role": "driver",
}

CONDUCTOR_USER = {
    "email": "conductor1@transitos.app",
    "password": "Conductor#Transit2026!",
    "full_name": "Funke Adebayo",
    "phone": "+234-800-000-0011",
    "role": "conductor",
}

VEHICLE = {
    "reg_number": "LSR-001-AA",
    "type": "bus",
    "capacity_seats": 50,
    "capacity_kg": 5000,
    "status": "available",
    "current_odometer_km": 0,
    "current_fuel_level": 100.0,
    "documents": [],
}

DRIVER_PROFILE = {
    "license_no": "LAG-DR-0001",
    "license_expiry": datetime(2030, 12, 31, tzinfo=timezone.utc),
    "years_experience": 8,
    "status": "active",
}

CONDUCTOR_PROFILE = {
    "badge_no": "LAG-CD-0001",
    "status": "active",
}

ROUTE = {
    "name": "Lagos → Ibadan Express",
    "type": "interstate",
    "origin_city": "Lagos",
    "destination_city": "Ibadan",
    "distance_km": 120.0,
    "base_fare_passenger": 2500.0,
    "base_fare_cargo_per_kg": 50.0,
    "estimated_duration_hours": 2.5,
    "intermediate_stops": [],
    "required_permits": ["interstate_license"],
    "is_active": True,
}


async def _upsert_user(db: Any, data: dict[str, Any]) -> str:
    """Insert if missing; return id."""
    existing = await db.users.find_one({"email": data["email"].lower()})
    if existing:
        log.info("user exists: %s", data["email"])
        return str(existing["_id"])

    now = datetime.now(timezone.utc)
    doc = {
        "email": data["email"].lower(),
        "full_name": data["full_name"],
        "phone": data.get("phone"),
        "role": data["role"],
        "branch_id": None,
        "status": "active",
        "hire_date": None,
        "photo_url": None,
        "password_hash": hash_password(data["password"]),
        "is_active": True,
        "last_login_at": None,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.users.insert_one(doc)
    log.info("user created: %s (%s)", data["email"], data["role"])
    return str(result.inserted_id)


async def _upsert_branch(db: Any, data: dict[str, Any]) -> str:
    existing = await db.branches.find_one({"code": data["code"]})
    if existing:
        log.info("branch exists: %s", data["code"])
        return str(existing["_id"])

    now = datetime.now(timezone.utc)
    doc = {**data, "manager_id": None, "is_active": True, "created_at": now, "updated_at": now}
    result = await db.branches.insert_one(doc)
    log.info("branch created: %s", data["code"])
    return str(result.inserted_id)


async def _upsert_vehicle(db: Any, data: dict[str, Any], branch_id: str) -> str:
    existing = await db.vehicles.find_one({"reg_number": data["reg_number"]})
    if existing:
        log.info("vehicle exists: %s", data["reg_number"])
        return str(existing["_id"])

    now = datetime.now(timezone.utc)
    doc = {**data, "branch_id": branch_id, "is_active": True, "created_at": now, "updated_at": now}
    result = await db.vehicles.insert_one(doc)
    log.info("vehicle created: %s", data["reg_number"])
    return str(result.inserted_id)


async def _upsert_driver(db: Any, data: dict[str, Any], user_id: str, branch_id: str) -> str:
    existing = await db.drivers.find_one({"user_id": user_id})
    if existing:
        log.info("driver profile exists for user %s", user_id)
        return str(existing["_id"])

    now = datetime.now(timezone.utc)
    doc = {
        **data,
        "user_id": user_id,
        "branch_id": branch_id,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.drivers.insert_one(doc)
    log.info("driver profile created: %s", data["license_no"])
    return str(result.inserted_id)


async def _upsert_conductor(db: Any, data: dict[str, Any], user_id: str, branch_id: str) -> str:
    existing = await db.conductors.find_one({"user_id": user_id})
    if existing:
        log.info("conductor profile exists for user %s", user_id)
        return str(existing["_id"])

    now = datetime.now(timezone.utc)
    doc = {
        **data,
        "user_id": user_id,
        "branch_id": branch_id,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.conductors.insert_one(doc)
    log.info("conductor profile created: %s", data["badge_no"])
    return str(result.inserted_id)


async def _upsert_route(db: Any, data: dict[str, Any], branch_id: str) -> str:
    existing = await db.routes.find_one({"name": data["name"], "branch_id": branch_id})
    if existing:
        log.info("route exists: %s", data["name"])
        return str(existing["_id"])

    now = datetime.now(timezone.utc)
    doc = {
        **data,
        "branch_id": branch_id,
        "origin_branch_id": branch_id,
        "destination_branch_id": branch_id,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.routes.insert_one(doc)
    log.info("route created: %s", data["name"])
    return str(result.inserted_id)


async def main() -> None:
    client = AsyncIOMotorClient(settings.mongodb_url, tz_aware=True)
    db = client[settings.mongodb_db_name]

    try:
        await create_indexes()
        log.info("indexes ensured")

        # 1. super admin
        sa_id = await _upsert_user(db, SUPER_ADMIN)
        # 2. owner + general manager
        await _upsert_user(db, OWNER)
        await _upsert_user(db, GENERAL_MANAGER)
        # 3. branch
        branch_id = await _upsert_branch(db, BRANCH)
        # 4. branch manager + fleet manager (branch-scoped)
        bm_id = await _upsert_user(db, BRANCH_MANAGER_USER)
        fm_id = await _upsert_user(db, FLEET_MANAGER_USER)
        await db.users.update_one(
            {"_id": ObjectId(bm_id)}, {"$set": {"branch_id": branch_id}}
        )
        await db.users.update_one(
            {"_id": ObjectId(fm_id)}, {"$set": {"branch_id": branch_id}}
        )
        # 5. driver + conductor users + profiles
        driver_user_id = await _upsert_user(db, DRIVER_USER)
        await db.users.update_one(
            {"_id": ObjectId(driver_user_id)}, {"$set": {"branch_id": branch_id}}
        )
        await _upsert_driver(db, DRIVER_PROFILE, driver_user_id, branch_id)

        conductor_user_id = await _upsert_user(db, CONDUCTOR_USER)
        await db.users.update_one(
            {"_id": ObjectId(conductor_user_id)}, {"$set": {"branch_id": branch_id}}
        )
        await _upsert_conductor(db, CONDUCTOR_PROFILE, conductor_user_id, branch_id)

        # 6. set branch manager
        await db.branches.update_one(
            {"_id": ObjectId(branch_id)}, {"$set": {"manager_id": bm_id}}
        )

        # 7. vehicle
        await _upsert_vehicle(db, VEHICLE, branch_id)
        # 8. route
        await _upsert_route(db, ROUTE, branch_id)

        log.info("=" * 60)
        log.info("SEED COMPLETE — logins (password shown for dev only):")
        for u in (SUPER_ADMIN, OWNER, GENERAL_MANAGER, BRANCH_MANAGER_USER, FLEET_MANAGER_USER, DRIVER_USER, CONDUCTOR_USER):
            log.info("  %-32s  %s", u["email"], u["password"])
        log.info("=" * 60)
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
