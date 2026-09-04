"""Pydantic v2 models for Sprint A. See ``data-model.md`` for source of truth.

Models are split per-entity. ``__init__`` re-exports the public names
so callers can do ``from app.models import BranchCreate``.
"""
from app.models.audit import AuditAction, AuditLogEntry
from app.models.branch import (
    BankAccount,
    Branch,
    BranchBase,
    BranchCreate,
    BranchStatus,
    BranchUpdate,
    GPS,
)
from app.models.conductor import (
    Conductor,
    ConductorBase,
    ConductorCreate,
    ConductorStatus,
    ConductorUpdate,
)
from app.models.driver import (
    Driver,
    DriverBase,
    DriverCreate,
    DriverStatus,
    DriverUpdate,
)
from app.models.refresh_token import RefreshToken
from app.models.route import (
    IntermediateStop,
    Route,
    RouteBase,
    RouteCreate,
    RouteType,
    RouteUpdate,
)
from app.models.user import (
    User,
    UserBase,
    UserCreate,
    UserStatus,
    UserUpdate,
)
from app.models.vehicle import (
    Vehicle,
    VehicleBase,
    VehicleCreate,
    VehicleDocument,
    VehicleStatus,
    VehicleType,
    VehicleUpdate,
)

__all__ = [
    # branch
    "BankAccount",
    "Branch",
    "BranchBase",
    "BranchCreate",
    "BranchStatus",
    "BranchUpdate",
    "GPS",
    # user
    "User",
    "UserBase",
    "UserCreate",
    "UserStatus",
    "UserUpdate",
    # vehicle
    "Vehicle",
    "VehicleBase",
    "VehicleCreate",
    "VehicleDocument",
    "VehicleStatus",
    "VehicleType",
    "VehicleUpdate",
    # driver
    "Driver",
    "DriverBase",
    "DriverCreate",
    "DriverStatus",
    "DriverUpdate",
    # conductor
    "Conductor",
    "ConductorBase",
    "ConductorCreate",
    "ConductorStatus",
    "ConductorUpdate",
    # route
    "IntermediateStop",
    "Route",
    "RouteBase",
    "RouteCreate",
    "RouteType",
    "RouteUpdate",
    # audit
    "AuditAction",
    "AuditLogEntry",
    # refresh
    "RefreshToken",
]
