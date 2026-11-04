#!/bin/sh
# TransitOS backend startup script.
# ----------------------------------------------------------------
# Used by both the Dockerfile CMD and railway.toml startCommand.
#
# Why a script and not a direct command:
#   - Railway's startCommand is passed to the container WITHOUT a shell
#     wrapper, so ``${PORT:-8000}`` would arrive as a literal string and
#     uvicorn would fail with "invalid integer".
#   - Docker's ``CMD ["sh", "-c", "..."]`` form CAN do the expansion,
#     but having a single source of truth in start.sh keeps the two
#     deployment paths in sync.
#
# This script:
#   1. Resolves the port from Railway's $PORT env var (or default 8000).
#   2. ``exec``s uvicorn so the shell process is replaced (PID 1 = uvicorn)
#      — important for receiving SIGTERM from Railway's shutdown signal.
# ----------------------------------------------------------------

set -e

PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"
WORKERS="${WORKERS:-1}"

echo "[start.sh] TransitOS backend starting"
echo "[start.sh]   host:    $HOST"
echo "[start.sh]   port:    $PORT"
echo "[start.sh]   workers: $WORKERS"
echo "[start.sh]   env:     ${ENV:-dev}"

# ``exec`` replaces the shell with uvicorn — uvicorn becomes PID 1 and
# receives signals directly (clean shutdown on Railway restart).
exec uvicorn app.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    --proxy-headers \
    --forwarded-allow-ips="*"
