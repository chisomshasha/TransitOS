"""Vehicle schemas."""

from __future__ import annotations

from app.models.vehicle import Vehicle, VehicleCreate, VehicleUpdate


class VehicleCreateRequest(VehicleCreate):
    pass


class VehicleUpdateRequest(VehicleUpdate):
    pass


class VehicleResponse(Vehicle):
    """Wire shape — same as in-DB model."""

    pass
