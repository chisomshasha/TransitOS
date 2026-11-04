"""Vehicle document model (insurance, permits, etc.)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    INSURANCE = "insurance"
    ROADWORTHINESS = "roadworthiness"
    HACKNEY_PERMIT = "hackney_permit"
    ROUTE_PERMIT = "route_permit"
    OTHER = "other"


class VehicleDocument(BaseModel):
    id: Optional[str] = None
    vehicle_id: str
    doc_type: DocumentType
    issuer: Optional[str] = None
    ref_number: str
    issued_at: Optional[datetime] = None
    expires_at: datetime
    alert_days: int = 30
    file_url: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class VehicleDocumentCreate(BaseModel):
    doc_type: DocumentType
    issuer: Optional[str] = None
    ref_number: str
    issued_at: Optional[datetime] = None
    expires_at: datetime
    alert_days: int = Field(30, ge=1, le=365)
    file_url: Optional[str] = None


class VehicleDocumentUpdate(BaseModel):
    doc_type: Optional[DocumentType] = None
    issuer: Optional[str] = None
    ref_number: Optional[str] = None
    issued_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    alert_days: Optional[int] = Field(None, ge=1, le=365)
    file_url: Optional[str] = None


class VehicleDocumentResponse(VehicleDocument):
    pass
