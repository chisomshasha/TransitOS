"""Fleet positions router — live map data source.

GET /fleet/positions returns one synthetic position per active vehicle,
anchored near its home branch's GPS with a small random jitter so the
map is not a stack of coincident pins.

A real deployment would POST positions from a telematics device to
POST /vehicles/{id}/position (mounted in a future sprint); this router
is the read surface the live-map screen consumes today.
"""

from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.rbac import CREW_READ, require_roles
from app.models.vehicle_position import VehiclePositionResponse
from app.routers._common import BRANCH_OPS_SCOPED, branch_scope_query

router = APIRouter(prefix="/fleet", tags=["fleet"])


def _jitter(seed: str, magnitude_deg: float = 0.02) -> tuple[float, float]:
    """Deterministic small offset from a stable seed so positions don't jump."""
    h = hashlib.sha256(seed.encode("utf-8")).digest()
    a = (int.from_bytes(h[0:4], "big") / 0xFFFFFFFF - 0.5) * 2 * magnitude_deg
    b = (int.from_bytes(h[4:8], "big") / 0xFFFFFFFF - 0.5) * 2 * magnitude_deg
    return a, b


def _synthetic_speed(status: str, seed: str) -> float:
    """Mock speed based on trip status — on-trip vehicles appear moving."""
    if status != "on_trip":
        return 0.0
    # Deterministic 40–95 kph when on trip
    h = int.from_bytes(hashlib.sha256(seed.encode("utf-8")).digest()[8:12], "big")
    return 40 + (h % 56)


@router.get("/positions")
async def list_fleet_positions(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*CREW_READ)),
    branch_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
):
    """Return one synthetic position per active vehicle, in the user's scope."""
    scope = branch_scope_query(user, roles=BRANCH_OPS_SCOPED)
    query: dict = {"is_active": True, "status": {"$ne": "grounded"}}
    if branch_id:
        query["branch_id"] = branch_id
    if status_filter:
        query["status"] = status_filter
    if scope:
        query.update(scope)

    # Cache branch GPS so we don't re-read per vehicle
    branches = {}
    async for b in db.branches.find({}, {"gps": 1, "name": 1, "city": 1}):
        branches[str(b["_id"])] = b

    # Current trip → vehicle map (for driver_name lookup)
    trip_by_vehicle: dict[str, dict] = {}
    async for t in db.trips.find(
        {"status": {"$in": ["boarding", "departed"]}, "is_active": True},
        {"vehicle_id": 1, "driver_id": 1},
    ):
        trip_by_vehicle[str(t["vehicle_id"])] = t

    # Driver name cache
    driver_name_cache: dict[str, str] = {}
    async for d in db.drivers.find({"is_active": True}, {"full_name": 1}):
        driver_name_cache[str(d["_id"])] = d.get("full_name") or "Driver"

    items: list[dict] = []
    async for v in db.vehicles.find(query, {
        "reg_number": 1, "branch_id": 1, "status": 1, "home_terminal_id": 1,
    }):
        vid = str(v["_id"])
        b = branches.get(str(v.get("branch_id")))
        gps = (b or {}).get("gps") or {}
        lat = gps.get("lat")
        lng = gps.get("lng")
        if lat is None or lng is None:
            # Fallback: Abuja center with jitter so the vehicle still shows
            lat, lng = 9.057, 7.489

        dlat, dlng = _jitter(vid)
        status = v.get("status", "available")
        trip = trip_by_vehicle.get(vid)
        driver_name = None
        if trip and trip.get("driver_id"):
            driver_name = driver_name_cache.get(str(trip["driver_id"]))

        items.append(
            VehiclePositionResponse(
                vehicle_id=vid,
                branch_id=str(v.get("branch_id")),
                lat=lat + dlat,
                lng=lng + dlng,
                speed_kph=_synthetic_speed(status, vid),
                heading_deg=None,
                status=status,
                reg_number=v.get("reg_number"),
                driver_name=driver_name,
                trip_id=str(trip["_id"]) if trip else None,
                recorded_at=datetime.now(timezone.utc),
            ).model_dump()
        )

    # Sort by reg_number for stable rendering
    items.sort(key=lambda x: x.get("reg_number") or "")
    return {
        "items": items,
        "total": len(items),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


__all__ = ["router"]
