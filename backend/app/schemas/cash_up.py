"""CashUp request/response schemas."""

from typing import Optional

from pydantic import BaseModel, Field

from app.models.cash_up import CashUp, CashUpCreate, CashUpUpdate


class CashUpCreateRequest(CashUpCreate):
    pass


class CashUpUpdateRequest(CashUpUpdate):
    pass


class CashUpResponse(CashUp):
    pass


class CashUpApproveRequest(BaseModel):
    notes: Optional[str] = Field(default=None, max_length=2000)
