"""Common response shapes and error model.

Per ``api-contract.md`` §0.7:

  Single:  { "data": { ... entity ... } }
  List:    { "items": [...], "total": N, "page": P, "totalPages": T, "hasMore": H }
  Error:   { "detail": "Human-readable", "type": "validation_error" }
"""

from __future__ import annotations

import math
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorBody(BaseModel):
    """Standard error response body. Used by global exception handlers."""

    detail: str
    type: str = "internal_error"


class SingleResponse(BaseModel, Generic[T]):
    """Single-resource envelope: ``{ data: ... }``."""

    data: T


class ListResponse(BaseModel, Generic[T]):
    """Paginated list envelope (api-contract.md §0.7)."""

    items: List[T]
    total: int
    page: int
    totalPages: int
    hasMore: bool

    @classmethod
    def build(
        cls,
        items: List[T],
        total: int,
        page: int,
        limit: int,
    ) -> "ListResponse[T]":
        total_pages = math.ceil(total / limit) if total else 0
        return cls(
            items=items,
            total=total,
            page=page,
            totalPages=total_pages,
            hasMore=page < total_pages,
        )


class PageParams(BaseModel):
    """Query params for pagination — bound by FastAPI on each list route."""

    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    search: Optional[str] = Field(default=None, max_length=80)
    sort: str = Field(default="created_at")
    order: str = Field(default="desc")
    include_inactive: bool = False

    def sort_field(self) -> str:
        """Translate the public ``sort`` name into a Mongo field.

        The spec only allows ``name | created_at | updated_at``.
        """
        allowed = {"name", "created_at", "updated_at"}
        return self.sort if self.sort in allowed else "created_at"

    def sort_direction(self) -> int:
        from pymongo import ASCENDING, DESCENDING

        return ASCENDING if self.order == "asc" else DESCENDING
