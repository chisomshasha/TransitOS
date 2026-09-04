"""Password hashing + JWT minting/verifying + ``get_current_user`` dependency."""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Literal, Optional

from bson import ObjectId
from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from motor.motor_asyncio import AsyncIOMotorDatabase
from passlib.context import CryptContext
from pydantic import AfterValidator

from app.core.config import settings
from app.core.database import get_db
from app.core.roles import Role

logger = logging.getLogger(__name__)


# ─── password policy ─────────────────────────────────────────────────────────
# Applied when *setting* a password (create / change / reset).
# Login intentionally stays loose so we never reveal policy details on failure.
_PASSWORD_MIN_LEN = 10
_PASSWORD_MAX_LEN = 128
_PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).+$"
)
_PASSWORD_POLICY_MSG = (
    f"Password must be {_PASSWORD_MIN_LEN}–{_PASSWORD_MAX_LEN} characters and contain "
    "at least one uppercase letter, one lowercase letter, one digit, and one special character"
)


def validate_password_strength(value: str) -> str:
    """Raise ValueError if the password fails the strength policy."""
    if not isinstance(value, str):
        raise ValueError(_PASSWORD_POLICY_MSG)
    if len(value) < _PASSWORD_MIN_LEN or len(value) > _PASSWORD_MAX_LEN:
        raise ValueError(_PASSWORD_POLICY_MSG)
    if not _PASSWORD_PATTERN.match(value):
        raise ValueError(_PASSWORD_POLICY_MSG)
    return value


# Re-usable Pydantic type for request bodies that set a new password.
StrongPassword = Annotated[str, AfterValidator(validate_password_strength)]


# ─── password hashing ────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt. Returns the encoded hash string."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time comparison of a plaintext password against a bcrypt hash."""
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:  # pragma: no cover — defensive
        return False


# ─── JWT helpers ─────────────────────────────────────────────────────────────
def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(
    sub: str,
    *,
    role: str,
    email: str,
    branch_id: Optional[str] = None,
    extra_claims: Optional[dict[str, Any]] = None,
) -> str:
    """Mint a short-lived access JWT. ``sub`` is the user id (str)."""
    now = _now_utc()
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": sub,
        "role": role,
        "email": email,
        "branch_id": branch_id,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": uuid.uuid4().hex,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(sub: str) -> tuple[str, str]:
    """Mint a long-lived refresh JWT. Returns ``(jwt, jti)``.

    The ``jti`` is recorded in the ``refresh_tokens`` collection so we
    can revoke/rotate it on logout and refresh.
    """
    now = _now_utc()
    expire = now + timedelta(days=settings.refresh_token_expire_days)
    jti = uuid.uuid4().hex
    payload = {
        "sub": sub,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": jti,
    }
    token = jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    return token, jti


def verify_token(
    token: str, expected_type: Literal["access", "refresh"] = "access"
) -> dict[str, Any]:
    """Decode + validate a JWT. Raises ``HTTPException(401)`` on any failure."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        logger.debug("JWT decode failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    if payload.get("type") != expected_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token type, expected {expected_type}",
        )
    return payload


def verify_refresh_token(token: str) -> dict[str, Any]:
    """Convenience wrapper for ``verify_token(..., expected_type="refresh")``."""
    return verify_token(token, expected_type="refresh")


# ─── get_current_user dependency ─────────────────────────────────────────────
async def _load_user(db: AsyncIOMotorDatabase, user_id: str) -> Optional[dict]:
    """Fetch a user doc by id; ``None`` if not found or invalid id."""
    if not ObjectId.is_valid(user_id):
        return None
    return await db.users.find_one({"_id": ObjectId(user_id)})


def _raise_unauthorized(detail: str = "Not authenticated") -> None:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _raise_forbidden(detail: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail,
    )


async def get_current_user(
    authorization: Annotated[Optional[str], Header()] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    """FastAPI dependency: extract Bearer token, validate, load user.

    Returns the raw Mongo user document (dict). Each router decides
    how to project it into a response model.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        _raise_unauthorized()

    token = authorization.split(" ", 1)[1].strip()
    payload = verify_token(token, expected_type="access")

    user_id = payload.get("sub")
    if not user_id:
        _raise_unauthorized("Token missing subject")

    user = await _load_user(db, user_id)
    if user is None:
        _raise_unauthorized("User not found")

    # Stringify ObjectId for downstream code
    user["id"] = str(user["_id"])
    user.pop("password_hash", None)

    # Enforce active + status checks for every authenticated request.
    if not user.get("is_active", False):
        _raise_forbidden("Account is deactivated")
    if user.get("status") == "suspended":
        _raise_forbidden("Account is suspended")

    return user


def get_current_user_with_roles(
    required_roles: Optional[list[Role]] = None,
):
    """Build a dependency that enforces ``required_roles`` after auth.

    Returns the same user dict as ``get_current_user``. Use this factory
    when you want a one-line role check at the route signature.
    """
    if required_roles is None:
        required_roles = []

    required_values = {r.value if isinstance(r, Role) else str(r) for r in required_roles}

    async def _dep(
        authorization: Annotated[Optional[str], Header()] = None,
        db: AsyncIOMotorDatabase = Depends(get_db),
    ) -> dict:
        user = await get_current_user(authorization=authorization, db=db)
        if required_values and user.get("role") not in required_values:
            _raise_forbidden("Insufficient role")
        return user

    return _dep
