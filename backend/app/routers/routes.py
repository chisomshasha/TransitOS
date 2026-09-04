"""Routes router — CRUD with RBAC + branch-scoping + audit."""

from __future__ import annotations

import re
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.rbac import FLEET_OPS, READ_ALL, require_roles
from app.models.route import RouteType
from app.models.user import UserRole
from app.schemas.common import ListResponse, SingleResponse
from app.schemas.route import (
    RouteCreateRequest,
    RouteResponse,
    RouteUpdateRequest,
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

router = APIRouter(prefix="/routes", tags=["routes"])


def _branch_scope_for(actor: dict) -> Optional[dict]:
    # Routes can touch multiple branches; scope by home/origin/destination.
    if actor.get("role") in BRANCH_OPS_SCOPED:
        bid = actor.get("branch_id")
        if not bid:
            return None
        return {"$or": [
            {"branch_id": bid},
            {"origin_branch_id": bid},
            {"destination_branch_id": bid},
        ]}
    return None


@router.get("", response_model=ListResponse[RouteResponse])
async def list_routes(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*READ_ALL)),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    q: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None),
    route_type: Optional[RouteType] = Query(None, alias="type"),
    is_active: Optional[bool] = Query(None),
):
    query: dict = {"is_active": True}
    if route_type:
        query["type"] = route_type.value
    if is_active is not None:
        query["is_active"] = is_active
    if branch_id:
        query["branch_id"] = branch_id
    if q:
        rx = re.compile(re.escape(q), re.IGNORECASE)
        query["$or"] = [
            {"name": rx},
            {"origin_city": rx},
            {"destination_city": rx},
        ]
    scope = _branch_scope_for(user)
    if scope:
        query.update(scope)

    return await paginate(
        db,
        "routes",
        page=page,
        page_size=page_size,
        query=query,
        sort=[("name", 1)],
    )


@router.get("/{route_id}", response_model=SingleResponse[RouteResponse])
async def get_route(
    route_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*READ_ALL)),
):
    doc = await db.routes.find_one({"_id": oid(route_id)})
    if doc is None or not doc.get("is_active", True):
        raise HTTPException(status_code=404, detail="Route not found")
    scope = _branch_scope_for(user)
    if scope:
        branch = user.get("branch_id")
        if not any(doc.get(k) == branch for k in ("branch_id", "origin_branch_id", "destination_branch_id")):
            raise HTTPException(status_code=404, detail="Route not found")
    return SingleResponse[RouteResponse](data=project(doc))


@router.post("", response_model=SingleResponse[RouteResponse], status_code=201)
async def create_route(
    body: RouteCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*FLEET_OPS)),
):
    if body.origin_branch_id == body.destination_branch_id:
        raise HTTPException(
            status_code=400,
            detail="destination_branch_id must differ from origin_branch_id",
        )

    # Branch must exist
    for label, bid in (
        ("branch_id", body.branch_id),
        ("origin_branch_id", body.origin_branch_id),
        ("destination_branch_id", body.destination_branch_id),
    ):
        if not ObjectId.is_valid(bid) or not await db.branches.find_one(
            {"_id": ObjectId(bid), "is_active": True}
        ):
            raise HTTPException(status_code=400, detail=f"{label} does not exist")

    if actor["role"] == UserRole.BRANCH_MANAGER.value:
        if body.branch_id != actor.get("branch_id"):
            raise HTTPException(status_code=403, detail="Not your branch")

    now = utcnow()
    payload = body.model_dump()
    payload.update({"created_at": now, "updated_at": now})

    result = await db.routes.insert_one(payload)
    payload["_id"] = result.inserted_id

    await write_audit(
        db,
        action="create",
        entity_type="route",
        entity_id=str(result.inserted_id),
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=body.branch_id,
        after=project(payload),
    )
    return SingleResponse[RouteResponse](data=project(payload))


@router.patch("/{route_id}", response_model=SingleResponse[RouteResponse])
async def update_route(
    route_id: str,
    body: RouteUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*FLEET_OPS)),
):
    _id = oid(route_id)
    existing = await db.routes.find_one({"_id": _id})
    if existing is None or not existing.get("is_active", True):
        raise HTTPException(status_code=404, detail="Route not found")

    if actor["role"] == UserRole.BRANCH_MANAGER.value:
        if existing.get("branch_id") != actor.get("branch_id"):
            raise HTTPException(status_code=403, detail="Not your branch")

    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        return SingleResponse[RouteResponse](data=project(existing))

    # Cross-field validation: origin vs destination
    new_origin = updates.get("origin_branch_id", existing.get("origin_branch_id"))
    new_dest = updates.get("destination_branch_id", existing.get("destination_branch_id"))
    if new_origin == new_dest:
        raise HTTPException(
            status_code=400, detail="destination_branch_id must differ from origin_branch_id"
        )

    updates["updated_at"] = utcnow()
    await db.routes.update_one({"_id": _id}, {"$set": updates})
    new_doc = await db.routes.find_one({"_id": _id})

    await write_audit(
        db,
        action="update",
        entity_type="route",
        entity_id=route_id,
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=existing.get("branch_id"),
        before=project(existing),
        after=project(new_doc),
    )
    return SingleResponse[RouteResponse](data=project(new_doc))


@router.delete("/{route_id}", status_code=204)
async def delete_route(
    route_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*FLEET_OPS)),
):
    _id = oid(route_id)
    existing = await db.routes.find_one({"_id": _id})
    if existing is None or not existing.get("is_active", True):
        raise HTTPException(status_code=404, detail="Route not found")

    if actor["role"] == UserRole.BRANCH_MANAGER.value:
        if existing.get("branch_id") != actor.get("branch_id"):
            raise HTTPException(status_code=403, detail="Not your branch")

    linked_trips = await db.trips.count_documents(
        {
            "route_id": route_id,
            "is_active": True,
            "status": {"$nin": ["cashed_up", "cancelled"]},
        }
    )
    if linked_trips > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Route has {linked_trips} active trip(s) in progress; complete or cancel them before delete",
        )

    await db.routes.update_one(
        {"_id": _id},
        {"$set": {"is_active": False, "deleted_at": utcnow(), "updated_at": utcnow()}},
    )
    await write_audit(
        db,
        action="delete",
        entity_type="route",
        entity_id=route_id,
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=existing.get("branch_id"),
        before=project(existing),
    )
    return None


__all__ = ["router"]
