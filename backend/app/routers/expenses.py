"""Expenses router — fuel, tolls, maintenance, etc."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.rbac import BA, BM, CA, DRIVER, GM, OWNER, SA, require_roles
from app.schemas.common import ListResponse, SingleResponse
from app.schemas.expense import (
    ExpenseCreateRequest,
    ExpenseResponse,
    ExpenseUpdateRequest,
)
from app.services import write_audit
from app.routers._common import (
    BRANCH_OPS_SCOPED,
    assert_branch_access,
    branch_scope_query,
    enforce_branch_write,
    paginate,
    project,
    utcnow,
)

router = APIRouter(prefix="/expenses", tags=["expenses"])

EXPENSE_READ = [SA, OWNER, GM, CA, BA, BM]
EXPENSE_MUTATE = [SA, OWNER, GM, CA, BA, BM, DRIVER]




@router.get("", response_model=ListResponse[ExpenseResponse])
async def list_expenses(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*EXPENSE_READ)),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    trip_id: Optional[str] = Query(None),
    vehicle_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None),
    occurred_from: Optional[datetime] = Query(None),
    occurred_to: Optional[datetime] = Query(None),
):
    query: dict = {"is_active": True}
    if trip_id:
        query["trip_id"] = trip_id
    if vehicle_id:
        query["vehicle_id"] = vehicle_id
    if category:
        query["category"] = category
    if branch_id:
        query["branch_id"] = branch_id
    if occurred_from or occurred_to:
        rng: dict = {}
        if occurred_from:
            rng["$gte"] = occurred_from
        if occurred_to:
            rng["$lte"] = occurred_to
        query["occurred_at"] = rng
    scope = branch_scope_query(user, roles=BRANCH_OPS_SCOPED)
    if scope:
        query.update(scope)
    return await paginate(
        db, "expenses", page=page, page_size=page_size,
        query=query, sort=[("occurred_at", -1)],
    )


@router.get("/{expense_id}", response_model=SingleResponse[ExpenseResponse])
async def get_expense(
    expense_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*EXPENSE_READ)),
):
    if not ObjectId.is_valid(expense_id):
        raise HTTPException(status_code=404, detail="Expense not found")
    doc = await db["expenses"].find_one({"_id": ObjectId(expense_id), "is_active": True})
    if doc is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    assert_branch_access(user, doc.get("branch_id"), roles=BRANCH_OPS_SCOPED)
    return SingleResponse[ExpenseResponse](data=project(doc))


@router.post(
    "", response_model=SingleResponse[ExpenseResponse], status_code=201
)
async def create_expense(
    body: ExpenseCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*EXPENSE_MUTATE)),
):
    # Validate FKs
    if not ObjectId.is_valid(body.vehicle_id) or not await db["vehicles"].find_one(
        {"_id": ObjectId(body.vehicle_id), "is_active": True}
    ):
        raise HTTPException(status_code=400, detail="Vehicle does not exist")
    if body.trip_id:
        if not ObjectId.is_valid(body.trip_id) or not await db["trips"].find_one(
            {"_id": ObjectId(body.trip_id)}
        ):
            raise HTTPException(status_code=400, detail="Trip does not exist")

    enforce_branch_write(actor, body.branch_id, roles=BRANCH_OPS_SCOPED)

    now = utcnow()
    payload = body.model_dump()
    payload.update(
        {
            "recorded_by_id": actor["id"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    result = await db["expenses"].insert_one(payload)
    payload["_id"] = result.inserted_id

    # Bump trip totals if on-trip
    if body.trip_id:
        from app.services import update_trip_totals
        await update_trip_totals(db, body.trip_id)

    await write_audit(
        db,
        action="create",
        entity_type="expense",
        entity_id=str(result.inserted_id),
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=body.branch_id,
        after=project(payload),
    )
    return SingleResponse[ExpenseResponse](data=project(payload))


@router.patch(
    "/{expense_id}", response_model=SingleResponse[ExpenseResponse]
)
async def update_expense(
    expense_id: str,
    body: ExpenseUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*EXPENSE_MUTATE)),
):
    if not ObjectId.is_valid(expense_id):
        raise HTTPException(status_code=404, detail="Expense not found")
    existing = await db["expenses"].find_one({"_id": ObjectId(expense_id), "is_active": True})
    if existing is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    enforce_branch_write(actor, existing.get("branch_id"), roles=BRANCH_OPS_SCOPED)

    EXPENSE_NULLABLE = {"vendor_name", "receipt_url", "odometer_km", "notes"}
    raw = body.model_dump(exclude_unset=True)
    updates = {k: v for k, v in raw.items() if v is not None or k in EXPENSE_NULLABLE}
    if not updates:
        return SingleResponse[ExpenseResponse](data=project(existing))
    updates["updated_at"] = utcnow()
    await db["expenses"].update_one({"_id": ObjectId(expense_id)}, {"$set": updates})
    new_doc = await db["expenses"].find_one({"_id": ObjectId(expense_id)})

    if existing.get("trip_id"):
        from app.services import update_trip_totals
        await update_trip_totals(db, existing["trip_id"])

    await write_audit(
        db,
        action="update",
        entity_type="expense",
        entity_id=expense_id,
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=existing.get("branch_id"),
        before=project(existing),
        after=project(new_doc),
    )
    return SingleResponse[ExpenseResponse](data=project(new_doc))


@router.delete("/{expense_id}", status_code=204)
async def delete_expense(
    expense_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: dict = Depends(require_roles(*EXPENSE_MUTATE)),
):
    if not ObjectId.is_valid(expense_id):
        raise HTTPException(status_code=404, detail="Expense not found")
    existing = await db["expenses"].find_one({"_id": ObjectId(expense_id), "is_active": True})
    if existing is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    enforce_branch_write(actor, existing.get("branch_id"), roles=BRANCH_OPS_SCOPED)
    await db["expenses"].update_one(
        {"_id": ObjectId(expense_id)},
        {"$set": {"is_active": False, "updated_at": utcnow()}},
    )
    if existing.get("trip_id"):
        from app.services import update_trip_totals
        await update_trip_totals(db, existing["trip_id"])
    await write_audit(
        db,
        action="delete",
        entity_type="expense",
        entity_id=expense_id,
        actor_id=actor["id"],
        actor_email=actor.get("email"),
        branch_id=existing.get("branch_id"),
    )
    return None


__all__ = ["router"]
