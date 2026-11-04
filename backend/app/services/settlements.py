"""Settlement service — compute a branch's payables for a period.

The computation walks the operational record once:

1. Find every **completed** trip for the branch whose departure falls
   in the period. Completed means ``closed`` or ``cashed_up`` — a trip
   that is still ``planned`` or ``boarding`` has not earned anything.
2. For each trip, take the revenue from its **cash-up** (the money that
   was actually banked). If the trip closed without a cash-up, fall
   back to the trip's ``total_revenue`` (manifest fares) so the
   settlement still reflects the work done.
3. Subtract the trip's **on_trip expenses** to get the trip's net.
4. Apply the driver's and conductor's per-trip pay rate.
5. Add any **standalone** expenses for the branch in the period — these
   are branch overhead and reduce what the branch owes, but are not
   attributed to a trip.

The result is stored on the settlement document *with* its per-trip
lines, so the headline number is always traceable back to the trips that
produced it.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.settlement import (
    SETTLEMENT_LOCKED_STATUSES,
    SETTLEMENT_OPEN_STATUSES,
    Settlement,
    SettlementLine,
    SettlementStatus,
)
from app.routers._common import utcnow

#: Trip statuses that count towards a settlement.
COMPLETED_TRIP_STATUSES = ["closed", "cashed_up"]


def _to_object_id(value: str) -> Any:
    """ObjectId when possible, else the raw value (mongomock-safe)."""
    return ObjectId(value) if ObjectId.is_valid(value) else value


def _aware(value: Any) -> Optional[datetime]:
    """Normalise a stored datetime to timezone-aware UTC."""
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=utcnow().tzinfo)
    return value


async def _name_for(db: AsyncIOMotorDatabase, collection: str, doc_id: Any) -> Optional[str]:
    if not doc_id:
        return None
    try:
        doc = await db[collection].find_one({"_id": _to_object_id(str(doc_id))})
    except Exception:  # pragma: no cover - defensive
        return None
    if not doc:
        return None
    return doc.get("full_name") or doc.get("name") or doc.get("reg_number")


async def compute_settlement(
    db: AsyncIOMotorDatabase,
    *,
    branch_id: str,
    period_start: datetime,
    period_end: datetime,
    driver_rate: float = 0.0,
    conductor_rate: float = 0.0,
    notes: Optional[str] = None,
) -> dict[str, Any]:
    """Compute a settlement from the operational record.

    Returns a plain dict ready to be stored as a settlement document.
    """
    # ---- 1. completed trips in the period --------------------------------
    trip_query = {
        "branch_id": branch_id,
        "status": {"$in": COMPLETED_TRIP_STATUSES},
        "$or": [
            {"is_active": True},
            {"is_active": {"$exists": False}},
        ],
    }
    # Date filter: prefer the actual departure, fall back to scheduled.
    trips = [
        t
        async for t in db["trips"].find(trip_query)
    ]
    in_period: list[dict[str, Any]] = []
    for trip in trips:
        stamp = _aware(trip.get("actual_departure")) or _aware(
            trip.get("scheduled_departure")
        )
        if stamp is None:
            continue
        if period_start <= stamp <= period_end:
            in_period.append(trip)

    # ---- 2. cash-ups keyed by trip ----------------------------------------
    trip_ids = [str(t.get("_id")) for t in in_period]
    cash_ups: dict[str, dict[str, Any]] = {}
    if trip_ids:
        async for cu in db["cash_ups"].find(
            {
                "trip_id": {"$in": trip_ids},
                "$or": [{"is_active": True}, {"is_active": {"$exists": False}}],
            }
        ):
            cash_ups[str(cu.get("trip_id"))] = cu

    # ---- 3. on-trip expenses keyed by trip ---------------------------------
    trip_expense_map: dict[str, float] = {}
    if trip_ids:
        async for exp in db["expenses"].find(
            {
                "trip_id": {"$in": trip_ids},
                "$or": [{"is_active": True}, {"is_active": {"$exists": False}}],
            }
        ):
            trip_id = str(exp.get("trip_id"))
            trip_expense_map[trip_id] = trip_expense_map.get(trip_id, 0.0) + float(
                exp.get("amount") or 0.0
            )

    # ---- 4. build the lines -------------------------------------------------
    gross_revenue = 0.0
    trip_expenses_total = 0.0
    driver_payroll = 0.0
    conductor_payroll = 0.0
    lines: list[SettlementLine] = []

    for trip in in_period:
        trip_id = str(trip.get("_id"))
        cu = cash_ups.get(trip_id)

        if cu is not None:
            revenue = float(cu.get("expected_total") or 0.0)
            if revenue <= 0:
                revenue = float(cu.get("declared_total") or 0.0)
            variance = cu.get("variance")
            cash_up_id = str(cu.get("_id"))
        else:
            revenue = float(trip.get("total_revenue") or 0.0)
            variance = None
            cash_up_id = None

        trip_exp = trip_expense_map.get(trip_id, 0.0)
        net = round(revenue - trip_exp, 2)

        driver_id = trip.get("driver_id")
        conductor_id = trip.get("conductor_id")

        driver_pay = round(float(driver_rate), 2)
        conductor_pay = round(float(conductor_rate), 2)

        gross_revenue += revenue
        trip_expenses_total += trip_exp
        driver_payroll += driver_pay
        conductor_payroll += conductor_pay

        lines.append(
            SettlementLine(
                trip_id=trip_id,
                trip_date=_aware(trip.get("scheduled_departure")),
                status=trip.get("status"),
                route_name=await _route_name(db, trip.get("route_id")),
                gross_revenue=round(revenue, 2),
                trip_expenses=round(trip_exp, 2),
                net=net,
                driver_id=str(driver_id) if driver_id else None,
                driver_name=await _name_for(db, "drivers", driver_id),
                driver_pay=driver_pay,
                conductor_id=str(conductor_id) if conductor_id else None,
                conductor_name=await _name_for(db, "conductors", conductor_id),
                conductor_pay=conductor_pay,
                cash_up_id=cash_up_id,
                cash_up_variance=variance,
            )
        )

    # ---- 5. standalone branch overhead --------------------------------------
    standalone_expenses = 0.0
    async for exp in db["expenses"].find(
        {
            "branch_id": branch_id,
            "scope": "standalone",
            "occurred_at": {"$gte": period_start, "$lte": period_end},
            "$or": [{"is_active": True}, {"is_active": {"$exists": False}}],
        }
    ):
        standalone_expenses += float(exp.get("amount") or 0.0)

    net_payable = round(
        gross_revenue - trip_expenses_total - standalone_expenses, 2
    )

    branch_name = await _name_for(db, "branches", branch_id)

    return {
        "branch_id": branch_id,
        "branch_name": branch_name,
        "period_start": period_start,
        "period_end": period_end,
        "driver_rate": float(driver_rate),
        "conductor_rate": float(conductor_rate),
        "notes": notes,
        "status": SettlementStatus.DRAFT.value,
        "lines": [line.model_dump() for line in lines],
        "gross_revenue": round(gross_revenue, 2),
        "trip_expenses": round(trip_expenses_total, 2),
        "standalone_expenses": round(standalone_expenses, 2),
        "net_payable": net_payable,
        "driver_payroll": round(driver_payroll, 2),
        "conductor_payroll": round(conductor_payroll, 2),
        "trip_count": len(lines),
        "created_at": utcnow(),
        "updated_at": utcnow(),
    }


async def _route_name(db: AsyncIOMotorDatabase, route_id: Any) -> Optional[str]:
    if not route_id:
        return None
    try:
        route = await db["routes"].find_one({"_id": _to_object_id(str(route_id))})
    except Exception:  # pragma: no cover - defensive
        return None
    if not route:
        return None
    return route.get("name")


def recompute_payroll(
    settlement: dict[str, Any],
    *,
    driver_rate: float,
    conductor_rate: float,
) -> dict[str, Any]:
    """Recompute crew payroll on a stored settlement.

    Used when a manager changes the pay rate after the settlement was
    generated. Only the payroll columns change — revenue and expenses
    are a record of what happened and are never recomputed.
    """
    lines = settlement.get("lines") or []
    driver_total = 0.0
    conductor_total = 0.0

    for line in lines:
        line["driver_pay"] = round(float(driver_rate), 2)
        line["conductor_pay"] = round(float(conductor_rate), 2)
        driver_total += line["driver_pay"]
        conductor_total += line["conductor_pay"]

    settlement["driver_rate"] = float(driver_rate)
    settlement["conductor_rate"] = float(conductor_rate)
    settlement["driver_payroll"] = round(driver_total, 2)
    settlement["conductor_payroll"] = round(conductor_total, 2)
    settlement["updated_at"] = utcnow()
    return settlement


def is_editable(settlement: dict[str, Any]) -> bool:
    """True when the settlement may still be changed."""
    status = settlement.get("status")
    status_value = status.value if hasattr(status, "value") else status
    return status_value in {s.value for s in SETTLEMENT_OPEN_STATUSES}


def is_locked(settlement: dict[str, Any]) -> bool:
    """True when the settlement is financially closed."""
    status = settlement.get("status")
    status_value = status.value if hasattr(status, "value") else status
    return status_value in {s.value for s in SETTLEMENT_LOCKED_STATUSES}


__all__ = [
    "COMPLETED_TRIP_STATUSES",
    "compute_settlement",
    "recompute_payroll",
    "is_editable",
    "is_locked",
]
