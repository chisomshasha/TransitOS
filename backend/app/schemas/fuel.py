"""FuelLog request/response schemas."""

from app.models.fuel import FuelLog, FuelLogCreate, FuelLogUpdate


class FuelLogCreateRequest(FuelLogCreate):
    pass


class FuelLogUpdateRequest(FuelLogUpdate):
    pass


class FuelLogResponse(FuelLog):
    pass
