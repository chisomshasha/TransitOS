"""QR code generation + lookup.

GET /qr/generate/{entity_type}/{id}  — returns { token, deeplink, qr_png_url }
GET /qr/lookup?token=...             — resolves a token to { entity_type, id }

The deeplink is a transitos:// URI that the mobile app handles to
navigate directly to the entity detail screen.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.rbac import ANY_AUTHENTICATED, require_roles
from app.routers._common import oid
from app.services.qr import generate_qr_token, verify_qr_token

router = APIRouter(prefix="/qr", tags=["qr"])

# Entity types that can be encoded as QR. Kept small on purpose — only
# entities a field worker would reasonably scan on the yard or at the gate.
ALLOWED_ENTITY_TYPES = {"vehicle", "driver", "conductor", "branch"}


@router.get("/generate/{entity_type}/{entity_id}")
async def generate_qr(
    entity_type: str,
    entity_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*ANY_AUTHENTICATED)),
):
    """Generate a signed QR token for an entity. The entity must exist."""
    if entity_type not in ALLOWED_ENTITY_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported entity type: {entity_type}",
        )

    collection_map = {
        "vehicle": "vehicles",
        "driver": "drivers",
        "conductor": "conductors",
        "branch": "branches",
    }
    collection = collection_map[entity_type]

    # Validate the entity exists
    doc = await db[collection].find_one({"_id": oid(entity_id), "is_active": True})
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity_type} not found",
        )

    token = generate_qr_token(entity_type, entity_id)
    deeplink = f"transitos://{entity_type}/{entity_id}"

    return {
        "token": token,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "deeplink": deeplink,
    }


@router.get("/lookup")
async def lookup_qr(
    token: str = Query(..., min_length=8, max_length=256),
    user: dict = Depends(require_roles(*ANY_AUTHENTICATED)),
):
    """Resolve a scanned QR token back to an entity reference."""
    result = verify_qr_token(token)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired QR code",
        )
    entity_type, entity_id, _ts = result
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "deeplink": f"transitos://{entity_type}/{entity_id}",
    }


__all__ = ["router"]
