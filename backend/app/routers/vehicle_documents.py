"""Vehicle documents router — CRUD + expiring list."""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.rbac import CREW_READ, FLEET_OPS, READ_ALL, require_roles
from app.models.vehicle_document import (
    VehicleDocumentCreate,
    VehicleDocumentResponse,
    VehicleDocumentUpdate,
)
from app.routers._common import (
    assert_branch_access,
    BRANCH_OPS_SCOPED,
    enforce_branch_write,
    oid,
    project,
    utcnow,
)
from app.services import write_audit
from app.schemas.common import ListResponse, SingleResponse

router = APIRouter(prefix="/vehicles/{vehicle_id}/documents", tags=["vehicle-documents"])
exp_router = APIRouter(prefix="/vehicle-documents", tags=["vehicle-documents"])


async def _vehicle_or_404(db, vehicle_id: str, user: dict, write: bool = False):
    doc = await db.vehicles.find_one({"_id": oid(vehicle_id), "is_active": True})
    if doc is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    if write:
        enforce_branch_write(user, doc.get("branch_id"), roles=BRANCH_OPS_SCOPED)
    else:
        assert_branch_access(user, doc.get("branch_id"), roles=BRANCH_OPS_SCOPED)
    return doc


@router.get("", response_model=ListResponse[VehicleDocumentResponse])
async def list_documents(
    vehicle_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*CREW_READ)),
):
    await _vehicle_or_404(db, vehicle_id, user)
    items = []
    async for d in db.vehicle_documents.find({"vehicle_id": vehicle_id, "is_active": True}):
        items.append(project(d))
    items.sort(key=lambda x: x.get("expires_at") or "")
    return ListResponse[VehicleDocumentResponse](
        items=items, total=len(items), page=1, totalPages=1, hasMore=False
    )


@router.post("", response_model=SingleResponse[VehicleDocumentResponse], status_code=201)
async def create_document(
    vehicle_id: str,
    body: VehicleDocumentCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*FLEET_OPS)),
):
    vehicle = await _vehicle_or_404(db, vehicle_id, actor, write=True)
    now = utcnow()
    payload = body.model_dump()
    payload.update(
        {
            "vehicle_id": vehicle_id,
            "branch_id": vehicle.get("branch_id"),
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    result = await db.vehicle_documents.insert_one(payload)
    payload["_id"] = result.inserted_id
    await write_audit(
        db,
        action="create",
        entity_type="vehicle_document",
        entity_id=str(result.inserted_id),
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=vehicle.get("branch_id"),
        after=project(payload),
    )
    return SingleResponse[VehicleDocumentResponse](data=project(payload))


@router.patch("/{doc_id}", response_model=SingleResponse[VehicleDocumentResponse])
async def update_document(
    vehicle_id: str,
    doc_id: str,
    body: VehicleDocumentUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*FLEET_OPS)),
):
    await _vehicle_or_404(db, vehicle_id, actor, write=True)
    existing = await db.vehicle_documents.find_one({"_id": oid(doc_id), "vehicle_id": vehicle_id})
    if existing is None:
        raise HTTPException(status_code=404, detail="Document not found")
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        return SingleResponse[VehicleDocumentResponse](data=project(existing))
    updates["updated_at"] = utcnow()
    await db.vehicle_documents.update_one({"_id": oid(doc_id)}, {"$set": updates})
    new_doc = await db.vehicle_documents.find_one({"_id": oid(doc_id)})
    return SingleResponse[VehicleDocumentResponse](data=project(new_doc))


@router.delete("/{doc_id}", status_code=204)
async def delete_document(
    vehicle_id: str,
    doc_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*FLEET_OPS)),
):
    await _vehicle_or_404(db, vehicle_id, actor, write=True)
    existing = await db.vehicle_documents.find_one({"_id": oid(doc_id), "vehicle_id": vehicle_id})
    if existing is None:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.vehicle_documents.update_one(
        {"_id": oid(doc_id)}, {"$set": {"is_active": False, "updated_at": utcnow()}}
    )
    return None


@exp_router.get("/expiring", response_model=ListResponse[VehicleDocumentResponse])
async def expiring_documents(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*READ_ALL)),
    days: int = Query(30, ge=1, le=365),
):
    from app.routers._common import branch_scope_query

    scope = branch_scope_query(user, roles=BRANCH_OPS_SCOPED)
    query: dict = {"is_active": True, "expires_at": {"$lte": utcnow() + timedelta(days=days)}}
    if scope:
        vid_query = {}
        vid_query.update(scope)
        ids = [str(v["_id"]) async for v in db.vehicles.find(vid_query, {"_id": 1})]
        query["vehicle_id"] = {"$in": ids}
    items = [project(d) async for d in db.vehicle_documents.find(query)]
    items.sort(key=lambda x: x.get("expires_at") or "")
    return ListResponse[VehicleDocumentResponse](
        items=items, total=len(items), page=1, totalPages=1, hasMore=False
    )


__all__ = ["router", "exp_router"]
