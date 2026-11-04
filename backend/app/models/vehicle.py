"""Vehicle entity — see ``data-model.md`` §3."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class VehicleType(str, Enum):
    BUS = "bus"
    MINIBUS = "minibus"
    TRUCK = "truck"


class VehicleStatus(str, Enum):
    AVAILABLE = "available"
    ON_TRIP = "on_trip"
    MAINTENANCE = "maintenance"
    GROUNDED = "grounded"


class VehicleDocument(BaseModel):
    document_type: str = Field(min_length=2, max_length=40)
    reference_no: Optional[str] = Field(default=None, max_length=80)
    issued_at: Optional[datetime] = None
    expires_at: datetime
    file_url: Optional[str] = None


class VehicleBase(BaseModel):
    reg_number: str = Field(
        min_length=3, max_length=20, pattern=r"^[A-Z0-9-]+$"
    )
    type: VehicleType
    capacity_seats: int = Field(ge=1, le=200)
    capacity_kg: int = Field(ge=0, le=50_000)
    branch_id: str
    home_terminal_id: Optional[str] = None
    status: VehicleStatus = VehicleStatus.AVAILABLE
    current_odometer_km: int = Field(ge=0, default=0)
    current_fuel_level: float = Field(ge=0, le=100, default=0)
    documents: list[VehicleDocument] = Field(default_factory=list)


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseModel):
    reg_number: Optional[str] = Field(
        default=None, min_length=3, max_length=20, pattern=r"^[A-Z0-9-]+$"
    )
    type: Optional[VehicleType] = None
    capacity_seats: Optional[int] = Field(default=None, ge=1, le=200)
    capacity_kg: Optional[int] = Field(default=None, ge=0, le=50_000)
    home_terminal_id: Optional[str] = None
    status: Optional[VehicleStatus] = None
    current_odometer_km: Optional[int] = Field(default=None, ge=0)
    current_fuel_level: Optional[float] = Field(default=None, ge=0, le=100)
    documents: Optional[list[VehicleDocument]] = None


class Vehicle(VehicleBase):
    id: str = Field(default="")
    is_active: bool = True
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("id", mode="before")
    @classmethod
    def _stringify_id(cls, v):
        return str(v) if v is not None else v
