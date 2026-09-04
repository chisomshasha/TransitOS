"""Branch request / response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.branch import (
    BankAccount,
    Branch,
    BranchCreate,
    BranchStatus,
    BranchUpdate,
    GPS,
)


# ─── request bodies ──────────────────────────────────────────────────────────
# These are thin aliases for the model classes; the routers import
# these names for clarity. Behavior is identical to the models.

class BranchCreateRequest(BranchCreate):
    """All required fields per spec; optional fields default to None."""


class BranchUpdateRequest(BranchUpdate):
    """Every field optional."""


class SetManagerRequest(BaseModel):
    manager_id: Optional[str] = Field(default=None, min_length=24, max_length=24)


# ─── response ────────────────────────────────────────────────────────────────
class BranchResponse(Branch):
    """Wire shape — same as the in-DB model."""

    model_config = ConfigDict(populate_by_name=True)
