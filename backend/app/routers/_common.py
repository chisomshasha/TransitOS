"""Shared helpers for routers: response shapes, pagination, field projection,
branch scoping, and crew (driver/conductor) self-scoping.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.common import ListResponse, SingleResponse


# ─── ID handling ─────────────────────────────────────────────────────────────
def oid(maybe_id: str) -> ObjectId:
    """Convert a *path* id string to ``ObjectId``.

    Convention (consistent across all routers):
      - Path parameters that look like resource ids → **404** on invalid
        format (same response as a missing resource). This avoids leaking
        whether an id is malformed vs. simply unknown.
      - Body / query fields that reference other entities (e.g. ``branch_id``,
        ``user_id`` on create) → callers must use ``ObjectId.is_valid`` and
        raise **400** with an explicit "Invalid …" message. Do **not** use
        ``oid()`` for those — it would hide the validation error behind 404.
    """
    if not ObjectId.is_valid(maybe_id):
        from fastapi import HTTPException, status as st

        raise HTTPException(
            status_code=st.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )
    return ObjectId(maybe_id)


def require_valid_oid(value: str, field_name: str = "id") -> ObjectId:
    """Validate a body/query ObjectId string; raise 400 on bad format.

    Use this (not ``oid``) when the id comes from a request body or query
    parameter and the client should be told the field is invalid.
    """
    if not ObjectId.is_valid(value):
        from fastapi import HTTPException, status as st

        raise HTTPException(
            status_code=st.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name}",
        )
    return ObjectId(value)


# ─── projection ──────────────────────────────────────────────────────────────
def project_user(doc: dict[str, Any]) -> dict[str, Any]:
    """Strip password_hash and reset-token fields, stringify id for the wire."""
    if doc is None:
        return doc
    out = dict(doc)
    out["id"] = str(out.pop("_id", out.get("id")))
    out.pop("password_hash", None)
    out.pop("password_reset_token", None)       # legacy plaintext
    out.pop("password_reset_token_hash", None)  # hashed form
    out.pop("password_reset_expires", None)
    return out


def project(doc: dict[str, Any]) -> dict[str, Any]:
    """Generic project: stringify ``_id`` → ``id``, leave the rest."""
    if doc is None:
        return doc
    out = dict(doc)
    if "_id" in out and "id" not in out:
        out["id"] = str(out["_id"])
        out.pop("_id", None)
    return out


# ─── pagination ──────────────────────────────────────────────────────────────
async def paginate(
    db: AsyncIOMotorDatabase,
    collection: str,
    *,
    page: int = 1,
    page_size: int = 25,
    query: Optional[dict[str, Any]] = None,
    sort: list[tuple[str, int]] = None,
    projection: Optional[dict[str, int]] = None,
) -> ListResponse[dict[str, Any]]:
    """Standard paginated list. Returns ``ListResponse`` with envelope."""
    page = max(1, page)
    page_size = max(1, min(200, page_size))
    q = query or {}

    coll = db[collection]
    total = await coll.count_documents(q)
    skip = (page - 1) * page_size

    cursor = coll.find(q, projection or None).skip(skip).limit(page_size)
    if sort:
        cursor = cursor.sort(sort)
    items = [project(d) async for d in cursor]

    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return ListResponse[dict[str, Any]](
        items=items,
        total=total,
        page=page,
        totalPages=total_pages,
        hasMore=page < total_pages,
    )


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ─── branch scoping ──────────────────────────────────────────────────────────
# Roles restricted to their own branch_id on list/get/mutate of branch-owned
# resources (users, vehicles, drivers, conductors, trips, expenses, …).
BRANCH_SCOPED_ROLES: frozenset[str] = frozenset(
    {
        "branch_manager",
        "branch_accountant",
        "fleet_manager",
        "driver",
        "conductor",
    }
)

# Subset for branch-ops resources (cash-ups, reports, expenses, fleet entities).
BRANCH_OPS_SCOPED: frozenset[str] = frozenset(
    {
        "branch_manager",
        "branch_accountant",
        "fleet_manager",
    }
)


def branch_scope_query(
    actor: dict,
    *,
    roles: Optional[frozenset[str]] = None,
) -> dict | None:
    """Return a Mongo filter fragment restricting to the actor's branch, or None.

    Use on list endpoints::

        scope = branch_scope_query(user)
        if scope:
            query.update(scope)
    """
    role_set = roles if roles is not None else BRANCH_SCOPED_ROLES
    if actor.get("role") in role_set:
        bid = actor.get("branch_id")
        if bid:
            return {"branch_id": bid}
    return None


def assert_branch_access(
    actor: dict,
    resource_branch_id: str | None,
    *,
    roles: Optional[frozenset[str]] = None,
) -> None:
    """Raise 404 if a branch-scoped actor tries to touch another branch's resource.

    Using 404 (not 403) avoids leaking the existence of out-of-scope records.
    """
    role_set = roles if roles is not None else BRANCH_SCOPED_ROLES
    if actor.get("role") not in role_set:
        return
    actor_bid = actor.get("branch_id")
    if not actor_bid:
        return
    if resource_branch_id != actor_bid:
        from fastapi import HTTPException, status as st

        raise HTTPException(
            status_code=st.HTTP_404_NOT_FOUND, detail="Resource not found"
        )


def enforce_branch_write(
    actor: dict,
    resource_branch_id: str | None,
    *,
    roles: Optional[frozenset[str]] = None,
) -> None:
    """Like ``assert_branch_access`` but raises 403 for write operations."""
    role_set = roles if roles is not None else BRANCH_OPS_SCOPED
    if actor.get("role") not in role_set:
        return
    actor_bid = actor.get("branch_id")
    if not actor_bid:
        return
    if resource_branch_id != actor_bid:
        from fastapi import HTTPException, status as st

        raise HTTPException(
            status_code=st.HTTP_403_FORBIDDEN, detail="Not your branch"
        )


# ─── crew (driver / conductor) self-scoping for trips ────────────────────────
async def resolve_crew_profile_id(
    db: AsyncIOMotorDatabase, actor: dict
) -> Optional[str]:
    """Return the driver or conductor profile id linked to ``actor``, or None."""
    role = actor.get("role")
    user_id = actor.get("id") or str(actor.get("_id", ""))
    if not user_id:
        return None
    if role == "driver":
        doc = await db["drivers"].find_one(
            {"user_id": user_id, "is_active": True}
        )
        return str(doc["_id"]) if doc else None
    if role == "conductor":
        doc = await db["conductors"].find_one(
            {"user_id": user_id, "is_active": True}
        )
        return str(doc["_id"]) if doc else None
    return None


async def trip_scope_query(
    db: AsyncIOMotorDatabase, actor: dict
) -> dict | None:
    """Mongo filter for trip list/get based on role.

    - branch-scoped management roles → ``{branch_id: …}``
    - driver → ``{driver_id: <their profile id>}``
    - conductor → ``{conductor_id: <their profile id>}``
    - global roles → ``None`` (no extra filter)
    """
    role = actor.get("role")
    if role in ("branch_manager", "branch_accountant", "fleet_manager"):
        bid = actor.get("branch_id")
        return {"branch_id": bid} if bid else None
    if role in ("driver", "conductor"):
        profile_id = await resolve_crew_profile_id(db, actor)
        if not profile_id:
            # No profile → empty result set (match nothing)
            return {"_id": {"$exists": False}}
        field = "driver_id" if role == "driver" else "conductor_id"
        return {field: profile_id}
    return None


async def assert_trip_access(
    db: AsyncIOMotorDatabase, actor: dict, trip: dict
) -> None:
    """Raise 404 if actor may not see this trip (branch or crew assignment)."""
    role = actor.get("role")
    if role in ("branch_manager", "branch_accountant", "fleet_manager"):
        assert_branch_access(actor, trip.get("branch_id"), roles=BRANCH_OPS_SCOPED)
        return
    if role in ("driver", "conductor"):
        profile_id = await resolve_crew_profile_id(db, actor)
        field = "driver_id" if role == "driver" else "conductor_id"
        if not profile_id or trip.get(field) != profile_id:
            from fastapi import HTTPException, status as st

            raise HTTPException(
                status_code=st.HTTP_404_NOT_FOUND, detail="Trip not found"
            )
        return
    # Global roles (SA, OWNER, GM, …) — no restriction


__all__ = [
    "oid",
    "require_valid_oid",
    "project",
    "project_user",
    "paginate",
    "utcnow",
    "BRANCH_SCOPED_ROLES",
    "BRANCH_OPS_SCOPED",
    "branch_scope_query",
    "assert_branch_access",
    "enforce_branch_write",
    "resolve_crew_profile_id",
    "trip_scope_query",
    "assert_trip_access",
    "ListResponse",
    "SingleResponse",
]
