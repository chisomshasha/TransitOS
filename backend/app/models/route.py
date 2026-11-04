"""Route entity — see ``data-model.md`` §6."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RouteType(str, Enum):
    INTRASTATE = "intrastate"
    INTERSTATE = "interstate"


class IntermediateStop(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    eta_minutes: int = Field(ge=0, le=1440)


class RouteBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    branch_id: str
    type: RouteType
    origin_branch_id: str
    destination_branch_id: str
    origin_city: str = Field(min_length=1, max_length=80)
    destination_city: str = Field(min_length=1, max_length=80)
    distance_km: float = Field(ge=0, le=10_000)
    base_fare_passenger: float = Field(ge=0, le=10_000_000)
    base_fare_cargo_per_kg: float = Field(ge=0, le=1_000_000)
    estimated_duration_hours: float = Field(ge=0, le=72)
    intermediate_stops: list[IntermediateStop] = Field(default_factory=list)
    required_permits: list[str] = Field(default_factory=list)
    is_active: bool = True


class RouteCreate(RouteBase):
    @field_validator("destination_branch_id")
    @classmethod
    def _origin_ne_destination(cls, v, info):
        origin = info.data.get("origin_branch_id")
        if origin and v and origin == v:
            raise ValueError(
                "destination_branch_id must differ from origin_branch_id"
            )
        return v


class RouteUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    type: Optional[RouteType] = None
    origin_branch_id: Optional[str] = None
    destination_branch_id: Optional[str] = None
    origin_city: Optional[str] = Field(default=None, min_length=1, max_length=80)
    destination_city: Optional[str] = Field(default=None, min_length=1, max_length=80)
    distance_km: Optional[float] = Field(default=None, ge=0, le=10_000)
    base_fare_passenger: Optional[float] = Field(default=None, ge=0)
    base_fare_cargo_per_kg: Optional[float] = Field(default=None, ge=0)
    estimated_duration_hours: Optional[float] = Field(default=None, ge=0, le=72)
    intermediate_stops: Optional[list[IntermediateStop]] = None
    required_permits: Optional[list[str]] = None
    is_active: Optional[bool] = None

    @field_validator("destination_branch_id")
    @classmethod
    def _origin_ne_destination_when_both_present(
        cls, v, info
    ):
        origin = info.data.get("origin_branch_id")
        if origin is not None and v is not None and origin == v:
            raise ValueError(
                "destination_branch_id must differ from origin_branch_id"
            )
        return v


class Route(RouteBase):
    id: str = Field(default="")
    is_active: bool = True
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("id", mode="before")
    @classmethod
    def _stringify_id(cls, v):
        return str(v) if v is not None else v
