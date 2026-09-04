"""Notification model (alerts inbox)."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class Notification(BaseModel):
    id: Optional[str] = None
    type: str  # documents | licenses | maintenance | low_fuel | trips | cashups | incidents | system
    severity: str = "info"  # info | warn | danger | success
    title: str
    body: str = ""
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    branch_id: Optional[str] = None
    roles: Optional[List[str]] = None  # None = all authenticated roles
    source: str = "event"  # event | scan
    dedupe_key: Optional[str] = None
    read_by: List[str] = []
    created_at: Optional[datetime] = None
    refreshed_at: Optional[datetime] = None


class NotificationResponse(Notification):
    pass
