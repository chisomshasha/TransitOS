"""Route schemas."""

from __future__ import annotations

from app.models.route import Route, RouteCreate, RouteUpdate


class RouteCreateRequest(RouteCreate):
    pass


class RouteUpdateRequest(RouteUpdate):
    pass


class RouteResponse(Route):
    """Wire shape — same as in-DB model."""

    pass
