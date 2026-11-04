"""Driver entity — see ``data-model.md`` §4."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class DriverStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ON_LEAVE = "on_leave"


class DriverBase(BaseModel):
    user_id: str
    license_no: str = Field(min_length=3, max_length=40)
    license_expiry: datetime
    years_experience: int = Field(ge=0, le=60, default=0)
    status: DriverStatus = DriverStatus.ACTIVE


class DriverCreate(DriverBase):
    pass


class DriverUpdate(BaseModel):
    license_no: Optional[str] = Field(default=None, min_length=3, max_length=40)
    license_expiry: Optional[datetime] = None
    years_experience: Optional[int] = Field(default=None, ge=0, le=60)
    status: Optional[DriverStatus] = None


class Driver(DriverBase):
    """In-DB shape."""

    id: str = Field(default="")
    branch_id: Optional[str] = None
    is_active: bool = True
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("id", mode="before")
    @classmethod
    def _stringify_id(cls, v):
        return str(v) if v is not None else v
