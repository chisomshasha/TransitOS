"""CashUp entity — conductor's reconciliation at end of trip.

Records the declared cash, mobile transfers, and any other payment-method
breakdown. Computes variance = declared - expected.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CashUpStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class PaymentMethodBreakdown(BaseModel):
    """One line in the breakdown — e.g. 12,500 in cash, 5,000 in transfer."""

    method: str = Field(min_length=2, max_length=40)  # cash, transfer, pos, etc.
    amount: float = Field(ge=0)
    reference: Optional[str] = Field(default=None, max_length=80)


class CashUpBase(BaseModel):
    trip_id: str
    conductor_id: str
    branch_id: str
    breakdown: list[PaymentMethodBreakdown] = Field(default_factory=list)
    declared_total: float = Field(ge=0)
    notes: Optional[str] = Field(default=None, max_length=2000)
    status: CashUpStatus = CashUpStatus.DRAFT


class CashUpCreate(CashUpBase):
    pass


class CashUpUpdate(BaseModel):
    breakdown: Optional[list[PaymentMethodBreakdown]] = None
    declared_total: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = Field(default=None, max_length=2000)
    status: Optional[CashUpStatus] = None


class CashUp(CashUpBase):
    id: str = Field(default="")
    # Computed at submission time
    expected_total: float = Field(default=0.0, ge=0)
    variance: float = 0.0  # declared - expected; negative = shortage
    approved_by_id: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(populate_by_name=True)
