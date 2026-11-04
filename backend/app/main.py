"""TransitOS FastAPI application entry point.

`uvicorn app.main:app` (see `start.sh` / Dockerfile).
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import CORS_ORIGINS_LIST, settings
from app.core.database import client as mongo_client
from app.core.database import create_indexes
from app.core.rate_limit import limiter


logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("transitos")

if settings.env in ("staging", "prod"):
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


_ADMIN_ROUTER_AVAILABLE = False
_admin_router = None
try:
    from app.routers import admin as _admin_mod

    if _admin_mod is not None and hasattr(_admin_mod, "router"):
        _admin_router = _admin_mod.router
        _ADMIN_ROUTER_AVAILABLE = True
except Exception as exc:  # noqa: BLE001
    logger.warning("admin router not available (POST /admin/seed disabled): %s", exc)


async def _alerts_scan_loop() -> None:
    """Background worker: keep indexes and the notifications inbox fresh.

    Two jobs, run on a fixed interval:

    1. **Ensure indexes.** ``create_indexes()`` is retried here until it
       succeeds, so a database that was not reachable at boot still gets
       its indexes as soon as it comes back.
    2. **Run the alerts scan.** The alerts engine
       (``app/services/alerts.py``) turns expiring vehicle documents, low
       fuel and due maintenance into notification rows. Before this
       worker existed the only way to run it was for somebody to call
       ``POST /alerts/scan`` by hand — so in production the inbox stayed
       permanently empty and the Notifications screen always showed its
       "no notifications yet" placeholder.

    The loop is cancelled cleanly on shutdown.
    """
    from app.core.database import db as _app_db
    from app.services.alerts import run_alerts_scan

    interval = settings.alerts_scan_interval_seconds
    if interval <= 0:
        logger.info("alerts worker disabled (ALERTS_SCAN_INTERVAL_SECONDS=0)")
        return

    indexes_ready = False

    while True:
        if not indexes_ready:
            try:
                await create_indexes()
                logger.info("Mongo indexes ensured")
                indexes_ready = True
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.warning("index creation failed (will retry): %s", exc)

        try:
            counts = await run_alerts_scan(_app_db)
            total = sum(counts.values()) if isinstance(counts, dict) else 0
            logger.info("alerts scan complete: %s", counts)
            if total:
                logger.info("alerts scan raised %s notification(s)", total)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            # A failed scan must never kill the worker — the next tick
            # retries. Log and keep going.
            logger.warning("alerts scan failed (will retry): %s", exc)

        try:
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            raise


# How long start-up may block on the database before giving up and
# letting the background worker retry. Railway's healthcheck timeout is
# 30s, so two sequential 30s driver timeouts (one per start-up call)
# used to push start-up past the deadline and get the deploy marked
# unhealthy.
_STARTUP_DB_TIMEOUT_SECONDS = float(os.environ.get("STARTUP_DB_TIMEOUT_SECONDS", "8"))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "TransitOS starting (env=%s, db=%s)",
        settings.env,
        settings.mongodb_db_name,
    )

    # Best-effort index creation, bounded so a slow/unreachable database
    # can never hold the container past the healthcheck deadline. The
    # background worker retries until the indexes are in place.
    try:
        await asyncio.wait_for(
            create_indexes(), timeout=_STARTUP_DB_TIMEOUT_SECONDS
        )
        logger.info("Mongo indexes ensured")
    except asyncio.TimeoutError:
        logger.warning(
            "Index creation timed out after %ss — the background worker will retry",
            _STARTUP_DB_TIMEOUT_SECONDS,
        )
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to create indexes (worker will retry): %s", exc)

    try:
        from app.core.database import db as _app_db
        from app.services.auth import purge_revoked_refresh_tokens

        await asyncio.wait_for(
            purge_revoked_refresh_tokens(_app_db, older_than_hours=24),
            timeout=_STARTUP_DB_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning("revoked-token purge timed out — skipped")
    except Exception as exc:  # pragma: no cover
        logger.warning("revoked-token purge skipped: %s", exc)

    # Start the alerts worker.
    alerts_task = asyncio.create_task(_alerts_scan_loop())

    # Start the realtime trip-event broker (feeds the live trip board).
    # The broker owns its own background task — we only start/stop it.
    try:
        from app.services.events import broker as _event_broker

        await _event_broker.start(
            poll_interval=float(settings.events_poll_interval_seconds)
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("event broker not started: %s", exc)

    try:
        yield
    finally:
        try:
            from app.services.events import broker as _event_broker

            await _event_broker.stop()
        except Exception:  # pragma: no cover - defensive
            pass
        alerts_task.cancel()
        try:
            await alerts_task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass
        logger.info("TransitOS shutting down")
        try:
            mongo_client.close()
        except Exception:  # pragma: no cover
            pass


_docs_enabled = settings.env == "dev"

app = FastAPI(
    title="TransitOS",
    description="Role-based transport company management platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)

app.state.limiter = limiter


_MAX_BODY_BYTES = int(os.environ.get("MAX_REQUEST_BODY_BYTES", str(1 * 1024 * 1024)))


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                length = int(content_length)
            except ValueError:
                length = 0
            if length > _MAX_BODY_BYTES:
                code_413 = getattr(
                    status,
                    "HTTP_413_REQUEST_ENTITY_TOO_LARGE",
                    getattr(status, "HTTP_413_CONTENT_TOO_LARGE", 413),
                )
                return JSONResponse(
                    status_code=code_413,
                    content={
                        "detail": (
                            f"Request body too large "
                            f"(max {_MAX_BODY_BYTES} bytes)"
                        )
                    },
                )
        return await call_next(request)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = request_id
        start = time.perf_counter()

        response = await call_next(request)

        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{elapsed_ms:.1f}ms"
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
        )
        if settings.env in ("staging", "prod"):
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response


app.add_middleware(RequestContextMiddleware)
app.add_middleware(MaxBodySizeMiddleware)

_CORS_METHODS = ["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"]
_CORS_HEADERS = [
    "Authorization",
    "Content-Type",
    "Accept",
    "X-Request-ID",
    "X-Admin-Token",
]

_cors_is_wildcard = CORS_ORIGINS_LIST == ["*"] or "*" in CORS_ORIGINS_LIST
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS_LIST,
    allow_credentials=not _cors_is_wildcard,
    allow_methods=_CORS_METHODS,
    allow_headers=_CORS_HEADERS,
    expose_headers=["X-Request-ID", "X-Response-Time"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Render a body/param validation failure.

    The status is **422**, not 400: 422 is the standard answer for "the
    request was well-formed but the values are not acceptable", it is
    what FastAPI returns by default, and it is what the API contract
    (``specs/api-contract.md`` §0.5/§0.7), the client-facing testing
    manual (``docs/TESTING_MANUAL.md``) and the whole testing
    methodology in ``docs/IT-DEVELOPER-GUIDE.md`` (§"Required query
    params & body fields → The 422") specify.

    The body carries the contract's error shape — ``detail`` plus
    ``type: "validation_error"`` — and keeps the per-field ``errors``
    array so a form can point at the offending field. ``detail`` holds
    the first offending rule so a client that only shows ``detail``
    still tells the user *what* was wrong instead of "Validation
    error".

    Note that 400 is still used elsewhere, for *semantic* refusals
    ("Vehicle does not exist", "Invalid trip_id"). Those are not
    validation errors and are deliberately left alone.
    """
    errors = []
    for err in exc.errors():
        loc = " → ".join(str(x) for x in err.get("loc", ()))
        errors.append({"loc": loc, "msg": err.get("msg"), "type": err.get("type")})

    detail = "Validation error"
    if errors:
        first = errors[0].get("msg") or detail
        # Pydantic prefixes custom-validator messages with "Value error, ".
        # That is noise in a toast, so strip it.
        if isinstance(first, str) and first.startswith("Value error, "):
            first = first[len("Value error, ") :]
        detail = first

    code_422 = getattr(
        status,
        "HTTP_422_UNPROCESSABLE_ENTITY",
        getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
    )
    return JSONResponse(
        status_code=code_422,
        content={
            "detail": detail,
            "type": "validation_error",
            "errors": errors,
        },
    )


@app.get("/healthz", tags=["health"])
async def healthz():
    mongo_ok = False
    try:
        await mongo_client.admin.command("ping")
        mongo_ok = True
    except Exception as exc:  # pragma: no cover
        logger.warning("healthz mongo ping failed: %s", exc)

    payload = {
        "status": "ok" if mongo_ok else "degraded",
        "env": settings.env,
        "mongo": "up" if mongo_ok else "down",
    }
    code = status.HTTP_200_OK if mongo_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(content=payload, status_code=code)


from app.routers import (  # noqa: E402
    alerts as alerts_mod,
    audit_log as audit_log_mod,
    auth,
    branches,
    cash_ups,
    conductors,
    dashboard as dashboard_mod,
    drivers,
    expenses,
    fuel,
    incidents as incidents_mod,
    inspections as inspections_mod,
    maintenance,
    notifications as notifications_mod,
    positions as positions_mod,
    push as push_mod,
    qr as qr_mod,
    reports,
    role_permissions as role_permissions_mod,
    routes,
    settlements as settlements_mod,
    events as events_mod,
    sync as sync_mod,
    trips,
    users,
    vehicle_documents as vehicle_documents_mod,
    vehicle_transfers as vehicle_transfers_mod,
    vehicles,
)

_CORE_ROUTERS = [
    auth.router,
    branches.router,
    users.router,
    vehicles.router,
    drivers.router,
    conductors.router,
    routes.router,
    trips.router,
    cash_ups.router,
    expenses.router,
    fuel.router,
    maintenance.router,
    reports.router,
    settlements_mod.router,
    events_mod.router,
    notifications_mod.router,
    vehicle_documents_mod.router,
    vehicle_documents_mod.exp_router,
    alerts_mod.router,
    audit_log_mod.router,
    role_permissions_mod.router,
    inspections_mod.router,
    incidents_mod.router,
    positions_mod.router,
    vehicle_transfers_mod.router,
    push_mod.router,
    sync_mod.router,
    qr_mod.router,
    dashboard_mod.router,
]

for r in _CORE_ROUTERS:
    app.include_router(r)

if _ADMIN_ROUTER_AVAILABLE and _admin_router is not None:
    app.include_router(_admin_router)
    logger.info("admin router mounted at /admin")
else:
    logger.info("admin router not mounted")


__all__ = ["app", "_ADMIN_ROUTER_AVAILABLE"]
