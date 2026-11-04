"""Vehicle transfer model — cross-branch vehicle borrow/return.

State machine: initiated → confirmed → returned  (or cancelled from any non-terminal).
`confirmed` flips the vehicle's `branch_id` to `to_branch_id`.
`returned` flips it back to `from_branch_id`.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TransferStatus(str, Enum):
    INITIATED = "initiated"
    CONFIRMED = "confirmed"
    RETURNED = "returned"
    CANCELLED = "cancelled"


TRANSFER_TRANSITIONS: dict[TransferStatus, set[TransferStatus]] = {
    TransferStatus.INITIATED: {TransferStatus.CONFIRMED, TransferStatus.CANCELLED},
    TransferStatus.CONFIRMED: {TransferStatus.RETURNED, TransferStatus.CANCELLED},
    TransferStatus.RETURNED: set(),
    TransferStatus.CANCELLED: set(),
}


class VehicleTransfer(BaseModel):
    id: Optional[str] = None
    vehicle_id: str
    from_branch_id: str
    to_branch_id: str
    initiated_by: Optional[str] = None
    confirmed_by: Optional[str] = None
    returned_by: Optional[str] = None
    cancelled_by: Optional[str] = None
    status: TransferStatus = TransferStatus.INITIATED
    reason: Optional[str] = None
    notes: Optional[str] = None
    expected_return_at: Optional[datetime] = None
    initiated_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class VehicleTransferCreate(BaseModel):
    vehicle_id: str
    to_branch_id: str
    reason: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = Field(default=None, max_length=1000)
    expected_return_at: Optional[datetime] = None


class VehicleTransferAdvance(BaseModel):
    notes: Optional[str] = Field(default=None, max_length=1000)


class VehicleTransferResponse(VehicleTransfer):
    pass


__all__ = [
    "TransferStatus",
    "TRANSFER_TRANSITIONS",
    "VehicleTransfer",
    "VehicleTransferCreate",
    "VehicleTransferAdvance",
    "VehicleTransferResponse",
]
