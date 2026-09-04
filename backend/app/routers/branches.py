"""Branches router — CRUD with RBAC + audit."""

from __future__ import annotations

import re
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.rbac import READ_ALL, SAFETY_OPS, require_roles
from app.models.branch import Branch, BranchStatus
from app.schemas.branch import (
    BranchCreateRequest,
    BranchResponse,
    BranchUpdateRequest,
    SetManagerRequest,
)
from app.schemas.common import ListResponse, SingleResponse
from app.services import write_audit
from app.routers._common import (
    BRANCH_OPS_SCOPED,
    assert_branch_access,
    branch_scope_query,
    oid,
    paginate,
    project,
    utcnow,
)

router = APIRouter(prefix="/branches", tags=["branches"])


# ─── LIST ────────────────────────────────────────────────────────────────────
@router.get("", response_model=ListResponse[BranchResponse])
async def list_branches(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*READ_ALL)),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    q: Optional[str] = Query(None, description="Search by name / code / city"),
    status_filter: Optional[BranchStatus] = Query(None, alias="status"),
    is_active: Optional[bool] = Query(None),
):
    query: dict = {}
    if status_filter:
        query["status"] = status_filter.value
    if is_active is not None:
        query["is_active"] = is_active
    if q:
        rx = re.compile(re.escape(q), re.IGNORECASE)
        query["$or"] = [{"name": rx}, {"code": rx}, {"city": rx}]

    # Branch-scoped roles only see their own branch.
    if user.get("role") in BRANCH_OPS_SCOPED:
        bid = user.get("branch_id")
        if bid:
            query["_id"] = oid(bid)

    return await paginate(
        db,
        "branches",
        page=page,
        page_size=page_size,
        query=query,
        sort=[("name", 1)],
    )


# ─── GET ─────────────────────────────────────────────────────────────────────
@router.get("/{branch_id}", response_model=SingleResponse[BranchResponse])
async def get_branch(
    branch_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*READ_ALL)),
):
    doc = await db.branches.find_one({"_id": oid(branch_id), "is_active": True})
    if doc is None:
        raise HTTPException(status_code=404, detail="Branch not found")
    # Branch-scoped roles cannot read other branches.
    if user.get("role") in BRANCH_OPS_SCOPED:
        if str(doc.get("_id")) != user.get("branch_id"):
            raise HTTPException(status_code=404, detail="Branch not found")
    return SingleResponse[BranchResponse](data=project(doc))


# ─── CREATE ──────────────────────────────────────────────────────────────────
@router.post(
    "", response_model=SingleResponse[BranchResponse], status_code=201
)
async def create_branch(
    body: BranchCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*SAFETY_OPS)),
):
    # Uniqueness on code
    if await db.branches.find_one({"code": body.code}):
        raise HTTPException(status_code=409, detail=f"Branch code '{body.code}' already exists")

    payload = body.model_dump()
    now = utcnow()
    payload.update(
        {
            "manager_id": None,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    result = await db.branches.insert_one(payload)
    payload["_id"] = result.inserted_id

    await write_audit(
        db,
        action="create",
        entity_type="branch",
        entity_id=str(result.inserted_id),
        actor_id=user["id"],
        actor_email=user.get("email"),
        after=project(payload),
    )
    return SingleResponse[BranchResponse](data=project(payload))


# ─── PATCH ───────────────────────────────────────────────────────────────────
@router.patch("/{branch_id}", response_model=SingleResponse[BranchResponse])
async def update_branch(
    branch_id: str,
    body: BranchUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*SAFETY_OPS)),
):
    _id = oid(branch_id)
    existing = await db.branches.find_one({"_id": _id, "is_active": True})
    if existing is None:
        raise HTTPException(status_code=404, detail="Branch not found")

    BRANCH_NULLABLE = {"contact_phone", "contact_email", "gps", "bank_account", "manager_id"}
    raw = body.model_dump(exclude_unset=True)
    updates = {k: v for k, v in raw.items() if v is not None or k in BRANCH_NULLABLE}
    if not updates:
        return SingleResponse[BranchResponse](data=project(existing))

    if "code" in updates and updates["code"] != existing["code"]:
        if await db.branches.find_one({"code": updates["code"], "_id": {"$ne": _id}}):
            raise HTTPException(status_code=409, detail="Branch code already in use")

    updates["updated_at"] = utcnow()
    await db.branches.update_one({"_id": _id}, {"$set": updates})
    new_doc = await db.branches.find_one({"_id": _id})

    await write_audit(
        db,
        action="update",
        entity_type="branch",
        entity_id=branch_id,
        actor_id=user["id"],
        actor_email=user.get("email"),
        before=project(existing),
        after=project(new_doc),
    )
    return SingleResponse[BranchResponse](data=project(new_doc))


# ─── DELETE (soft) ──────────────────────────────────────────────────────────
@router.delete("/{branch_id}", status_code=204)
async def delete_branch(
    branch_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*SAFETY_OPS)),
):
    _id = oid(branch_id)
    existing = await db.branches.find_one({"_id": _id, "is_active": True})
    if existing is None:
        raise HTTPException(status_code=404, detail="Branch not found")

    # Block delete if any users / vehicles / drivers / conductors / routes
    # still reference this branch.
    linked_counts = {
        coll: await db[coll].count_documents(
            {"branch_id": branch_id, "is_active": True}
        )
        for coll in ("users", "vehicles", "drivers", "conductors", "routes")
    }
    total_linked = sum(linked_counts.values())
    if total_linked > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Branch has {total_linked} active linked records; reassign before delete",
        )

    await db.branches.update_one(
        {"_id": _id}, {"$set": {"is_active": False, "updated_at": utcnow()}}
    )
    await write_audit(
        db,
        action="delete",
        entity_type="branch",
        entity_id=branch_id,
        actor_id=user["id"],
        actor_email=user.get("email"),
        before=project(existing),
    )
    return None


# ─── SET MANAGER ─────────────────────────────────────────────────────────────
@router.post(
    "/{branch_id}/manager", response_model=SingleResponse[BranchResponse]
)
async def set_manager(
    branch_id: str,
    body: SetManagerRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*SAFETY_OPS)),
):
    _id = oid(branch_id)
    branch = await db.branches.find_one({"_id": _id, "is_active": True})
    if branch is None:
        raise HTTPException(status_code=404, detail="Branch not found")

    if body.manager_id:
        if not ObjectId.is_valid(body.manager_id):
            raise HTTPException(status_code=400, detail="Invalid manager id")
        mgr = await db.users.find_one({"_id": ObjectId(body.manager_id), "is_active": True})
        if mgr is None:
            raise HTTPException(status_code=404, detail="Manager user not found")
        if mgr.get("branch_id") != branch_id:
            raise HTTPException(
                status_code=400, detail="Manager must belong to this branch"
            )

    await db.branches.update_one(
        {"_id": _id},
        {"$set": {"manager_id": body.manager_id, "updated_at": utcnow()}},
    )
    new_doc = await db.branches.find_one({"_id": _id})

    await write_audit(
        db,
        action="set_manager",
        entity_type="branch",
        entity_id=branch_id,
        actor_id=user["id"],
        actor_email=user.get("email"),
        before=project(branch),
        after=project(new_doc),
    )
    return SingleResponse[BranchResponse](data=project(new_doc))


__all__ = ["router"]
