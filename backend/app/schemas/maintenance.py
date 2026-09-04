"""MaintenanceRecord request/response schemas."""

from app.models.maintenance import MaintenanceRecord, MaintenanceRecordCreate, MaintenanceRecordUpdate


class MaintenanceRecordCreateRequest(MaintenanceRecordCreate):
    pass


class MaintenanceRecordUpdateRequest(MaintenanceRecordUpdate):
    pass


class MaintenanceRecordResponse(MaintenanceRecord):
    pass
