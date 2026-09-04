"""Reports — aggregations for the owner dashboard.

Includes operations summary, daily timeline, branch performance, vehicle ROI,
fuel summary (Sprint C originals) plus Phase-6 expansions:
  - Profit & Loss
  - Cash Flow (bucketed)
  - Top Routes
  - Driver Performance
  - Vehicle Utilization
  - Incidents Summary
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.rbac import BA, BM, CA, FM, GM, OM, OWNER, SA, require_roles
from app.schemas.common import SingleResponse

router = APIRouter(prefix="/reports", tags=["reports"])

REPORTS_READ = [SA, OWNER, GM, CA, BA, BM, OM, FM]


def _branch_scope_for(actor: dict) -> Optional[str]:
    from app.routers._common import BRANCH_OPS_SCOPED
    if actor.get("role") in BRANCH_OPS_SCOPED:
        return actor.get("branch_id")
    return None


def _date_range(from_: Optional[datetime], to: Optional[datetime]) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    to_ = to or now
    from_ = from_ or (to_ - timedelta(days=30))
    return from_, to_


# ─── operations summary ──────────────────────────────────────────────────────
@router.get("/operations/summary", response_model=SingleResponse[dict])
async def operations_summary(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*REPORTS_READ)),
    from_: Optional[datetime] = Query(None, alias="from"),
    to: Optional[datetime] = Query(None),
):
    from_dt, to_dt = _date_range(from_, to)
    trip_q: dict[str, Any] = {
        "is_active": True,
        "scheduled_departure": {"$gte": from_dt, "$lte": to_dt},
    }
    if (bid := _branch_scope_for(user)):
        trip_q["branch_id"] = bid

    pipeline = [
        {"$match": trip_q},
        {
            "$group": {
                "_id": "$status",
                "count": {"$sum": 1},
                "revenue": {"$sum": "$total_revenue"},
                "expenses": {"$sum": "$total_expenses"},
                "passengers": {"$sum": "$passenger_count"},
                "cargo_kg": {"$sum": "$cargo_weight_kg"},
            }
        },
    ]
    by_status = [d async for d in db["trips"].aggregate(pipeline)]

    total_revenue = sum(d.get("revenue", 0) for d in by_status)
    total_expenses = sum(d.get("expenses", 0) for d in by_status)
    total_trips = sum(d.get("count", 0) for d in by_status)
    total_passengers = sum(d.get("passengers", 0) for d in by_status)
    total_cargo_kg = sum(d.get("cargo_kg", 0) for d in by_status)

    cu_q: dict[str, Any] = {
        "status": {"$in": ["submitted", "approved"]},
        "updated_at": {"$gte": from_dt, "$lte": to_dt},
    }
    if (bid := _branch_scope_for(user)):
        cu_q["branch_id"] = bid
    total_variance = 0.0
    async for cu in db["cash_ups"].find(cu_q):
        total_variance += float(cu.get("variance") or 0.0)

    return SingleResponse[dict](
        data={
            "window": {"from": from_dt.isoformat(), "to": to_dt.isoformat()},
            "totals": {
                "trips": total_trips,
                "revenue": round(total_revenue, 2),
                "expenses": round(total_expenses, 2),
                "net": round(total_revenue - total_expenses, 2),
                "variance": round(total_variance, 2),
                "passengers": total_passengers,
                "cargo_kg": round(total_cargo_kg, 2),
            },
            "by_status": [
                {
                    "status": d["_id"],
                    "count": d["count"],
                    "revenue": round(d.get("revenue", 0), 2),
                    "expenses": round(d.get("expenses", 0), 2),
                    "passengers": d.get("passengers", 0),
                }
                for d in by_status
            ],
        }
    )


# ─── daily revenue/expense timeline ──────────────────────────────────────────
@router.get("/operations/daily", response_model=SingleResponse[dict])
async def daily_timeline(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*REPORTS_READ)),
    from_: Optional[datetime] = Query(None, alias="from"),
    to: Optional[datetime] = Query(None),
    bucket: str = Query("day", pattern="^(day|week)$"),
):
    from_dt, to_dt = _date_range(from_, to)
    trip_q: dict[str, Any] = {
        "is_active": True,
        "scheduled_departure": {"$gte": from_dt, "$lte": to_dt},
    }
    if (bid := _branch_scope_for(user)):
        trip_q["branch_id"] = bid

    date_format = "%Y-%m-%d" if bucket == "day" else "%G-W%V"
    pipeline = [
        {"$match": trip_q},
        {
            "$group": {
                "_id": {
                    "$dateToString": {
                        "format": date_format,
                        "date": "$scheduled_departure",
                    }
                },
                "revenue": {"$sum": "$total_revenue"},
                "expenses": {"$sum": "$total_expenses"},
                "trips": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    series = [d async for d in db["trips"].aggregate(pipeline)]
    return SingleResponse[dict](
        data={
            "bucket": bucket,
            "series": [
                {
                    "label": d["_id"],
                    "revenue": round(d.get("revenue", 0), 2),
                    "expenses": round(d.get("expenses", 0), 2),
                    "net": round(d.get("revenue", 0) - d.get("expenses", 0), 2),
                    "trips": d.get("trips", 0),
                }
                for d in series
            ],
        }
    )


# ─── branch performance comparison ───────────────────────────────────────────
@router.get("/branches/performance", response_model=SingleResponse[dict])
async def branch_performance(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*REPORTS_READ)),
    from_: Optional[datetime] = Query(None, alias="from"),
    to: Optional[datetime] = Query(None),
):
    if user["role"] == "branch_manager":
        match_branch = {"$eq": [user.get("branch_id"), "$branch_id"]}
    else:
        match_branch = {"$ne": [None, "$branch_id"]}
    from_dt, to_dt = _date_range(from_, to)
    pipeline = [
        {
            "$match": {
                "is_active": True,
                "scheduled_departure": {"$gte": from_dt, "$lte": to_dt},
                "$expr": match_branch,
            }
        },
        {
            "$group": {
                "_id": "$branch_id",
                "trips": {"$sum": 1},
                "revenue": {"$sum": "$total_revenue"},
                "expenses": {"$sum": "$total_expenses"},
                "passengers": {"$sum": "$passenger_count"},
            }
        },
    ]
    rows = [d async for d in db["trips"].aggregate(pipeline)]
    out = []
    for row in rows:
        branch_doc = None
        if row["_id"] and ObjectId.is_valid(row["_id"]):
            branch_doc = await db["branches"].find_one({"_id": ObjectId(row["_id"])})
        out.append(
            {
                "branch_id": row["_id"],
                "branch_name": branch_doc.get("name") if branch_doc else None,
                "trips": row["trips"],
                "revenue": round(row.get("revenue", 0), 2),
                "expenses": round(row.get("expenses", 0), 2),
                "net": round(row.get("revenue", 0) - row.get("expenses", 0), 2),
                "passengers": row.get("passengers", 0),
            }
        )
    out.sort(key=lambda r: r["revenue"], reverse=True)
    return SingleResponse[dict](data={"branches": out})


# ─── vehicle ROI ─────────────────────────────────────────────────────────────
@router.get("/vehicles/roi", response_model=SingleResponse[dict])
async def vehicle_roi(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*REPORTS_READ)),
    from_: Optional[datetime] = Query(None, alias="from"),
    to: Optional[datetime] = Query(None),
):
    from_dt, to_dt = _date_range(from_, to)
    trip_q: dict[str, Any] = {
        "is_active": True,
        "scheduled_departure": {"$gte": from_dt, "$lte": to_dt},
    }
    if (bid := _branch_scope_for(user)):
        trip_q["branch_id"] = bid
    pipeline = [
        {"$match": trip_q},
        {
            "$group": {
                "_id": "$vehicle_id",
                "trips": {"$sum": 1},
                "revenue": {"$sum": "$total_revenue"},
                "expenses": {"$sum": "$total_expenses"},
                "passengers": {"$sum": "$passenger_count"},
                "cargo_kg": {"$sum": "$cargo_weight_kg"},
            }
        },
    ]
    rows = [d async for d in db["trips"].aggregate(pipeline)]
    out = []
    for row in rows:
        v_doc = None
        if row["_id"] and ObjectId.is_valid(row["_id"]):
            v_doc = await db["vehicles"].find_one({"_id": ObjectId(row["_id"])})
        out.append(
            {
                "vehicle_id": row["_id"],
                "reg_number": v_doc.get("reg_number") if v_doc else None,
                "type": v_doc.get("type") if v_doc else None,
                "trips": row["trips"],
                "revenue": round(row.get("revenue", 0), 2),
                "expenses": round(row.get("expenses", 0), 2),
                "net": round(row.get("revenue", 0) - row.get("expenses", 0), 2),
                "passengers": row.get("passengers", 0),
                "cargo_kg": round(row.get("cargo_kg", 0), 2),
            }
        )
    out.sort(key=lambda r: r["net"], reverse=True)
    return SingleResponse[dict](data={"vehicles": out})


# ─── fuel cost summary ───────────────────────────────────────────────────────
@router.get("/fuel/summary", response_model=SingleResponse[dict])
async def fuel_summary(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*REPORTS_READ)),
    from_: Optional[datetime] = Query(None, alias="from"),
    to: Optional[datetime] = Query(None),
):
    from_dt, to_dt = _date_range(from_, to)
    q: dict[str, Any] = {
        "is_active": True,
        "occurred_at": {"$gte": from_dt, "$lte": to_dt},
    }
    if (bid := _branch_scope_for(user)):
        q["branch_id"] = bid
    pipeline = [
        {"$match": q},
        {
            "$group": {
                "_id": None,
                "total_liters": {"$sum": "$liters"},
                "total_cost": {"$sum": "$cost_total"},
                "samples": {"$sum": 1},
            }
        },
    ]
    agg = [d async for d in db["fuel_logs"].aggregate(pipeline)]
    if not agg:
        return SingleResponse[dict](
            data={"total_liters": 0.0, "total_cost": 0.0, "samples": 0, "avg_cost_per_liter": None}
        )
    row = agg[0]
    return SingleResponse[dict](
        data={
            "total_liters": round(row["total_liters"], 2),
            "total_cost": round(row["total_cost"], 2),
            "samples": row["samples"],
            "avg_cost_per_liter": (
                round(row["total_cost"] / row["total_liters"], 2)
                if row["total_liters"] > 0
                else None
            ),
        }
    )


# ══════════════════════════════════════════════════════════════════════════════
# Phase 6 — expanded reports
# ══════════════════════════════════════════════════════════════════════════════


# ─── profit & loss ───────────────────────────────────────────────────────────
@router.get("/financials/profit-loss", response_model=SingleResponse[dict])
async def profit_loss(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*REPORTS_READ)),
    from_: Optional[datetime] = Query(None, alias="from"),
    to: Optional[datetime] = Query(None),
):
    """Revenue (trips) − Expenses (trip expenses + fuel + maintenance)."""
    from_dt, to_dt = _date_range(from_, to)
    scope: dict[str, Any] = {}
    if (bid := _branch_scope_for(user)):
        scope["branch_id"] = bid

    # Revenue from trips
    trip_q = {"is_active": True, "scheduled_departure": {"$gte": from_dt, "$lte": to_dt}, **scope}
    trip_agg = [d async for d in db["trips"].aggregate([
        {"$match": trip_q},
        {"$group": {"_id": None, "revenue": {"$sum": "$total_revenue"}, "trip_expenses": {"$sum": "$total_expenses"}}},
    ])]
    trip_totals = trip_agg[0] if trip_agg else {"revenue": 0.0, "trip_expenses": 0.0}
    revenue = float(trip_totals.get("revenue") or 0)
    trip_exp = float(trip_totals.get("trip_expenses") or 0)

    # Fuel cost
    fuel_q = {"is_active": True, "occurred_at": {"$gte": from_dt, "$lte": to_dt}, **scope}
    fuel_agg = [d async for d in db["fuel_logs"].aggregate([
        {"$match": fuel_q},
        {"$group": {"_id": None, "total": {"$sum": "$cost_total"}}},
    ])]
    fuel = float(fuel_agg[0].get("total") or 0) if fuel_agg else 0.0

    # Maintenance cost
    maint_q = {"is_active": True, "completed_at": {"$gte": from_dt, "$lte": to_dt}, **scope}
    maint_agg = [d async for d in db["maintenance_records"].aggregate([
        {"$match": maint_q},
        {"$group": {"_id": None, "total": {"$sum": "$cost_total"}}},
    ])]
    maint = float(maint_agg[0].get("total") or 0) if maint_agg else 0.0

    # Standalone expenses
    exp_q = {"is_active": True, "occurred_at": {"$gte": from_dt, "$lte": to_dt}, "scope": "standalone", **scope}
    exp_agg = [d async for d in db["expenses"].aggregate([
        {"$match": exp_q},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ])]
    standalone_exp = float(exp_agg[0].get("total") or 0) if exp_agg else 0.0

    total_expenses = trip_exp + fuel + maint + standalone_exp
    net = revenue - total_expenses

    return SingleResponse[dict](
        data={
            "window": {"from": from_dt.isoformat(), "to": to_dt.isoformat()},
            "revenue": round(revenue, 2),
            "expenses_breakdown": {
                "trip_expenses": round(trip_exp, 2),
                "fuel": round(fuel, 2),
                "maintenance": round(maint, 2),
                "standalone": round(standalone_exp, 2),
            },
            "total_expenses": round(total_expenses, 2),
            "net": round(net, 2),
        }
    )


# ─── cash flow ───────────────────────────────────────────────────────────────
@router.get("/financials/cash-flow", response_model=SingleResponse[dict])
async def cash_flow(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*REPORTS_READ)),
    from_: Optional[datetime] = Query(None, alias="from"),
    to: Optional[datetime] = Query(None),
    bucket: str = Query("week", pattern="^(day|week|month)$"),
):
    """Money in (trip revenue) vs money out (expenses) bucketed over time."""
    from_dt, to_dt = _date_range(from_, to)
    scope: dict[str, Any] = {}
    if (bid := _branch_scope_for(user)):
        scope["branch_id"] = bid

    date_format = {"day": "%Y-%m-%d", "week": "%G-W%V", "month": "%Y-%m"}[bucket]

    # Revenue by bucket (trip scheduled_departure)
    trip_q = {"is_active": True, "scheduled_departure": {"$gte": from_dt, "$lte": to_dt}, **scope}
    rev_series = {
        d["_id"]: {"revenue": float(d.get("revenue") or 0)}
        async for d in db["trips"].aggregate([
            {"$match": trip_q},
            {"$group": {
                "_id": {"$dateToString": {"format": date_format, "date": "$scheduled_departure"}},
                "revenue": {"$sum": "$total_revenue"},
            }},
        ])
    }

    # Expenses by bucket (occurred_at) — combine fuel + standalone expenses
    fuel_q = {"is_active": True, "occurred_at": {"$gte": from_dt, "$lte": to_dt}, **scope}
    async for d in db["fuel_logs"].aggregate([
        {"$match": fuel_q},
        {"$group": {
            "_id": {"$dateToString": {"format": date_format, "date": "$occurred_at"}},
            "expenses": {"$sum": "$cost_total"},
        }},
    ]):
        k = d["_id"]
        rev_series.setdefault(k, {"revenue": 0})
        rev_series[k]["expenses"] = rev_series[k].get("expenses", 0) + float(d.get("expenses") or 0)

    exp_q = {"is_active": True, "occurred_at": {"$gte": from_dt, "$lte": to_dt}, **scope}
    async for d in db["expenses"].aggregate([
        {"$match": exp_q},
        {"$group": {
            "_id": {"$dateToString": {"format": date_format, "date": "$occurred_at"}},
            "expenses": {"$sum": "$amount"},
        }},
    ]):
        k = d["_id"]
        rev_series.setdefault(k, {"revenue": 0})
        rev_series[k]["expenses"] = rev_series[k].get("expenses", 0) + float(d.get("expenses") or 0)

    series = [
        {
            "label": k,
            "revenue": round(v.get("revenue", 0), 2),
            "expenses": round(v.get("expenses", 0), 2),
            "net": round(v.get("revenue", 0) - v.get("expenses", 0), 2),
        }
        for k, v in sorted(rev_series.items())
    ]
    return SingleResponse[dict](data={"bucket": bucket, "series": series})


# ─── top routes ──────────────────────────────────────────────────────────────
@router.get("/routes/top", response_model=SingleResponse[dict])
async def top_routes(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*REPORTS_READ)),
    from_: Optional[datetime] = Query(None, alias="from"),
    to: Optional[datetime] = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    from_dt, to_dt = _date_range(from_, to)
    trip_q = {"is_active": True, "scheduled_departure": {"$gte": from_dt, "$lte": to_dt}}
    if (bid := _branch_scope_for(user)):
        trip_q["branch_id"] = bid

    pipeline = [
        {"$match": trip_q},
        {
            "$group": {
                "_id": "$route_id",
                "trips": {"$sum": 1},
                "revenue": {"$sum": "$total_revenue"},
                "passengers": {"$sum": "$passenger_count"},
                "cargo_kg": {"$sum": "$cargo_weight_kg"},
            }
        },
        {"$sort": {"revenue": -1}},
        {"$limit": limit},
    ]
    rows = [d async for d in db["trips"].aggregate(pipeline)]
    out = []
    for row in rows:
        r_doc = None
        if row["_id"] and ObjectId.is_valid(row["_id"]):
            r_doc = await db["routes"].find_one({"_id": ObjectId(row["_id"])})
        out.append(
            {
                "route_id": row["_id"],
                "name": r_doc.get("name") if r_doc else "Unknown route",
                "origin_city": r_doc.get("origin_city") if r_doc else None,
                "destination_city": r_doc.get("destination_city") if r_doc else None,
                "trips": row["trips"],
                "revenue": round(row.get("revenue", 0), 2),
                "passengers": row.get("passengers", 0),
                "cargo_kg": round(row.get("cargo_kg", 0), 2),
            }
        )
    return SingleResponse[dict](data={"routes": out})


# ─── driver performance ──────────────────────────────────────────────────────
@router.get("/drivers/performance", response_model=SingleResponse[dict])
async def driver_performance(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*REPORTS_READ)),
    from_: Optional[datetime] = Query(None, alias="from"),
    to: Optional[datetime] = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    from_dt, to_dt = _date_range(from_, to)
    trip_q = {"is_active": True, "scheduled_departure": {"$gte": from_dt, "$lte": to_dt}}
    if (bid := _branch_scope_for(user)):
        trip_q["branch_id"] = bid

    pipeline = [
        {"$match": trip_q},
        {
            "$group": {
                "_id": "$driver_id",
                "trips": {"$sum": 1},
                "revenue": {"$sum": "$total_revenue"},
                "passengers": {"$sum": "$passenger_count"},
                "completed": {
                    "$sum": {"$cond": [{"$eq": ["$status", "cashed_up"]}, 1, 0]}
                },
                "cancelled": {
                    "$sum": {"$cond": [{"$eq": ["$status", "cancelled"]}, 1, 0]}
                },
            }
        },
        {"$sort": {"revenue": -1}},
        {"$limit": limit},
    ]
    rows = [d async for d in db["trips"].aggregate(pipeline)]
    out = []
    for row in rows:
        d_doc = None
        if row["_id"] and ObjectId.is_valid(row["_id"]):
            d_doc = await db["drivers"].find_one({"_id": ObjectId(row["_id"])})
        trips = row["trips"] or 1
        out.append(
            {
                "driver_id": row["_id"],
                "name": d_doc.get("full_name") if d_doc else "Unknown driver",
                "trips": row["trips"],
                "completed": row.get("completed", 0),
                "cancelled": row.get("cancelled", 0),
                "completion_pct": round((row.get("completed", 0) / trips) * 100, 1) if trips else 0,
                "revenue": round(row.get("revenue", 0), 2),
                "passengers": row.get("passengers", 0),
            }
        )
    return SingleResponse[dict](data={"drivers": out})


# ─── vehicle utilization ─────────────────────────────────────────────────────
@router.get("/vehicles/utilization", response_model=SingleResponse[dict])
async def vehicle_utilization(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*REPORTS_READ)),
    from_: Optional[datetime] = Query(None, alias="from"),
    to: Optional[datetime] = Query(None),
):
    """Per-vehicle: trips, revenue, days on maintenance."""
    from_dt, to_dt = _date_range(from_, to)
    trip_q = {"is_active": True, "scheduled_departure": {"$gte": from_dt, "$lte": to_dt}}
    if (bid := _branch_scope_for(user)):
        trip_q["branch_id"] = bid

    trip_pipeline = [
        {"$match": trip_q},
        {
            "$group": {
                "_id": "$vehicle_id",
                "trips": {"$sum": 1},
                "revenue": {"$sum": "$total_revenue"},
                "passengers": {"$sum": "$passenger_count"},
            }
        },
    ]
    trip_rows = {d["_id"]: d async for d in db["trips"].aggregate(trip_pipeline)}

    # Maintenance downtime (completed_at in window)
    maint_q = {
        "is_active": True,
        "status": "completed",
        "completed_at": {"$gte": from_dt, "$lte": to_dt},
    }
    if (bid := _branch_scope_for(user)):
        maint_q["branch_id"] = bid
    maint_rows = {}
    async for m in db["maintenance_records"].find(maint_q):
        vid = m.get("vehicle_id")
        started = m.get("started_at")
        completed = m.get("completed_at")
        if started and completed:
            try:
                days = (completed - started).total_seconds() / 86400.0
                maint_rows[vid] = maint_rows.get(vid, 0) + max(0.0, days)
            except Exception:
                pass

    # All active vehicles (optionally scoped)
    v_q: dict[str, Any] = {"is_active": True}
    if (bid := _branch_scope_for(user)):
        v_q["branch_id"] = bid
    out = []
    async for v in db["vehicles"].find(v_q):
        vid = str(v["_id"])
        tr = trip_rows.get(vid)
        downtime = round(maint_rows.get(vid, 0.0), 1)
        window_days = max(1, (to_dt - from_dt).total_seconds() / 86400.0)
        utilization_pct = round(max(0, (window_days - downtime) / window_days) * 100, 1)
        out.append(
            {
                "vehicle_id": vid,
                "reg_number": v.get("reg_number"),
                "trips": tr["trips"] if tr else 0,
                "revenue": round((tr.get("revenue", 0) if tr else 0), 2),
                "passengers": tr.get("passengers", 0) if tr else 0,
                "downtime_days": downtime,
                "utilization_pct": utilization_pct,
            }
        )
    out.sort(key=lambda r: r["revenue"], reverse=True)
    return SingleResponse[dict](data={"vehicles": out})


# ─── incidents summary ───────────────────────────────────────────────────────
@router.get("/incidents/summary", response_model=SingleResponse[dict])
async def incidents_summary(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*REPORTS_READ)),
    from_: Optional[datetime] = Query(None, alias="from"),
    to: Optional[datetime] = Query(None),
):
    from_dt, to_dt = _date_range(from_, to)
    q: dict[str, Any] = {"created_at": {"$gte": from_dt, "$lte": to_dt}}
    if (bid := _branch_scope_for(user)):
        q["branch_id"] = bid

    by_severity: dict[str, int] = {"minor": 0, "moderate": 0, "severe": 0}
    by_category: dict[str, int] = {}
    by_status: dict[str, int] = {}
    total = 0
    async for i in db.incidents.find(q):
        total += 1
        sev = i.get("severity") or "minor"
        by_severity[sev] = by_severity.get(sev, 0) + 1
        cat = i.get("category") or "other"
        by_category[cat] = by_category.get(cat, 0) + 1
        st = i.get("status") or "open"
        by_status[st] = by_status.get(st, 0) + 1

    return SingleResponse[dict](
        data={
            "window": {"from": from_dt.isoformat(), "to": to_dt.isoformat()},
            "total": total,
            "by_severity": by_severity,
            "by_category": by_category,
            "by_status": by_status,
        }
    )


__all__ = ["router"]
