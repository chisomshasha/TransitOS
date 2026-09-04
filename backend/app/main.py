"""TransitOS FastAPI application entry point.

`uvicorn app.main:app` (see `start.sh` / Dockerfile).
"""

from __future__ import annotations

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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "TransitOS starting (env=%s, db=%s)",
        settings.env,
        settings.mongodb_db_name,
    )
    try:
        await create_indexes()
        logger.info("Mongo indexes ensured")
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to create indexes (will retry on first request): %s", exc)

    try:
        from app.core.database import db as _app_db
        from app.services.auth import purge_revoked_refresh_tokens

        await purge_revoked_refresh_tokens(_app_db, older_than_hours=24)
    except Exception as exc:  # pragma: no cover
        logger.warning("revoked-token purge skipped: %s", exc)

    yield
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
    errors = []
    for err in exc.errors():
        loc = " → ".join(str(x) for x in err.get("loc", ()))
        errors.append({"loc": loc, "msg": err.get("msg"), "type": err.get("type")})
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Validation error", "errors": errors},
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
