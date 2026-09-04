"""Alerts engine — scans fleet data and upserts notifications."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.routers._common import utcnow

LICENSE_WINDOW_DAYS = 30
FUEL_LOW_PCT = 20.0
MAINT_WINDOW_DAYS = 7


def _days_left(expires: Any, now: Any) -> Optional[float]:
    if not expires:
        return None
    try:
        return (expires - now).total_seconds() / 86400.0
    except Exception:
        return None


async def _upsert(
    db: AsyncIOMotorDatabase,
    *,
    dedupe_key: str,
    type: str,
    severity: str,
    title: str,
    body: str,
    branch_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
) -> None:
    now = utcnow()
    existing = await db.notifications.find_one({"dedupe_key": dedupe_key})
    if existing is not None:
        await db.notifications.update_one(
            {"_id": existing["_id"]},
            {"$set": {"severity": severity, "title": title, "body": body, "refreshed_at": now}},
        )
        return
    await db.notifications.insert_one(
        {
            "type": type,
            "severity": severity,
            "title": title,
            "body": body,
            "branch_id": branch_id,
            "roles": None,
            "source": "scan",
            "dedupe_key": dedupe_key,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "read_by": [],
            "created_at": now,
            "refreshed_at": now,
        }
    )


async def run_alerts_scan(db: AsyncIOMotorDatabase) -> dict[str, int]:
    """Scan documents, licenses, maintenance and fuel; upsert notifications."""
    now = utcnow()
    counts = {"documents": 0, "licenses": 0, "maintenance": 0, "low_fuel": 0}

    # ── Vehicle documents ────────────────────────────────────────────────
    async for doc in db.vehicle_documents.find({"is_active": True}):
        alert_days = doc.get("alert_days") or 30
        days = _days_left(doc.get("expires_at"), now)
        if days is None or days > alert_days:
            continue
        counts["documents"] += 1
        ref = doc.get("ref_number", "?")
        if days < 0:
            sev, title = "danger", f"{doc.get('doc_type', 'Document').replace('_', ' ').title()} EXPIRED — {ref}"
        else:
            sev, title = "warn", f"{doc.get('doc_type', 'Document').replace('_', ' ').title()} expires in {int(days)}d — {ref}"
        await _upsert(
            db,
            dedupe_key=f"doc:{doc.get('id') or doc.get('_id')}",
            type="documents",
            severity=sev,
            title=title,
            body=f"Ref {ref}. Renew and update the document to clear this alert.",
            branch_id=doc.get("branch_id"),
            entity_type="vehicle_document",
            entity_id=str(doc.get("_id")),
        )

    # ── Driver licenses ──────────────────────────────────────────────────
    async for d in db.drivers.find({"is_active": True, "status": {"$ne": "on_leave"}}):
        days = _days_left(d.get("license_expiry"), now)
        if days is None or days > LICENSE_WINDOW_DAYS:
            continue
        counts["licenses"] += 1
        name = d.get("full_name") or "Driver"
        if days < 0:
            sev, title = "danger", f"License EXPIRED — {name}"
        else:
            sev, title = "warn", f"Driver license expires in {int(days)} days — {name}"
        await _upsert(
            db,
            dedupe_key=f"lic:{d.get('_id')}",
            type="licenses",
            severity=sev,
            title=title,
            body=f"License #{d.get('license_no', '?')}. Schedule renewal.",
            branch_id=d.get("branch_id"),
            entity_type="driver",
            entity_id=str(d.get("_id")),
        )

    # ── Maintenance due ──────────────────────────────────────────────────
    cutoff = now + timedelta(days=MAINT_WINDOW_DAYS)
    async for m in db.maintenance_records.find(
        {"is_active": True, "status": {"$in": ["scheduled", "in_progress"]}}
    ):
        due = m.get("next_due_date") or m.get("scheduled_for")
        if not due or due > cutoff:
            continue
        counts["maintenance"] += 1
        overdue = due < now
        await _upsert(
            db,
            dedupe_key=f"mnt:{m.get('_id')}",
            type="maintenance",
            severity="danger" if overdue else "info",
            title=f"{'Maintenance OVERDUE' if overdue else 'Maintenance due'} — {m.get('title', 'Service')}",
            body=m.get("description") or "Book service.",
            branch_id=m.get("branch_id"),
            entity_type="maintenance_record",
            entity_id=str(m.get("_id")),
        )

    # ── Low fuel ─────────────────────────────────────────────────────────
    async for v in db.vehicles.find({"is_active": True, "status": {"$ne": "grounded"}}):
        level = v.get("current_fuel_level")
        if level is None or level > FUEL_LOW_PCT:
            continue
        counts["low_fuel"] += 1
        await _upsert(
            db,
            dedupe_key=f"fuel:{v.get('_id')}",
            type="low_fuel",
            severity="danger" if level <= 10 else "warn",
            title=f"Low fuel ({int(level)}%) — {v.get('reg_number', '?')}",
            body="Schedule refuelling before next dispatch.",
            branch_id=v.get("branch_id"),
            entity_type="vehicle",
            entity_id=str(v.get("_id")),
        )

    counts["total"] = sum(counts.values())
    return counts
