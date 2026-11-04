"""Conductor schemas — response includes denormalized user fields."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.conductor import (
    Conductor,
    ConductorCreate,
    ConductorStatus,
    ConductorUpdate,
)


class ConductorCreateRequest(ConductorCreate):
    pass


class ConductorUpdateRequest(ConductorUpdate):
    pass


class ConductorResponse(BaseModel):
    """Wire shape. Includes denormalized user fields when available."""

    id: str
    user_id: str
    badge_no: str
    status: ConductorStatus
    branch_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)
