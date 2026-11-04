"""MaintenanceRecord — vehicle maintenance history.

Used for tracking due-soon maintenance, total cost of ownership, and
uptime analytics.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class MaintenanceType(str, Enum):
    ROUTINE = "routine"
    REPAIR = "repair"
    INSPECTION = "inspection"
    RECALL = "recall"


class MaintenanceStatus(str, Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MaintenanceRecordBase(BaseModel):
    vehicle_id: str
    branch_id: str
    type: MaintenanceType
    status: MaintenanceStatus = MaintenanceStatus.SCHEDULED
    title: str = Field(min_length=2, max_length=120)
    description: Optional[str] = Field(default=None, max_length=2000)
    scheduled_for: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    odometer_km: Optional[int] = Field(default=None, ge=0)
    vendor_name: Optional[str] = Field(default=None, max_length=120)
    cost_parts: float = Field(default=0.0, ge=0)
    cost_labor: float = Field(default=0.0, ge=0)
    cost_total: float = Field(default=0.0, ge=0)
    next_due_km: Optional[int] = Field(default=None, ge=0)
    next_due_date: Optional[datetime] = None
    notes: Optional[str] = Field(default=None, max_length=2000)


class MaintenanceRecordCreate(MaintenanceRecordBase):
    pass


class MaintenanceRecordUpdate(BaseModel):
    type: Optional[MaintenanceType] = None
    status: Optional[MaintenanceStatus] = None
    title: Optional[str] = Field(default=None, min_length=2, max_length=120)
    description: Optional[str] = Field(default=None, max_length=2000)
    scheduled_for: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    odometer_km: Optional[int] = Field(default=None, ge=0)
    vendor_name: Optional[str] = Field(default=None, max_length=120)
    cost_parts: Optional[float] = Field(default=None, ge=0)
    cost_labor: Optional[float] = Field(default=None, ge=0)
    cost_total: Optional[float] = Field(default=None, ge=0)
    next_due_km: Optional[int] = Field(default=None, ge=0)
    next_due_date: Optional[datetime] = None
    notes: Optional[str] = Field(default=None, max_length=2000)


class MaintenanceRecord(MaintenanceRecordBase):
    id: str = Field(default="")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_active: bool = True

    model_config = ConfigDict(populate_by_name=True)
