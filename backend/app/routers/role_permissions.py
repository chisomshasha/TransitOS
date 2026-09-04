"""Role-permissions router — view and edit the dynamic RBAC matrix.

Only SA / OWNER / GM can read or modify. On first GET the collection
is seeded from ``DEFAULT_PERMISSIONS`` so the UI always has data.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.rbac import require_roles
from app.core.roles import GM, OWNER, SA, Role
from app.models.role_permission import (
    ACTIONS,
    DEFAULT_PERMISSIONS,
    DEFAULT_SCOPES,
    RESOURCES,
    RolePermissionResponse,
    RolePermissionUpdate,
    SCOPES,
)
from app.routers._common import project, utcnow
from app.services import write_audit

router = APIRouter(prefix="/role-permissions", tags=["role-permissions"])


async def _ensure_seeded(db: AsyncIOMotorDatabase) -> None:
    """Seed the role_permissions collection if it's empty."""
    count = await db.role_permissions.count_documents({})
    if count > 0:
        return
    now = utcnow()
    docs = []
    for role_val, perms in DEFAULT_PERMISSIONS.items():
        docs.append(
            {
                "role": role_val,
                "permissions": perms,
                "scope": DEFAULT_SCOPES.get(role_val, "all"),
                "updated_at": now,
                "updated_by": "system",
            }
        )
    if docs:
        await db.role_permissions.insert_many(docs)


@router.get("", response_model=List[RolePermissionResponse])
async def list_role_permissions(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(SA, OWNER, GM)),
):
    """Return the full permissions matrix — one entry per role."""
    await _ensure_seeded(db)
    items = []
    async for doc in db.role_permissions.find().sort("role", 1):
        items.append(project(doc))
    return items


@router.get("/meta")
async def permissions_meta(
    user: dict = Depends(require_roles(SA, OWNER, GM)),
):
    """Return the static metadata (resources, actions, scopes, roles) for the matrix editor."""
    return {
        "resources": RESOURCES,
        "actions": ACTIONS,
        "scopes": SCOPES,
        "roles": [r.value for r in Role],
    }


@router.get("/{role_name}", response_model=RolePermissionResponse)
async def get_role_permissions(
    role_name: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(SA, OWNER, GM)),
):
    """Return permissions for a single role."""
    await _ensure_seeded(db)
    doc = await db.role_permissions.find_one({"role": role_name})
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No permissions found for role: {role_name}",
        )
    return project(doc)


@router.put("/{role_name}", response_model=RolePermissionResponse)
async def update_role_permissions(
    role_name: str,
    body: RolePermissionUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(SA, OWNER, GM)),
):
    """Replace the entire permission set for a role."""
    await _ensure_seeded(db)

    # Validate role exists
    valid_roles = {r.value for r in Role}
    if role_name not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown role: {role_name}",
        )

    # Validate resources
    for resource in body.permissions:
        if resource not in RESOURCES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown resource: {resource}",
            )

    # Validate actions
    for resource, actions in body.permissions.items():
        for action in actions:
            if action not in ACTIONS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unknown action '{action}' for resource '{resource}'",
                )

    # Validate scope
    if body.scope and body.scope not in SCOPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown scope: {body.scope}",
        )

    # Prevent locking yourself out: SA/OWNER must always have role_permissions.read
    if role_name in ("super_admin", "owner"):
        rp_perms = body.permissions.get("role_permissions", [])
        if "read" not in rp_perms:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot remove 'read' on role_permissions from {role_name}",
            )

    now = utcnow()
    existing = await db.role_permissions.find_one({"role": role_name})

    update_doc = {
        "permissions": body.permissions,
        "updated_at": now,
        "updated_by": actor.get("email") or actor["id"],
    }
    if body.scope:
        update_doc["scope"] = body.scope

    if existing:
        await db.role_permissions.update_one(
            {"role": role_name}, {"$set": update_doc}
        )
    else:
        update_doc["role"] = role_name
        if "scope" not in update_doc:
            update_doc["scope"] = DEFAULT_SCOPES.get(role_name, "all")
        await db.role_permissions.insert_one(update_doc)

    new_doc = await db.role_permissions.find_one({"role": role_name})

    await write_audit(
        db,
        action="update",
        entity_type="role_permission",
        entity_id=role_name,
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        before=project(existing) if existing else None,
        after=project(new_doc),
    )

    return project(new_doc)


@router.post("/{role_name}/reset", response_model=RolePermissionResponse)
async def reset_role_permissions(
    role_name: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(SA, OWNER, GM)),
):
    """Reset a role's permissions to the built-in defaults."""
    valid_roles = {r.value for r in Role}
    if role_name not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown role: {role_name}",
        )
    if role_name not in DEFAULT_PERMISSIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No default permissions defined for role: {role_name}",
        )

    now = utcnow()
    existing = await db.role_permissions.find_one({"role": role_name})

    default_perms = DEFAULT_PERMISSIONS[role_name]
    default_scope = DEFAULT_SCOPES.get(role_name, "all")

    update_doc = {
        "permissions": default_perms,
        "scope": default_scope,
        "updated_at": now,
        "updated_by": actor.get("email") or actor["id"],
    }

    if existing:
        await db.role_permissions.update_one(
            {"role": role_name}, {"$set": update_doc}
        )
    else:
        update_doc["role"] = role_name
        await db.role_permissions.insert_one(update_doc)

    new_doc = await db.role_permissions.find_one({"role": role_name})

    await write_audit(
        db,
        action="update",
        entity_type="role_permission",
        entity_id=role_name,
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        before=project(existing) if existing else None,
        after=project(new_doc),
        metadata={"reason": "reset_to_defaults"},
    )

    return project(new_doc)


@router.post("/reset-all", status_code=204)
async def reset_all_role_permissions(
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(SA, OWNER)),
):
    """Reset ALL roles to defaults. SA/OWNER only."""
    await db.role_permissions.delete_many({})
    await _ensure_seeded(db)

    await write_audit(
        db,
        action="update",
        entity_type="role_permission",
        entity_id="all",
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        metadata={"reason": "reset_all_to_defaults"},
    )
    return None


__all__ = ["router"]
