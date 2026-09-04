"""FuelLog router — refueling events + analytics."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.rbac import BA, BM, CA, DRIVER, GM, OWNER, SA, require_roles
from app.schemas.common import ListResponse, SingleResponse
from app.schemas.fuel import (
    FuelLogCreateRequest,
    FuelLogResponse,
    FuelLogUpdateRequest,
)
from app.services import write_audit
from app.routers._common import (
    BRANCH_OPS_SCOPED,
    assert_branch_access,
    branch_scope_query,
    enforce_branch_write,
    paginate,
    project,
    utcnow,
)

router = APIRouter(prefix="/fuel-logs", tags=["fuel-logs"])

FUEL_READ = [SA, OWNER, GM, CA, BA, BM]
FUEL_MUTATE = [SA, OWNER, GM, CA, BA, BM, DRIVER]




@router.get("", response_model=ListResponse[FuelLogResponse])
async def list_fuel_logs(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*FUEL_READ)),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    vehicle_id: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None),
    occurred_from: Optional[datetime] = Query(None),
    occurred_to: Optional[datetime] = Query(None),
):
    query: dict = {"is_active": True}
    if vehicle_id:
        query["vehicle_id"] = vehicle_id
    if branch_id:
        query["branch_id"] = branch_id
    if occurred_from or occurred_to:
        rng: dict = {}
        if occurred_from:
            rng["$gte"] = occurred_from
        if occurred_to:
            rng["$lte"] = occurred_to
        query["occurred_at"] = rng
    scope = branch_scope_query(user, roles=BRANCH_OPS_SCOPED)
    if scope:
        query.update(scope)
    return await paginate(
        db, "fuel_logs", page=page, page_size=page_size,
        query=query, sort=[("occurred_at", -1)],
    )


@router.get(
    "/vehicle/{vehicle_id}/efficiency",
    response_model=SingleResponse[dict],
)
async def vehicle_fuel_efficiency(
    vehicle_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*FUEL_READ)),
    since: Optional[datetime] = Query(None),
):
    """Returns km / liter over the given window. Used by dashboard."""
    if not ObjectId.is_valid(vehicle_id):
        raise HTTPException(status_code=400, detail="Invalid vehicle_id")
    query: dict = {"vehicle_id": vehicle_id, "is_active": True}
    if since:
        query["occurred_at"] = {"$gte": since}
    logs = [log async for log in db["fuel_logs"].find(query).sort("occurred_at", 1)]
    if len(logs) < 2:
        return SingleResponse[dict](
            data={"km_per_liter": None, "total_liters": 0.0, "total_cost": 0.0, "samples": len(logs)}
        )
    first, last = logs[0], logs[-1]
    km = max(0, int(last.get("odometer_km") or 0) - int(first.get("odometer_km") or 0))
    total_liters = sum(float(log.get("liters") or 0.0) for log in logs)
    total_cost = sum(float(log.get("cost_total") or 0.0) for log in logs)
    km_per_liter = (km / total_liters) if total_liters > 0 else None
    return SingleResponse[dict](
        data={
            "km_per_liter": round(km_per_liter, 2) if km_per_liter is not None else None,
            "total_liters": round(total_liters, 2),
            "total_cost": round(total_cost, 2),
            "samples": len(logs),
        }
    )


@router.post(
    "", response_model=SingleResponse[FuelLogResponse], status_code=201
)
async def create_fuel_log(
    body: FuelLogCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*FUEL_MUTATE)),
):
    if not ObjectId.is_valid(body.vehicle_id) or not await db["vehicles"].find_one(
        {"_id": ObjectId(body.vehicle_id), "is_active": True}
    ):
        raise HTTPException(status_code=400, detail="Vehicle does not exist")
    enforce_branch_write(actor, body.branch_id, roles=BRANCH_OPS_SCOPED)

    now = utcnow()
    payload = body.model_dump()
    payload.update(
        {
            "recorded_by_id": actor["id"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    result = await db["fuel_logs"].insert_one(payload)
    payload["_id"] = result.inserted_id

    # Bump vehicle odometer + fuel level
    await db["vehicles"].update_one(
        {"_id": ObjectId(body.vehicle_id)},
        {
            "$set": {
                "current_odometer_km": body.odometer_km,
                "current_fuel_level": 100.0,  # refilled — assume full
                "updated_at": now,
            }
        },
    )

    await write_audit(
        db,
        action="create",
        entity_type="fuel_log",
        entity_id=str(result.inserted_id),
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=body.branch_id,
        after=project(payload),
    )
    return SingleResponse[FuelLogResponse](data=project(payload))


@router.patch(
    "/{fuel_log_id}", response_model=SingleResponse[FuelLogResponse]
)
async def update_fuel_log(
    fuel_log_id: str,
    body: FuelLogUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*FUEL_MUTATE)),
):
    if not ObjectId.is_valid(fuel_log_id):
        raise HTTPException(status_code=404, detail="Fuel log not found")
    existing = await db["fuel_logs"].find_one({"_id": ObjectId(fuel_log_id), "is_active": True})
    if existing is None:
        raise HTTPException(status_code=404, detail="Fuel log not found")
    enforce_branch_write(actor, existing.get("branch_id"), roles=BRANCH_OPS_SCOPED)
    FUEL_NULLABLE = {"station_name", "station_location", "receipt_url", "notes"}
    raw = body.model_dump(exclude_unset=True)
    updates = {k: v for k, v in raw.items() if v is not None or k in FUEL_NULLABLE}
    if not updates:
        return SingleResponse[FuelLogResponse](data=project(existing))
    updates["updated_at"] = utcnow()
    await db["fuel_logs"].update_one({"_id": ObjectId(fuel_log_id)}, {"$set": updates})
    new_doc = await db["fuel_logs"].find_one({"_id": ObjectId(fuel_log_id)})
    return SingleResponse[FuelLogResponse](data=project(new_doc))


@router.delete("/{fuel_log_id}", status_code=204)
async def delete_fuel_log(
    fuel_log_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*FUEL_MUTATE)),
):
    if not ObjectId.is_valid(fuel_log_id):
        raise HTTPException(status_code=404, detail="Fuel log not found")
    existing = await db["fuel_logs"].find_one({"_id": ObjectId(fuel_log_id), "is_active": True})
    if existing is None:
        raise HTTPException(status_code=404, detail="Fuel log not found")
    enforce_branch_write(actor, existing.get("branch_id"), roles=BRANCH_OPS_SCOPED)
    await db["fuel_logs"].update_one(
        {"_id": ObjectId(fuel_log_id)},
        {"$set": {"is_active": False, "updated_at": utcnow()}},
    )
    return None


__all__ = ["router"]
