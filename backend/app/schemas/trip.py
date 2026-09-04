"""Trip request/response schemas."""

from typing import Optional

from pydantic import BaseModel, Field

from app.models.trip import Trip, TripCreate, TripStatus, TripUpdate


class TripCreateRequest(TripCreate):
    pass


class TripUpdateRequest(TripUpdate):
    pass


class TripResponse(Trip):
    pass


class TripStatusChangeRequest(BaseModel):
    """Body for PATCH /trips/{id}/status — includes optional context fields."""

    status: TripStatus
    cancelled_reason: Optional[str] = Field(default=None, max_length=500)
    actual_departure: Optional[str] = None
    actual_arrival: Optional[str] = None
