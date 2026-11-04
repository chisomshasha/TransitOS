"""Settlements router — generate, list, review and pay a branch's period.

Sprint D. The financial close:

    POST /settlements/generate   compute from the operational record
    POST /settlements/{id}/submit
    POST /settlements/{id}/approve
    POST /settlements/{id}/reject
    POST /settlements/{id}/pay

Settlements are money. Once a settlement is ``approved`` or ``paid`` it
is locked — the lines, the rates and the totals can no longer change.
Corrections are made by rejecting and regenerating, never by editing
an approved settlement in place.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.rbac import BA, BM, CA, GM, OWNER, SA, require_roles
from app.models.settlement import (
    SettlementResponse,
    SettlementStatus,
)
from app.routers._common import (
    assert_branch_access,
    branch_scope_query,
    enforce_branch_write,
    paginate,
    project,
    utcnow,
)
from app.schemas.common import ListResponse, SingleResponse
from app.schemas.settlement import (
    SettlementGenerateRequest,
    SettlementPayRequest,
    SettlementRejectRequest,
    SettlementResponse,
    SettlementUpdateRequest,
)
from app.services.audit import write_audit
from app.services.settlements import (
    compute_settlement,
    is_editable,
    recompute_payroll,
)

router = APIRouter(prefix="/settlements", tags=["settlements"])

SETTLEMENT_READ = [SA, OWNER, GM, CA, BA, BM]
SETTLEMENT_MUTATE = [SA, OWNER, GM, CA, BA]
SETTLEMENT_APPROVE = [SA, OWNER, GM, CA]


# ─── helpers ────────────────────────────────────────────────────────────────
def _oid(value: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise HTTPException(status_code=400, detail="Invalid id")
    return ObjectId(value)


async def _get_settlement_or_404(
    db: AsyncIOMotorDatabase, settlement_id: str
) -> dict:
    doc = await db.settlements.find_one({"_id": _oid(settlement_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Settlement not found")
    return doc


def _require_editable(doc: dict) -> None:
    if not is_editable(doc):
        raise HTTPException(
            status_code=409,
            detail=(
                f"Settlement is {doc.get('status')} and can no longer be changed. "
                "Reject it and generate a new one instead."
            ),
        )


# ─── list ───────────────────────────────────────────────────────────────────
@router.get("", response_model=ListResponse[SettlementResponse])
async def list_settlements(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*SETTLEMENT_READ)),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    branch_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    period_start: Optional[datetime] = Query(None),
    period_end: Optional[datetime] = Query(None),
):
    query: dict = {}
    if branch_id:
        query["branch_id"] = branch_id
    if status_filter:
        query["status"] = status_filter
    if period_start or period_end:
        date_query: dict = {}
        if period_start:
            date_query["$gte"] = period_start
        if period_end:
            date_query["$lte"] = period_end
        query["period_start"] = date_query

    scope = branch_scope_query(user)
    if scope:
        query.update(scope)

    return await paginate(
        db,
        "settlements",
        page=page,
        page_size=page_size,
        query=query,
        sort=[("period_start", -1), ("created_at", -1)],
    )


# ─── summary ────────────────────────────────────────────────────────────────
@router.get("/summary", response_model=SingleResponse[dict])
async def settlement_summary(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*SETTLEMENT_READ)),
    branch_id: Optional[str] = Query(None),
):
    """Aggregate settlement totals — what is owed, approved and paid."""
    query: dict = {}
    if branch_id:
        query["branch_id"] = branch_id
    scope = branch_scope_query(user)
    if scope:
        query.update(scope)

    buckets: dict[str, dict[str, float]] = {
        "draft": {"count": 0, "net_payable": 0.0},
        "submitted": {"count": 0, "net_payable": 0.0},
        "approved": {"count": 0, "net_payable": 0.0},
        "paid": {"count": 0, "net_payable": 0.0},
    }
    totals = {
        "gross_revenue": 0.0,
        "trip_expenses": 0.0,
        "standalone_expenses": 0.0,
        "net_payable": 0.0,
        "driver_payroll": 0.0,
        "conductor_payroll": 0.0,
    }

    async for doc in db.settlements.find(query):
        bucket = buckets.get(doc.get("status"))
        if bucket is not None:
            bucket["count"] += 1
            bucket["net_payable"] += float(doc.get("net_payable") or 0.0)
        for key in totals:
            totals[key] += float(doc.get(key) or 0.0)

    for bucket in buckets.values():
        bucket["net_payable"] = round(bucket["net_payable"], 2)
    for key in totals:
        totals[key] = round(totals[key], 2)

    return SingleResponse[dict](
        data={
            "by_status": buckets,
            "totals": totals,
            "outstanding": round(
                buckets["submitted"]["net_payable"] + buckets["approved"]["net_payable"],
                2,
            ),
        }
    )


# ─── generate ───────────────────────────────────────────────────────────────
@router.post(
    "/generate",
    response_model=SingleResponse[SettlementResponse],
    status_code=status.HTTP_201_CREATED,
)
async def generate_settlement(
    body: SettlementGenerateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*SETTLEMENT_MUTATE)),
):
    """Compute a settlement from the operational record and store it.

    The generated settlement is a draft — it must be submitted, approved
    and paid like any other.
    """
    if body.period_end < body.period_start:
        raise HTTPException(
            status_code=400, detail="period_end must be after period_start"
        )

    enforce_branch_write(user, body.branch_id)

    branch = await db.branches.find_one({"_id": _oid(body.branch_id)})
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    doc = await compute_settlement(
        db,
        branch_id=body.branch_id,
        period_start=body.period_start,
        period_end=body.period_end,
        driver_rate=body.driver_rate,
        conductor_rate=body.conductor_rate,
        notes=body.notes,
    )

    result = await db.settlements.insert_one(doc)
    stored = await db.settlements.find_one({"_id": result.inserted_id})

    await write_audit(
        db,
        action="settlement.generate",
        entity_type="settlement",
        entity_id=str(result.inserted_id),
        actor_id=user["id"],
        actor_email=user.get("email"),
        metadata={
            "branch_id": body.branch_id,
            "trip_count": doc.get("trip_count", 0),
            "net_payable": doc.get("net_payable", 0.0),
        },
    )

    return SingleResponse[SettlementResponse](data=project(stored))


# ─── read one ───────────────────────────────────────────────────────────────
@router.get("/{settlement_id}", response_model=SingleResponse[SettlementResponse])
async def get_settlement(
    settlement_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*SETTLEMENT_READ)),
):
    doc = await _get_settlement_or_404(db, settlement_id)
    assert_branch_access(user, doc.get("branch_id"))
    return SingleResponse[SettlementResponse](data=project(doc))


# ─── update ─────────────────────────────────────────────────────────────────
@router.patch("/{settlement_id}", response_model=SingleResponse[SettlementResponse])
async def update_settlement(
    settlement_id: str,
    body: SettlementUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*SETTLEMENT_MUTATE)),
):
    """Adjust the pay rates or notes on a draft settlement.

    Changing a pay rate recomputes crew payroll across every line — the
    revenue and expense columns are a historical record and never move.
    """
    doc = await _get_settlement_or_404(db, settlement_id)
    enforce_branch_write(user, doc.get("branch_id"))
    _require_editable(doc)

    updates: dict = {}
    if body.notes is not None:
        updates["notes"] = body.notes[:2000]

    if body.driver_rate is not None or body.conductor_rate is not None:
        driver_rate = float(
            body.driver_rate if body.driver_rate is not None else doc.get("driver_rate") or 0.0
        )
        conductor_rate = float(
            body.conductor_rate
            if body.conductor_rate is not None
            else doc.get("conductor_rate") or 0.0
        )
        if driver_rate < 0 or conductor_rate < 0:
            raise HTTPException(status_code=400, detail="Pay rates cannot be negative")
        recompute_payroll(
            doc, driver_rate=driver_rate, conductor_rate=conductor_rate
        )
        updates["driver_rate"] = driver_rate
        updates["conductor_rate"] = conductor_rate
        updates["lines"] = doc.get("lines", [])
        updates["driver_payroll"] = doc.get("driver_payroll", 0.0)
        updates["conductor_payroll"] = doc.get("conductor_payroll", 0.0)

    updates["updated_at"] = utcnow()

    await db.settlements.update_one({"_id": _oid(settlement_id)}, {"$set": updates})
    stored = await db.settlements.find_one({"_id": _oid(settlement_id)})

    await write_audit(
        db,
        action="settlement.update",
        entity_type="settlement",
        entity_id=settlement_id,
        actor_id=user["id"],
        actor_email=user.get("email"),
        metadata={"fields": list(updates.keys())},
    )

    return SingleResponse[SettlementResponse](data=project(stored))


# ─── submit ─────────────────────────────────────────────────────────────────
@router.post("/{settlement_id}/submit", response_model=SingleResponse[SettlementResponse])
async def submit_settlement(
    settlement_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*SETTLEMENT_MUTATE)),
):
    """Move a draft settlement into review."""
    doc = await _get_settlement_or_404(db, settlement_id)
    enforce_branch_write(user, doc.get("branch_id"))
    _require_editable(doc)

    if doc.get("status") == SettlementStatus.SUBMITTED.value:
        return SingleResponse[SettlementResponse](data=project(doc))

    await db.settlements.update_one(
        {"_id": _oid(settlement_id)},
        {
            "$set": {
                "status": SettlementStatus.SUBMITTED.value,
                "submitted_by_id": user["id"],
                "submitted_at": utcnow(),
                "updated_at": utcnow(),
            }
        },
    )
    stored = await db.settlements.find_one({"_id": _oid(settlement_id)})

    await write_audit(
        db,
        action="settlement.submit",
        entity_type="settlement",
        entity_id=settlement_id,
        actor_id=user["id"],
        actor_email=user.get("email"),
    )

    return SingleResponse[SettlementResponse](data=project(stored))


# ─── approve ────────────────────────────────────────────────────────────────
@router.post("/{settlement_id}/approve", response_model=SingleResponse[SettlementResponse])
async def approve_settlement(
    settlement_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*SETTLEMENT_APPROVE)),
):
    """Approve a submitted settlement. This locks it."""
    doc = await _get_settlement_or_404(db, settlement_id)

    if doc.get("status") != SettlementStatus.SUBMITTED.value:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Only a submitted settlement can be approved "
                f"(this one is {doc.get('status')})."
            ),
        )

    await db.settlements.update_one(
        {"_id": _oid(settlement_id)},
        {
            "$set": {
                "status": SettlementStatus.APPROVED.value,
                "approved_by_id": user["id"],
                "approved_at": utcnow(),
                "updated_at": utcnow(),
            }
        },
    )
    stored = await db.settlements.find_one({"_id": _oid(settlement_id)})

    await write_audit(
        db,
        action="settlement.approve",
        entity_type="settlement",
        entity_id=settlement_id,
        actor_id=user["id"],
        actor_email=user.get("email"),
        metadata={"net_payable": doc.get("net_payable", 0.0)},
    )

    return SingleResponse[SettlementResponse](data=project(stored))


# ─── reject ─────────────────────────────────────────────────────────────────
@router.post("/{settlement_id}/reject", response_model=SingleResponse[SettlementResponse])
async def reject_settlement(
    settlement_id: str,
    body: Optional[SettlementRejectRequest] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*SETTLEMENT_APPROVE)),
):
    """Send a submitted settlement back for correction."""
    doc = await _get_settlement_or_404(db, settlement_id)

    if doc.get("status") not in {
        SettlementStatus.SUBMITTED.value,
        SettlementStatus.APPROVED.value,
    }:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot reject a settlement in state {doc.get('status')}.",
        )

    reason = (body.reason if body else None) or "No reason supplied"

    await db.settlements.update_one(
        {"_id": _oid(settlement_id)},
        {
            "$set": {
                "status": SettlementStatus.REJECTED.value,
                "rejection_reason": str(reason)[:2000],
                "updated_at": utcnow(),
            }
        },
    )
    stored = await db.settlements.find_one({"_id": _oid(settlement_id)})

    await write_audit(
        db,
        action="settlement.reject",
        entity_type="settlement",
        entity_id=settlement_id,
        actor_id=user["id"],
        actor_email=user.get("email"),
        metadata={"reason": str(reason)[:200]},
    )

    return SingleResponse[SettlementResponse](data=project(stored))


# ─── pay ────────────────────────────────────────────────────────────────────
@router.post("/{settlement_id}/pay", response_model=SingleResponse[SettlementResponse])
async def pay_settlement(
    settlement_id: str,
    body: Optional[SettlementPayRequest] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*SETTLEMENT_APPROVE)),
):
    """Mark an approved settlement as paid. This is terminal."""
    doc = await _get_settlement_or_404(db, settlement_id)

    if doc.get("status") != SettlementStatus.APPROVED.value:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Only an approved settlement can be paid "
                f"(this one is {doc.get('status')})."
            ),
        )

    reference = body.payment_reference if body else None

    await db.settlements.update_one(
        {"_id": _oid(settlement_id)},
        {
            "$set": {
                "status": SettlementStatus.PAID.value,
                "paid_at": utcnow(),
                "payment_reference": (
                    str(reference)[:120] if reference else doc.get("payment_reference")
                ),
                "updated_at": utcnow(),
            }
        },
    )
    stored = await db.settlements.find_one({"_id": _oid(settlement_id)})

    await write_audit(
        db,
        action="settlement.pay",
        entity_type="settlement",
        entity_id=settlement_id,
        actor_id=user["id"],
        actor_email=user.get("email"),
        metadata={
            "net_payable": doc.get("net_payable", 0.0),
            "payment_reference": reference,
        },
    )

    return SingleResponse[SettlementResponse](data=project(stored))


__all__ = ["router"]
