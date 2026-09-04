"""Push-token router — register/unregister device tokens, list own tokens.

Stores one document per (user_id, token) pair in ``push_tokens`` so a
user can have several devices registered at once. Registration is
idempotent: re-registering the same token just refreshes it (and
reactivates it if it had been deactivated).
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.rbac import ANY_AUTHENTICATED, require_roles
from app.models.push_token import PushTokenRegister, PushTokenResponse
from app.routers._common import project
from app.schemas.common import ListResponse, SingleResponse
from app.services.audit import write_audit

router = APIRouter(prefix="/push", tags=["push"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@router.post(
    "/register",
    response_model=SingleResponse[PushTokenResponse],
    status_code=status.HTTP_200_OK,
)
async def register_token(
    payload: PushTokenRegister,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*ANY_AUTHENTICATED)),
):
    """Register (or refresh) a push token for the current user's device.

    Upserts on ``(user_id, token)`` so calling this again on every app
    launch is safe and cheap — it never creates duplicate rows for the
    same device/token pair.
    """
    user_id = user["id"]
    now = _utcnow()

    existing = await db.push_tokens.find_one(
        {"user_id": user_id, "token": payload.token}
    )

    update_doc = {
        "user_id": user_id,
        "token": payload.token,
        "platform": payload.platform.value
        if hasattr(payload.platform, "value")
        else payload.platform,
        "device_id": payload.device_id,
        "app_version": payload.app_version,
        "is_active": True,
        "updated_at": now,
    }

    if existing:
        await db.push_tokens.update_one(
            {"_id": existing["_id"]}, {"$set": update_doc}
        )
        doc = await db.push_tokens.find_one({"_id": existing["_id"]})
    else:
        update_doc["created_at"] = now
        result = await db.push_tokens.insert_one(update_doc)
        doc = await db.push_tokens.find_one({"_id": result.inserted_id})

    await write_audit(
        db,
        action="push_token.register",
        entity_type="push_token",
        entity_id=str(doc["_id"]),
        actor_id=user_id,
        actor_email=user.get("email"),
        metadata={"platform": update_doc["platform"], "device_id": payload.device_id},
    )

    return SingleResponse[PushTokenResponse](data=project(doc))


@router.get("", response_model=ListResponse[PushTokenResponse])
async def list_my_tokens(
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*ANY_AUTHENTICATED)),
):
    """List the current user's active registered push tokens."""
    cursor = db.push_tokens.find(
        {"user_id": user["id"], "is_active": True}
    ).sort("updated_at", -1)
    items = [project(d) async for d in cursor]
    return ListResponse[PushTokenResponse](
        items=items,
        total=len(items),
        page=1,
        totalPages=1 if items else 0,
        hasMore=False,
    )


@router.post("/unregister", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_token(
    payload: PushTokenRegister,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*ANY_AUTHENTICATED)),
):
    """Deactivate a push token for the current user (e.g. on logout).

    Soft-deletes (``is_active = False``) rather than removing the row,
    consistent with the rest of the app's soft-delete convention.
    """
    user_id = user["id"]
    existing = await db.push_tokens.find_one(
        {"user_id": user_id, "token": payload.token}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Push token not found")

    await db.push_tokens.update_one(
        {"_id": existing["_id"]},
        {"$set": {"is_active": False, "updated_at": _utcnow()}},
    )

    await write_audit(
        db,
        action="push_token.unregister",
        entity_type="push_token",
        entity_id=str(existing["_id"]),
        actor_id=user_id,
        actor_email=user.get("email"),
    )
    return None


__all__ = ["router"]
