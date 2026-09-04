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

# ─── Role-assignment hierarchy ─────────────────────────────────────────────
# Used to stop an actor from granting a role more senior than their own
# (privilege escalation via user create/update). Actors may assign a role
# at their own tier or below; SA sits at tier 0 so it can assign any role.
# Peers at the same tier (e.g. OM/FM/CA) may assign one another — this is
# a coarse safety net, not a full per-actor allow-list; Branch Manager
# additionally keeps its own narrower explicit allow-list on top of this.
ROLE_RANK: dict[Role, int] = {
    SA: 0,
    OWNER: 1,
    GM: 2,
    OM: 3,
    FM: 3,
    CA: 3,
    BM: 4,
    BA: 5,
    DRIVER: 6,
    CONDUCTOR: 6,
}


def can_assign_role(actor_role: Role | str, target_role: Role | str) -> bool:
    """True if ``actor_role`` is permitted to grant ``target_role``.

    An actor may only assign a role at its own seniority tier or below
    (i.e. it can never grant something more senior than itself). Roles
    outside ``ROLE_RANK`` (shouldn't happen — it covers all 10) are
    treated as unassignable, failing closed rather than open.
    """
    actor = Role(actor_role) if not isinstance(actor_role, Role) else actor_role
    target = Role(target_role) if not isinstance(target_role, Role) else target_role
    if actor not in ROLE_RANK or target not in ROLE_RANK:
        return False
    return ROLE_RANK[target] >= ROLE_RANK[actor]


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
    "ROLE_RANK",
    "can_assign_role",
]
