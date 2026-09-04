"""Cash-ups router — list, create, submit, approve, reject, export PDF."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.rbac import BA, BM, CA, CONDUCTOR, GM, OWNER, SA, require_roles
from app.schemas.cash_up import (
    CashUpApproveRequest,
    CashUpCreateRequest,
    CashUpResponse,
    CashUpUpdateRequest,
)
from app.schemas.common import ListResponse, SingleResponse
from app.services import (
    approve_cash_up,
    reject_cash_up,
    submit_cash_up,
    write_audit,
)
from app.routers._common import (
    BRANCH_OPS_SCOPED,
    assert_branch_access,
    branch_scope_query,
    enforce_branch_write,
    paginate,
    project,
    utcnow,
)

router = APIRouter(prefix="/cash-ups", tags=["cash-ups"])

CASHUP_READ = [SA, OWNER, GM, CA, BA, BM, CONDUCTOR]
CASHUP_MUTATE = [SA, OWNER, GM, CA, BA, BM, CONDUCTOR]
CASHUP_APPROVE = [SA, OWNER, GM, CA, BA]


@router.get("", response_model=ListResponse[CashUpResponse])
async def list_cash_ups(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*CASHUP_READ)),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    trip_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    branch_id: Optional[str] = Query(None),
):
    query: dict = {}
    if trip_id:
        query["trip_id"] = trip_id
    if status_filter:
        query["status"] = status_filter
    if branch_id:
        query["branch_id"] = branch_id
    scope = branch_scope_query(user, roles=BRANCH_OPS_SCOPED)
    if scope:
        query.update(scope)
    return await paginate(
        db, "cash_ups", page=page, page_size=page_size,
        query=query, sort=[("created_at", -1)],
    )


@router.get("/{cash_up_id}", response_model=SingleResponse[CashUpResponse])
async def get_cash_up(
    cash_up_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*CASHUP_READ)),
):
    if not ObjectId.is_valid(cash_up_id):
        raise HTTPException(status_code=404, detail="Cash-up not found")
    doc = await db["cash_ups"].find_one({"_id": ObjectId(cash_up_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="Cash-up not found")
    assert_branch_access(user, doc.get("branch_id"), roles=BRANCH_OPS_SCOPED)
    return SingleResponse[CashUpResponse](data=project(doc))


@router.get("/{cash_up_id}/pdf")
async def export_cash_up_pdf(
    cash_up_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*CASHUP_READ)),
):
    if not ObjectId.is_valid(cash_up_id):
        raise HTTPException(status_code=404, detail="Cash-up not found")
    doc = await db["cash_ups"].find_one({"_id": ObjectId(cash_up_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="Cash-up not found")
    assert_branch_access(user, doc.get("branch_id"), roles=BRANCH_OPS_SCOPED)

    trip = None
    conductor = None
    if doc.get("trip_id") and ObjectId.is_valid(doc["trip_id"]):
        trip = await db["trips"].find_one({"_id": ObjectId(doc["trip_id"])})
    if doc.get("conductor_id") and ObjectId.is_valid(doc["conductor_id"]):
        conductor = await db["conductors"].find_one({"_id": ObjectId(doc["conductor_id"])})

    from app.services.pdf import generate_cash_up_pdf

    pdf_bytes = generate_cash_up_pdf(project(doc), project(trip) if trip else None, project(conductor) if conductor else None)
    filename = f"cashup-{cash_up_id[:8]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("", response_model=SingleResponse[CashUpResponse], status_code=201)
async def create_cash_up(
    body: CashUpCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*CASHUP_MUTATE)),
):
    if not ObjectId.is_valid(body.trip_id):
        raise HTTPException(status_code=400, detail="Invalid trip_id")
    trip = await db["trips"].find_one({"_id": ObjectId(body.trip_id)})
    if trip is None:
        raise HTTPException(status_code=400, detail="Trip does not exist")
    if trip.get("status") != "closed":
        raise HTTPException(
            status_code=409,
            detail=f"Trip must be 'closed' before cash-up, not '{trip.get('status')}'",
        )

    enforce_branch_write(actor, body.branch_id, roles=BRANCH_OPS_SCOPED)
    if body.branch_id != trip.get("branch_id"):
        raise HTTPException(
            status_code=400, detail="Cash-up branch does not match trip branch"
        )

    existing_cu = await db["cash_ups"].find_one({"trip_id": body.trip_id})
    if existing_cu is not None:
        raise HTTPException(
            status_code=409,
            detail="A cash-up already exists for this trip — edit it instead of creating a new one",
        )

    breakdown_sum = sum(b.amount for b in body.breakdown)
    if abs(breakdown_sum - body.declared_total) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Breakdown sum ({breakdown_sum}) does not match declared_total ({body.declared_total})",
        )

    now = utcnow()
    payload = body.model_dump()
    payload.update(
        {
            "expected_total": 0.0,
            "variance": 0.0,
            "approved_by_id": None,
            "approved_at": None,
            "rejection_reason": None,
            "created_at": now,
            "updated_at": now,
        }
    )
    result = await db["cash_ups"].insert_one(payload)
    payload["_id"] = result.inserted_id

    await write_audit(
        db,
        action="create",
        entity_type="cash_up",
        entity_id=str(result.inserted_id),
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=body.branch_id,
        after=project(payload),
    )
    return SingleResponse[CashUpResponse](data=project(payload))


@router.patch("/{cash_up_id}", response_model=SingleResponse[CashUpResponse])
async def update_cash_up(
    cash_up_id: str,
    body: CashUpUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*CASHUP_MUTATE)),
):
    if not ObjectId.is_valid(cash_up_id):
        raise HTTPException(status_code=404, detail="Cash-up not found")
    existing = await db["cash_ups"].find_one({"_id": ObjectId(cash_up_id)})
    if existing is None:
        raise HTTPException(status_code=404, detail="Cash-up not found")
    enforce_branch_write(actor, existing.get("branch_id"), roles=BRANCH_OPS_SCOPED)
    if existing.get("status") not in ("draft", "rejected"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot edit a cash-up in status '{existing.get('status')}'",
        )

    CASH_UP_NULLABLE = {"notes"}
    raw = body.model_dump(exclude_unset=True)
    updates = {k: v for k, v in raw.items() if v is not None or k in CASH_UP_NULLABLE}
    updates.pop("status", None)
    if "breakdown" in updates or "declared_total" in updates:
        new_breakdown = updates.get("breakdown", existing.get("breakdown", []))
        new_declared = updates.get("declared_total", existing.get("declared_total", 0.0))

        def _amt(b: object) -> float:
            if isinstance(b, dict):
                return float(b.get("amount") or 0.0)
            return float(getattr(b, "amount", 0.0) or 0.0)

        if abs(sum(_amt(b) for b in new_breakdown) - float(new_declared or 0.0)) > 0.01:
            raise HTTPException(
                status_code=400, detail="Breakdown sum does not match declared_total"
            )
        if existing.get("status") == "rejected":
            updates["status"] = "draft"
            updates["rejection_reason"] = None

    updates["updated_at"] = utcnow()
    await db["cash_ups"].update_one({"_id": ObjectId(cash_up_id)}, {"$set": updates})
    new_doc = await db["cash_ups"].find_one({"_id": ObjectId(cash_up_id)})
    return SingleResponse[CashUpResponse](data=project(new_doc))


@router.post("/{cash_up_id}/submit", response_model=SingleResponse[CashUpResponse])
async def submit(
    cash_up_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*CASHUP_MUTATE)),
):
    if not ObjectId.is_valid(cash_up_id):
        raise HTTPException(status_code=404, detail="Cash-up not found")
    existing = await db["cash_ups"].find_one({"_id": ObjectId(cash_up_id)})
    if existing is None:
        raise HTTPException(status_code=404, detail="Cash-up not found")
    enforce_branch_write(actor, existing.get("branch_id"), roles=BRANCH_OPS_SCOPED)

    cu = await submit_cash_up(db, cash_up_id)
    await write_audit(
        db,
        action="submit",
        entity_type="cash_up",
        entity_id=cash_up_id,
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=cu.get("branch_id"),
        after=project(cu),
    )
    return SingleResponse[CashUpResponse](data=project(cu))


@router.post("/{cash_up_id}/approve", response_model=SingleResponse[CashUpResponse])
async def approve(
    cash_up_id: str,
    body: CashUpApproveRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*CASHUP_APPROVE)),
):
    if not ObjectId.is_valid(cash_up_id):
        raise HTTPException(status_code=404, detail="Cash-up not found")
    existing = await db["cash_ups"].find_one({"_id": ObjectId(cash_up_id)})
    if existing is None:
        raise HTTPException(status_code=404, detail="Cash-up not found")
    enforce_branch_write(actor, existing.get("branch_id"), roles=BRANCH_OPS_SCOPED)

    cu = await approve_cash_up(db, cash_up_id, actor["id"], notes=body.notes)
    await write_audit(
        db,
        action="approve",
        entity_type="cash_up",
        entity_id=cash_up_id,
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=cu.get("branch_id"),
        after=project(cu),
    )
    return SingleResponse[CashUpResponse](data=project(cu))


@router.post("/{cash_up_id}/reject", response_model=SingleResponse[CashUpResponse])
async def reject(
    cash_up_id: str,
    reason: str = Query(..., min_length=2, max_length=500),
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*CASHUP_APPROVE)),
):
    if not ObjectId.is_valid(cash_up_id):
        raise HTTPException(status_code=404, detail="Cash-up not found")
    existing = await db["cash_ups"].find_one({"_id": ObjectId(cash_up_id)})
    if existing is None:
        raise HTTPException(status_code=404, detail="Cash-up not found")
    enforce_branch_write(actor, existing.get("branch_id"), roles=BRANCH_OPS_SCOPED)

    cu = await reject_cash_up(db, cash_up_id, actor["id"], reason)
    await write_audit(
        db,
        action="reject",
        entity_type="cash_up",
        entity_id=cash_up_id,
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=cu.get("branch_id"),
        after=project(cu),
    )
    return SingleResponse[CashUpResponse](data=project(cu))


__all__ = ["router"]
