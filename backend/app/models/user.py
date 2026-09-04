"""User entity — see ``data-model.md`` §2."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import StrongPassword


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    OWNER = "owner"
    GENERAL_MANAGER = "general_manager"
    BRANCH_MANAGER = "branch_manager"
    OPERATIONS_MANAGER = "operations_manager"
    FLEET_MANAGER = "fleet_manager"
    CHIEF_ACCOUNTANT = "chief_accountant"
    BRANCH_ACCOUNTANT = "branch_accountant"
    DRIVER = "driver"
    CONDUCTOR = "conductor"


class UserStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"


# Roles that require a branch_id on create.
BRANCH_SCOPED_ROLES: set[UserRole] = {
    UserRole.BRANCH_MANAGER,
    UserRole.BRANCH_ACCOUNTANT,
    UserRole.DRIVER,
    UserRole.CONDUCTOR,
}


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=20)
    role: UserRole
    branch_id: Optional[str] = None
    status: UserStatus = UserStatus.ACTIVE
    hire_date: Optional[datetime] = None
    photo_url: Optional[str] = None

    @field_validator("email", mode="before")
    @classmethod
    def _lowercase_email(cls, v):
        return v.lower() if isinstance(v, str) else v


class UserCreate(UserBase):
    password: StrongPassword


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=20)
    role: Optional[UserRole] = None
    branch_id: Optional[str] = None
    status: Optional[UserStatus] = None
    hire_date: Optional[datetime] = None
    photo_url: Optional[str] = None


class User(UserBase):
    """In-DB shape with password_hash. NEVER serialize to clients."""

    id: str = Field(default="")
    password_hash: str
    is_active: bool = True
    deleted_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
