"""Rate limiter compatible with ``@limiter.limit("N/period")``.

Backends
--------
* **In-process** (default) — sliding window in memory. Fine for single-worker
  and tests.
* **Redis** — when ``REDIS_URL`` (or ``RATE_LIMIT_REDIS_URL``) is set, counters
  are stored in Redis so limits are shared across workers / instances.

The decorator preserves the original function signature so FastAPI dependency
injection and body parsing keep working under ``from __future__ import annotations``.
"""

from __future__ import annotations

import inspect
import logging
import os
import re
import time
from collections import defaultdict, deque
from typing import Any, Callable, Deque, Dict, Optional, Protocol, Tuple

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)

_PERIOD_SECONDS = {
    "second": 1,
    "seconds": 1,
    "minute": 60,
    "minutes": 60,
    "hour": 3600,
    "hours": 3600,
    "day": 86400,
    "days": 86400,
}

_LIMIT_RE = re.compile(
    r"^\s*(\d+)\s*/\s*(\d+)?\s*(second|seconds|minute|minutes|hour|hours|day|days)\s*$",
    re.IGNORECASE,
)


def _parse_limit(limit_str: str) -> Tuple[int, int]:
    m = _LIMIT_RE.match(limit_str)
    if not m:
        raise ValueError(f"Invalid rate limit string: {limit_str!r}")
    count = int(m.group(1))
    mult = int(m.group(2) or 1)
    period = m.group(3).lower()
    return count, mult * _PERIOD_SECONDS[period]


def _client_key(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return "unknown"


class _Backend(Protocol):
    def hit(self, key: str, max_calls: int, window: int) -> bool:
        """Record a hit. Return True if allowed, False if over limit."""
        ...

    def reset(self) -> None: ...


class MemoryBackend:
    """Process-local sliding window."""

    def __init__(self) -> None:
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    def hit(self, key: str, max_calls: int, window: int) -> bool:
        now = time.monotonic()
        bucket = self._hits[key]
        cutoff = now - window
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= max_calls:
            return False
        bucket.append(now)
        return True

    def reset(self) -> None:
        self._hits.clear()


class RedisBackend:
    """Shared sliding window via Redis sorted sets.

    Requires the ``redis`` package (``pip install redis``). Connection is lazy
    so missing Redis at import time does not crash the app.

    Failure policy
    --------------
    Controlled by ``RATE_LIMIT_FAIL_CLOSED`` (default ``false``):

    * **fail-open** (default): when Redis is unreachable, the request is
      allowed and a warning is logged. After ``_CIRCUIT_THRESHOLD`` consecutive
      failures an ERROR is logged so operators notice the outage.
    * **fail-closed**: when Redis is unreachable, the request is rejected with
      429. Use in high-security deployments where rate limiting must never be
      silently disabled.

    A simple circuit breaker cools down after ``_CIRCUIT_COOLDOWN_S`` seconds
    and retries the connection, avoiding a permanent hard-fail on transient
    blips.
    """

    _CIRCUIT_THRESHOLD = 5
    _CIRCUIT_COOLDOWN_S = 30.0

    def __init__(self, url: str, *, fail_closed: bool = False) -> None:
        self._url = url
        self._client: Any = None
        self._fail_closed = fail_closed
        self._consecutive_failures = 0
        self._circuit_open_until = 0.0
        self._error_logged = False

    def _get_client(self) -> Any:
        now = time.monotonic()
        if now < self._circuit_open_until:
            return None  # circuit still open — skip reconnect attempts

        if self._client is not None:
            return self._client
        try:
            import redis  # type: ignore

            self._client = redis.Redis.from_url(
                self._url,
                decode_responses=True,
                socket_connect_timeout=1.5,
                socket_timeout=1.5,
            )
            # Probe
            self._client.ping()
            logger.info(
                "rate_limit: Redis backend connected (%s)", self._url.split("@")[-1]
            )
            self._consecutive_failures = 0
            self._error_logged = False
            return self._client
        except Exception as exc:  # pragma: no cover
            self._client = None
            self._record_failure(exc)
            return None

    def _record_failure(self, exc: Exception) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._CIRCUIT_THRESHOLD:
            self._circuit_open_until = time.monotonic() + self._CIRCUIT_COOLDOWN_S
            if not self._error_logged:
                logger.error(
                    "rate_limit: Redis unavailable after %d consecutive failures "
                    "(%s) — circuit open for %.0fs; policy=%s",
                    self._consecutive_failures,
                    exc,
                    self._CIRCUIT_COOLDOWN_S,
                    "fail-closed" if self._fail_closed else "fail-open",
                )
                self._error_logged = True
        else:
            logger.warning(
                "rate_limit: Redis error (%s) — %s",
                exc,
                "rejecting request" if self._fail_closed else "allowing request",
            )

    def _on_backend_down(self) -> bool:
        """Return whether the request is allowed when Redis is down."""
        if self._fail_closed:
            return False  # reject → caller raises 429
        return True  # allow

    def hit(self, key: str, max_calls: int, window: int) -> bool:
        client = self._get_client()
        if client is None:
            return self._on_backend_down()

        rkey = f"rl:{key}"
        now = time.time()
        cutoff = now - window
        pipe = client.pipeline()
        pipe.zremrangebyscore(rkey, 0, cutoff)
        pipe.zcard(rkey)
        pipe.zadd(rkey, {f"{now}": now})
        pipe.expire(rkey, window + 1)
        try:
            results = pipe.execute()
            count = int(results[1])
            self._consecutive_failures = 0
            self._error_logged = False
            return count < max_calls
        except Exception as exc:  # pragma: no cover
            self._client = None  # force reconnect next time
            self._record_failure(exc)
            return self._on_backend_down()

    def reset(self) -> None:
        client = self._get_client()
        if client is None:
            return
        try:
            for key in client.scan_iter("rl:*"):
                client.delete(key)
        except Exception:  # pragma: no cover
            pass


def _build_backend() -> _Backend:
    url = (
        os.environ.get("RATE_LIMIT_REDIS_URL")
        or os.environ.get("REDIS_URL")
        or ""
    ).strip()
    if url:
        fail_closed = os.environ.get("RATE_LIMIT_FAIL_CLOSED", "").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        return RedisBackend(url, fail_closed=fail_closed)
    return MemoryBackend()


class RateLimiter:
    def __init__(self, backend: Optional[_Backend] = None) -> None:
        self._backend: _Backend = backend or _build_backend()
        self.enabled: bool = True

    def limit(self, limit_str: str) -> Callable[[Callable], Callable]:
        max_calls, window = _parse_limit(limit_str)

        def decorator(func: Callable) -> Callable:
            sig = inspect.signature(func)
            param_names = list(sig.parameters.keys())

            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                if self.enabled:
                    request: Optional[Request] = kwargs.get("request")
                    if request is None and args:
                        if "request" in param_names:
                            idx = param_names.index("request")
                            if idx < len(args) and isinstance(args[idx], Request):
                                request = args[idx]
                        if request is None:
                            for a in args:
                                if isinstance(a, Request):
                                    request = a
                                    break
                    if request is not None:
                        key = f"{func.__module__}.{func.__name__}:{_client_key(request)}"
                        allowed = self._backend.hit(key, max_calls, window)
                        if not allowed:
                            raise HTTPException(
                                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                                detail="Rate limit exceeded. Try again later.",
                                headers={"Retry-After": str(window)},
                            )

                return await func(*args, **kwargs)

            wrapper.__name__ = func.__name__
            wrapper.__qualname__ = func.__qualname__
            wrapper.__doc__ = func.__doc__
            wrapper.__module__ = func.__module__
            wrapper.__annotations__ = getattr(func, "__annotations__", {}).copy()
            wrapper.__signature__ = sig  # type: ignore[attr-defined]
            wrapper.__wrapped__ = func  # type: ignore[attr-defined]
            if hasattr(func, "__globals__"):
                try:
                    wrapper.__globals__.update(func.__globals__)  # type: ignore[attr-defined]
                except Exception:
                    pass

            return wrapper

        return decorator

    def reset(self) -> None:
        self._backend.reset()


limiter = RateLimiter()
