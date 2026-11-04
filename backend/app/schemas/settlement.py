"""Settlement request/response shapes."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.settlement import Settlement, SettlementLine


class SettlementGenerateRequest(BaseModel):
    """Body for ``POST /settlements/generate``."""

    branch_id: str = Field(min_length=1)
    period_start: datetime
    period_end: datetime
    driver_rate: float = Field(default=0.0, ge=0)
    conductor_rate: float = Field(default=0.0, ge=0)
    notes: Optional[str] = Field(default=None, max_length=2000)


class SettlementUpdateRequest(BaseModel):
    """Body for ``PATCH /settlements/{id}``."""

    driver_rate: Optional[float] = Field(default=None, ge=0)
    conductor_rate: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = Field(default=None, max_length=2000)


class SettlementRejectRequest(BaseModel):
    """Body for ``POST /settlements/{id}/reject``."""

    reason: Optional[str] = Field(default=None, max_length=2000)


class SettlementPayRequest(BaseModel):
    """Body for ``POST /settlements/{id}/pay``."""

    payment_reference: Optional[str] = Field(default=None, max_length=120)


class SettlementResponse(Settlement):
    pass


__all__ = [
    "SettlementGenerateRequest",
    "SettlementUpdateRequest",
    "SettlementRejectRequest",
    "SettlementPayRequest",
    "SettlementResponse",
    "SettlementLine",
]
