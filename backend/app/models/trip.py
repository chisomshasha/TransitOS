"""Trip entity — see ``sprint-b-tasks.md`` §1.

A trip is the operational unit: one vehicle, one driver, one conductor, one
route, scheduled departure, with a manifest of bookings and a cash-up at the
end. State machine: planned → boarding → departed → arrived → closed →
cashed_up. Cancellation is a terminal side-state from any non-terminal state.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TripStatus(str, Enum):
    PLANNED = "planned"
    BOARDING = "boarding"
    DEPARTED = "departed"
    ARRIVED = "arrived"
    CLOSED = "closed"
    CASHED_UP = "cashed_up"
    CANCELLED = "cancelled"


# Allowed transitions. `cashed_up` is terminal; `cancelled` is reachable
# from any pre-departure state.
TRIP_TRANSITIONS: dict[TripStatus, set[TripStatus]] = {
    TripStatus.PLANNED: {TripStatus.BOARDING, TripStatus.CANCELLED},
    TripStatus.BOARDING: {TripStatus.DEPARTED, TripStatus.CANCELLED},
    TripStatus.DEPARTED: {TripStatus.ARRIVED},
    TripStatus.ARRIVED: {TripStatus.CLOSED},
    TripStatus.CLOSED: {TripStatus.CASHED_UP},
    TripStatus.CASHED_UP: set(),
    TripStatus.CANCELLED: set(),
}


class TripBase(BaseModel):
    route_id: str
    vehicle_id: str
    driver_id: str
    conductor_id: str
    branch_id: str
    scheduled_departure: datetime
    scheduled_arrival: datetime
    origin_terminal: Optional[str] = None
    destination_terminal: Optional[str] = None
    notes: Optional[str] = Field(default=None, max_length=2000)
    status: TripStatus = TripStatus.PLANNED


class TripCreate(TripBase):
    @model_validator(mode="after")
    def _arrival_after_departure(self):
        if self.scheduled_arrival <= self.scheduled_departure:
            raise ValueError("scheduled_arrival must be after scheduled_departure")
        return self


class TripUpdate(BaseModel):
    scheduled_departure: Optional[datetime] = None
    scheduled_arrival: Optional[datetime] = None
    origin_terminal: Optional[str] = None
    destination_terminal: Optional[str] = None
    notes: Optional[str] = Field(default=None, max_length=2000)
    status: Optional[TripStatus] = None

    @model_validator(mode="after")
    def _arrival_after_departure_when_both_present(self):
        # If only one is being updated, the router must cross-check
        # against the existing doc.
        return self


class Trip(TripBase):
    id: str = Field(default="")
    actual_departure: Optional[datetime] = None
    actual_arrival: Optional[datetime] = None
    passenger_count: int = Field(default=0, ge=0)
    cargo_weight_kg: float = Field(default=0.0, ge=0)
    total_revenue: float = Field(default=0.0, ge=0)
    total_expenses: float = Field(default=0.0, ge=0)
    is_active: bool = True
    cancelled_reason: Optional[str] = Field(default=None, max_length=500)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
