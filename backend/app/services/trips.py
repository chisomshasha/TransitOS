"""Trip lifecycle helpers — state machine, totals, manifest aggregation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.trip import TRIP_TRANSITIONS, TripStatus


# ─── state machine ───────────────────────────────────────────────────────────
def assert_transition(current: TripStatus, target: TripStatus) -> None:
    """Raise 409 if the transition is not allowed."""
    if current == target:
        return
    allowed = TRIP_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot transition trip from '{current.value}' to '{target.value}'",
        )


# ─── totals aggregation ──────────────────────────────────────────────────────
async def recompute_trip_totals(
    db: AsyncIOMotorDatabase, trip_id: str
) -> dict[str, Any]:
    """Recompute passenger_count / cargo_weight_kg / total_revenue from manifest."""
    # Use bracket access for collection names — works with both Motor and mongomock.
    # Treat missing is_active as active (older docs / inserts that omit the flag).
    cursor = db["manifest"].find(
        {"trip_id": trip_id, "$or": [{"is_active": True}, {"is_active": {"$exists": False}}]}
    )
    passenger_count = 0
    cargo_weight_kg = 0.0
    total_revenue = 0.0
    async for entry in cursor:
        if entry.get("payment_status") == "cancelled":
            continue
        if entry.get("type") == "passenger":
            passenger_count += 1
        if entry.get("type") == "cargo":
            cargo_weight_kg += float(entry.get("cargo_weight_kg") or 0.0)
        total_revenue += float(entry.get("fare") or 0.0)

    expense_total = 0.0
    async for e in db["expenses"].find({"trip_id": trip_id, "is_active": True}):
        expense_total += float(e.get("amount") or 0.0)

    return {
        "passenger_count": passenger_count,
        "cargo_weight_kg": cargo_weight_kg,
        "total_revenue": total_revenue,
        "total_expenses": expense_total,
    }


async def update_trip_totals(db: AsyncIOMotorDatabase, trip_id: str) -> dict[str, Any]:
    totals = await recompute_trip_totals(db, trip_id)
    await db["trips"].update_one(
        {"_id": ObjectId(trip_id) if ObjectId.is_valid(trip_id) else trip_id},
        {"$set": totals},
    )
    return totals


# ─── create / status change helpers ──────────────────────────────────────────
async def get_trip_or_404(db: AsyncIOMotorDatabase, trip_id: str) -> dict[str, Any]:
    if not ObjectId.is_valid(trip_id):
        raise HTTPException(status_code=404, detail="Trip not found")
    doc = await db["trips"].find_one({"_id": ObjectId(trip_id), "is_active": True})
    if doc is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return doc


async def get_branch_id_for(
    db: AsyncIOMotorDatabase,
    *,
    route_id: Optional[str] = None,
    vehicle_id: Optional[str] = None,
) -> Optional[str]:
    if route_id and ObjectId.is_valid(route_id):
        r = await db["routes"].find_one({"_id": ObjectId(route_id)})
        if r:
            return r.get("branch_id")
    if vehicle_id and ObjectId.is_valid(vehicle_id):
        v = await db["vehicles"].find_one({"_id": ObjectId(vehicle_id)})
        if v:
            return v.get("branch_id")
    return None


__all__ = [
    "assert_transition",
    "recompute_trip_totals",
    "update_trip_totals",
    "get_trip_or_404",
    "get_branch_id_for",
]
