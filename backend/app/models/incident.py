"""Incident model — safety / operational events with a workflow."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class Incident(BaseModel):
    id: Optional[str] = None
    trip_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    branch_id: Optional[str] = None
    severity: str = "minor"  # minor | moderate | severe
    category: str = "other"
    description: str = ""
    photos: List[str] = Field(default_factory=list)  # base64 data-URIs or URLs
    status: str = "open"  # open | acknowledged | resolved | closed
    reported_by: Optional[str] = None
    notified: List[str] = Field(default_factory=list)  # user ids
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class IncidentCreate(BaseModel):
    trip_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    branch_id: Optional[str] = None
    severity: str = "minor"
    category: str = "other"
    description: str
    photos: List[str] = Field(default_factory=list)
    notified: List[str] = Field(default_factory=list)


class IncidentResponse(Incident):
    pass


INCIDENT_CATEGORIES = [
    "mechanical",
    "accident",
    "theft",
    "passenger_dispute",
    "cargo_damage",
    "weather",
    "other",
]


__all__ = ["Incident", "IncidentCreate", "IncidentResponse", "INCIDENT_CATEGORIES"]
