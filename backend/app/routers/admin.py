"""Admin endpoints — one-shot bootstrap + maintenance.

- ``POST /admin/seed`` — idempotent bootstrap of super_admin, owner, general_manager
  accounts plus a demo branch / vehicle / driver / conductor / route. Gated by the
  ``ADMIN_BOOTSTRAP_TOKEN`` env var. Returns 403 if not configured.

  After the first successful seed, a DB flag (``system_flags.bootstrap_completed``)
  permanently disables the endpoint — even if the env token is still set.
  Unset ``ADMIN_BOOTSTRAP_TOKEN`` after first use as an extra safeguard.
"""

from __future__ import annotations

import hmac
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.schemas.common import SingleResponse
from app.services import write_audit
from app.services.auth import hash_password

router = APIRouter(prefix="/admin", tags=["admin"])

_BOOTSTRAP_FLAG_KEY = "bootstrap_completed"


# ─── Seed payload (mirrors scripts/seed.py but in-app) ──────────────────────
SEED_USERS = [
    {
        "email": "admin@transitos.app",
        "password": "Admin#Transit2026!",
        "full_name": "Platform Admin",
        "phone": "+1-555-0100",
        "role": "super_admin",
    },
    {
        "email": "owner@transitos.app",
        "password": "Owner#Transit2026!",
        "full_name": "Company Owner",
        "phone": "+1-555-0200",
        "role": "owner",
    },
    {
        "email": "gm@transitos.app",
        "password": "Gm#Transit2026!",
        "full_name": "General Manager",
        "phone": "+1-555-0300",
        "role": "general_manager",
    },
]


def _check_bootstrap_token(provided: Optional[str]) -> None:
    """Compare provided token to the configured ``ADMIN_BOOTSTRAP_TOKEN``.

    Reads directly from ``os.environ`` (not the cached Settings singleton)
    so test fixtures that mutate the env at runtime work correctly.
    Uses constant-time comparison to avoid timing leaks.
    """
    expected = os.environ.get("ADMIN_BOOTSTRAP_TOKEN", "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Admin bootstrap is disabled. Set ADMIN_BOOTSTRAP_TOKEN in your "
                "environment to enable one-shot seeding, then unset it after success."
            ),
        )
    if not provided:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Admin-Token header is required",
        )
    if not hmac.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin token",
        )


async def _assert_bootstrap_not_completed(db: AsyncIOMotorDatabase) -> None:
    """Block re-use after the first successful seed (DB-level one-time lock)."""
    flag = await db.system_flags.find_one({"_id": _BOOTSTRAP_FLAG_KEY})
    if flag and flag.get("value") is True:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Bootstrap has already been completed on this database. "
                "The /admin/seed endpoint is permanently disabled. "
                "Unset ADMIN_BOOTSTRAP_TOKEN in your environment."
            ),
        )


async def _mark_bootstrap_completed(db: AsyncIOMotorDatabase) -> None:
    await db.system_flags.update_one(
        {"_id": _BOOTSTRAP_FLAG_KEY},
        {
            "$set": {
                "value": True,
                "completed_at": datetime.now(timezone.utc),
            }
        },
        upsert=True,
    )


@router.post(
    "/seed",
    response_model=SingleResponse[dict],
    status_code=200,
)
@limiter.limit("3/hour")
async def seed_bootstrap(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    """Idempotent resource creation, but one-shot at the endpoint level.

    Creates demo users / branch / vehicle / crew / route on first run.
    After success, sets ``system_flags.bootstrap_completed`` so subsequent
    calls return 403 regardless of the env token.
    """
    _check_bootstrap_token(x_admin_token)
    await _assert_bootstrap_not_completed(db)

    now = datetime.now(timezone.utc)
    created: dict[str, list[str]] = {
        "users": [],
        "branches": [],
        "vehicles": [],
        "drivers": [],
        "conductors": [],
        "routes": [],
    }
    skipped: dict[str, list[str]] = {k: [] for k in created}

    # ─── Users ────────────────────────────────────────────────────────────
    user_ids: dict[str, str] = {}
    for u in SEED_USERS:
        existing = await db.users.find_one({"email": u["email"].lower()})
        if existing:
            user_ids[u["email"]] = str(existing["_id"])
            skipped["users"].append(u["email"])
            continue
        doc = {
            "email": u["email"].lower(),
            "full_name": u["full_name"],
            "phone": u.get("phone"),
            "role": u["role"],
            "branch_id": None,
            "status": "active",
            "hire_date": None,
            "photo_url": None,
            "password_hash": hash_password(u["password"]),
            "is_active": True,
            "last_login_at": None,
            "created_at": now,
            "updated_at": now,
        }
        result = await db.users.insert_one(doc)
        user_ids[u["email"]] = str(result.inserted_id)
        created["users"].append(u["email"])

    # ─── Branch ──────────────────────────────────────────────────────────
    branch_code = "LOS-01"
    branch = await db.branches.find_one({"code": branch_code})
    if branch:
        branch_id = str(branch["_id"])
        skipped["branches"].append(branch_code)
    else:
        doc = {
            "name": "Lagos Main Branch",
            "code": branch_code,
            "city": "Lagos",
            "state": "Lagos",
            "address": "1 Marina Road, Lagos Island",
            "contact_phone": "+234-800-000-0001",
            "contact_email": "lagos@transitos.app",
            "gps": {"lat": 6.4474, "lng": 3.3903},
            "status": "active",
            "manager_id": None,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        result = await db.branches.insert_one(doc)
        branch_id = str(result.inserted_id)
        created["branches"].append(branch_code)

    # ─── Vehicle ──────────────────────────────────────────────────────────
    vehicle_reg = "LSR-001-AA"
    vehicle = await db.vehicles.find_one({"reg_number": vehicle_reg})
    if vehicle:
        skipped["vehicles"].append(vehicle_reg)
    else:
        doc = {
            "reg_number": vehicle_reg,
            "type": "bus",
            "capacity_seats": 50,
            "capacity_kg": 5000,
            "branch_id": branch_id,
            "home_terminal_id": None,
            "status": "available",
            "current_odometer_km": 0,
            "current_fuel_level": 100.0,
            "documents": [],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        await db.vehicles.insert_one(doc)
        created["vehicles"].append(vehicle_reg)

    # ─── Driver user + profile ───────────────────────────────────────────
    driver_email = "driver1@transitos.app"
    driver_user = await db.users.find_one({"email": driver_email})
    if driver_user:
        driver_user_id = str(driver_user["_id"])
        skipped["users"].append(driver_email)
    else:
        doc = {
            "email": driver_email,
            "full_name": "Adebayo Ogunlesi",
            "phone": "+234-800-000-0010",
            "role": "driver",
            "branch_id": branch_id,
            "status": "active",
            "hire_date": None,
            "photo_url": None,
            "password_hash": hash_password("Driver#Transit2026!"),
            "is_active": True,
            "last_login_at": None,
            "created_at": now,
            "updated_at": now,
        }
        result = await db.users.insert_one(doc)
        driver_user_id = str(result.inserted_id)
        created["users"].append(driver_email)

    driver_profile = await db.drivers.find_one({"user_id": driver_user_id})
    if driver_profile:
        skipped["drivers"].append(driver_user_id)
    else:
        from datetime import timedelta
        await db.drivers.insert_one({
            "user_id": driver_user_id,
            "branch_id": branch_id,
            "license_no": "LAG-DR-0001",
            "license_expiry": now + timedelta(days=730),
            "years_experience": 8,
            "status": "active",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        })
        created["drivers"].append(driver_user_id)

    # ─── Conductor user + profile ─────────────────────────────────────────
    conductor_email = "conductor1@transitos.app"
    conductor_user = await db.users.find_one({"email": conductor_email})
    if conductor_user:
        conductor_user_id = str(conductor_user["_id"])
        skipped["users"].append(conductor_email)
    else:
        doc = {
            "email": conductor_email,
            "full_name": "Funke Adebayo",
            "phone": "+234-800-000-0011",
            "role": "conductor",
            "branch_id": branch_id,
            "status": "active",
            "hire_date": None,
            "photo_url": None,
            "password_hash": hash_password("Conductor#Transit2026!"),
            "is_active": True,
            "last_login_at": None,
            "created_at": now,
            "updated_at": now,
        }
        result = await db.users.insert_one(doc)
        conductor_user_id = str(result.inserted_id)
        created["users"].append(conductor_email)

    conductor_profile = await db.conductors.find_one({"user_id": conductor_user_id})
    if conductor_profile:
        skipped["conductors"].append(conductor_user_id)
    else:
        await db.conductors.insert_one({
            "user_id": conductor_user_id,
            "branch_id": branch_id,
            "badge_no": "LAG-CD-0001",
            "status": "active",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        })
        created["conductors"].append(conductor_user_id)

    # ─── Branch Manager + Fleet Manager (Lagos) ───────────────────────────
    for role_email, role_name, role_phone, role_value, password in (
        ("bm.lagos@transitos.app", "Lagos Branch Manager", "+234-800-000-0002", "branch_manager", "Bm#Transit2026!"),
        ("fm.lagos@transitos.app", "Lagos Fleet Manager", "+234-800-000-0003", "fleet_manager", "Fm#Transit2026!"),
    ):
        existing_role_user = await db.users.find_one({"email": role_email})
        if existing_role_user:
            skipped["users"].append(role_email)
            continue
        doc = {
            "email": role_email,
            "full_name": role_name,
            "phone": role_phone,
            "role": role_value,
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
        await db.users.insert_one(doc)
        created["users"].append(role_email)

    # ─── Route ───────────────────────────────────────────────────────────
    route_name = "Lagos Marina Loop"
    route = await db.routes.find_one({"name": route_name, "branch_id": branch_id})
    if route:
        skipped["routes"].append(route_name)
    else:
        await db.routes.insert_one({
            "name": route_name,
            "branch_id": branch_id,
            "type": "intrastate",
            "origin_branch_id": branch_id,
            "destination_branch_id": branch_id,
            "origin_city": "Lagos",
            "destination_city": "Lagos",
            "distance_km": 25.0,
            "base_fare_passenger": 500.0,
            "base_fare_cargo_per_kg": 50.0,
            "estimated_duration_hours": 1.0,
            "intermediate_stops": [
                {
                    "name": "Victoria Island",
                    "lat": 6.4281,
                    "lng": 3.4219,
                    "eta_minutes": 15,
                },
                {
                    "name": "Ikeja",
                    "lat": 6.6018,
                    "lng": 3.3515,
                    "eta_minutes": 35,
                },
            ],
            "required_permits": [],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        })
        created["routes"].append(route_name)

    # ─── Permanent one-time lock ──────────────────────────────────────────
    await _mark_bootstrap_completed(db)

    await write_audit(
        db,
        action="admin_seed",
        entity_type="system",
        entity_id="bootstrap",
        actor_id=None,
        actor_email="admin-endpoint",
        metadata={"created": created, "skipped": skipped},
    )

    if settings.env == "dev":
        credentials: dict = {
            "note": "DEV ONLY — CHANGE ALL PASSWORDS BEFORE GOING LIVE.",
            "super_admin": {"email": "admin@transitos.app", "password": "Admin#Transit2026!"},
            "owner": {"email": "owner@transitos.app", "password": "Owner#Transit2026!"},
            "general_manager": {"email": "gm@transitos.app", "password": "Gm#Transit2026!"},
            "branch_manager": {"email": "bm.lagos@transitos.app", "password": "Bm#Transit2026!"},
            "fleet_manager": {"email": "fm.lagos@transitos.app", "password": "Fm#Transit2026!"},
            "driver": {"email": "driver1@transitos.app", "password": "Driver#Transit2026!"},
            "conductor": {"email": "conductor1@transitos.app", "password": "Conductor#Transit2026!"},
        }
    else:
        credentials = {
            "note": (
                "Plaintext passwords are omitted outside ENV=dev. "
                "Log in with the seeded emails and change every password immediately."
            ),
            "emails": [
                "admin@transitos.app",
                "owner@transitos.app",
                "gm@transitos.app",
                "bm.lagos@transitos.app",
                "fm.lagos@transitos.app",
                "driver1@transitos.app",
                "conductor1@transitos.app",
            ],
        }

    return SingleResponse[dict](
        data={
            "status": "ok",
            "summary": {
                "created": created,
                "skipped": skipped,
            },
            "credentials": credentials,
            "next_steps": [
                "1. Unset ADMIN_BOOTSTRAP_TOKEN in Railway (endpoint is also DB-locked).",
                "2. Log in as owner@transitos.app and change the password immediately.",
                "3. Replace the demo Branch Manager / Fleet Manager with real staff.",
                "4. Deactivate the demo driver / conductor accounts when real crew is onboarded.",
            ],
        }
    )


__all__ = ["router"]
