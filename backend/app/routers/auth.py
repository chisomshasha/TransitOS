"""Auth router: login, refresh, logout, me, change-password, forgot/reset.

All endpoints are under ``/auth`` (no ``/api`` prefix in Sprint A).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.rbac import ANY_AUTHENTICATED
from app.core.security import (
    get_current_user,
    verify_refresh_token,
)
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    ResetPasswordRequest,
)
from app.schemas.common import SingleResponse
from app.schemas.user import UserResponse
from app.services import (
    assert_refresh_device_match,
    authenticate_user,
    complete_password_reset,
    issue_token_pair,
    revoke_all_user_tokens,
    revoke_refresh_token,
    start_password_reset,
    write_audit,
)
from app.services.auth import _deliver_reset_email
from app.routers._common import project_user, utcnow

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


# ─── POST /auth/login ────────────────────────────────────────────────────────
@router.post("/login", response_model=SingleResponse[LoginResponse])
@limiter.limit("10/minute")
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Email + password → access + refresh tokens."""
    user = await authenticate_user(db, email=body.email, password=body.password)
    tokens = await issue_token_pair(
        db,
        user,
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )
    await write_audit(
        db,
        action="login",
        entity_type="user",
        entity_id=str(user["_id"]),
        actor_id=str(user["_id"]),
        actor_email=user.get("email"),
        branch_id=user.get("branch_id"),
    )
    return SingleResponse[LoginResponse](data=tokens)


# ─── POST /auth/refresh ──────────────────────────────────────────────────────
@router.post("/refresh", response_model=SingleResponse[LoginResponse])
@limiter.limit("30/minute")
async def refresh(
    request: Request,
    authorization: Annotated[Optional[str], Header()] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Exchange a valid refresh token for a fresh access + refresh pair.

    Per api-contract.md §1.2: the refresh token travels in the
    ``Authorization: Bearer <token>`` header, body is empty.
    Soft device binding is enforced when a fingerprint was stored at login.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
        )
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="refresh_token is required",
        )

    payload = verify_refresh_token(token)
    jti = payload.get("jti")
    user_id = payload.get("sub")
    if not jti or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed refresh token"
        )

    # Has the token been revoked?
    rec = await db.refresh_tokens.find_one({"jti": jti})
    if rec is None or rec.get("revoked"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revoked or unknown",
        )

    # Soft device binding
    await assert_refresh_device_match(
        db,
        jti,
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )

    # Rotate — revoke old, issue new
    await revoke_refresh_token(db, jti)

    from bson import ObjectId

    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user"
        )
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if user is None or not user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    if user.get("status") == "suspended":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is suspended"
        )

    tokens = await issue_token_pair(
        db,
        user,
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )
    return SingleResponse[LoginResponse](data=tokens)


# ─── POST /auth/logout ───────────────────────────────────────────────────────
@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: dict,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Revoke the supplied refresh token. Idempotent."""
    token = body.get("refresh_token")
    if token:
        try:
            payload = verify_refresh_token(token)
            jti = payload.get("jti")
            if jti:
                await revoke_refresh_token(db, jti)
        except HTTPException:
            pass  # idempotent — already gone is fine
    await write_audit(
        db,
        action="logout",
        entity_type="user",
        entity_id=str(user["_id"]),
        actor_id=str(user["_id"]),
        actor_email=user.get("email"),
    )
    return None


# ─── GET /auth/me ────────────────────────────────────────────────────────────
@router.get("/me", response_model=SingleResponse[UserResponse])
async def me(user: dict = Depends(get_current_user)):
    return SingleResponse[UserResponse](data=project_user(user))


# ─── POST /auth/change-password ──────────────────────────────────────────────
@router.post(
    "/change-password", status_code=status.HTTP_204_NO_CONTENT
)
@limiter.limit("5/minute")
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Self-service password change. Requires current password for verification.

    Revokes all refresh tokens on success (forces re-login everywhere).
    """
    from app.core.security import verify_password, get_password_hash

    from bson import ObjectId

    full = await db.users.find_one({"_id": ObjectId(user["id"])})
    if not full or not verify_password(body.current_password, full.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    await db.users.update_one(
        {"_id": ObjectId(user["id"])},
        {
            "$set": {
                "password_hash": get_password_hash(body.new_password),
                "updated_at": utcnow(),
            }
        },
    )
    await revoke_all_user_tokens(db, user["id"])
    await write_audit(
        db,
        action="change_password",
        entity_type="user",
        entity_id=user["id"],
        actor_id=user["id"],
        actor_email=user.get("email"),
    )
    return None


# ─── POST /auth/forgot-password ──────────────────────────────────────────────
@router.post(
    "/forgot-password", status_code=status.HTTP_202_ACCEPTED
)
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Always returns 202 — never reveals whether the email exists.

    In dev we log the reset token so the tester can complete the flow.
    In staging/prod the token is never written to logs.
    """
    token = await start_password_reset(db, body.email)
    if token:
        await _deliver_reset_email(email=body.email, token=token)
    return None
	
# ─── POST /auth/forgot-username ──────────────────────────────────────────────
@router.post(
    "/forgot-username", status_code=status.HTTP_202_ACCEPTED
)
@limiter.limit("5/minute")
async def forgot_username(
    request: Request,
    body: ForgotUsernameRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Send username reminder if email exists. Always returns 202."""
    from app.services.auth import _deliver_username_email

    user = await db.users.find_one({"email": body.email.lower()})
    if user:
        await _deliver_username_email(email=body.email, username=user.get("email"))
    return None	


# ─── POST /auth/reset-password ───────────────────────────────────────────────
@router.post(
    "/reset-password", status_code=status.HTTP_204_NO_CONTENT
)
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    ok = await complete_password_reset(
        db, token=body.token, new_password=body.new_password
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    return None


__all__ = ["router"]
