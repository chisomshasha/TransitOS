"""TransitOS FastAPI application entry point.

`uvicorn app.main:app` (see `start.sh` / Dockerfile).

Responsibilities:
  * Create the FastAPI app
  * CORS + security headers middleware
  * Request-id correlation + structured logging
  * Mount all routers (admin is optional / tolerant of ImportError)
  * Lifespan: create Mongo indexes on startup
  * Health check that pings Mongo
  * Convert Pydantic 422 → 400 for consistent client errors
  * Wire the shared rate limiter
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


# ─── logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("transitos")

# Quiet noisy libraries in prod
if settings.env in ("staging", "prod"):
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


# ─── optional admin router (must tolerate absence) ───────────────────────────
_ADMIN_ROUTER_AVAILABLE = False
_admin_router = None
try:
    from app.routers import admin as _admin_mod

    if _admin_mod is not None and hasattr(_admin_mod, "router"):
        _admin_router = _admin_mod.router
        _ADMIN_ROUTER_AVAILABLE = True
except Exception as exc:  # noqa: BLE001 — boot must never fail on admin
    logger.warning("admin router not available (POST /admin/seed disabled): %s", exc)


# ─── lifespan ────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create indexes on startup; purge revoked tokens; close Mongo on shutdown."""
    logger.info(
        "TransitOS starting (env=%s, db=%s)",
        settings.env,
        settings.mongodb_db_name,
    )
    try:
        await create_indexes()
        logger.info("Mongo indexes ensured")
    except Exception as exc:  # pragma: no cover — connection may be down at boot
        logger.error("Failed to create indexes (will retry on first request): %s", exc)

    # Best-effort cleanup of revoked-but-not-yet-expired refresh tokens.
    # TTL index handles natural expiry; this keeps the collection lean after
    # logout / password-change / rotation storms.
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


# ─── app ─────────────────────────────────────────────────────────────────────
# Hide interactive docs in staging/prod (OpenAPI still available when needed
# via a reverse-proxy ACL). Local/dev keeps the full Swagger UI.
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

# Expose limiter on app.state so decorators / tests can reach it
app.state.limiter = limiter


# ─── middleware: max request body size ───────────────────────────────────────
# Reject oversized payloads early (before JSON parse) so a malicious client
# cannot force the process to buffer multi-megabyte bodies into memory.
# Default 1 MiB is ample for TransitOS payloads (manifests, user records, …).
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
                # 413 constant name varies across Starlette versions
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


# ─── middleware: request-id + timing + security headers ───────────────────────
class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = request_id
        start = time.perf_counter()

        response = await call_next(request)

        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{elapsed_ms:.1f}ms"
        # Security headers (safe defaults for an API)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        # Minimal CSP for a pure JSON API — blocks accidental HTML/script
        # execution if a response is ever mis-served as text/html.
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


# Order: outermost runs first on the way in.
# Max body size must run before anything that consumes the body.
app.add_middleware(RequestContextMiddleware)
app.add_middleware(MaxBodySizeMiddleware)

# CORS — origins come from env (module-level list, already validated in prod).
# Methods/headers are tightened to what the SPA actually needs rather than "*".
# Spec note: browsers reject Access-Control-Allow-Origin: * together with
# Access-Control-Allow-Credentials: true. When the configured origin list is
# the wildcard we therefore disable credentials so local/dev CORS still works.
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


# ─── exception handlers ──────────────────────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Convert FastAPI's default 422 into 400 for a consistent client contract."""
    errors = []
    for err in exc.errors():
        loc = " → ".join(str(x) for x in err.get("loc", ()))
        errors.append({"loc": loc, "msg": err.get("msg"), "type": err.get("type")})
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Validation error", "errors": errors},
    )


# ─── health ──────────────────────────────────────────────────────────────────
@app.get("/healthz", tags=["health"])
async def healthz():
    """Liveness + basic Mongo connectivity check."""
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


# ─── routers ─────────────────────────────────────────────────────────────────
from app.routers import (  # noqa: E402
    alerts as alerts_mod,
    audit_log as audit_log_mod,
    auth,
    branches,
    cash_ups,
    conductors,
    drivers,
    expenses,
    fuel,
    maintenance,
    notifications as notifications_mod,
    reports,
    routes,
    trips,
    users,
    vehicle_documents as vehicle_documents_mod,
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
]

for r in _CORE_ROUTERS:
    app.include_router(r)

if _ADMIN_ROUTER_AVAILABLE and _admin_router is not None:
    app.include_router(_admin_router)
    logger.info("admin router mounted at /admin")
else:
    logger.info("admin router not mounted")


__all__ = ["app", "_ADMIN_ROUTER_AVAILABLE"]
