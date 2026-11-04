"""Request / response schemas (per-entity)."""

from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    ResetPasswordRequest,
)
from app.schemas.branch import (
    BranchCreateRequest,
    BranchResponse,
    BranchUpdateRequest,
    SetManagerRequest,
)
from app.schemas.cash_up import (
    CashUpApproveRequest,
    CashUpCreateRequest,
    CashUpResponse,
    CashUpUpdateRequest,
)
from app.schemas.common import (
    ErrorBody,
    ListResponse,
    SingleResponse,
)
from app.schemas.conductor import (
    ConductorCreateRequest,
    ConductorResponse,
    ConductorUpdateRequest,
)
from app.schemas.driver import (
    DriverCreateRequest,
    DriverResponse,
    DriverUpdateRequest,
)
from app.schemas.expense import (
    ExpenseCreateRequest,
    ExpenseResponse,
    ExpenseUpdateRequest,
)
from app.schemas.fuel import (
    FuelLogCreateRequest,
    FuelLogResponse,
    FuelLogUpdateRequest,
)
from app.schemas.maintenance import (
    MaintenanceRecordCreateRequest,
    MaintenanceRecordResponse,
    MaintenanceRecordUpdateRequest,
)
from app.schemas.manifest import (
    ManifestCreateRequest,
    ManifestResponse,
    ManifestUpdateRequest,
)
from app.schemas.route import (
    RouteCreateRequest,
    RouteResponse,
    RouteUpdateRequest,
)
from app.schemas.trip import (
    TripCreateRequest,
    TripResponse,
    TripStatusChangeRequest,
    TripUpdateRequest,
)
from app.schemas.user import (
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)
from app.schemas.vehicle import (
    VehicleCreateRequest,
    VehicleResponse,
    VehicleUpdateRequest,
)
from app.schemas.vehicle import (
    VehicleCreateRequest,
    VehicleResponse,
    VehicleUpdateRequest,
)

__all__ = [
    "ErrorBody",
    "ListResponse",
    "SingleResponse",
    # auth
    "LoginRequest",
    "LoginResponse",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    "ChangePasswordRequest",
    # branch
    "BranchCreateRequest",
    "BranchResponse",
    "BranchUpdateRequest",
    "SetManagerRequest",
    # user
    "UserCreateRequest",
    "UserResponse",
    "UserUpdateRequest",
    # vehicle
    "VehicleCreateRequest",
    "VehicleResponse",
    "VehicleUpdateRequest",
    # driver
    "DriverCreateRequest",
    "DriverResponse",
    "DriverUpdateRequest",
    # conductor
    "ConductorCreateRequest",
    "ConductorResponse",
    "ConductorUpdateRequest",
    # route
    "RouteCreateRequest",
    "RouteResponse",
    "RouteUpdateRequest",
]
