"""Realtime events router — Server-Sent Events for the live trip board.

Sprint D.

    GET /events/trips   SSE stream of trip state changes

SSE rather than WebSockets because the data flow is one-way (server →
client), SSE rides ordinary HTTP so it works through Railway's proxy
and through Expo's plain ``fetch``, and it reconnects on its own.

Response headers matter here: ``no-cache`` plus ``X-Accel-Buffering: no``
stop nginx (and Railway's edge) from buffering the stream, which would
otherwise hold every event until the connection closed.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.rbac import ANY_AUTHENTICATED, require_roles
from app.services.events import broker, event_stream

logger = logging.getLogger("transitos.events")

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/trips")
async def trip_events(
    request: Request,
    max_events: int = Query(
        0,
        ge=0,
        le=1000,
        description=(
            "Close the stream after this many events. 0 (the default) keeps "
            "it open indefinitely."
        ),
    ),
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(require_roles(*ANY_AUTHENTICATED)),
):
    """Stream trip state changes as Server-Sent Events.

    The stream stays open until the client disconnects — or until
    ``max_events`` events have been sent, when that option is used.
    Each event is shaped::

        event: trip.updated
        data: {"trip_id": "...", "status": "departed", ...}

    A ``ping`` event is sent every 15 seconds of silence so proxies and
    mobile radios do not drop the connection.
    """
    logger.info("SSE stream opened (user=%s)", user.get("id"))

    async def generate() -> AsyncIterator[bytes]:
        sent = 0
        try:
            async for event in event_stream():
                # Stop promptly when the client goes away.
                if await request.is_disconnected():
                    break
                payload = json.dumps(event.get("data", {}), default=str)
                name = event.get("type", "message")
                yield f"event: {name}\ndata: {payload}\n\n".encode("utf-8")
                sent += 1
                if max_events and sent >= max_events:
                    break
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("SSE stream error: %s", exc)
        finally:
            logger.info("SSE stream closed (user=%s)", user.get("id"))

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/status")
async def events_status(
    user: dict = Depends(require_roles(*ANY_AUTHENTICATED)),
):
    """Broker diagnostics — handy when debugging the live board."""
    from app.schemas.common import SingleResponse

    return SingleResponse[dict](data={
        "running": broker._running,
        "subscribers": broker.subscriber_count,
        "tracked_trips": len(broker._snapshot),
    })


__all__ = ["router"]
