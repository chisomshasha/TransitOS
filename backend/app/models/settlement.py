"""Settlement — a branch's payables for a period, plus crew payroll.

Sprint D. A settlement is the financial close for a branch over a date
range. It is computed from the operational record — trips, their
cash-ups, their expenses — and then reviewed and paid:

    draft → submitted → approved → paid

What it captures
----------------
* **gross_revenue** — what the branch collected (from cash-ups, falling
  back to the trip's manifest total when a trip closed without one).
* **trip_expenses** — expenses scoped ``on_trip`` for trips in the range.
* **standalone_expenses** — branch overhead not tied to a trip.
* **net_payable** — what the branch owes the company.
* **driver_payroll / conductor_payroll** — what each crew member earned
  over the period, computed per trip from a pay rate.

Why per-trip lines
------------------
A settlement is stored with its per-trip breakdown (``lines``) so the
number on the settlement can always be traced back to the trips that
produced it. A flat total is not auditable; a line list is.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SettlementStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    PAID = "paid"
    REJECTED = "rejected"


#: Statuses that can still be edited.
SETTLEMENT_OPEN_STATUSES = {
    SettlementStatus.DRAFT,
    SettlementStatus.SUBMITTED,
    SettlementStatus.REJECTED,
}

#: Statuses that lock the settlement against further mutation.
SETTLEMENT_LOCKED_STATUSES = {
    SettlementStatus.APPROVED,
    SettlementStatus.PAID,
}


class SettlementLine(BaseModel):
    """One trip's contribution to the settlement."""

    trip_id: str
    trip_date: Optional[datetime] = None
    status: Optional[str] = None
    route_name: Optional[str] = None

    gross_revenue: float = Field(default=0.0, ge=0)
    trip_expenses: float = Field(default=0.0, ge=0)
    net: float = 0.0

    driver_id: Optional[str] = None
    driver_name: Optional[str] = None
    driver_pay: float = Field(default=0.0, ge=0)

    conductor_id: Optional[str] = None
    conductor_name: Optional[str] = None
    conductor_pay: float = Field(default=0.0, ge=0)

    cash_up_id: Optional[str] = None
    cash_up_variance: Optional[float] = None


class SettlementBase(BaseModel):
    branch_id: str
    branch_name: Optional[str] = None
    period_start: datetime
    period_end: datetime

    # Pay rates, per completed trip, used to derive crew payroll.
    driver_rate: float = Field(default=0.0, ge=0)
    conductor_rate: float = Field(default=0.0, ge=0)

    notes: Optional[str] = Field(default=None, max_length=2000)


class SettlementCreate(SettlementBase):
    """A settlement is normally *generated* rather than hand-written.

    ``POST /settlements/generate`` computes the figures from the
    operational record. Creating one directly is allowed for corrections
    but leaves the totals at zero.
    """


class SettlementUpdate(BaseModel):
    driver_rate: Optional[float] = Field(default=None, ge=0)
    conductor_rate: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = Field(default=None, max_length=2000)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class Settlement(SettlementBase):
    id: str = Field(default="")

    status: SettlementStatus = SettlementStatus.DRAFT
    lines: List[SettlementLine] = Field(default_factory=list)

    gross_revenue: float = 0.0
    trip_expenses: float = 0.0
    standalone_expenses: float = 0.0
    net_payable: float = 0.0
    driver_payroll: float = 0.0
    conductor_payroll: float = 0.0
    trip_count: int = 0

    submitted_by_id: Optional[str] = None
    submitted_at: Optional[datetime] = None
    approved_by_id: Optional[str] = None
    approved_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    payment_reference: Optional[str] = None
    rejection_reason: Optional[str] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(populate_by_name=True)


class SettlementResponse(Settlement):
    pass


__all__ = [
    "SettlementStatus",
    "SETTLEMENT_OPEN_STATUSES",
    "SETTLEMENT_LOCKED_STATUSES",
    "SettlementLine",
    "SettlementBase",
    "SettlementCreate",
    "SettlementUpdate",
    "Settlement",
    "SettlementResponse",
]
