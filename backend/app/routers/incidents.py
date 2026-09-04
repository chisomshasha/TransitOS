"""Incidents router — report, list, acknowledge, resolve."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.rbac import ANY_AUTHENTICATED, CREW_READ, FLEET_OPS, require_roles
from app.models.incident import IncidentCreate, IncidentResponse, INCIDENT_CATEGORIES
from app.routers._common import oid, project, utcnow
from app.services import write_audit
from app.schemas.common import ListResponse, SingleResponse

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=ListResponse[IncidentResponse])
async def list_incidents(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*CREW_READ)),
    status_filter: Optional[str] = Query(None, alias="status"),
    severity: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    query: dict = {}
    if status_filter:
        query["status"] = status_filter
    if severity:
        query["severity"] = severity
    items = []
    async for d in db.incidents.find(query).sort("created_at", -1):
        items.append(project(d))
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return ListResponse[IncidentResponse](
        items=items[start:end],
        total=total,
        page=page,
        totalPages=max(1, (total + page_size - 1) // page_size),
        hasMore=end < total,
    )


@router.get("/summary")
async def incident_summary(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*CREW_READ)),
):
    """Counts by severity + closed, for the counter cards."""
    severe = await db.incidents.count_documents({"severity": "severe", "status": {"$ne": "closed"}})
    moderate = await db.incidents.count_documents({"severity": "moderate", "status": {"$ne": "closed"}})
    minor = await db.incidents.count_documents({"severity": "minor", "status": {"$ne": "closed"}})
    closed = await db.incidents.count_documents({"status": "closed"})
    return {
        "severe": severe,
        "moderate": moderate,
        "minor": minor,
        "closed": closed,
    }


@router.get("/categories")
async def incident_categories(
    user: dict = Depends(require_roles(*ANY_AUTHENTICATED)),
):
    return {"items": INCIDENT_CATEGORIES}


@router.get("/{incident_id}", response_model=SingleResponse[IncidentResponse])
async def get_incident(
    incident_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*ANY_AUTHENTICATED)),
):
    doc = await db.incidents.find_one({"_id": oid(incident_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return SingleResponse[IncidentResponse](data=project(doc))


@router.post("", response_model=SingleResponse[IncidentResponse], status_code=201)
async def create_incident(
    body: IncidentCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*ANY_AUTHENTICATED)),
):
    now = utcnow()
    payload = body.model_dump()
    payload.update(
        {
            "status": "open",
            "reported_by": actor["id"],
            "created_at": now,
            "updated_at": now,
        }
    )
    result = await db.incidents.insert_one(payload)
    payload["_id"] = result.inserted_id

    await write_audit(
        db,
        action="create",
        entity_type="incident",
        entity_id=str(result.inserted_id),
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=body.branch_id,
        after=project(payload),
    )
    return SingleResponse[IncidentResponse](data=project(payload))


@router.post("/{incident_id}/acknowledge", response_model=SingleResponse[IncidentResponse])
async def acknowledge_incident(
    incident_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*FLEET_OPS)),
):
    doc = await db.incidents.find_one({"_id": oid(incident_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    now = utcnow()
    await db.incidents.update_one(
        {"_id": oid(incident_id)},
        {
            "$set": {
                "status": "acknowledged",
                "acknowledged_by": actor["id"],
                "acknowledged_at": now,
                "updated_at": now,
            }
        },
    )
    new_doc = await db.incidents.find_one({"_id": oid(incident_id)})
    return SingleResponse[IncidentResponse](data=project(new_doc))


@router.post("/{incident_id}/resolve", response_model=SingleResponse[IncidentResponse])
async def resolve_incident(
    incident_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*FLEET_OPS)),
    resolution_note: Optional[str] = Query(None),
):
    doc = await db.incidents.find_one({"_id": oid(incident_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    now = utcnow()
    await db.incidents.update_one(
        {"_id": oid(incident_id)},
        {
            "$set": {
                "status": "resolved",
                "resolved_by": actor["id"],
                "resolved_at": now,
                "resolution_note": resolution_note,
                "updated_at": now,
            }
        },
    )
    new_doc = await db.incidents.find_one({"_id": oid(incident_id)})
    return SingleResponse[IncidentResponse](data=project(new_doc))


__all__ = ["router"]
