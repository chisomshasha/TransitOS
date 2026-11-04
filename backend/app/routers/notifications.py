"""Notifications router — inbox, unread count, mark read."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.rbac import ANY_AUTHENTICATED, require_roles
from app.models.notification import NotificationResponse
from app.routers._common import paginate, project
from app.schemas.common import ListResponse, SingleResponse

router = APIRouter(prefix="/notifications", tags=["notifications"])

BRANCH_SCOPED_ROLES = {"branch_manager", "branch_accountant", "driver", "conductor"}


def _base_query(user: dict) -> dict:
    q: dict = {}
    roles = user.get("role")
    q_roles: dict = {"roles": None}
    if roles:
        q_roles = {"$or": [{"roles": None}, {"roles": roles}]}
    q.update(q_roles)
    if roles in BRANCH_SCOPED_ROLES and user.get("branch_id"):
        q["$or"] = [{"branch_id": None}, {"branch_id": user["branch_id"]}]
    return q


@router.get("", response_model=ListResponse[NotificationResponse])
async def list_notifications(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*ANY_AUTHENTICATED)),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    type: Optional[str] = Query(None),
    unread: Optional[bool] = Query(None),
):
    query = _base_query(user)
    if type:
        query["type"] = type
    if unread:
        query["read_by"] = {"$ne": user["id"]}
    return await paginate(
        db, "notifications", page=page, page_size=page_size, query=query, sort=[("created_at", -1)]
    )


@router.get("/unread-count", response_model=SingleResponse[dict])
async def unread_count(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*ANY_AUTHENTICATED)),
):
    query = _base_query(user)
    query["read_by"] = {"$ne": user["id"]}
    count = await db.notifications.count_documents(query)
    return SingleResponse[dict](data={"count": count})


@router.post("/mark-all-read", status_code=204)
async def mark_all_read(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*ANY_AUTHENTICATED)),
):
    await db.notifications.update_many(_base_query(user), {"$addToSet": {"read_by": user["id"]}})
    return None


@router.post("/{notification_id}/mark-read", status_code=204)
async def mark_read(
    notification_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*ANY_AUTHENTICATED)),
):
    from bson import ObjectId

    if not ObjectId.is_valid(notification_id):
        raise HTTPException(status_code=400, detail="Invalid id")
    await db.notifications.update_one(
        {"_id": ObjectId(notification_id)}, {"$addToSet": {"read_by": user["id"]}}
    )
    return None


__all__ = ["router"]
