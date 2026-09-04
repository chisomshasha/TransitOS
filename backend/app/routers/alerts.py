"""Alerts router — manual scan trigger."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.rbac import READ_ALL, require_roles
from app.schemas.common import SingleResponse
from app.services.alerts import run_alerts_scan

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("/scan", response_model=SingleResponse[dict])
async def scan(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*READ_ALL)),
):
    counts = await run_alerts_scan(db)
    return SingleResponse[dict](data=counts)


__all__ = ["router"]
