"""Maintenance records router."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.rbac import BA, BM, CA, FM, GM, OWNER, SA, require_roles
from app.schemas.common import ListResponse, SingleResponse
from app.schemas.maintenance import (
    MaintenanceRecordCreateRequest,
    MaintenanceRecordResponse,
    MaintenanceRecordUpdateRequest,
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

router = APIRouter(prefix="/maintenance", tags=["maintenance"])

MAINT_READ = [SA, OWNER, GM, CA, BA, BM, FM]
MAINT_MUTATE = [SA, OWNER, GM, BM, FM]




@router.get("", response_model=ListResponse[MaintenanceRecordResponse])
async def list_maintenance(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*MAINT_READ)),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    vehicle_id: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
):
    query: dict = {"is_active": True}
    if vehicle_id:
        query["vehicle_id"] = vehicle_id
    if branch_id:
        query["branch_id"] = branch_id
    if type:
        query["type"] = type
    if status_filter:
        query["status"] = status_filter
    scope = branch_scope_query(user, roles=BRANCH_OPS_SCOPED)
    if scope:
        query.update(scope)
    return await paginate(
        db, "maintenance", page=page, page_size=page_size,
        query=query, sort=[("scheduled_for", -1)],
    )


@router.get(
    "/vehicle/{vehicle_id}/upcoming",
    response_model=ListResponse[MaintenanceRecordResponse],
)
async def upcoming_for_vehicle(
    vehicle_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*MAINT_READ)),
):
    """Scheduled/in-progress maintenance for one vehicle."""
    if not ObjectId.is_valid(vehicle_id):
        raise HTTPException(status_code=400, detail="Invalid vehicle_id")
    return await paginate(
        db, "maintenance", page=1, page_size=10,
        query={
            "vehicle_id": vehicle_id,
            "status": {"$in": ["scheduled", "in_progress"]},
            "is_active": True,
        },
        sort=[("scheduled_for", 1)],
    )


@router.post(
    "", response_model=SingleResponse[MaintenanceRecordResponse], status_code=201
)
async def create_maintenance(
    body: MaintenanceRecordCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*MAINT_MUTATE)),
):
    if not ObjectId.is_valid(body.vehicle_id) or not await db["vehicles"].find_one(
        {"_id": ObjectId(body.vehicle_id), "is_active": True}
    ):
        raise HTTPException(status_code=400, detail="Vehicle does not exist")
    enforce_branch_write(actor, body.branch_id, roles=BRANCH_OPS_SCOPED)

    now = utcnow()
    payload = body.model_dump()
    payload.update(
        {"is_active": True, "created_at": now, "updated_at": now}
    )
    result = await db["maintenance"].insert_one(payload)
    payload["_id"] = result.inserted_id

    # If status is completed, set vehicle back to available
    if body.status.value == "completed":
        await db["vehicles"].update_one(
            {"_id": ObjectId(body.vehicle_id)},
            {"$set": {"status": "available", "updated_at": now}},
        )

    await write_audit(
        db,
        action="create",
        entity_type="maintenance",
        entity_id=str(result.inserted_id),
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=body.branch_id,
        after=project(payload),
    )
    return SingleResponse[MaintenanceRecordResponse](data=project(payload))


@router.patch(
    "/{record_id}", response_model=SingleResponse[MaintenanceRecordResponse]
)
async def update_maintenance(
    record_id: str,
    body: MaintenanceRecordUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*MAINT_MUTATE)),
):
    if not ObjectId.is_valid(record_id):
        raise HTTPException(status_code=404, detail="Maintenance record not found")
    existing = await db["maintenance"].find_one({"_id": ObjectId(record_id), "is_active": True})
    if existing is None:
        raise HTTPException(status_code=404, detail="Maintenance record not found")
    enforce_branch_write(actor, existing.get("branch_id"), roles=BRANCH_OPS_SCOPED)
    MAINTENANCE_NULLABLE = {"description", "scheduled_for", "started_at", "completed_at", "odometer_km", "vendor_name", "next_due_km", "next_due_date", "notes"}
    raw = body.model_dump(exclude_unset=True)
    updates = {k: v for k, v in raw.items() if v is not None or k in MAINTENANCE_NULLABLE}
    if not updates:
        return SingleResponse[MaintenanceRecordResponse](data=project(existing))
    # Auto-derive cost_total if parts or labor provided
    if "cost_parts" in updates or "cost_labor" in updates:
        parts = updates.get("cost_parts", existing.get("cost_parts", 0.0))
        labor = updates.get("cost_labor", existing.get("cost_labor", 0.0))
        updates["cost_total"] = float(parts) + float(labor)
    updates["updated_at"] = utcnow()
    await db["maintenance"].update_one({"_id": ObjectId(record_id)}, {"$set": updates})
    new_doc = await db["maintenance"].find_one({"_id": ObjectId(record_id)})

    # Side effects on vehicle status
    if body.status is not None and body.status.value == "completed":
        await db["vehicles"].update_one(
            {"_id": ObjectId(existing["vehicle_id"])},
            {"$set": {"status": "available"}},
        )
    if body.status is not None and body.status.value == "in_progress":
        await db["vehicles"].update_one(
            {"_id": ObjectId(existing["vehicle_id"])},
            {"$set": {"status": "maintenance"}},
        )

    await write_audit(
        db,
        action="update",
        entity_type="maintenance",
        entity_id=record_id,
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=existing.get("branch_id"),
        before=project(existing),
        after=project(new_doc),
    )
    return SingleResponse[MaintenanceRecordResponse](data=project(new_doc))


@router.delete("/{record_id}", status_code=204)
async def delete_maintenance(
    record_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*MAINT_MUTATE)),
):
    if not ObjectId.is_valid(record_id):
        raise HTTPException(status_code=404, detail="Maintenance record not found")
    existing = await db["maintenance"].find_one({"_id": ObjectId(record_id), "is_active": True})
    if existing is None:
        raise HTTPException(status_code=404, detail="Maintenance record not found")
    enforce_branch_write(actor, existing.get("branch_id"), roles=BRANCH_OPS_SCOPED)
    await db["maintenance"].update_one(
        {"_id": ObjectId(record_id)},
        {"$set": {"is_active": False, "updated_at": utcnow()}},
    )
    return None


__all__ = ["router"]
