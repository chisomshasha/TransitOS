"""Trips router — CRUD + state machine + manifest + waybill PDF export."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.rbac import (
    BA, BM, CA, CONDUCTOR, DRIVER, GM, OM, OWNER, SA, require_roles,
)
from app.models.trip import TripStatus
from app.schemas.common import ListResponse, SingleResponse
from app.schemas.manifest import (
    ManifestCreateRequest, ManifestResponse, ManifestUpdateRequest,
)
from app.schemas.trip import (
    TripCreateRequest, TripResponse, TripStatusChangeRequest, TripUpdateRequest,
)
from app.services import (
    assert_transition, get_branch_id_for, get_trip_or_404, update_trip_totals, write_audit,
)
from app.routers._common import (
    BRANCH_OPS_SCOPED, assert_trip_access, enforce_branch_write, paginate, project,
    trip_scope_query, utcnow,
)

router = APIRouter(prefix="/trips", tags=["trips"])

TRIPS_READ = [SA, OWNER, GM, CA, BA, BM, OM, DRIVER, CONDUCTOR]
TRIPS_MUTATE = [SA, OWNER, GM, BM, OM]
TRIPS_MANIFEST_MUTATE = [SA, OWNER, GM, BM, OM, CONDUCTOR]


@router.get("", response_model=ListResponse[TripResponse])
async def list_trips(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*TRIPS_READ)),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    branch_id: Optional[str] = Query(None),
    vehicle_id: Optional[str] = Query(None),
    driver_id: Optional[str] = Query(None),
    conductor_id: Optional[str] = Query(None),
    status_filter: Optional[TripStatus] = Query(None, alias="status"),
    scheduled_from: Optional[datetime] = Query(None),
    scheduled_to: Optional[datetime] = Query(None),
):
    query: dict[str, Any] = {"is_active": True}
    if status_filter:
        query["status"] = status_filter.value
    if branch_id:
        query["branch_id"] = branch_id
    if vehicle_id:
        query["vehicle_id"] = vehicle_id
    if driver_id:
        query["driver_id"] = driver_id
    if conductor_id:
        query["conductor_id"] = conductor_id
    if scheduled_from or scheduled_to:
        rng: dict[str, Any] = {}
        if scheduled_from:
            rng["$gte"] = scheduled_from
        if scheduled_to:
            rng["$lte"] = scheduled_to
        query["scheduled_departure"] = rng

    scope = await trip_scope_query(db, user)
    if scope:
        query.update(scope)

    return await paginate(
        db, "trips", page=page, page_size=page_size, query=query,
        sort=[("scheduled_departure", -1)],
    )


@router.get("/{trip_id}", response_model=SingleResponse[TripResponse])
async def get_trip(
    trip_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*TRIPS_READ)),
):
    doc = await get_trip_or_404(db, trip_id)
    await assert_trip_access(db, user, doc)
    return SingleResponse[TripResponse](data=project(doc))


@router.get("/{trip_id}/waybill.pdf")
async def waybill_pdf(
    trip_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*TRIPS_READ)),
):
    """Download a printable waybill for the trip (A4, with manifest + signatures)."""
    trip = await get_trip_or_404(db, trip_id)
    await assert_trip_access(db, user, trip)

    route = vehicle = driver = conductor = branch = None
    if trip.get("route_id") and ObjectId.is_valid(trip["route_id"]):
        route = await db["routes"].find_one({"_id": ObjectId(trip["route_id"])})
    if trip.get("vehicle_id") and ObjectId.is_valid(trip["vehicle_id"]):
        vehicle = await db["vehicles"].find_one({"_id": ObjectId(trip["vehicle_id"])})
    if trip.get("driver_id") and ObjectId.is_valid(trip["driver_id"]):
        driver = await db["drivers"].find_one({"_id": ObjectId(trip["driver_id"])})
    if trip.get("conductor_id") and ObjectId.is_valid(trip["conductor_id"]):
        conductor = await db["conductors"].find_one({"_id": ObjectId(trip["conductor_id"])})
    if trip.get("branch_id") and ObjectId.is_valid(trip["branch_id"]):
        branch = await db["branches"].find_one({"_id": ObjectId(trip["branch_id"])})

    manifest_items = [
        project(m) async for m in db["manifest"].find(
            {"trip_id": trip_id, "is_active": True}
        ).sort("created_at", 1)
    ]

    from app.services.pdf import generate_trip_waybill_pdf

    pdf_bytes = generate_trip_waybill_pdf(
        trip=project(trip),
        route=project(route) if route else None,
        vehicle=project(vehicle) if vehicle else None,
        driver=project(driver) if driver else None,
        conductor=project(conductor) if conductor else None,
        manifest=manifest_items,
        branch_name=branch.get("name") if branch else None,
    )
    filename = f"waybill-{trip_id[:8]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("", response_model=SingleResponse[TripResponse], status_code=201)
async def create_trip(
    body: TripCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*TRIPS_MUTATE)),
):
    for coll, fid in (
        ("routes", body.route_id),
        ("vehicles", body.vehicle_id),
        ("drivers", body.driver_id),
        ("conductors", body.conductor_id),
    ):
        if not ObjectId.is_valid(fid) or not await db[coll].find_one(
            {"_id": ObjectId(fid), "is_active": True}
        ):
            raise HTTPException(
                status_code=400, detail=f"{coll[:-1].rstrip('s')} does not exist"
            )

    branch_id = await get_branch_id_for(
        db, route_id=body.route_id, vehicle_id=body.vehicle_id
    )
    if not branch_id:
        raise HTTPException(status_code=400, detail="Cannot determine branch for trip")
    enforce_branch_write(actor, branch_id, roles=BRANCH_OPS_SCOPED)

    active = await db["trips"].find_one(
        {
            "vehicle_id": body.vehicle_id,
            "status": {
                "$in": [
                    TripStatus.PLANNED.value,
                    TripStatus.BOARDING.value,
                    TripStatus.DEPARTED.value,
                ]
            },
            "is_active": True,
        }
    )
    if active:
        raise HTTPException(
            status_code=409,
            detail=f"Vehicle is already on trip {active['_id']} ({active.get('status')})",
        )

    now = utcnow()
    payload = body.model_dump()
    payload.update(
        {
            "branch_id": branch_id,
            "actual_departure": None,
            "actual_arrival": None,
            "passenger_count": 0,
            "cargo_weight_kg": 0.0,
            "total_revenue": 0.0,
            "total_expenses": 0.0,
            "cash_up_id": None,
            "cancelled_reason": None,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )

    result = await db["trips"].insert_one(payload)
    payload["_id"] = result.inserted_id

    await write_audit(
        db,
        action="create",
        entity_type="trip",
        entity_id=str(result.inserted_id),
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=branch_id,
        after=project(payload),
    )
    return SingleResponse[TripResponse](data=project(payload))


@router.patch("/{trip_id}", response_model=SingleResponse[TripResponse])
async def update_trip(
    trip_id: str,
    body: TripUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*TRIPS_MUTATE)),
):
    existing = await get_trip_or_404(db, trip_id)
    enforce_branch_write(actor, existing.get("branch_id"), roles=BRANCH_OPS_SCOPED)

    if body.status is not None:
        raise HTTPException(
            status_code=400,
            detail="Use PATCH /trips/{id}/status to change status",
        )

    TRIP_NULLABLE = {"origin_terminal", "destination_terminal", "notes"}
    raw = body.model_dump(exclude_unset=True)
    updates = {k: v for k, v in raw.items() if v is not None or k in TRIP_NULLABLE}
    if not updates:
        return SingleResponse[TripResponse](data=project(existing))

    new_dep = updates.get("scheduled_departure", existing.get("scheduled_departure"))
    new_arr = updates.get("scheduled_arrival", existing.get("scheduled_arrival"))
    if new_arr <= new_dep:
        raise HTTPException(
            status_code=400, detail="scheduled_arrival must be after scheduled_departure"
        )

    updates["updated_at"] = utcnow()
    await db["trips"].update_one({"_id": existing["_id"]}, {"$set": updates})
    new_doc = await db["trips"].find_one({"_id": existing["_id"]})

    await write_audit(
        db,
        action="update",
        entity_type="trip",
        entity_id=trip_id,
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=existing.get("branch_id"),
        before=project(existing),
        after=project(new_doc),
    )
    return SingleResponse[TripResponse](data=project(new_doc))


@router.patch("/{trip_id}/status", response_model=SingleResponse[TripResponse])
async def change_trip_status(
    trip_id: str,
    body: TripStatusChangeRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*TRIPS_MUTATE)),
):
    existing = await get_trip_or_404(db, trip_id)
    enforce_branch_write(actor, existing.get("branch_id"), roles=BRANCH_OPS_SCOPED)

    current = TripStatus(existing["status"])
    target = body.status
    assert_transition(current, target)

    updates: dict[str, Any] = {"status": target.value, "updated_at": utcnow()}
    if target == TripStatus.DEPARTED:
        if not body.actual_departure:
            updates["actual_departure"] = utcnow()
        else:
            updates["actual_departure"] = datetime.fromisoformat(
                body.actual_departure.replace("Z", "+00:00")
            )
    if target == TripStatus.ARRIVED:
        if not body.actual_arrival:
            updates["actual_arrival"] = utcnow()
        else:
            updates["actual_arrival"] = datetime.fromisoformat(
                body.actual_arrival.replace("Z", "+00:00")
            )
    if target == TripStatus.CANCELLED:
        if not body.cancelled_reason:
            raise HTTPException(
                status_code=400, detail="cancelled_reason is required when cancelling"
            )
        updates["cancelled_reason"] = body.cancelled_reason

    await db["trips"].update_one({"_id": existing["_id"]}, {"$set": updates})
    new_doc = await db["trips"].find_one({"_id": existing["_id"]})

    await write_audit(
        db,
        action=f"status:{target.value}",
        entity_type="trip",
        entity_id=trip_id,
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=existing.get("branch_id"),
        before=project(existing),
        after=project(new_doc),
    )
    return SingleResponse[TripResponse](data=project(new_doc))


@router.delete("/{trip_id}", status_code=204)
async def cancel_trip(
    trip_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*TRIPS_MUTATE)),
):
    existing = await get_trip_or_404(db, trip_id)
    enforce_branch_write(actor, existing.get("branch_id"), roles=BRANCH_OPS_SCOPED)
    if existing.get("status") in (
        TripStatus.CASHED_UP.value,
        TripStatus.ARRIVED.value,
        TripStatus.CLOSED.value,
    ):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel a trip in status '{existing.get('status')}'",
        )
    await db["trips"].update_one(
        {"_id": existing["_id"]},
        {"$set": {"status": "cancelled", "is_active": False, "updated_at": utcnow()}},
    )
    await write_audit(
        db,
        action="cancel",
        entity_type="trip",
        entity_id=trip_id,
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=existing.get("branch_id"),
    )
    return None


# ─── manifest ────────────────────────────────────────────────────────────────
@router.get("/{trip_id}/manifest", response_model=ListResponse[ManifestResponse])
async def list_manifest(
    trip_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*TRIPS_READ)),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
):
    trip = await get_trip_or_404(db, trip_id)
    await assert_trip_access(db, user, trip)
    return await paginate(
        db, "manifest", page=page, page_size=page_size,
        query={"trip_id": trip_id, "is_active": True},
        sort=[("created_at", 1)],
    )


@router.post(
    "/{trip_id}/manifest",
    response_model=SingleResponse[ManifestResponse],
    status_code=201,
)
async def add_manifest_entry(
    trip_id: str,
    body: ManifestCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*TRIPS_MANIFEST_MUTATE)),
):
    trip = await get_trip_or_404(db, trip_id)
    if actor.get("role") == "conductor":
        await assert_trip_access(db, actor, trip)
    else:
        enforce_branch_write(actor, trip.get("branch_id"), roles=BRANCH_OPS_SCOPED)

    if trip.get("status") in (
        TripStatus.DEPARTED.value,
        TripStatus.ARRIVED.value,
        TripStatus.CLOSED.value,
        TripStatus.CASHED_UP.value,
        TripStatus.CANCELLED.value,
    ):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot add manifest to a trip in status '{trip.get('status')}'",
        )

    payload = body.model_dump()
    payload["trip_id"] = trip_id
    payload["branch_id"] = trip.get("branch_id")
    now = utcnow()
    payload.update({"created_at": now, "updated_at": now, "is_active": True})
    result = await db["manifest"].insert_one(payload)
    payload["_id"] = result.inserted_id

    await update_trip_totals(db, trip_id)
    await write_audit(
        db,
        action="create",
        entity_type="manifest_entry",
        entity_id=str(result.inserted_id),
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=trip.get("branch_id"),
        after=project(payload),
    )
    return SingleResponse[ManifestResponse](data=project(payload))


@router.patch(
    "/{trip_id}/manifest/{entry_id}",
    response_model=SingleResponse[ManifestResponse],
)
async def update_manifest_entry(
    trip_id: str,
    entry_id: str,
    body: ManifestUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*TRIPS_MANIFEST_MUTATE)),
):
    if not ObjectId.is_valid(entry_id):
        raise HTTPException(status_code=404, detail="Manifest entry not found")
    existing = await db["manifest"].find_one(
        {"_id": ObjectId(entry_id), "trip_id": trip_id, "is_active": True}
    )
    if existing is None:
        raise HTTPException(status_code=404, detail="Manifest entry not found")

    trip = await get_trip_or_404(db, trip_id)
    if actor.get("role") == "conductor":
        await assert_trip_access(db, actor, trip)
    else:
        enforce_branch_write(actor, trip.get("branch_id"), roles=BRANCH_OPS_SCOPED)

    if trip.get("status") in (
        TripStatus.DEPARTED.value,
        TripStatus.ARRIVED.value,
        TripStatus.CLOSED.value,
        TripStatus.CASHED_UP.value,
        TripStatus.CANCELLED.value,
    ):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot edit manifest on a trip in status '{trip.get('status')}'",
        )

    MANIFEST_NULLABLE = {
        "passenger_name", "passenger_phone", "seat_number",
        "cargo_description", "cargo_weight_kg", "payment_method",
    }
    raw = body.model_dump(exclude_unset=True)
    updates = {k: v for k, v in raw.items() if v is not None or k in MANIFEST_NULLABLE}
    if not updates:
        return SingleResponse[ManifestResponse](data=project(existing))
    updates["updated_at"] = utcnow()
    await db["manifest"].update_one({"_id": ObjectId(entry_id)}, {"$set": updates})
    new_doc = await db["manifest"].find_one({"_id": ObjectId(entry_id)})
    await update_trip_totals(db, trip_id)
    return SingleResponse[ManifestResponse](data=project(new_doc))


@router.delete("/{trip_id}/manifest/{entry_id}", status_code=204)
async def delete_manifest_entry(
    trip_id: str,
    entry_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*TRIPS_MANIFEST_MUTATE)),
):
    if not ObjectId.is_valid(entry_id):
        raise HTTPException(status_code=404, detail="Manifest entry not found")
    trip = await get_trip_or_404(db, trip_id)
    if actor.get("role") == "conductor":
        await assert_trip_access(db, actor, trip)
    else:
        enforce_branch_write(actor, trip.get("branch_id"), roles=BRANCH_OPS_SCOPED)

    if trip.get("status") in (
        TripStatus.DEPARTED.value,
        TripStatus.ARRIVED.value,
        TripStatus.CLOSED.value,
        TripStatus.CASHED_UP.value,
        TripStatus.CANCELLED.value,
    ):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot remove manifest entries from a trip in status '{trip.get('status')}'",
        )
    res = await db["manifest"].update_one(
        {"_id": ObjectId(entry_id), "trip_id": trip_id, "is_active": True},
        {"$set": {"is_active": False, "updated_at": utcnow()}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Manifest entry not found")
    await update_trip_totals(db, trip_id)
    return None


__all__ = ["router"]
