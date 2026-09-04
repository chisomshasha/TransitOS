"""Pre-trip inspection router — checklist drafts + submit & depart."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.rbac import ANY_AUTHENTICATED, CREW_READ, require_roles
from app.models.inspection import (
    CHECKLIST_TEMPLATE,
    InspectionItem,
    InspectionResponse,
    InspectionUpsert,
)
from app.routers._common import oid, project, utcnow
from app.services import write_audit
from app.schemas.common import ListResponse, SingleResponse

router = APIRouter(prefix="/inspections", tags=["inspections"])


def _blank_items() -> list[dict]:
    return [
        {"key": t["key"], "label": t["label"], "status": "pending", "note": None}
        for t in CHECKLIST_TEMPLATE
    ]


@router.get("", response_model=ListResponse[InspectionResponse])
async def list_inspections(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*CREW_READ)),
    trip_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
):
    query: dict = {}
    if trip_id:
        query["trip_id"] = trip_id
    items = []
    async for d in db.inspections.find(query).sort("created_at", -1):
        items.append(project(d))
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return ListResponse[InspectionResponse](
        items=items[start:end],
        total=total,
        page=page,
        totalPages=max(1, (total + page_size - 1) // page_size),
        hasMore=end < total,
    )


@router.get("/template")
async def inspection_template(
    user: dict = Depends(require_roles(*ANY_AUTHENTICATED)),
):
    """Return the canonical checklist template for the UI."""
    return {"items": _blank_items()}


@router.get("/{inspection_id}", response_model=SingleResponse[InspectionResponse])
async def get_inspection(
    inspection_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*ANY_AUTHENTICATED)),
):
    doc = await db.inspections.find_one({"_id": oid(inspection_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return SingleResponse[InspectionResponse](data=project(doc))


@router.post("", response_model=SingleResponse[InspectionResponse], status_code=201)
async def create_or_get_inspection(
    body: InspectionUpsert,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*ANY_AUTHENTICATED)),
):
    """Create a draft for a trip, or return the existing draft."""
    existing = await db.inspections.find_one(
        {"trip_id": body.trip_id, "status": "draft"}
    )
    if existing is not None:
        return SingleResponse[InspectionResponse](data=project(existing))

    now = utcnow()
    payload = body.model_dump()
    if not payload.get("items"):
        payload["items"] = _blank_items()
    payload.update(
        {
            "status": "draft",
            "created_by": actor["id"],
            "created_at": now,
            "updated_at": now,
        }
    )
    result = await db.inspections.insert_one(payload)
    payload["_id"] = result.inserted_id
    return SingleResponse[InspectionResponse](data=project(payload))


@router.put("/{inspection_id}", response_model=SingleResponse[InspectionResponse])
async def update_inspection(
    inspection_id: str,
    body: InspectionUpsert,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*ANY_AUTHENTICATED)),
):
    doc = await db.inspections.find_one({"_id": oid(inspection_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="Inspection not found")
    if doc.get("status") == "submitted":
        raise HTTPException(status_code=409, detail="Inspection already submitted")

    updates = body.model_dump()
    updates["updated_at"] = utcnow()
    await db.inspections.update_one({"_id": oid(inspection_id)}, {"$set": updates})
    new_doc = await db.inspections.find_one({"_id": oid(inspection_id)})
    return SingleResponse[InspectionResponse](data=project(new_doc))


@router.post("/{inspection_id}/submit", response_model=SingleResponse[InspectionResponse])
async def submit_inspection(
    inspection_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*ANY_AUTHENTICATED)),
):
    """Submit the checklist and, if the trip is planned/boarding, depart it."""
    doc = await db.inspections.find_one({"_id": oid(inspection_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="Inspection not found")
    if doc.get("status") == "submitted":
        raise HTTPException(status_code=409, detail="Inspection already submitted")

    now = utcnow()
    await db.inspections.update_one(
        {"_id": oid(inspection_id)},
        {"$set": {"status": "submitted", "submitted_at": now, "updated_at": now}},
    )

    # Depart the trip if it hasn't left yet (Submit & depart).
    trip = await db.trips.find_one({"_id": oid(doc["trip_id"])})
    if trip and trip.get("status") in ("planned", "boarding"):
        await db.trips.update_one(
            {"_id": oid(doc["trip_id"])},
            {"$set": {"status": "departed", "actual_departure": now, "updated_at": now}},
        )

    new_doc = await db.inspections.find_one({"_id": oid(inspection_id)})

    await write_audit(
        db,
        action="update",
        entity_type="inspection",
        entity_id=inspection_id,
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=trip.get("branch_id") if trip else None,
        after=project(new_doc),
    )
    return SingleResponse[InspectionResponse](data=project(new_doc))


__all__ = ["router"]
