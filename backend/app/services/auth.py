"""Auth flow helpers — login, refresh-token issuance, revocation.

``issue_token_pair`` mints both tokens, persists the refresh-token record
(jti + expiry) for revocation, and returns the wire shape. The actual
JWT signing lives in ``app.core.security`` so the same crypto is used
by tests.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from app.core.lockout import clear_failed_logins, is_locked, record_failed_login
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from app.schemas.auth import LoginResponse

logger = logging.getLogger(__name__)


# ─── password helpers ────────────────────────────────────────────────────────
def hash_password(plain: str) -> str:
    """Wrap ``get_password_hash`` for ergonomic imports in services."""
    return get_password_hash(plain)


def _hash_reset_token(token: str) -> str:
    """SHA-256 hex digest of a password-reset token.

    One-way: a DB leak cannot be used to forge a valid reset link.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _device_fingerprint(user_agent: Optional[str], ip: Optional[str]) -> str:
    """Stable fingerprint used for soft device binding of refresh tokens."""
    raw = f"{(user_agent or '').strip().lower()}|{(ip or '').strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def _deliver_reset_email(*, email: str, token: str) -> None:
    """Send password-reset email when SMTP is configured.

    In ENV=dev without SMTP the plaintext token is logged so testers can
    complete the flow. In staging/prod the token is **never** written to
    logs — only a non-sensitive status line.
    """
    from app.core.config import settings

    reset_link = f"{settings.frontend_url.rstrip('/')}/(auth)/reset-password?token={token}"
    subject = "TransitOS password reset"
    body = (
        f"You requested a password reset for {email}.\n\n"
        f"Open this link within 30 minutes:\n{reset_link}\n\n"
        "If you did not request this, ignore this email."
    )

    if not settings.smtp_host:
        if settings.env == "dev":
            # Dev-only: intentionally log the token for local testing.
            # Never enable this path in staging/prod (Settings.env guard).
            logger.info(
                "password reset token for %s = %s (no SMTP configured, ENV=dev only)",
                email,
                token,
            )
        else:
            logger.warning(
                "password reset requested for %s but SMTP_HOST is unset — "
                "email not sent (token withheld)",
                email,
            )
        return

    try:
        import smtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from
        msg["To"] = email
        msg.set_content(body)

        if settings.smtp_use_tls:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
                smtp.starttls()
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(msg)
        # Never log the token — only the destination address.
        logger.info("password reset email sent to %s", email)
    except Exception as exc:  # pragma: no cover — network/SMTP failures
        logger.error("failed to send password-reset email to %s: %s", email, exc)

async def _deliver_username_email(*, email: str, username: str) -> None:
    """Send username reminder via Resend."""
    subject = "Your TransitOS username"
    text = (
        f"Your TransitOS username is: {username}\n\n"
        "If you need to reset your password, tap 'Forgot password?' in the app."
    )
    html = f"""
    <div style="font-family:Arial,Helvetica,sans-serif;background:#F8F7F4;padding:24px;">
      <div style="max-width:480px;margin:0 auto;background:#ffffff;border-radius:12px;padding:24px;border:1px solid #E5E7EB;">
        <h2 style="color:#0B3D91;margin:0 0 8px;">TransitOS</h2>
        <p style="color:#374151;font-size:14px;margin:0 0 16px;">
          Your username is:
        </p>
        <div style="background:#F1F5F9;border:1px dashed #94A3B8;border-radius:8px;padding:12px;text-align:center;">
          <span style="font-family:monospace;font-size:16px;color:#0F172A;word-break:break-all;">{username}</span>
        </div>
        <p style="color:#6B7280;font-size:12px;margin:16px 0 0;">
          If you need to reset your password, tap &ldquo;Forgot password?&rdquo; in the app.
        </p>
      </div>
    </div>
    """
    sent = await send_via_resend(to=email, subject=subject, html=html, text=text)
    if not sent:
        env = getattr(settings, "env", "production").lower()
        if env in ("dev", "development", "local"):
            logger.info("DEV username reminder for %s: %s", email, username)
        else:
            logger.warning("Username email NOT delivered for %s (email not configured)", email)


# ─── authenticate ────────────────────────────────────────────────────────────
async def authenticate_user(
    db: AsyncIOMotorDatabase, *, email: str, password: str
) -> dict[str, Any]:
    """Look up user by email, verify password, return the user doc.

    Raises ``HTTPException(401/403)`` on bad credentials or lockout —
    we deliberately don't reveal whether the email exists on 401.
    """
    doc = await db.users.find_one({"email": email.lower()})
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not doc.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated"
        )
    if doc.get("status") == "suspended":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is suspended"
        )

    if is_locked(doc):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account temporarily locked due to too many failed login attempts. Try again later.",
        )

    if not verify_password(password, doc.get("password_hash", "")):
        await record_failed_login(db, doc["_id"])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    await clear_failed_logins(db, doc["_id"])
    return doc


# ─── token issuance ──────────────────────────────────────────────────────────
async def issue_token_pair(
    db: AsyncIOMotorDatabase,
    user: dict[str, Any],
    *,
    user_agent: Optional[str] = None,
    ip: Optional[str] = None,
) -> LoginResponse:
    """Mint access + refresh tokens for ``user`` and persist the refresh record."""
    user_id = str(user["_id"])
    role = user.get("role", "driver")
    branch_id = user.get("branch_id")

    access_token = create_access_token(
        sub=user_id,
        role=role,
        email=user.get("email", ""),
        branch_id=branch_id,
    )
    refresh_token, jti = create_refresh_token(sub=user_id)

    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    fingerprint = _device_fingerprint(user_agent, ip)

    await db.refresh_tokens.insert_one(
        {
            "jti": jti,
            "user_id": user_id,
            "revoked": False,
            "user_agent": user_agent,
            "ip": ip,
            "device_fingerprint": fingerprint,
            "created_at": datetime.now(timezone.utc),
            "expires_at": expires_at,
        }
    )

    # Bump last_login_at (best-effort)
    try:
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"last_login_at": datetime.now(timezone.utc)}},
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("last_login_at update failed: %s", exc)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


# ─── refresh-token revocation ────────────────────────────────────────────────
async def revoke_refresh_token(db: AsyncIOMotorDatabase, jti: str) -> bool:
    """Mark a refresh token revoked. Idempotent."""
    result = await db.refresh_tokens.update_one(
        {"jti": jti, "revoked": False}, {"$set": {"revoked": True}}
    )
    return result.modified_count > 0


async def revoke_all_user_tokens(db: AsyncIOMotorDatabase, user_id: str) -> int:
    """Revoke every active refresh token for a user. Used on password change."""
    result = await db.refresh_tokens.update_many(
        {"user_id": user_id, "revoked": False}, {"$set": {"revoked": True}}
    )
    return result.modified_count


async def assert_refresh_device_match(
    db: AsyncIOMotorDatabase,
    jti: str,
    *,
    user_agent: Optional[str] = None,
    ip: Optional[str] = None,
) -> None:
    """Soft device binding: reject refresh if fingerprint diverges.

    If the stored record has no fingerprint (legacy tokens), the check is
    skipped so existing sessions keep working until they rotate.
    """
    rec = await db.refresh_tokens.find_one({"jti": jti})
    if rec is None:
        return
    stored = rec.get("device_fingerprint")
    if not stored:
        return  # legacy / unbound
    current = _device_fingerprint(user_agent, ip)
    if stored != current:
        # Revoke the suspicious token and force re-login.
        await revoke_refresh_token(db, jti)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token device mismatch — please log in again",
        )


# ─── forgot / reset password (token-based) ──────────────────────────────────
# Tokens live in ``password_reset_tokens`` (hashed + TTL). The user document
# is never touched for reset state, so a TTL cannot accidentally delete a user.
RESET_TOKEN_TTL_MIN = 30


async def start_password_reset(
    db: AsyncIOMotorDatabase, email: str
) -> Optional[str]:
    """Generate a reset token, store its hash, return the plaintext.

    Returns ``None`` when the email is unknown (caller must not reveal this).
    Any previous outstanding tokens for the same user are deleted first.

    Timing: when the email is unknown we still perform comparable work
    (hash a dummy token + a no-op write path) so response latency does not
    become an oracle for account enumeration.
    """
    user = await db.users.find_one({"email": email.lower()})
    if user is None:
        # Constant-ish work so unknown emails are not faster than known ones.
        dummy = secrets.token_urlsafe(32)
        _hash_reset_token(dummy)
        # Touch the collection with a no-op filter so DB latency is similar.
        await db.password_reset_tokens.find_one({"token_hash": _hash_reset_token("0")})
        return None

    user_id = str(user["_id"])
    token = secrets.token_urlsafe(32)
    token_hash = _hash_reset_token(token)
    expires = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_TTL_MIN)

    # Invalidate any previous outstanding tokens for this user.
    await db.password_reset_tokens.delete_many({"user_id": user_id})

    await db.password_reset_tokens.insert_one(
        {
            "token_hash": token_hash,
            "user_id": user_id,
            "expires_at": expires,
            "created_at": datetime.now(timezone.utc),
        }
    )

    # Clean legacy fields left on the user document from earlier versions.
    await db.users.update_one(
        {"_id": user["_id"]},
        {
            "$unset": {
                "password_reset_token": "",
                "password_reset_token_hash": "",
                "password_reset_expires": "",
            }
        },
    )
    return token


async def complete_password_reset(
    db: AsyncIOMotorDatabase, *, token: str, new_password: str
) -> bool:
    """Validate token (by hash), set new password, revoke all refresh tokens.

    Returns True on success. The token document is deleted immediately
    (single-use); the TTL index is a safety net for unused tokens.
    """
    now = datetime.now(timezone.utc)
    token_hash = _hash_reset_token(token)

    rec = await db.password_reset_tokens.find_one(
        {
            "token_hash": token_hash,
            "expires_at": {"$gt": now},
        }
    )
    if rec is None:
        return False

    user_id = rec["user_id"]
    if not ObjectId.is_valid(user_id):
        return False

    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {
            "$set": {
                "password_hash": hash_password(new_password),
                "updated_at": now,
            },
            "$unset": {
                "password_reset_token": "",
                "password_reset_token_hash": "",
                "password_reset_expires": "",
            },
        },
    )
    if result.matched_count == 0:
        return False

    # Single-use: remove the token immediately.
    await db.password_reset_tokens.delete_one({"_id": rec["_id"]})
    await revoke_all_user_tokens(db, user_id)
    return True


async def purge_revoked_refresh_tokens(
    db: AsyncIOMotorDatabase, *, older_than_hours: int = 24
) -> int:
    """Delete revoked refresh-token rows that are older than ``older_than_hours``.

    The TTL index on ``expires_at`` already removes *expired* tokens. This
    cleans up tokens that were explicitly revoked (logout / password change /
    rotation) well before their natural expiry so the collection stays small.
    Safe to call on every startup and periodically.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
    result = await db.refresh_tokens.delete_many(
        {
            "revoked": True,
            "created_at": {"$lt": cutoff},
        }
    )
    deleted = int(result.deleted_count or 0)
    if deleted:
        logger.info(
            "purged %d revoked refresh tokens older than %dh",
            deleted,
            older_than_hours,
        )
    return deleted


__all__ = [
    "hash_password",
    "authenticate_user",
    "issue_token_pair",
    "revoke_refresh_token",
    "revoke_all_user_tokens",
    "assert_refresh_device_match",
    "start_password_reset",
    "complete_password_reset",
    "purge_revoked_refresh_tokens",
    "_deliver_reset_email",
]
