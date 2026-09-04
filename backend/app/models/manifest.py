"""Manifest entry — passenger or cargo booking attached to a trip.

Two flavors: ``passenger`` and ``cargo``. Payment can be paid-in-advance or
collected on-board (and reconciled at cash-up).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ManifestType(str, Enum):
    PASSENGER = "passenger"
    CARGO = "cargo"


class ManifestPaymentStatus(str, Enum):
    PAID = "paid"
    ON_BOARD = "on_board"  # conductor collects later
    CANCELLED = "cancelled"


class ManifestBase(BaseModel):
    trip_id: str
    type: ManifestType
    # Passenger fields
    passenger_name: Optional[str] = Field(default=None, max_length=120)
    passenger_phone: Optional[str] = Field(default=None, max_length=20)
    passenger_id_number: Optional[str] = Field(default=None, max_length=40)
    seat_number: Optional[str] = Field(default=None, max_length=10)
    # Cargo fields
    cargo_description: Optional[str] = Field(default=None, max_length=200)
    cargo_weight_kg: Optional[float] = Field(default=None, ge=0, le=50_000)
    cargo_sender_name: Optional[str] = Field(default=None, max_length=120)
    cargo_receiver_name: Optional[str] = Field(default=None, max_length=120)
    cargo_receiver_phone: Optional[str] = Field(default=None, max_length=20)
    # Shared
    fare: float = Field(ge=0)
    payment_status: ManifestPaymentStatus = ManifestPaymentStatus.ON_BOARD
    payment_method: Optional[str] = Field(default=None, max_length=20)
    boarded: bool = False


class ManifestCreate(ManifestBase):
    pass


class ManifestUpdate(BaseModel):
    passenger_name: Optional[str] = Field(default=None, max_length=120)
    passenger_phone: Optional[str] = Field(default=None, max_length=20)
    seat_number: Optional[str] = Field(default=None, max_length=10)
    cargo_description: Optional[str] = Field(default=None, max_length=200)
    cargo_weight_kg: Optional[float] = Field(default=None, ge=0, le=50_000)
    fare: Optional[float] = Field(default=None, ge=0)
    payment_status: Optional[ManifestPaymentStatus] = None
    payment_method: Optional[str] = Field(default=None, max_length=20)
    boarded: Optional[bool] = None


class Manifest(ManifestBase):
    id: str = Field(default="")
    branch_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(populate_by_name=True)
