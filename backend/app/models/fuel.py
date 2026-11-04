"""FuelLog — refueling event for a vehicle.

Distinct from ``Expense`` in that it always tracks volume, odometer, and
fuel station — used for fuel efficiency analytics.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class FuelLogBase(BaseModel):
    vehicle_id: str
    branch_id: str
    occurred_at: datetime
    liters: float = Field(gt=0, le=10_000)
    cost_total: float = Field(ge=0)
    cost_per_liter: float = Field(ge=0)
    odometer_km: int = Field(ge=0)
    station_name: Optional[str] = Field(default=None, max_length=120)
    station_location: Optional[str] = Field(default=None, max_length=240)
    receipt_url: Optional[str] = None
    notes: Optional[str] = Field(default=None, max_length=2000)


class FuelLogCreate(FuelLogBase):
    pass


class FuelLogUpdate(BaseModel):
    occurred_at: Optional[datetime] = None
    liters: Optional[float] = Field(default=None, gt=0, le=10_000)
    cost_total: Optional[float] = Field(default=None, ge=0)
    cost_per_liter: Optional[float] = Field(default=None, ge=0)
    odometer_km: Optional[int] = Field(default=None, ge=0)
    station_name: Optional[str] = Field(default=None, max_length=120)
    station_location: Optional[str] = Field(default=None, max_length=240)
    receipt_url: Optional[str] = None
    notes: Optional[str] = Field(default=None, max_length=2000)


class FuelLog(FuelLogBase):
    id: str = Field(default="")
    recorded_by_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_active: bool = True

    model_config = ConfigDict(populate_by_name=True)
