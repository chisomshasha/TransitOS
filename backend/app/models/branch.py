"""Branch entity — see ``data-model.md`` §1."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class GPS(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class BankAccount(BaseModel):
    bank: str = Field(min_length=2, max_length=80)
    number: str = Field(min_length=6, max_length=20)
    name: str = Field(min_length=2, max_length=120)


class BranchStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class BranchBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    code: str = Field(
        min_length=2, max_length=10, pattern=r"^[A-Z0-9-]+$"
    )
    city: str = Field(min_length=1, max_length=80)
    state: str = Field(min_length=1, max_length=80)
    address: str = Field(min_length=2, max_length=240)
    contact_phone: Optional[str] = Field(default=None, max_length=20)
    contact_email: Optional[EmailStr] = None
    gps: Optional[GPS] = None
    bank_account: Optional[BankAccount] = None
    status: BranchStatus = BranchStatus.ACTIVE


class BranchCreate(BranchBase):
    """Create payload — all base fields required except optional ones."""


class BranchUpdate(BaseModel):
    """Patch payload — every field optional."""

    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    code: Optional[str] = Field(
        default=None, min_length=2, max_length=10, pattern=r"^[A-Z0-9-]+$"
    )
    city: Optional[str] = Field(default=None, min_length=1, max_length=80)
    state: Optional[str] = Field(default=None, min_length=1, max_length=80)
    address: Optional[str] = Field(default=None, min_length=2, max_length=240)
    contact_phone: Optional[str] = Field(default=None, max_length=20)
    contact_email: Optional[EmailStr] = None
    gps: Optional[GPS] = None
    bank_account: Optional[BankAccount] = None
    status: Optional[BranchStatus] = None
    manager_id: Optional[str] = None  # set via dedicated endpoint


class Branch(BranchBase):
    """In-DB shape — used internally, has ObjectId alias and metadata."""

    id: str = Field(default="")
    manager_id: Optional[str] = None
    is_active: bool = True
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("id", mode="before")
    @classmethod
    def _stringify_id(cls, v):
        if v is None:
            return v
        return str(v)
