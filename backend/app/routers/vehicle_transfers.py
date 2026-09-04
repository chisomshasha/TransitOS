"""Vehicle transfers router — initiate / confirm / return / cancel.

`confirm` flips the vehicle's `branch_id` to the destination branch; the
vehicle status becomes `maintenance` briefly while in transit (ops can
flip it to `available` when it arrives).
`return` flips `branch_id` back to the originating branch.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.rbac import FLEET_OPS, GM, OM, OWNER, SA, require_roles
from app.models.vehicle_transfer import (
    TRANSFER_TRANSITIONS,
    TransferStatus,
    VehicleTransferAdvance,
    VehicleTransferCreate,
    VehicleTransferResponse,
)
from app.routers._common import oid, paginate, project, utcnow
from app.services import write_audit
from app.schemas.common import ListResponse, SingleResponse

router = APIRouter(prefix="/vehicle-transfers", tags=["vehicle-transfers"])

# Roles that can initiate / confirm / return / cancel
TRANSFER_OPERATORS = [SA, OWNER, GM, OM] + FLEET_OPS


async def _transfer_or_404(db, transfer_id: str):
    doc = await db.vehicle_transfers.find_one({"_id": oid(transfer_id), "is_active": True})
    if doc is None:
        raise HTTPException(status_code=404, detail="Transfer not found")
    return doc


def _assert_transition(current: TransferStatus, target: TransferStatus) -> None:
    allowed = TRANSFER_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot transition from {current.value} to {target.value}",
        )


@router.get("", response_model=ListResponse[VehicleTransferResponse])
async def list_transfers(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*TRANSFER_OPERATORS)),
    status_filter: Optional[TransferStatus] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
):
    query: dict = {"is_active": True}
    if status_filter:
        query["status"] = status_filter.value
    return await paginate(
        db,
        "vehicle_transfers",
        page=page,
        page_size=page_size,
        query=query,
        sort=[("initiated_at", -1)],
    )


@router.get("/{transfer_id}", response_model=SingleResponse[VehicleTransferResponse])
async def get_transfer(
    transfer_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*TRANSFER_OPERATORS)),
):
    doc = await _transfer_or_404(db, transfer_id)
    return SingleResponse[VehicleTransferResponse](data=project(doc))


@router.post("", response_model=SingleResponse[VehicleTransferResponse], status_code=201)
async def initiate_transfer(
    body: VehicleTransferCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*TRANSFER_OPERATORS)),
):
    # Validate vehicle + branches
    if not ObjectId.is_valid(body.vehicle_id):
        raise HTTPException(status_code=400, detail="Invalid vehicle_id")
    vehicle = await db.vehicles.find_one({"_id": ObjectId(body.vehicle_id), "is_active": True})
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    if not ObjectId.is_valid(body.to_branch_id):
        raise HTTPException(status_code=400, detail="Invalid to_branch_id")
    to_branch = await db.branches.find_one({"_id": ObjectId(body.to_branch_id), "is_active": True})
    if to_branch is None:
        raise HTTPException(status_code=400, detail="Destination branch not found")

    from_branch_id = str(vehicle.get("branch_id"))
    if from_branch_id == body.to_branch_id:
        raise HTTPException(
            status_code=400, detail="Vehicle is already at that branch"
        )

    # Refuse if the vehicle is on an active trip
    active_trip = await db.trips.find_one(
        {
            "vehicle_id": body.vehicle_id,
            "status": {"$in": ["boarding", "departed"]},
            "is_active": True,
        }
    )
    if active_trip:
        raise HTTPException(
            status_code=409,
            detail=f"Vehicle is on active trip {active_trip['_id']} — cannot transfer",
        )

    # Refuse if an open transfer already exists for this vehicle
    open_xfer = await db.vehicle_transfers.find_one(
        {
            "vehicle_id": body.vehicle_id,
            "status": {"$in": [TransferStatus.INITIATED.value, TransferStatus.CONFIRMED.value]},
            "is_active": True,
        }
    )
    if open_xfer:
        raise HTTPException(
            status_code=409,
            detail=f"Vehicle already has an open transfer ({open_xfer['status']})",
        )

    now = utcnow()
    payload = body.model_dump()
    payload.update(
        {
            "from_branch_id": from_branch_id,
            "status": TransferStatus.INITIATED.value,
            "initiated_by": actor["id"],
            "initiated_at": now,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    result = await db.vehicle_transfers.insert_one(payload)
    payload["_id"] = result.inserted_id

    await write_audit(
        db,
        action="create",
        entity_type="vehicle_transfer",
        entity_id=str(result.inserted_id),
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=from_branch_id,
        after=project(payload),
    )
    return SingleResponse[VehicleTransferResponse](data=project(payload))


async def _advance(
    db: AsyncIOMotorDatabase,
    transfer_id: str,
    target: TransferStatus,
    actor: dict,
    notes: Optional[str],
):
    doc = await _transfer_or_404(db, transfer_id)
    current = TransferStatus(doc["status"])
    _assert_transition(current, target)
    now = utcnow()

    updates = {"status": target.value, "updated_at": now}
    if notes:
        updates["notes"] = notes

    if target == TransferStatus.CONFIRMED:
        updates["confirmed_by"] = actor["id"]
        updates["confirmed_at"] = now
        # Flip the vehicle's branch_id to the destination
        await db.vehicles.update_one(
            {"_id": oid(doc["vehicle_id"])},
            {"$set": {"branch_id": doc["to_branch_id"], "updated_at": now}},
        )
    elif target == TransferStatus.RETURNED:
        updates["returned_by"] = actor["id"]
        updates["returned_at"] = now
        # Flip back to the origin branch
        await db.vehicles.update_one(
            {"_id": oid(doc["vehicle_id"])},
            {"$set": {"branch_id": doc["from_branch_id"], "updated_at": now}},
        )
    elif target == TransferStatus.CANCELLED:
        updates["cancelled_by"] = actor["id"]
        updates["cancelled_at"] = now
        # If it was confirmed (vehicle already moved), return it
        if current == TransferStatus.CONFIRMED:
            await db.vehicles.update_one(
                {"_id": oid(doc["vehicle_id"])},
                {"$set": {"branch_id": doc["from_branch_id"], "updated_at": now}},
            )

    await db.vehicle_transfers.update_one({"_id": oid(transfer_id)}, {"$set": updates})
    new_doc = await db.vehicle_transfers.find_one({"_id": oid(transfer_id)})

    await write_audit(
        db,
        action=f"status:{target.value}",
        entity_type="vehicle_transfer",
        entity_id=transfer_id,
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=doc.get("from_branch_id"),
        before=project(doc),
        after=project(new_doc),
    )
    return new_doc


@router.post("/{transfer_id}/confirm", response_model=SingleResponse[VehicleTransferResponse])
async def confirm_transfer(
    transfer_id: str,
    body: VehicleTransferAdvance,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*TRANSFER_OPERATORS)),
):
    new_doc = await _advance(db, transfer_id, TransferStatus.CONFIRMED, actor, body.notes)
    return SingleResponse[VehicleTransferResponse](data=project(new_doc))


@router.post("/{transfer_id}/return", response_model=SingleResponse[VehicleTransferResponse])
async def return_transfer(
    transfer_id: str,
    body: VehicleTransferAdvance,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*TRANSFER_OPERATORS)),
):
    new_doc = await _advance(db, transfer_id, TransferStatus.RETURNED, actor, body.notes)
    return SingleResponse[VehicleTransferResponse](data=project(new_doc))


@router.post("/{transfer_id}/cancel", response_model=SingleResponse[VehicleTransferResponse])
async def cancel_transfer(
    transfer_id: str,
    body: VehicleTransferAdvance,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*TRANSFER_OPERATORS)),
):
    new_doc = await _advance(db, transfer_id, TransferStatus.CANCELLED, actor, body.notes)
    return SingleResponse[VehicleTransferResponse](data=project(new_doc))


__all__ = ["router"]
