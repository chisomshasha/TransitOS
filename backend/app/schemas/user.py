"""User request / response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import StrongPassword
from app.models.user import UserRole, UserStatus


class UserCreateRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=20)
    role: UserRole
    branch_id: Optional[str] = None
    status: UserStatus = UserStatus.ACTIVE
    hire_date: Optional[datetime] = None
    photo_url: Optional[str] = None
    password: StrongPassword

    @field_validator("email", mode="before")
    @classmethod
    def _lowercase_email(cls, v):
        return v.lower() if isinstance(v, str) else v


class UserUpdateRequest(BaseModel):
    """Partial update for an existing user.

    ``new_password`` is optional and only accepted by roles with user-mutate
    privileges (see SAFETY_OPS). When set it is validated against the same
    strength policy as create/change/reset (``StrongPassword``) and all of
    the target user's refresh tokens are revoked server-side.
    """

    full_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=20)
    role: Optional[UserRole] = None
    branch_id: Optional[str] = None
    status: Optional[UserStatus] = None
    hire_date: Optional[datetime] = None
    photo_url: Optional[str] = None
    # Admin-initiated password reset. Strength-checked by StrongPassword.
    new_password: Optional[StrongPassword] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: str
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    role: str
    branch_id: Optional[str] = None
    status: str = "active"
    hire_date: Optional[datetime] = None
    photo_url: Optional[str] = None
    is_active: bool = True
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


__all__ = [
    "UserCreateRequest",
    "UserUpdateRequest",
    "UserResponse",
]
