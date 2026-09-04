"""Trip expense — fuel, tolls, repairs, etc. incurred during a trip.

Two variants: ``on_trip`` (linked to a specific trip) and ``standalone``
(branch/vehicle overhead not tied to a trip). Reports aggregate both.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ExpenseCategory(str, Enum):
    FUEL = "fuel"
    TOLL = "toll"
    MAINTENANCE = "maintenance"
    PERMIT = "permit"
    MEAL = "meal"
    ACCOMMODATION = "accommodation"
    OTHER = "other"


class ExpenseScope(str, Enum):
    ON_TRIP = "on_trip"
    STANDALONE = "standalone"


class ExpenseBase(BaseModel):
    vehicle_id: str
    branch_id: str
    scope: ExpenseScope
    trip_id: Optional[str] = None
    category: ExpenseCategory
    amount: float = Field(ge=0)
    occurred_at: datetime
    vendor_name: Optional[str] = Field(default=None, max_length=120)
    receipt_url: Optional[str] = None
    odometer_km: Optional[int] = Field(default=None, ge=0)
    notes: Optional[str] = Field(default=None, max_length=2000)


class ExpenseCreate(ExpenseBase):
    @property
    def is_trip_linked(self) -> bool:
        return self.scope == ExpenseScope.ON_TRIP


class ExpenseUpdate(BaseModel):
    category: Optional[ExpenseCategory] = None
    amount: Optional[float] = Field(default=None, ge=0)
    occurred_at: Optional[datetime] = None
    vendor_name: Optional[str] = Field(default=None, max_length=120)
    receipt_url: Optional[str] = None
    odometer_km: Optional[int] = Field(default=None, ge=0)
    notes: Optional[str] = Field(default=None, max_length=2000)


class Expense(ExpenseBase):
    id: str = Field(default="")
    recorded_by_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_active: bool = True

    model_config = ConfigDict(populate_by_name=True)
