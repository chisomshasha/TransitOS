"""Users router — CRUD with RBAC + branch-scoping for branch roles."""

from __future__ import annotations

import re
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.rbac import (
    OWNER,
    SAFETY_OPS,
    USERS_READ,
    require_roles,
)
from app.models.user import UserRole, UserStatus
from app.schemas.common import ListResponse, SingleResponse
from app.schemas.user import (
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)
from app.services import write_audit
from app.services.auth import hash_password, revoke_all_user_tokens
from app.routers._common import (
    BRANCH_OPS_SCOPED,
    assert_branch_access,
    branch_scope_query,
    enforce_branch_write,
    oid,
    paginate,
    project_user,
    utcnow,
)

router = APIRouter(prefix="/users", tags=["users"])


# ─── LIST ────────────────────────────────────────────────────────────────────
@router.get("", response_model=ListResponse[UserResponse])
async def list_users(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*USERS_READ)),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    q: Optional[str] = Query(None, description="Search by name / email"),
    role: Optional[UserRole] = Query(None),
    branch_id: Optional[str] = Query(None),
    status_filter: Optional[UserStatus] = Query(None, alias="status"),
):
    query: dict = {}
    if role:
        query["role"] = role.value
    if status_filter:
        query["status"] = status_filter.value
    if branch_id:
        query["branch_id"] = branch_id
    if q:
        rx = re.compile(re.escape(q), re.IGNORECASE)
        query["$or"] = [{"full_name": rx}, {"email": rx}]

    # Branch-scoped roles can only see users in their own branch.
    scope = branch_scope_query(user, roles=BRANCH_OPS_SCOPED)
    if scope:
        query.update(scope)

    return await paginate(
        db,
        "users",
        page=page,
        page_size=page_size,
        query=query,
        sort=[("full_name", 1)],
        projection={"password_hash": 0},
    )


# ─── GET ─────────────────────────────────────────────────────────────────────
@router.get("/{user_id}", response_model=SingleResponse[UserResponse])
async def get_user(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*USERS_READ)),
):
    doc = await db.users.find_one(
        {"_id": oid(user_id), "is_active": True}, {"password_hash": 0}
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="User not found")

    assert_branch_access(user, doc.get("branch_id"), roles=BRANCH_OPS_SCOPED)

    return SingleResponse[UserResponse](data=project_user(doc))


# ─── CREATE ──────────────────────────────────────────────────────────────────
@router.post("", response_model=SingleResponse[UserResponse], status_code=201)
async def create_user(
    body: UserCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*SAFETY_OPS)),
):
    # Email uniqueness (case-insensitive — schema lowercases on input)
    if await db.users.find_one({"email": body.email.lower()}):
        raise HTTPException(status_code=409, detail="Email already in use")

    # Branch-scoped roles require a branch_id
    if body.role.value in (
        UserRole.BRANCH_MANAGER.value,
        UserRole.BRANCH_ACCOUNTANT.value,
        UserRole.DRIVER.value,
        UserRole.CONDUCTOR.value,
    ) and not body.branch_id:
        raise HTTPException(
            status_code=400,
            detail=f"branch_id is required for role '{body.role.value}'",
        )

    # Branch managers can only create branch-scoped users in their own branch
    if actor["role"] == UserRole.BRANCH_MANAGER.value:
        if body.role not in (
            UserRole.BRANCH_ACCOUNTANT,
            UserRole.DRIVER,
            UserRole.CONDUCTOR,
        ):
            raise HTTPException(
                status_code=403,
                detail="Branch managers can only create branch-accountants, drivers, and conductors",
            )
        if body.branch_id != actor.get("branch_id"):
            raise HTTPException(
                status_code=403,
                detail="Branch managers can only create users in their own branch",
            )

    # Branch must exist (if provided)
    if body.branch_id:
        if not ObjectId.is_valid(body.branch_id) or not await db.branches.find_one(
            {"_id": ObjectId(body.branch_id), "is_active": True}
        ):
            raise HTTPException(status_code=400, detail="Branch does not exist")

    now = utcnow()
    payload = body.model_dump()
    payload["email"] = payload["email"].lower()
    payload["password_hash"] = hash_password(payload.pop("password"))
    payload.update(
        {"is_active": True, "last_login_at": None, "created_at": now, "updated_at": now}
    )

    result = await db.users.insert_one(payload)
    new_doc = await db.users.find_one({"_id": result.inserted_id}, {"password_hash": 0})

    await write_audit(
        db,
        action="create",
        entity_type="user",
        entity_id=str(result.inserted_id),
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=payload.get("branch_id"),
        after=project_user(new_doc),
    )
    return SingleResponse[UserResponse](data=project_user(new_doc))


# ─── PATCH ───────────────────────────────────────────────────────────────────
@router.patch("/{user_id}", response_model=SingleResponse[UserResponse])
async def update_user(
    user_id: str,
    body: UserUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*SAFETY_OPS)),
):
    _id = oid(user_id)
    existing = await db.users.find_one({"_id": _id, "is_active": True})
    if existing is None:
        raise HTTPException(status_code=404, detail="User not found")

    if actor["role"] == UserRole.BRANCH_MANAGER.value:
        if existing.get("branch_id") != actor.get("branch_id"):
            raise HTTPException(status_code=403, detail="Not your branch")

    USER_NULLABLE = {"phone", "branch_id", "hire_date", "photo_url"}
    raw = body.model_dump(exclude_unset=True)
    updates = {k: v for k, v in raw.items() if v is not None or k in USER_NULLABLE}
    new_password = updates.pop("new_password", None)
    if not updates and new_password is None:
        return SingleResponse[UserResponse](data=project_user(existing))

    if "branch_id" in updates and updates["branch_id"]:
        if not ObjectId.is_valid(updates["branch_id"]) or not await db.branches.find_one(
            {"_id": ObjectId(updates["branch_id"]), "is_active": True}
        ):
            raise HTTPException(status_code=400, detail="Branch does not exist")

    if new_password is not None:
        updates["password_hash"] = hash_password(new_password)

    updates["updated_at"] = utcnow()
    await db.users.update_one({"_id": _id}, {"$set": updates})
    new_doc = await db.users.find_one({"_id": _id}, {"password_hash": 0})

    if new_password is not None:
        await revoke_all_user_tokens(db, user_id)
        await write_audit(
            db,
            action="admin_reset_password",
            entity_type="user",
            entity_id=user_id,
            actor_id=actor["id"],
            actor_email=actor.get("email"),
        )

    await write_audit(
        db,
        action="update",
        entity_type="user",
        entity_id=user_id,
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        before=project_user(existing),
        after=project_user(new_doc),
    )
    return SingleResponse[UserResponse](data=project_user(new_doc))


# ─── DELETE (soft) ──────────────────────────────────────────────────────────
@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*SAFETY_OPS)),
):
    _id = oid(user_id)
    existing = await db.users.find_one({"_id": _id, "is_active": True})
    if existing is None:
        raise HTTPException(status_code=404, detail="User not found")

    if existing["_id"] == ObjectId(actor["id"]):
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    if actor["role"] == UserRole.BRANCH_MANAGER.value:
        if existing.get("branch_id") != actor.get("branch_id"):
            raise HTTPException(status_code=403, detail="Not your branch")

    await db.users.update_one(
        {"_id": _id},
        {"$set": {"is_active": False, "deleted_at": utcnow(), "updated_at": utcnow()}},
    )
    await write_audit(
        db,
        action="delete",
        entity_type="user",
        entity_id=user_id,
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        before=project_user(existing),
    )
    return None


__all__ = ["router"]
