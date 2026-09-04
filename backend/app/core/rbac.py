"""Role-based dependency factory. Role enum lives in ``app.core.roles``."""

from __future__ import annotations

from typing import Optional

from fastapi import Depends

from app.core.roles import (
    ANY_AUTHENTICATED,
    BA,
    BM,
    CA,
    CONDUCTOR,
    CREW_READ,
    DRIVER,
    FM,
    FLEET_OPS,
    GM,
    OM,
    OWNER,
    READ_ALL,
    Role,
    SA,
    SAFETY_OPS,
    USERS_READ,
)
from app.core.security import get_current_user, get_current_user_with_roles


def require_roles(*roles: Role):
    """Dependency factory: ``Depends(require_roles(SA, OWNER))``.

    Returns a dependency that authenticates the user and enforces the
    role allowlist. If ``roles`` is empty, only authentication is
    required (any logged-in user passes).
    """
    role_list: Optional[list[Role]] = list(roles) if roles else None
    return get_current_user_with_roles(role_list)


__all__ = [
    "Role",
    "SA",
    "OWNER",
    "GM",
    "BM",
    "OM",
    "FM",
    "CA",
    "BA",
    "DRIVER",
    "CONDUCTOR",
    "ANY_AUTHENTICATED",
    "READ_ALL",
    "SAFETY_OPS",
    "FLEET_OPS",
    "USERS_READ",
    "CREW_READ",
    "require_roles",
    "get_current_user",
]
