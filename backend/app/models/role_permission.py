"""Role-permission model — one document per role, storing all granted actions per resource."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# Every resource that can be gated
RESOURCES = [
    "branches",
    "users",
    "vehicles",
    "drivers",
    "conductors",
    "routes",
    "trips",
    "fuel",
    "maintenance",
    "expenses",
    "cash_ups",
    "reports",
    "audit_log",
    "notifications",
    "transfers",
    "incidents",
    "inspections",
    "vehicle_documents",
    "role_permissions",
]

# Every action that can be granted
ACTIONS = ["read", "create", "update", "delete", "approve", "export"]

# Scope values
SCOPES = ["all", "branch", "own"]


class RolePermission(BaseModel):
    id: Optional[str] = None
    role: str
    permissions: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Map of resource → list of granted actions",
    )
    scope: str = Field(
        default="all",
        description="Data scope: 'all' = global, 'branch' = own branch only, 'own' = own records only",
    )
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None


class RolePermissionUpdate(BaseModel):
    permissions: Dict[str, List[str]] = Field(
        ...,
        description="Complete permissions map for this role (replaces previous)",
    )
    scope: Optional[str] = None


class RolePermissionResponse(RolePermission):
    pass


# Default permissions matrix — used to seed the collection on first access
# and as the "Reset to defaults" baseline.
DEFAULT_PERMISSIONS: Dict[str, Dict[str, List[str]]] = {
    "super_admin": {r: list(ACTIONS) for r in RESOURCES},
    "owner": {r: list(ACTIONS) for r in RESOURCES},
    "general_manager": {
        r: list(ACTIONS) for r in RESOURCES
    },
    "branch_manager": {
        "branches": ["read"],
        "users": ["read", "create", "update"],
        "vehicles": ["read", "create", "update", "delete"],
        "drivers": ["read", "create", "update", "delete"],
        "conductors": ["read", "create", "update", "delete"],
        "routes": ["read"],
        "trips": ["read", "create", "update", "delete", "export"],
        "fuel": ["read", "create", "update"],
        "maintenance": ["read", "create", "update"],
        "expenses": ["read", "create", "update", "approve"],
        "cash_ups": ["read", "approve", "export"],
        "reports": ["read", "export"],
        "audit_log": ["read"],
        "notifications": ["read"],
        "transfers": ["read", "create", "update"],
        "incidents": ["read", "create", "update"],
        "inspections": ["read", "create"],
        "vehicle_documents": ["read", "create", "update", "delete"],
        "role_permissions": [],
    },
    "operations_manager": {
        "branches": ["read"],
        "users": [],
        "vehicles": ["read", "create", "update"],
        "drivers": ["read", "create", "update"],
        "conductors": ["read", "create", "update"],
        "routes": ["read", "create", "update"],
        "trips": ["read", "create", "update", "delete", "export"],
        "fuel": ["read"],
        "maintenance": ["read"],
        "expenses": [],
        "cash_ups": ["read"],
        "reports": ["read", "export"],
        "audit_log": ["read"],
        "notifications": ["read"],
        "transfers": ["read", "create", "update"],
        "incidents": ["read", "create", "update"],
        "inspections": ["read", "create"],
        "vehicle_documents": ["read"],
        "role_permissions": [],
    },
    "fleet_manager": {
        "branches": ["read"],
        "users": [],
        "vehicles": ["read", "create", "update", "delete"],
        "drivers": ["read", "create", "update", "delete"],
        "conductors": ["read", "create", "update", "delete"],
        "routes": ["read", "create", "update"],
        "trips": ["read", "create", "update", "export"],
        "fuel": ["read", "create", "update", "delete"],
        "maintenance": ["read", "create", "update", "delete"],
        "expenses": [],
        "cash_ups": ["read"],
        "reports": ["read", "export"],
        "audit_log": [],
        "notifications": ["read"],
        "transfers": ["read", "create", "update"],
        "incidents": ["read", "create"],
        "inspections": ["read", "create"],
        "vehicle_documents": ["read", "create", "update", "delete"],
        "role_permissions": [],
    },
    "chief_accountant": {
        "branches": ["read"],
        "users": [],
        "vehicles": ["read"],
        "drivers": ["read"],
        "conductors": ["read"],
        "routes": ["read"],
        "trips": ["read", "export"],
        "fuel": ["read"],
        "maintenance": ["read"],
        "expenses": ["read", "create", "update", "delete", "approve", "export"],
        "cash_ups": ["read", "approve", "export"],
        "reports": ["read", "export"],
        "audit_log": [],
        "notifications": ["read"],
        "transfers": [],
        "incidents": ["read"],
        "inspections": ["read"],
        "vehicle_documents": ["read"],
        "role_permissions": [],
    },
    "branch_accountant": {
        "branches": ["read"],
        "users": ["read"],
        "vehicles": ["read"],
        "drivers": ["read"],
        "conductors": ["read"],
        "routes": ["read"],
        "trips": ["read", "export"],
        "fuel": [],
        "maintenance": [],
        "expenses": ["read", "create", "update", "export"],
        "cash_ups": ["read", "create", "update", "export"],
        "reports": ["read", "export"],
        "audit_log": [],
        "notifications": ["read"],
        "transfers": [],
        "incidents": ["read"],
        "inspections": ["read"],
        "vehicle_documents": ["read"],
        "role_permissions": [],
    },
    "driver": {
        "branches": [],
        "users": [],
        "vehicles": ["read"],
        "drivers": [],
        "conductors": [],
        "routes": ["read"],
        "trips": ["read"],
        "fuel": ["read", "create"],
        "maintenance": ["read"],
        "expenses": [],
        "cash_ups": [],
        "reports": [],
        "audit_log": [],
        "notifications": ["read"],
        "transfers": [],
        "incidents": ["read", "create"],
        "inspections": ["read", "create"],
        "vehicle_documents": ["read"],
        "role_permissions": [],
    },
    "conductor": {
        "branches": [],
        "users": [],
        "vehicles": ["read"],
        "drivers": [],
        "conductors": [],
        "routes": ["read"],
        "trips": ["read"],
        "fuel": [],
        "maintenance": [],
        "expenses": [],
        "cash_ups": ["read", "create", "update"],
        "reports": [],
        "audit_log": [],
        "notifications": ["read"],
        "transfers": [],
        "incidents": ["read", "create"],
        "inspections": ["read"],
        "vehicle_documents": ["read"],
        "role_permissions": [],
    },
}

DEFAULT_SCOPES: Dict[str, str] = {
    "super_admin": "all",
    "owner": "all",
    "general_manager": "all",
    "branch_manager": "branch",
    "operations_manager": "all",
    "fleet_manager": "all",
    "chief_accountant": "all",
    "branch_accountant": "branch",
    "driver": "own",
    "conductor": "own",
}


__all__ = [
    "RolePermission",
    "RolePermissionUpdate",
    "RolePermissionResponse",
    "RESOURCES",
    "ACTIONS",
    "SCOPES",
    "DEFAULT_PERMISSIONS",
    "DEFAULT_SCOPES",
]
