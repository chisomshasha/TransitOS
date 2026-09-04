"""Vehicle position model — synthetic GPS for live fleet map.

TransitOS does not ship a telematics device. The backend generates
synthetic positions from each vehicle's home branch GPS (+ small offset)
so the live map has something meaningful to render. A real deployment
would replace the synthetic generator with device-pushed positions via
POST /vehicles/{id}/position (endpoint reserved, not mounted).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class VehiclePosition(BaseModel):
    id: Optional[str] = None
    vehicle_id: str
    branch_id: Optional[str] = None
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    speed_kph: float = Field(default=0, ge=0, le=200)
    heading_deg: Optional[float] = None
    status: str = "available"  # mirrors VehicleStatus
    reg_number: Optional[str] = None
    driver_name: Optional[str] = None
    trip_id: Optional[str] = None
    recorded_at: Optional[datetime] = None


class VehiclePositionResponse(VehiclePosition):
    pass


__all__ = ["VehiclePosition", "VehiclePositionResponse"]
