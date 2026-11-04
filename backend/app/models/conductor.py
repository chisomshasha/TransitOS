"""Conductor entity — see ``data-model.md`` §5."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ConductorStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ON_LEAVE = "on_leave"


class ConductorBase(BaseModel):
    user_id: str
    badge_no: str = Field(
        min_length=2, max_length=20, pattern=r"^[A-Z0-9-]+$"
    )
    status: ConductorStatus = ConductorStatus.ACTIVE


class ConductorCreate(ConductorBase):
    pass


class ConductorUpdate(BaseModel):
    badge_no: Optional[str] = Field(
        default=None, min_length=2, max_length=20, pattern=r"^[A-Z0-9-]+$"
    )
    status: Optional[ConductorStatus] = None


class Conductor(ConductorBase):
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
