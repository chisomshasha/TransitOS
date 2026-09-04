"""CashUp service — variance computation + approval flow."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.cash_up import CashUpStatus


async def compute_expected_total(db: AsyncIOMotorDatabase, trip_id: str) -> float:
    """Sum of manifest fares that were actually collected (paid or on-board,
    not cancelled). For on-board entries we assume collected; conductor
    can adjust the breakdown if a passenger didn't pay.
    """
    total = 0.0
    async for entry in db["manifest"].find({"trip_id": trip_id}):
        if entry.get("payment_status") == "cancelled":
            continue
        total += float(entry.get("fare") or 0.0)
    return total


async def submit_cash_up(
    db: AsyncIOMotorDatabase, cash_up_id: str
) -> dict[str, Any]:
    """Move a DRAFT cash-up to SUBMITTED and compute variance."""
    if not ObjectId.is_valid(cash_up_id):
        raise HTTPException(status_code=404, detail="Cash-up not found")
    cu = await db["cash_ups"].find_one({"_id": ObjectId(cash_up_id)})
    if cu is None:
        raise HTTPException(status_code=404, detail="Cash-up not found")
    if cu.get("status") != CashUpStatus.DRAFT.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot submit cash-up in status '{cu.get('status')}'",
        )

    expected = await compute_expected_total(db, cu["trip_id"])
    declared = float(cu.get("declared_total") or 0.0)
    variance = round(declared - expected, 2)

    now = datetime.now(timezone.utc)
    await db["cash_ups"].update_one(
        {"_id": ObjectId(cash_up_id)},
        {
            "$set": {
                "expected_total": expected,
                "variance": variance,
                "status": CashUpStatus.SUBMITTED.value,
                "updated_at": now,
            }
        },
    )
    return await db["cash_ups"].find_one({"_id": ObjectId(cash_up_id)})


async def approve_cash_up(
    db: AsyncIOMotorDatabase,
    cash_up_id: str,
    approver_id: str,
    *,
    notes: str | None = None,
) -> dict[str, Any]:
    cu = await db["cash_ups"].find_one({"_id": ObjectId(cash_up_id)})
    if cu is None:
        raise HTTPException(status_code=404, detail="Cash-up not found")
    if cu.get("status") != CashUpStatus.SUBMITTED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot approve cash-up in status '{cu.get('status')}'",
        )
    now = datetime.now(timezone.utc)
    await db["cash_ups"].update_one(
        {"_id": ObjectId(cash_up_id)},
        {
            "$set": {
                "status": CashUpStatus.APPROVED.value,
                "approved_by_id": approver_id,
                "approved_at": now,
                "updated_at": now,
            }
        },
    )
    # Also flip the trip to CASHED_UP and link the cash-up — only if the
    # trip is still in the one state this transition is valid from. This
    # is a defensive re-check: creation already requires 'closed', but
    # this function has write access to trip.status.
    if cu.get("trip_id"):
        trip = await db["trips"].find_one({"_id": ObjectId(cu["trip_id"])})
        if trip is not None and trip.get("status") == "closed":
            await db["trips"].update_one(
                {"_id": ObjectId(cu["trip_id"])},
                {
                    "$set": {
                        "status": "cashed_up",
                        "cash_up_id": cash_up_id,
                        "updated_at": now,
                    }
                },
            )
    return await db["cash_ups"].find_one({"_id": ObjectId(cash_up_id)})


async def reject_cash_up(
    db: AsyncIOMotorDatabase,
    cash_up_id: str,
    approver_id: str,
    reason: str,
) -> dict[str, Any]:
    cu = await db["cash_ups"].find_one({"_id": ObjectId(cash_up_id)})
    if cu is None:
        raise HTTPException(status_code=404, detail="Cash-up not found")
    if cu.get("status") not in (CashUpStatus.SUBMITTED.value, CashUpStatus.DRAFT.value):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot reject cash-up in status '{cu.get('status')}'",
        )
    now = datetime.now(timezone.utc)
    await db["cash_ups"].update_one(
        {"_id": ObjectId(cash_up_id)},
        {
            "$set": {
                "status": CashUpStatus.REJECTED.value,
                "approved_by_id": approver_id,
                "approved_at": now,
                "rejection_reason": reason,
                "updated_at": now,
            }
        },
    )
    return await db["cash_ups"].find_one({"_id": ObjectId(cash_up_id)})


__all__ = [
    "compute_expected_total",
    "submit_cash_up",
    "approve_cash_up",
    "reject_cash_up",
]
