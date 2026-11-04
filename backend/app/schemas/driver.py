"""Driver schemas — note: response includes denormalized user fields
(see Open Decision #2 in SUMMARY.md)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.driver import Driver, DriverCreate, DriverStatus, DriverUpdate


class DriverCreateRequest(DriverCreate):
    pass


class DriverUpdateRequest(DriverUpdate):
    pass


class DriverResponse(BaseModel):
    """Wire shape. Includes denormalized user fields when available."""

    id: str
    user_id: str
    license_no: str
    license_expiry: datetime
    years_experience: int
    status: DriverStatus
    branch_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # Denormalized from the linked User record (data-model.md §0.5):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)
