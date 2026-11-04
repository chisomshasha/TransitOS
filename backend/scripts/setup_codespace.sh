#!/usr/bin/env bash
# Bootstrap a GitHub Codespace (or any machine) for TransitOS.
#
# Works in a DEFAULT Codespace — no .devcontainer/ required.
#
#   cd /workspaces/TransitOS
#   bash backend/scripts/setup_codespace.sh
#
# Does:
#   1. checks Python
#   2. creates .venv and installs the backend requirements
#   3. starts MongoDB (Docker first — Codespaces have it)
#   4. writes backend/.env if there isn't one
#   5. creates the MongoDB indexes
#   6. seeds a demo account for every role
#   7. prints the logins and how to reach the API from your phone
#
# Safe to re-run.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

say() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[33m    %s\033[0m\n' "$*"; }
die() { printf '\033[31m    %s\033[0m\n' "$*" >&2; exit 1; }

# ── 1. python ─────────────────────────────────────────────────────────────
say "Checking Python"
PY=""
for cand in python3.13 python3.12 python3.11 python3; do
  if command -v "$cand" >/dev/null 2>&1 && \
     "$cand" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 11) else 1)' 2>/dev/null; then
    PY="$cand"
    break
  fi
done
[ -n "$PY" ] || {
  echo "    available: $(command -v python3 >/dev/null 2>&1 && python3 -V 2>&1 || echo 'no python3')" >&2
  die "Python 3.11+ is required. In a Codespace: sudo apt-get update && sudo apt-get install -y python3.11 python3.11-venv"
}
PYVER="$("$PY" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
echo "    $PY ($PYVER) ✓"

# ── 2. virtualenv + backend deps ──────────────────────────────────────────
say "Backend dependencies"
if [ ! -d .venv ]; then
  "$PY" -m venv .venv || die "could not create the virtualenv (install python3-venv)"
fi
.venv/bin/python -m pip install --quiet --upgrade pip
if ! .venv/bin/python -m pip install --quiet -r backend/requirements.txt; then
  die "pip install failed. If bcrypt fails to build, try: sudo apt-get install -y build-essential"
fi
echo "    .venv ready ($(cd .venv && .venv/bin/python -V 2>/dev/null || echo "$ROOT/.venv"))"

# ── 3. MongoDB ────────────────────────────────────────────────────────────
say "MongoDB"
MONGO_UP=0
if (echo > /dev/tcp/127.0.0.1/27017) >/dev/null 2>&1; then
  echo "    already listening on 27017 ✓"
  MONGO_UP=1
elif command -v docker >/dev/null 2>&1; then
  echo "    starting mongo:7 in Docker"
  docker rm -f transitos-mongo >/dev/null 2>&1
  docker run -d --name transitos-mongo -p 27017:27017 mongo:7 >/dev/null 2>&1 \
    || warn "could not start the container — try: sudo service mongodb start"
  for _ in $(seq 1 30); do
    if (echo > /dev/tcp/127.0.0.1/27017) >/dev/null 2>&1; then MONGO_UP=1; break; fi
    sleep 1
  done
  [ "$MONGO_UP" = 1 ] && echo "    mongo:7 up on 27017 ✓" || warn "MongoDB did not come up."
elif command -v mongod >/dev/null 2>&1; then
  echo "    starting the local mongod"
  mkdir -p /tmp/mongo-data
  mongod --dbpath /tmp/mongo-data --port 27017 --fork --logpath /tmp/mongod.log \
    || warn "could not start mongod"
  sleep 2
  (echo > /dev/tcp/127.0.0.1/27017) >/dev/null 2>&1 && MONGO_UP=1
else
  warn "Neither Docker nor mongod is available."
  warn "In a Codespace Docker is normally present — check 'docker ps'."
fi

# ── 4. .env ───────────────────────────────────────────────────────────────
say "Environment file"
if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
  sed -i 's|^ENV=.*|ENV=dev|'                                   backend/.env
  sed -i 's|^MONGODB_URL=.*|MONGODB_URL=mongodb://localhost:27017|' backend/.env
  sed -i 's|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=dev-only-local-secret-not-for-production-0123456789|' backend/.env
  sed -i 's|^CORS_ORIGINS=.*|CORS_ORIGINS=*|'                   backend/.env
  sed -i 's|^FRONTEND_URL=.*|FRONTEND_URL=http://localhost:8081|' backend/.env
  echo "    wrote backend/.env (dev defaults)"
else
  echo "    backend/.env already exists — left alone"
fi

# ── 5 + 6. indexes + seed ─────────────────────────────────────────────────
if [ "$MONGO_UP" = 1 ]; then
  say "Indexes"
  (cd backend && ../.venv/bin/python -c "
import asyncio, os, sys
sys.path.insert(0, os.getcwd())
from app.core.database import create_indexes, client
async def main():
    await create_indexes()
    print('    indexes ensured')
    client.close()
asyncio.run(main())
") || warn "index creation failed — the seed may still work."

  say "Seeding demo accounts"
  (cd backend && ../.venv/bin/python -m scripts.seed) \
    && echo "    seed complete ✓" \
    || warn "the seed failed — check that MongoDB is reachable on 27017"
else
  warn "Skipping the seed (no MongoDB). Start it, then run:"
  warn "  cd backend && ../.venv/bin/python -m scripts.seed"
fi

# ── 7. next steps ─────────────────────────────────────────────────────────
API_PORT=8000
say "Next"
cat <<EOF
    # 1. start the API (leave this running)
    cd backend && ../.venv/bin/uvicorn app.main:app --reload --port $API_PORT

    # 2. in a SECOND terminal, start the app
    cd frontend && npm ci --legacy-peer-deps && npx expo start

    # reach the API from a phone
    #   Ports tab -> $API_PORT -> click the globe to make it public, then use
    #   https://${CODESPACE_NAME:-<your-codespace>}-$API_PORT.app.github.dev
    #   (set it as EXPO_PUBLIC_API_URL before starting the app)
EOF
echo
echo "================================================================"
