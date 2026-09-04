"""Refresh token store — see ``data-model.md`` §8."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RefreshToken(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    jti: str
    expires_at: datetime
    revoked: bool = False
    revoked_at: Optional[datetime] = None
    replaced_by: Optional[str] = None
    user_agent: Optional[str] = None
    ip: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("id", mode="before")
    @classmethod
    def _stringify_id(cls, v):
        return str(v) if v is not None else v
