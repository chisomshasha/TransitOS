"""Realtime event broker — a lightweight pub/sub for live trip updates.

Sprint D. The app needs a live trip board: dispatchers watching the
fleet need to see a trip move from ``boarding`` to ``departed`` without
refreshing.

Why polling instead of Mongo change streams
-------------------------------------------
``watch()`` requires a replica set. Railway's MongoDB plugin and many
self-hosted deployments run a standalone mongod, where change streams
simply fail. A short poll over a tiny projection works everywhere, and
at a 5-second interval the cost is negligible next to the reliability
win.

How it works
------------
* One background poller per process snapshots ``(id, status, updated_at)``
  for every live trip and compares it to the previous snapshot.
* Any change is published to every subscriber queue.
* Subscribers are plain ``asyncio.Queue`` objects; a slow consumer is
  dropped rather than allowed to block the publisher.

The SSE endpoint in ``app/routers/events.py`` is a thin adapter over
this broker.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Optional

logger = logging.getLogger("transitos.events")

#: How many events to buffer per subscriber before the slowest one is
#: dropped. A client that cannot keep up should reconnect, not stall
#: the whole feed.
SUBSCRIBER_QUEUE_SIZE = 64


class EventBroker:
    """In-process pub/sub for trip events."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()
        self._snapshot: dict[str, tuple[str, Optional[datetime]]] = {}
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._db: Any = None

    # ── lifecycle ──────────────────────────────────────────────────────────
    async def start(self, poll_interval: float = 5.0, db: Any = None) -> None:
        """Start the background poller. Safe to call twice.

        ``db`` overrides the database handle. In production it is left
        unset and the app's own client is used; tests pass the in-memory
        mock so the poller never touches a real server.
        """
        if self._running:
            return
        self._db = db
        self._running = True
        self._task = asyncio.create_task(self._poll_loop(poll_interval))
        logger.info("trip event broker started (poll interval %.1fs)", poll_interval)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            self._task = None
        logger.info("trip event broker stopped")

    # ── pub/sub ────────────────────────────────────────────────────────────
    async def subscribe(self) -> asyncio.Queue:
        """Register a new subscriber and return its queue."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=SUBSCRIBER_QUEUE_SIZE)
        async with self._lock:
            self._subscribers.add(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue) -> None:
        async with self._lock:
            self._subscribers.discard(queue)

    async def publish(self, event: dict[str, Any]) -> None:
        """Fan an event out to every subscriber."""
        async with self._lock:
            targets = list(self._subscribers)

        for queue in targets:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                # The consumer is too slow. Drop the oldest event and
                # keep the newest — a stale trip state is worse than a
                # skipped one.
                try:
                    queue.get_nowait()
                    queue.put_nowait(event)
                except Exception:  # pragma: no cover - defensive
                    pass
                logger.warning("dropped a slow event subscriber")

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    # ── polling ────────────────────────────────────────────────────────────
    async def _poll_loop(self, interval: float) -> None:
        db = self._db
        if db is None:
            from app.core.database import db as _app_db

            db = _app_db

        while self._running:
            try:
                await self._poll_once(db)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.warning("event poll failed: %s", exc)

            try:
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                raise

    async def _poll_once(self, db) -> None:
        """Snapshot live trips and publish anything that changed."""
        cursor = db["trips"].find(
            {"$or": [{"is_active": True}, {"is_active": {"$exists": False}}]},
            {"status": 1, "updated_at": 1, "branch_id": 1, "route_id": 1},
        )

        current: dict[str, tuple[str, Optional[datetime]]] = {}
        details: dict[str, dict[str, Any]] = {}

        async for doc in cursor:
            trip_id = str(doc.get("_id"))
            current[trip_id] = (doc.get("status"), doc.get("updated_at"))
            details[trip_id] = {
                "trip_id": trip_id,
                "status": doc.get("status"),
                "branch_id": doc.get("branch_id"),
                "route_id": doc.get("route_id"),
                "updated_at": _iso(doc.get("updated_at")),
            }

        previous = self._snapshot
        self._snapshot = current

        # First pass: everything is "new". Don't spam on boot.
        if not previous:
            return

        for trip_id, (status, updated_at) in current.items():
            before = previous.get(trip_id)
            if before is None:
                # A trip that appeared (or was reactivated).
                await self.publish(
                    {"type": "trip.created", "data": details[trip_id]}
                )
                continue
            if before[0] != status or before[1] != updated_at:
                await self.publish(
                    {
                        "type": "trip.updated",
                        "data": {
                            **details[trip_id],
                            "previous_status": before[0],
                        },
                    }
                )

        # Trips that disappeared were deleted or deactivated.
        for trip_id in previous:
            if trip_id not in current:
                await self.publish(
                    {"type": "trip.removed", "data": {"trip_id": trip_id}}
                )


def _iso(value: Any) -> Optional[str]:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return None


#: Process-wide broker instance.
broker = EventBroker()


async def event_stream() -> AsyncIterator[dict[str, Any]]:
    """Yield events for one subscriber, cleaning up on disconnect."""
    queue = await broker.subscribe()
    try:
        while True:
            try:
                yield await asyncio.wait_for(queue.get(), timeout=15.0)
            except asyncio.TimeoutError:
                # Heartbeat — keeps proxies from closing an idle stream.
                yield {"type": "ping", "data": {}}
    finally:
        await broker.unsubscribe(queue)


__all__ = ["EventBroker", "broker", "event_stream", "SUBSCRIBER_QUEUE_SIZE"]
