"""Realtime events — the SSE broker and the live-board endpoint.

Sprint D. The broker is what makes the live trip board work: it polls
trips, notices a status change, and fans the event out to every
connected subscriber.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone

import pytest

from app.services.events import EventBroker


async def _seed_trip(db, *, status="planned", trip_id=None, updated_at=None):
    now = updated_at or datetime.now(timezone.utc)
    doc = {
        "branch_id": "b1",
        "route_id": "r1",
        "vehicle_id": "v1",
        "driver_id": "d1",
        "conductor_id": "c1",
        "status": status,
        "scheduled_departure": now,
        "scheduled_arrival": now + timedelta(hours=3),
        "updated_at": now,
        "is_active": True,
        "created_at": now,
    }
    result = await db.trips.insert_one(doc)
    doc["_id"] = result.inserted_id
    doc["id"] = str(result.inserted_id)
    return doc


# ─────────────────────────────────────────────────────────────────────────────
# The broker
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_broker_publishes_to_subscribers():
    broker = EventBroker()
    queue = await broker.subscribe()

    await broker.publish({"type": "trip.updated", "data": {"trip_id": "t1"}})

    event = await asyncio.wait_for(queue.get(), timeout=2)
    assert event["type"] == "trip.updated"
    assert event["data"]["trip_id"] == "t1"

    await broker.unsubscribe(queue)


@pytest.mark.asyncio
async def test_broker_fans_out_to_multiple_subscribers():
    broker = EventBroker()
    q1 = await broker.subscribe()
    q2 = await broker.subscribe()

    await broker.publish({"type": "ping", "data": {}})

    assert (await asyncio.wait_for(q1.get(), timeout=2))["type"] == "ping"
    assert (await asyncio.wait_for(q2.get(), timeout=2))["type"] == "ping"


@pytest.mark.asyncio
async def test_unsubscribe_stops_delivery():
    broker = EventBroker()
    queue = await broker.subscribe()
    await broker.unsubscribe(queue)

    await broker.publish({"type": "trip.updated", "data": {}})

    assert queue.empty()
    assert broker.subscriber_count == 0


@pytest.mark.asyncio
async def test_slow_subscriber_drops_oldest_event():
    """A consumer that cannot keep up loses the oldest event, not the newest."""
    broker = EventBroker()
    queue = await broker.subscribe()
    # Fill the queue past its limit.
    for i in range(100):
        await broker.publish({"type": "trip.updated", "data": {"n": i}})

    # The queue is bounded; the most recent event must still be in it.
    latest = None
    while not queue.empty():
        latest = queue.get_nowait()
    assert latest is not None
    assert latest["data"]["n"] == 99


@pytest.mark.asyncio
async def test_poll_detects_a_status_change(db):
    broker = EventBroker()
    trip = await _seed_trip(db, status="planned")
    queue = await broker.subscribe()

    # First poll establishes the baseline — it must not emit anything.
    await broker._poll_once(db)
    assert queue.empty()

    # The trip moves to `departed`.
    await db.trips.update_one(
        {"_id": trip["_id"]},
        {
            "$set": {
                "status": "departed",
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )

    await broker._poll_once(db)

    event = await asyncio.wait_for(queue.get(), timeout=2)
    assert event["type"] == "trip.updated"
    assert event["data"]["status"] == "departed"
    assert event["data"]["previous_status"] == "planned"
    assert event["data"]["trip_id"] == trip["id"]


@pytest.mark.asyncio
async def test_poll_reports_removed_trips(db):
    broker = EventBroker()
    trip = await _seed_trip(db, status="planned")
    queue = await broker.subscribe()

    await broker._poll_once(db)
    assert queue.empty()

    await db.trips.update_one(
        {"_id": trip["_id"]}, {"$set": {"is_active": False}}
    )
    await broker._poll_once(db)

    event = await asyncio.wait_for(queue.get(), timeout=2)
    assert event["type"] == "trip.removed"
    assert event["data"]["trip_id"] == trip["id"]


# ─────────────────────────────────────────────────────────────────────────────
# The endpoint
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_sse_endpoint_requires_auth(client):
    r = await client.get("/events/trips")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_events_status_endpoint(client, auth_headers):
    r = await client.get("/events/status", headers=auth_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    # The status endpoint follows the standard {"data": ...} envelope so
    # the frontend can read it with `getSingle`.
    assert "data" in body, body
    data = body["data"]
    assert "subscribers" in data
    assert "running" in data
    assert "tracked_trips" in data


@pytest.mark.asyncio
async def test_sse_stream_emits_events_in_sse_format(client, auth_headers, db):
    """The response must be a well-formed text/event-stream.

    The stream is opened with ``max_events=1`` so it terminates. Without
    that the response never ends — which is correct for a live feed, but
    httpx's ASGI transport buffers the whole body before returning, so an
    unbounded stream could never be asserted on.
    """
    from app.services.events import broker

    trip = await _seed_trip(db, status="planned")

    # Start the real poller so the stream has something to report. The
    # broker is a process-wide singleton, so stop it again afterwards.
    await broker.start(poll_interval=0.2, db=db)
    try:
        # Let the first poll establish the baseline snapshot.
        await asyncio.sleep(0.6)

        # Open the stream in the background so the client is subscribed
        # *before* the trip changes — otherwise the poller publishes into
        # an empty subscriber set and the event is lost.
        request_task = asyncio.create_task(
            client.get(
                "/events/trips", params={"max_events": 1}, headers=auth_headers
            )
        )
        await asyncio.sleep(0.3)
        assert broker.subscriber_count >= 1, "the SSE client never subscribed"

        await db.trips.update_one(
            {"_id": trip["_id"]},
            {
                "$set": {
                    "status": "departed",
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

        response = await asyncio.wait_for(request_task, timeout=20)
    finally:
        await broker.stop()

    assert response.status_code == 200, response.status_code
    assert response.headers["content-type"].startswith("text/event-stream")
    # nginx / Railway edge must not buffer the stream.
    assert response.headers.get("x-accel-buffering") == "no"

    text = response.text
    assert text, "the SSE stream produced no output"
    assert "event:" in text
    assert "data:" in text

    # Every frame is blank-line terminated and carries valid JSON.
    frames = [f for f in text.split("\n\n") if f.strip()]
    assert frames
    for frame in frames:
        assert "event:" in frame
        payload = [ln for ln in frame.splitlines() if ln.startswith("data:")]
        assert payload
        json.loads(payload[0][len("data:"):].strip())

    # The trip change must have been delivered.
    assert "trip.updated" in text
    assert "departed" in text


@pytest.mark.asyncio
async def test_sse_stream_sends_a_heartbeat_when_idle(client, auth_headers, db):
    """With nothing happening the stream still produces a `ping` frame."""
    from app.services.events import broker

    await broker.start(poll_interval=0.2, db=db)
    try:
        r = await client.get(
            "/events/trips", params={"max_events": 1}, headers=auth_headers
        )
        assert r.status_code == 200, r.status_code
        text = r.text
    finally:
        await broker.stop()

    assert "event:" in text
    assert "ping" in text or "trip." in text


@pytest.mark.asyncio
async def test_event_stream_generator_unsubscribes_on_exit():
    """The generator must not leak subscribers when the client leaves."""
    from app.services.events import broker, event_stream

    assert broker.subscriber_count == 0

    generator = event_stream()

    # Start the first pull in the background so the generator subscribes
    # *before* we publish — an event published with no subscribers is lost.
    pull = asyncio.create_task(generator.__anext__())
    await asyncio.sleep(0.1)
    assert broker.subscriber_count == 1

    await broker.publish({"type": "trip.updated", "data": {"trip_id": "t9"}})
    event = await asyncio.wait_for(pull, timeout=3)
    assert event["type"] == "trip.updated"

    # Closing the generator must release the subscription.
    await generator.aclose()

    assert broker.subscriber_count == 0
