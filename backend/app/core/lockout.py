"""Progressive account lockout after repeated failed logins.

Tracks failures on the user document:
  - failed_login_count
  - lock_until  (UTC datetime; requests while locked → 403)

Policy (defaults):
  - After 5 failures → lock 15 minutes
  - After 10 failures → lock 1 hour
  - Successful login clears the counters
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

# Thresholds: (failure_count_threshold, lock_duration)
_LOCK_STEPS = (
    (5, timedelta(minutes=15)),
    (10, timedelta(hours=1)),
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def is_locked(user: dict[str, Any]) -> bool:
    """Return True if the account is currently locked."""
    lock_until = user.get("lock_until")
    if lock_until is None:
        return False
    if isinstance(lock_until, str):
        # Defensive: tolerate string dates from older fixtures.
        try:
            lock_until = datetime.fromisoformat(lock_until.replace("Z", "+00:00"))
        except ValueError:
            return False
    if lock_until.tzinfo is None:
        lock_until = lock_until.replace(tzinfo=timezone.utc)
    return lock_until > _now()


async def record_failed_login(db: AsyncIOMotorDatabase, user_id) -> None:
    """Increment failure counter and apply lock if a threshold is crossed."""
    user = await db.users.find_one({"_id": user_id})
    if user is None:
        return
    count = int(user.get("failed_login_count") or 0) + 1
    update: dict[str, Any] = {"failed_login_count": count}

    for threshold, duration in reversed(_LOCK_STEPS):
        if count >= threshold:
            update["lock_until"] = _now() + duration
            break

    await db.users.update_one({"_id": user_id}, {"$set": update})


async def clear_failed_logins(db: AsyncIOMotorDatabase, user_id) -> None:
    """Reset counters after a successful authentication."""
    await db.users.update_one(
        {"_id": user_id},
        {"$set": {"failed_login_count": 0}, "$unset": {"lock_until": ""}},
    )
