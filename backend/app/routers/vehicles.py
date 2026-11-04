"""Vehicles router — CRUD with RBAC + branch-scoping + audit."""

from __future__ import annotations

import re
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.rbac import CREW_READ, FLEET_OPS, READ_ALL, require_roles
from app.models.user import UserRole
from app.models.vehicle import VehicleStatus
from app.schemas.common import ListResponse, SingleResponse
from app.schemas.vehicle import (
    VehicleCreateRequest,
    VehicleResponse,
    VehicleUpdateRequest,
)
from app.services import write_audit
from app.routers._common import (
    BRANCH_OPS_SCOPED,
    assert_branch_access,
    branch_scope_query,
    enforce_branch_write,
    oid,
    paginate,
    project,
    utcnow,
)

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("", response_model=ListResponse[VehicleResponse])
async def list_vehicles(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*CREW_READ)),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    q: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None),
    status_filter: Optional[VehicleStatus] = Query(None, alias="status"),
):
    query: dict = {"is_active": True}
    if status_filter:
        query["status"] = status_filter.value
    if branch_id:
        query["branch_id"] = branch_id
    if q:
        rx = re.compile(re.escape(q), re.IGNORECASE)
        query["$or"] = [{"reg_number": rx}, {"home_terminal_id": rx}]
    scope = branch_scope_query(user, roles=BRANCH_OPS_SCOPED)
    if scope:
        query.update(scope)

    return await paginate(
        db,
        "vehicles",
        page=page,
        page_size=page_size,
        query=query,
        sort=[("reg_number", 1)],
    )


@router.get("/{vehicle_id}", response_model=SingleResponse[VehicleResponse])
async def get_vehicle(
    vehicle_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*CREW_READ)),
):
    doc = await db.vehicles.find_one({"_id": oid(vehicle_id), "is_active": True})
    if doc is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    assert_branch_access(user, doc.get("branch_id"), roles=BRANCH_OPS_SCOPED)
    return SingleResponse[VehicleResponse](data=project(doc))


@router.post("", response_model=SingleResponse[VehicleResponse], status_code=201)
async def create_vehicle(
    body: VehicleCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*FLEET_OPS)),
):
    if await db.vehicles.find_one({"reg_number": body.reg_number}):
        raise HTTPException(status_code=409, detail="Registration number already in use")

    if not ObjectId.is_valid(body.branch_id) or not await db.branches.find_one(
        {"_id": ObjectId(body.branch_id), "is_active": True}
    ):
        raise HTTPException(status_code=400, detail="Branch does not exist")

    enforce_branch_write(actor, body.branch_id, roles=BRANCH_OPS_SCOPED)

    now = utcnow()
    payload = body.model_dump()
    payload.update({"is_active": True, "created_at": now, "updated_at": now})

    result = await db.vehicles.insert_one(payload)
    payload["_id"] = result.inserted_id

    await write_audit(
        db,
        action="create",
        entity_type="vehicle",
        entity_id=str(result.inserted_id),
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=body.branch_id,
        after=project(payload),
    )
    return SingleResponse[VehicleResponse](data=project(payload))


@router.patch("/{vehicle_id}", response_model=SingleResponse[VehicleResponse])
async def update_vehicle(
    vehicle_id: str,
    body: VehicleUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*FLEET_OPS)),
):
    _id = oid(vehicle_id)
    existing = await db.vehicles.find_one({"_id": _id, "is_active": True})
    if existing is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    enforce_branch_write(actor, existing.get("branch_id"), roles=BRANCH_OPS_SCOPED)

    VEHICLE_NULLABLE = {"home_terminal_id"}
    raw = body.model_dump(exclude_unset=True)
    updates = {k: v for k, v in raw.items() if v is not None or k in VEHICLE_NULLABLE}
    if not updates:
        return SingleResponse[VehicleResponse](data=project(existing))

    if "reg_number" in updates and updates["reg_number"] != existing["reg_number"]:
        if await db.vehicles.find_one(
            {"reg_number": updates["reg_number"], "_id": {"$ne": _id}}
        ):
            raise HTTPException(status_code=409, detail="Registration number already in use")

    updates["updated_at"] = utcnow()
    await db.vehicles.update_one({"_id": _id}, {"$set": updates})
    new_doc = await db.vehicles.find_one({"_id": _id})

    await write_audit(
        db,
        action="update",
        entity_type="vehicle",
        entity_id=vehicle_id,
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=existing.get("branch_id"),
        before=project(existing),
        after=project(new_doc),
    )
    return SingleResponse[VehicleResponse](data=project(new_doc))


@router.delete("/{vehicle_id}", status_code=204)
async def delete_vehicle(
    vehicle_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*FLEET_OPS)),
):
    _id = oid(vehicle_id)
    existing = await db.vehicles.find_one({"_id": _id, "is_active": True})
    if existing is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    enforce_branch_write(actor, existing.get("branch_id"), roles=BRANCH_OPS_SCOPED)

    if existing.get("status") == VehicleStatus.ON_TRIP.value:
        raise HTTPException(status_code=409, detail="Vehicle is currently on a trip")

    await db.vehicles.update_one(
        {"_id": _id},
        {"$set": {"is_active": False, "deleted_at": utcnow(), "updated_at": utcnow()}},
    )
    await write_audit(
        db,
        action="delete",
        entity_type="vehicle",
        entity_id=vehicle_id,
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=existing.get("branch_id"),
        before=project(existing),
    )
    return None


__all__ = ["router"]
