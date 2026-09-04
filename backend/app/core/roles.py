"""Role enum — single source of truth for user roles.

Lives in its own module to avoid the ``rbac ↔ security`` circular import
that happens when both modules try to import ``Role`` from each other.
"""

from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    """Closed role enum for Sprint A. Wire values are the ``.value`` strings.

    See ``data-model.md`` §0.5 — 10 roles (incl. ``super_admin`` for
    platform bootstrap).
    """

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


# Aliases for ergonomic, readable call sites. Use these instead of
# repeating the role string in router signatures.
SA = Role.SUPER_ADMIN
OWNER = Role.OWNER
GM = Role.GENERAL_MANAGER
BM = Role.BRANCH_MANAGER
OM = Role.OPERATIONS_MANAGER
FM = Role.FLEET_MANAGER
CA = Role.CHIEF_ACCOUNTANT
BA = Role.BRANCH_ACCOUNTANT
DRIVER = Role.DRIVER
CONDUCTOR = Role.CONDUCTOR


# Role group shortcuts. Mirrors the api-contract.md tables.
ANY_AUTHENTICATED: list[Role] = list(Role)

# Roles that can read branches/vehicles/routes (anywhere).
READ_ALL: list[Role] = [
    SA, OWNER, GM, BM, OM, FM, CA, BA,
]

# Roles that can mutate branches / users.
SAFETY_OPS: list[Role] = [SA, OWNER, GM, OM, BM, FM]

# Roles that can mutate vehicles / drivers / conductors.
FLEET_OPS: list[Role] = [SA, OWNER, GM, BM, FM]

# Roles that can list users (read-only for branch-scoped).
USERS_READ: list[Role] = [SA, OWNER, GM, BM, BA]

# Roles that can read drivers/conductors.
CREW_READ: list[Role] = [SA, OWNER, GM, BM, OM, FM]


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
]
