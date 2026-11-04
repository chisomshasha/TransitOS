#!/usr/bin/env bash
# Run the TransitOS backend dev server.
# Usage: ./scripts/run_dev.sh
set -euo pipefail
cd "$(dirname "$0")/.."
exec uvicorn app.main:app --reload --port 8000
