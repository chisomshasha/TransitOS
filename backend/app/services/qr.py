"""QR token generation + verification.

Each QR encodes a short signed token:
    <entity_type>:<entity_id>:<ts>:<hmac>

The HMAC prevents forgery; the timestamp lets us reject tokens
older than 30 days (configurable). Tokens are URL-safe base64
so they survive QR encoding without escaping issues.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from typing import Optional

# 32-byte secret, rotated via env var. Falls back to a deterministic
# dev value so local testing works without extra config.
_QR_SECRET = (
    os.environ.get("QR_SIGNING_SECRET")
    or "transitos-dev-qr-secret-change-me-in-prod"
).encode("utf-8")

TOKEN_MAX_AGE_SECONDS = 30 * 24 * 60 * 60  # 30 days


def _sign(payload: str) -> str:
    return hmac.new(_QR_SECRET, payload.encode("utf-8"), hashlib.sha256).hexdigest()[:16]


def generate_qr_token(entity_type: str, entity_id: str) -> str:
    """Return a URL-safe base64 token for the given entity."""
    ts = str(int(time.time()))
    payload = f"{entity_type}:{entity_id}:{ts}"
    sig = _sign(payload)
    raw = f"{payload}:{sig}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii").rstrip("=")


def verify_qr_token(token: str) -> Optional[tuple[str, str, int]]:
    """Decode + verify a token.

    Returns ``(entity_type, entity_id, ts)`` on success, ``None`` on any
    failure (bad format, bad signature, expired).
    """
    try:
        # Re-pad base64
        padded = token + "=" * (-len(token) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        parts = raw.split(":")
        if len(parts) != 4:
            return None
        entity_type, entity_id, ts_str, sig = parts
        payload = f"{entity_type}:{entity_id}:{ts_str}"
        if not hmac.compare_digest(_sign(payload), sig):
            return None
        ts = int(ts_str)
        if time.time() - ts > TOKEN_MAX_AGE_SECONDS:
            return None
        return entity_type, entity_id, ts
    except Exception:
        return None


__all__ = ["generate_qr_token", "verify_qr_token"]
