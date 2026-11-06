"""Dashboard summary — aggregated counters for the home screen.

Single endpoint that returns all KPI counters the dashboard needs,
avoiding the N+1 query pattern of calling 7 separate report endpoints.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.rbac import ANY_AUTHENTICATED, require_roles
from app.routers._common import BRANCH_SCOPED_ROLES
from app.schemas.common import SingleResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
async def dashboard_summary(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*ANY_AUTHENTICATED)),
):
    """Return aggregated counters for the home dashboard.

    Every counter is scoped. The branch-scoped roles — which includes
    drivers and conductors, not just the management tiers — see their
    own branch only, and the counters that have no branch of their own
    (vehicle transfers) are matched on the branch they move *from*.
    Before this, a driver opening the dashboard was shown the whole
    company's fleet, incidents and cash-ups.
    """
    branch_scope: dict[str, Any] = {}
    if user.get("role") in BRANCH_SCOPED_ROLES and user.get("branch_id"):
        branch_scope = {"branch_id": user["branch_id"]}

    # Vehicles in maintenance
    vehicles_maintenance = await db.vehicles.count_documents(
        {"status": "maintenance", "is_active": True, **branch_scope}
    )

    # Drivers on duty (assigned to a boarding or departed trip)
    on_duty_trip = await db.trips.distinct(
        "driver_id",
        {"status": {"$in": ["boarding", "departed"]}, "is_active": True, **branch_scope},
    )
    drivers_on_duty = len(on_duty_trip)

    # Documents expiring in 30 days
    now = datetime.now(timezone.utc)
    soon = now + timedelta(days=30)
    # Vehicles with any document.expires_at in [now, now+30d]
    doc_expiring_pipeline = [
        {"$match": {"is_active": True, **branch_scope}},
        {"$unwind": "$documents"},
        {
            "$match": {
                "documents.expires_at": {"$gte": now, "$lte": soon},
            }
        },
        {"$group": {"_id": "$_id"}},
        {"$count": "count"},
    ]
    doc_expiring_rows = [d async for d in db.vehicles.aggregate(doc_expiring_pipeline)]
    documents_expiring_30d = doc_expiring_rows[0]["count"] if doc_expiring_rows else 0

    # Licenses expiring in 30 days
    licenses_expiring_30d = await db.drivers.count_documents(
        {
            "license_expiry": {"$gte": now, "$lte": soon},
            "is_active": True,
            **branch_scope,
        }
    )

    # Open incidents (not resolved/closed)
    open_incidents = await db.incidents.count_documents(
        {"status": {"$in": ["open", "acknowledged"]}, **branch_scope}
    )

    # Open transfers (initiated or confirmed, not returned/cancelled)
    # A transfer has no branch of its own, so it is matched on the
    # branch the vehicle is leaving.
    open_transfers = await db.vehicle_transfers.count_documents(
        {
            "status": {"$in": ["initiated", "confirmed"]},
            "is_active": True,
            **({"from_branch_id": user["branch_id"]} if "branch_id" in branch_scope else {}),
        }
    )

    # Pending cash-ups (submitted, awaiting approval)
    pending_cash_ups = await db.cash_ups.count_documents(
        {"status": "submitted", **branch_scope}
    )

    return SingleResponse[dict](data={
        "vehicles_maintenance": vehicles_maintenance,
        "drivers_on_duty": drivers_on_duty,
        "documents_expiring_30d": documents_expiring_30d,
        "licenses_expiring_30d": licenses_expiring_30d,
        "open_incidents": open_incidents,
        "open_transfers": open_transfers,
        "pending_cash_ups": pending_cash_ups,
    })


__all__ = ["router"]
