"""Conductors router — CRUD with RBAC + branch-scoping + audit."""

from __future__ import annotations

import re
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.rbac import CREW_READ, FLEET_OPS, require_roles
from app.models.conductor import ConductorStatus
from app.models.user import UserRole
from app.schemas.common import ListResponse, SingleResponse
from app.schemas.conductor import (
    ConductorCreateRequest,
    ConductorResponse,
    ConductorUpdateRequest,
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

router = APIRouter(prefix="/conductors", tags=["conductors"])


@router.get("", response_model=ListResponse[ConductorResponse])
async def list_conductors(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*CREW_READ)),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    q: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None),
    status_filter: Optional[ConductorStatus] = Query(None, alias="status"),
):
    query: dict = {"is_active": True}
    if status_filter:
        query["status"] = status_filter.value
    if branch_id:
        query["branch_id"] = branch_id
    if q:
        rx = re.compile(re.escape(q), re.IGNORECASE)
        query["$or"] = [{"badge_no": rx}]
    scope = branch_scope_query(user, roles=BRANCH_OPS_SCOPED)
    if scope:
        query.update(scope)

    result = await paginate(
        db,
        "conductors",
        page=page,
        page_size=page_size,
        query=query,
        sort=[("badge_no", 1)],
    )
    await enrich_with_user_fields(db, result.items)
    return result


@router.get("/{conductor_id}", response_model=SingleResponse[ConductorResponse])
async def get_conductor(
    conductor_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*CREW_READ)),
):
    doc = await db.conductors.find_one({"_id": oid(conductor_id), "is_active": True})
    if doc is None:
        raise HTTPException(status_code=404, detail="Conductor not found")
    assert_branch_access(user, doc.get("branch_id"), roles=BRANCH_OPS_SCOPED)
    data = project(doc)
    await enrich_one_with_user_fields(db, data)
    return SingleResponse[ConductorResponse](data=data)


@router.post("", response_model=SingleResponse[ConductorResponse], status_code=201)
async def create_conductor(
    body: ConductorCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*FLEET_OPS)),
):
    if await db.conductors.find_one({"user_id": body.user_id}):
        raise HTTPException(status_code=409, detail="Conductor record already exists for this user")

    if await db.conductors.find_one({"badge_no": body.badge_no}):
        raise HTTPException(status_code=409, detail="Badge number already in use")

    if not ObjectId.is_valid(body.user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id")
    user_doc = await db.users.find_one(
        {"_id": ObjectId(body.user_id), "is_active": True}
    )
    if user_doc is None:
        raise HTTPException(status_code=400, detail="User does not exist")
    if user_doc.get("role") != UserRole.CONDUCTOR.value:
        raise HTTPException(
            status_code=400,
            detail=f"User role must be 'conductor', got '{user_doc.get('role')}'",
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

    result = await db.conductors.insert_one(payload)
    payload["_id"] = result.inserted_id

    await write_audit(
        db,
        action="create",
        entity_type="conductor",
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
    return SingleResponse[ConductorResponse](data=data)


@router.patch("/{conductor_id}", response_model=SingleResponse[ConductorResponse])
async def update_conductor(
    conductor_id: str,
    body: ConductorUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*FLEET_OPS)),
):
    _id = oid(conductor_id)
    existing = await db.conductors.find_one({"_id": _id, "is_active": True})
    if existing is None:
        raise HTTPException(status_code=404, detail="Conductor not found")

    enforce_branch_write(actor, existing.get("branch_id"), roles=BRANCH_OPS_SCOPED)

    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        data = project(existing)
        await enrich_one_with_user_fields(db, data)
        return SingleResponse[ConductorResponse](data=data)

    if "badge_no" in updates and updates["badge_no"] != existing["badge_no"]:
        if await db.conductors.find_one(
            {"badge_no": updates["badge_no"], "_id": {"$ne": _id}}
        ):
            raise HTTPException(status_code=409, detail="Badge number already in use")

    updates["updated_at"] = utcnow()
    await db.conductors.update_one({"_id": _id}, {"$set": updates})
    new_doc = await db.conductors.find_one({"_id": _id})

    await write_audit(
        db,
        action="update",
        entity_type="conductor",
        entity_id=conductor_id,
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=existing.get("branch_id"),
        before=project(existing),
        after=project(new_doc),
    )
    data = project(new_doc)
    await enrich_one_with_user_fields(db, data)
    return SingleResponse[ConductorResponse](data=data)


@router.delete("/{conductor_id}", status_code=204)
async def delete_conductor(
    conductor_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*FLEET_OPS)),
):
    _id = oid(conductor_id)
    existing = await db.conductors.find_one({"_id": _id, "is_active": True})
    if existing is None:
        raise HTTPException(status_code=404, detail="Conductor not found")

    enforce_branch_write(actor, existing.get("branch_id"), roles=BRANCH_OPS_SCOPED)

    linked_trips = await db.trips.count_documents(
        {"conductor_id": conductor_id, "is_active": True, "status": {"$nin": ["cashed_up", "cancelled"]}}
    )
    if linked_trips > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Conductor has {linked_trips} active trip(s) in progress; complete or cancel them before delete",
        )

    await db.conductors.update_one(
        {"_id": _id},
        {"$set": {"is_active": False, "deleted_at": utcnow(), "updated_at": utcnow()}},
    )
    await write_audit(
        db,
        action="delete",
        entity_type="conductor",
        entity_id=conductor_id,
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=existing.get("branch_id"),
        before=project(existing),
    )
    return None


__all__ = ["router"]
