"""Pre-trip inspection (checklist) model."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class InspectionItem(BaseModel):
    key: str
    label: str
    status: str = "pending"  # pending | ok | low | fail
    note: Optional[str] = None


class Inspection(BaseModel):
    id: Optional[str] = None
    trip_id: str
    vehicle_id: Optional[str] = None
    driver_id: Optional[str] = None
    items: List[InspectionItem] = Field(default_factory=list)
    odometer_reading: Optional[int] = None
    fuel_level_pct: Optional[float] = None
    signature_confirmed: bool = False
    status: str = "draft"  # draft | submitted
    submitted_at: Optional[datetime] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class InspectionUpsert(BaseModel):
    trip_id: str
    vehicle_id: Optional[str] = None
    driver_id: Optional[str] = None
    items: List[InspectionItem] = Field(default_factory=list)
    odometer_reading: Optional[int] = None
    fuel_level_pct: Optional[float] = None
    signature_confirmed: bool = False


class InspectionResponse(Inspection):
    pass


# The canonical 10-point checklist template (matches mockup 16)
CHECKLIST_TEMPLATE: List[dict] = [
    {"key": "tires_wheels", "label": "Tires & wheels"},
    {"key": "brakes_lights", "label": "Brakes & lights"},
    {"key": "mirrors_signals", "label": "Mirrors & signals"},
    {"key": "first_aid_kit", "label": "First-aid kit"},
    {"key": "fire_extinguisher", "label": "Fire extinguisher"},
    {"key": "fuel_level", "label": "Fuel level"},
    {"key": "vehicle_documents", "label": "Vehicle documents"},
    {"key": "odometer_reading", "label": "Odometer reading"},
    {"key": "engine_oil_coolant", "label": "Engine oil & coolant"},
    {"key": "driver_signature", "label": "Driver signature"},
]


__all__ = [
    "InspectionItem",
    "Inspection",
    "InspectionUpsert",
    "InspectionResponse",
    "CHECKLIST_TEMPLATE",
]
