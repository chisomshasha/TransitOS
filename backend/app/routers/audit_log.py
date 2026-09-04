"""Audit log reader — SA / OWNER / GM only.

The write path lives in ``app.services.audit.write_audit`` and is called
from every mutating endpoint. This router exposes the read surface so
the Owner can answer "who did what, when" without going to the DB.

The audit log is append-only and immutable (per data-model.md §7); no
endpoint here mutates or deletes entries.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.rbac import GM, OWNER, SA, require_roles
from app.routers._common import paginate, project
from app.schemas.common import ListResponse, SingleResponse

router = APIRouter(prefix="/audit-log", tags=["audit-log"])


AUDIT_ACTIONS = [
    "create",
    "update",
    "delete",
    "activate",
    "deactivate",
    "login",
    "login_failed",
    "logout",
    "password_reset",
    "role_change",
    "change_password",
]

AUDIT_ENTITY_TYPES = [
    "branch",
    "user",
    "vehicle",
    "driver",
    "conductor",
    "route",
    "trip",
    "manifest_entry",
    "fuel_log",
    "maintenance_record",
    "cash_up",
    "expense",
    "vehicle_document",
    "auth",
]


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    # Accept ISO-8601 with or without timezone.
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid ISO-8601 timestamp: {value}",
        )


@router.get("")
async def list_audit_log(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(SA, OWNER, GM)),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    actor_id: Optional[str] = Query(None),
    actor_email: Optional[str] = Query(None),
    from_ts: Optional[str] = Query(None),
    to_ts: Optional[str] = Query(None),
):
    """Return paginated audit log entries, most recent first."""
    query: dict = {}

    if action:
        if action not in AUDIT_ACTIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown action: {action}",
            )
        query["action"] = action

    if entity_type:
        if entity_type not in AUDIT_ENTITY_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown entity_type: {entity_type}",
            )
        query["entity_type"] = entity_type

    if entity_id:
        query["entity_id"] = entity_id

    if actor_id:
        query["actor_id"] = actor_id

    if actor_email:
        rx = re.compile(re.escape(actor_email.strip()), re.IGNORECASE)
        query["actor_email"] = rx

    from_dt = _parse_dt(from_ts)
    to_dt = _parse_dt(to_ts)
    if from_dt or to_dt:
        ts_q: dict = {}
        if from_dt:
            ts_q["$gte"] = from_dt
        if to_dt:
            ts_q["$lte"] = to_dt
        query["ts"] = ts_q

    # paginate() from _common handles total + projection
    result = await paginate(
        db,
        "audit_log",
        page=page,
        page_size=page_size,
        query=query,
        sort=[("ts", -1)],
    )
    # paginate returns ListResponse; re-wrap to ensure stable typing
    return result


@router.get("/summary")
async def audit_log_summary(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(SA, OWNER, GM)),
    from_ts: Optional[str] = Query(None),
    to_ts: Optional[str] = Query(None),
):
    """Return count of entries grouped by action type, for filter chips."""
    from_dt = _parse_dt(from_ts)
    to_dt = _parse_dt(to_ts)
    match: dict = {}
    if from_dt or to_dt:
        ts_q: dict = {}
        if from_dt:
            ts_q["$gte"] = from_dt
        if to_dt:
            ts_q["$lte"] = to_dt
        match["ts"] = ts_q

    pipeline = []
    if match:
        pipeline.append({"$match": match})
    pipeline.append({"$group": {"_id": "$action", "count": {"$sum": 1}}})

    cursor = db.audit_log.aggregate(pipeline)
    by_action: dict[str, int] = {}
    async for doc in cursor:
        action = doc.get("_id")
        if action:
            by_action[str(action)] = int(doc.get("count", 0))

    total = sum(by_action.values())
    return SingleResponse[dict](data={"total": total, "by_action": by_action})


@router.get("/actors")
async def audit_log_actors(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(SA, OWNER, GM)),
    q: Optional[str] = Query(None),
    limit: int = Query(25, ge=1, le=100),
):
    """Return distinct actor emails for the actor-filter dropdown."""
    match: dict = {}
    if q:
        rx = re.compile(re.escape(q.strip()), re.IGNORECASE)
        match["actor_email"] = rx

    pipeline: list[dict] = []
    if match:
        pipeline.append({"$match": match})
    pipeline.append({"$group": {"_id": "$actor_email"}})
    pipeline.append({"$sort": {"_id": 1}})
    pipeline.append({"$limit": limit})

    actors: list[str] = []
    async for doc in db.audit_log.aggregate(pipeline):
        email = doc.get("_id")
        if email:
            actors.append(str(email))
    return {"items": actors}


__all__ = ["router"]
