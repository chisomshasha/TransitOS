"""Drivers router — CRUD with RBAC + branch-scoping + audit."""

from __future__ import annotations

import re
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.rbac import CREW_READ, FLEET_OPS, require_roles
from app.models.driver import DriverStatus
from app.models.user import UserRole
from app.schemas.common import ListResponse, SingleResponse
from app.schemas.driver import (
    DriverCreateRequest,
    DriverResponse,
    DriverUpdateRequest,
)
from app.services import write_audit
from app.routers._common import (
    BRANCH_OPS_SCOPED,
    assert_branch_access,
    branch_scope_query,
    enforce_branch_write,
    enrich_one_with_user_fields,
    enrich_with_user_fields,
    oid,
    paginate,
    project,
    utcnow,
)

router = APIRouter(prefix="/drivers", tags=["drivers"])


@router.get("", response_model=ListResponse[DriverResponse])
async def list_drivers(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*CREW_READ)),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    q: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None),
    status_filter: Optional[DriverStatus] = Query(None, alias="status"),
):
    query: dict = {"is_active": True}
    if status_filter:
        query["status"] = status_filter.value
    if branch_id:
        query["branch_id"] = branch_id
    if q:
        rx = re.compile(re.escape(q), re.IGNORECASE)
        query["$or"] = [{"license_no": rx}]
    scope = branch_scope_query(user, roles=BRANCH_OPS_SCOPED)
    if scope:
        query.update(scope)

    result = await paginate(
        db,
        "drivers",
        page=page,
        page_size=page_size,
        query=query,
        sort=[("license_no", 1)],
    )
    await enrich_with_user_fields(db, result.items)
    return result


@router.get("/{driver_id}", response_model=SingleResponse[DriverResponse])
async def get_driver(
    driver_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*CREW_READ)),
):
    doc = await db.drivers.find_one({"_id": oid(driver_id), "is_active": True})
    if doc is None:
        raise HTTPException(status_code=404, detail="Driver not found")
    assert_branch_access(user, doc.get("branch_id"), roles=BRANCH_OPS_SCOPED)
    data = project(doc)
    await enrich_one_with_user_fields(db, data)
    return SingleResponse[DriverResponse](data=data)


@router.post("", response_model=SingleResponse[DriverResponse], status_code=201)
async def create_driver(
    body: DriverCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*FLEET_OPS)),
):
    if await db.drivers.find_one({"user_id": body.user_id}):
        raise HTTPException(status_code=409, detail="Driver record already exists for this user")

    if await db.drivers.find_one({"license_no": body.license_no}):
        raise HTTPException(status_code=409, detail="License number already in use")

    # Look up the user to get branch_id
    if not ObjectId.is_valid(body.user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id")
    user_doc = await db.users.find_one(
        {"_id": ObjectId(body.user_id), "is_active": True}
    )
    if user_doc is None:
        raise HTTPException(status_code=400, detail="User does not exist")
    if user_doc.get("role") != UserRole.DRIVER.value:
        raise HTTPException(
            status_code=400,
            detail=f"User role must be 'driver', got '{user_doc.get('role')}'",
        )

    branch_id = user_doc.get("branch_id")
    enforce_branch_write(actor, branch_id, roles=BRANCH_OPS_SCOPED)

    now = utcnow()
    payload = body.model_dump()
    payload.update(
        {
            "branch_id": branch_id,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    result = await db.drivers.insert_one(payload)
    payload["_id"] = result.inserted_id

    await write_audit(
        db,
        action="create",
        entity_type="driver",
        entity_id=str(result.inserted_id),
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=branch_id,
        after=project(payload),
    )
    data = project(payload)
    data["full_name"] = user_doc.get("full_name")
    data["email"] = user_doc.get("email")
    data["phone"] = user_doc.get("phone")
    return SingleResponse[DriverResponse](data=data)


@router.patch("/{driver_id}", response_model=SingleResponse[DriverResponse])
async def update_driver(
    driver_id: str,
    body: DriverUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*FLEET_OPS)),
):
    _id = oid(driver_id)
    existing = await db.drivers.find_one({"_id": _id, "is_active": True})
    if existing is None:
        raise HTTPException(status_code=404, detail="Driver not found")

    enforce_branch_write(actor, existing.get("branch_id"), roles=BRANCH_OPS_SCOPED)

    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        data = project(existing)
        await enrich_one_with_user_fields(db, data)
        return SingleResponse[DriverResponse](data=data)

    if "license_no" in updates and updates["license_no"] != existing["license_no"]:
        if await db.drivers.find_one(
            {"license_no": updates["license_no"], "_id": {"$ne": _id}}
        ):
            raise HTTPException(status_code=409, detail="License number already in use")

    updates["updated_at"] = utcnow()
    await db.drivers.update_one({"_id": _id}, {"$set": updates})
    new_doc = await db.drivers.find_one({"_id": _id})

    await write_audit(
        db,
        action="update",
        entity_type="driver",
        entity_id=driver_id,
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=existing.get("branch_id"),
        before=project(existing),
        after=project(new_doc),
    )
    data = project(new_doc)
    await enrich_one_with_user_fields(db, data)
    return SingleResponse[DriverResponse](data=data)


@router.delete("/{driver_id}", status_code=204)
async def delete_driver(
    driver_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*FLEET_OPS)),
):
    _id = oid(driver_id)
    existing = await db.drivers.find_one({"_id": _id, "is_active": True})
    if existing is None:
        raise HTTPException(status_code=404, detail="Driver not found")

    enforce_branch_write(actor, existing.get("branch_id"), roles=BRANCH_OPS_SCOPED)

    linked_trips = await db.trips.count_documents(
        {"driver_id": driver_id, "is_active": True, "status": {"$nin": ["cashed_up", "cancelled"]}}
    )
    if linked_trips > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Driver has {linked_trips} active trip(s) in progress; complete or cancel them before delete",
        )

    await db.drivers.update_one(
        {"_id": _id},
        {"$set": {"is_active": False, "deleted_at": utcnow(), "updated_at": utcnow()}},
    )
    await write_audit(
        db,
        action="delete",
        entity_type="driver",
        entity_id=driver_id,
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=existing.get("branch_id"),
        before=project(existing),
    )
    return None


__all__ = ["router"]
