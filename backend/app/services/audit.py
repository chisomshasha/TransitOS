"""Audit log writer.

Every mutating action should call ``write_audit(...)`` so the trail is
complete. Reads (``list_audit``) are exposed via the auth router (only
to roles that should see them: SA, OWNER, GM).

See ``data-model.md`` §0.6 and ``api-contract.md`` §8.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase


async def write_audit(
    db: AsyncIOMotorDatabase,
    *,
    action: str,
    entity_type: str,
    entity_id: str,
    actor_id: Optional[str] = None,
    actor_email: Optional[str] = None,
    branch_id: Optional[str] = None,
    before: Optional[dict[str, Any]] = None,
    after: Optional[dict[str, Any]] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """Append one audit_log document. Never raises — best-effort.

    Failures are logged but not propagated, because audit must not block
    the primary write path. The mongo indexes make the table cheap to
    query later.
    """
    doc: dict[str, Any] = {
        "ts": datetime.now(timezone.utc),
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
    }
    if actor_id is not None:
        doc["actor_id"] = actor_id
    if actor_email is not None:
        doc["actor_email"] = actor_email
    if branch_id is not None:
        doc["branch_id"] = branch_id
    if before is not None:
        doc["before"] = before
    if after is not None:
        doc["after"] = after
    if metadata is not None:
        doc["metadata"] = metadata

    try:
        await db.audit_log.insert_one(doc)
    except Exception as exc:  # pragma: no cover - never block the user
        # import here to avoid circular at module load
        import logging

        logging.getLogger(__name__).warning("audit_log insert failed: %s", exc)


__all__ = ["write_audit"]
