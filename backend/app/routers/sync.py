"""Offline sync endpoints — pull/push/status.

POST /sync/pull   — client sends last_sync_ts, server returns all entities
                     changed since that timestamp (scoped to the user's role).
POST /sync/push   — client posts queued mutations, server applies them
                     and returns {applied: N, rejected: [...]}.
GET  /sync/status — lightweight connectivity + server clock check.

This sprint ships a minimal implementation: /pull returns vehicles + drivers
+ trips changed since the cursor, /push accepts a list of {op, entity, body}
and applies them. Full conflict resolution (CRDT / last-write-wins with
client-wins fallback) is the next sprint.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.rbac import require_roles
from app.routers._common import project, utcnow
from app.schemas.common import SingleResponse

router = APIRouter(prefix="/sync", tags=["sync"])


class SyncPullRequest(BaseModel):
    last_sync_ts: Optional[datetime] = None
    entity_types: Optional[list[str]] = None


class SyncPullResponse(BaseModel):
    server_ts: datetime
    vehicles: list[dict] = Field(default_factory=list)
    drivers: list[dict] = Field(default_factory=list)
    trips: list[dict] = Field(default_factory=list)
    branches: list[dict] = Field(default_factory=list)


class SyncPushOp(BaseModel):
    op: Literal["create", "update", "delete"]
    entity_type: str
    entity_id: Optional[str] = None
    body: Optional[dict] = None


class SyncPushRequest(BaseModel):
    operations: list[SyncPushOp] = Field(default_factory=list)


class SyncPushResult(BaseModel):
    applied: int = 0
    rejected: list[dict] = Field(default_factory=list)


@router.get("/status")
async def sync_status():
    """Lightweight connectivity + server clock probe."""
    return SingleResponse[dict](
        data={
            "status": "ok",
            "server_ts": datetime.now(timezone.utc).isoformat(),
            "version": "1.0",
        }
    )


@router.post("/pull", response_model=SingleResponse[SyncPullResponse])
async def sync_pull(
    body: SyncPullRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles()),
):
    """Return entities changed since `last_sync_ts`, scoped to the user."""
    since = body.last_sync_ts or datetime(1970, 1, 1, tzinfo=timezone.utc)
    wanted = set(body.entity_types) if body.entity_types else {
        "vehicles", "drivers", "trips", "branches"
    }

    # Branch scope: branch-scoped roles only see their own branch's data.
    branch_scope: dict[str, Any] = {}
    from app.routers._common import BRANCH_OPS_SCOPED
    if user.get("role") in BRANCH_OPS_SCOPED and user.get("branch_id"):
        branch_scope = {"branch_id": user["branch_id"]}

    out = SyncPullResponse(server_ts=utcnow())

    if "branches" in wanted:
        async for d in db.branches.find(
            {"updated_at": {"$gt": since}, "is_active": True}
        ):
            out.branches.append(project(d))

    if "vehicles" in wanted:
        q = {"updated_at": {"$gt": since}, "is_active": True, **branch_scope}
        async for d in db.vehicles.find(q):
            out.vehicles.append(project(d))

    if "drivers" in wanted:
        q = {"updated_at": {"$gt": since}, "is_active": True, **branch_scope}
        async for d in db.drivers.find(q):
            out.drivers.append(project(d))

    if "trips" in wanted:
        q = {"updated_at": {"$gt": since}, "is_active": True, **branch_scope}
        async for d in db.trips.find(q):
            out.trips.append(project(d))

    return SingleResponse[SyncPullResponse](data=out)


@router.post("/push", response_model=SingleResponse[SyncPushResult])
async def sync_push(
    body: SyncPushRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles()),
):
    """Apply queued client mutations. Best-effort — failures go to `rejected`."""
    applied = 0
    rejected: list[dict] = []

    for i, op in enumerate(body.operations):
        try:
            # Very small, whitelisted surface: only fuel_logs + expenses can
            # be pushed offline. Everything else must go through the
            # canonical routers so the state machine / audit trail is intact.
            if op.entity_type not in ("fuel_log", "expense", "manifest_entry"):
                rejected.append({
                    "index": i,
                    "op": op.op,
                    "entity_type": op.entity_type,
                    "reason": "Entity type not allowed in offline push",
                })
                continue

            if op.op == "create" and op.body:
                collection = {
                    "fuel_log": "fuel_logs",
                    "expense": "expenses",
                    "manifest_entry": "manifest",
                }[op.entity_type]
                payload = dict(op.body)
                payload["recorded_by_id"] = actor["id"]
                payload["is_active"] = True
                payload["created_at"] = utcnow()
                payload["updated_at"] = utcnow()
                await db[collection].insert_one(payload)
                applied += 1
            elif op.op == "update" and op.entity_id and op.body:
                collection = {
                    "fuel_log": "fuel_logs",
                    "expense": "expenses",
                    "manifest_entry": "manifest",
                }[op.entity_type]
                if not ObjectId.is_valid(op.entity_id):
                    raise ValueError("Invalid entity_id")
                payload = dict(op.body)
                payload["updated_at"] = utcnow()
                await db[collection].update_one(
                    {"_id": ObjectId(op.entity_id)}, {"$set": payload}
                )
                applied += 1
            elif op.op == "delete" and op.entity_id:
                collection = {
                    "fuel_log": "fuel_logs",
                    "expense": "expenses",
                    "manifest_entry": "manifest",
                }[op.entity_type]
                if not ObjectId.is_valid(op.entity_id):
                    raise ValueError("Invalid entity_id")
                await db[collection].update_one(
                    {"_id": ObjectId(op.entity_id)},
                    {"$set": {"is_active": False, "updated_at": utcnow()}},
                )
                applied += 1
            else:
                rejected.append({
                    "index": i,
                    "op": op.op,
                    "entity_type": op.entity_type,
                    "reason": "Missing required fields for operation",
                })
        except Exception as exc:
            rejected.append({
                "index": i,
                "op": op.op,
                "entity_type": op.entity_type,
                "reason": str(exc),
            })

    return SingleResponse[SyncPushResult](
        data=SyncPushResult(applied=applied, rejected=rejected)
    )


__all__ = ["router"]
