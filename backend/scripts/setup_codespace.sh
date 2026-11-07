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

# ── 3. node ────────────────────────────────────────────────────────────────
# A Codespace created before .devcontainer/ existed has no Node at all,
# so `npm` is "command not found" and neither the app nor an
# over-the-air update can be published. Install it here.
say "Node"
if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
  echo "    node $(node -v) · npm $(npm -v) ✓"
else
  echo "    not found — installing Node 20"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - \
      || warn "could not add the NodeSource repository"
    sudo apt-get update -qq
    sudo apt-get install -y -qq nodejs || warn "could not install nodejs"
  else
    warn "curl is missing — install Node 20 by hand"
  fi
  if command -v node >/dev/null 2>&1; then
    echo "    node $(node -v) · npm $(npm -v) ✓"
  else
    warn "Node is still missing. The backend still works; the app and"
    warn "'eas update' will not. Install Node 20 and re-run this script."
  fi
fi

# ── 4. MongoDB ────────────────────────────────────────────────────────────
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

# Which database are we seeding? This decides everything below.
MONGO_URL="$(grep -E '^MONGODB_URL=' backend/.env | head -1 | cut -d= -f2- | tr -d '\r')"
[ -n "$MONGO_URL" ] || MONGO_URL="mongodb://localhost:27017"

# The host part of a mongodb URL: mongodb://user:pass@host:port/db
MONGO_HOST="$(printf '%s' "$MONGO_URL" | sed -E 's#^mongodb(\+srv)?://##; s#/.*$##; s#^[^@]*@##; s#[:/].*$##')"
case "$MONGO_HOST" in
  ""|localhost|127.0.0.1|0.0.0.0|::1|"[::1]") MONGO_IS_LOCAL=1 ;;
  *) MONGO_IS_LOCAL=0 ;;
esac

# ── 4. MongoDB ────────────────────────────────────────────────────────────
say "MongoDB"
MONGO_UP=0

if [ "$MONGO_IS_LOCAL" = 0 ]; then
  # A remote database — the Railway one, or MongoDB Atlas. There is
  # nothing to start here: the seed talks to it directly.
  echo "    using the remote database at $MONGO_HOST"
  MONGO_UP=1
elif (echo > /dev/tcp/127.0.0.1/27017) >/dev/null 2>&1; then
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
  # A stopped service is more common than a missing binary.
  sudo systemctl start mongod >/dev/null 2>&1 || true
  if ! (echo > /dev/tcp/127.0.0.1/27017) >/dev/null 2>&1; then
    mkdir -p "$HOME/.local/mongodb-data"
    mongod --dbpath "$HOME/.local/mongodb-data" --port 27017 --fork \
      --logpath "$HOME/.local/mongodb-data/mongod.log" \
      || warn "could not start mongod"
  fi
  sleep 2
  (echo > /dev/tcp/127.0.0.1/27017) >/dev/null 2>&1 && MONGO_UP=1
else
  # No Docker, no mongod. The official MongoDB build runs from a
  # tarball without root, without Docker and without systemd — it just
  # needs a download.
  MONGO_VER="8.0.12"
  MONGO_BASE="${MONGO_HOME:-$HOME/.local/mongodb}"
  MONGO_DATA="${MONGO_DATA:-$HOME/.local/mongodb-data}"
  echo "    no Docker and no mongod — installing MongoDB $MONGO_VER from the official tarball"
  if [ ! -x "$MONGO_BASE/bin/mongod" ]; then
    DISTRO="$(. /etc/os-release 2>/dev/null && echo "${VERSION_ID:-}")"
    case "$DISTRO" in
      24.04) BUILD="ubuntu2404" ;;
      22.04) BUILD="ubuntu2204" ;;
      12)    BUILD="debian12" ;;
      *)     BUILD="ubuntu2204" ;;
    esac
    URL="https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-${BUILD}-${MONGO_VER}.tgz"
    echo "    downloading $URL"
    TMP="$(mktemp -d)"
    if curl -fsSL --retry 3 --retry-delay 2 -o "$TMP/mongo.tgz" "$URL"; then
      mkdir -p "$MONGO_BASE"
      tar xzf "$TMP/mongo.tgz" -C "$MONGO_BASE" --strip-components=1 && echo "    installed to $MONGO_BASE"
    else
      warn "could not download MongoDB"
    fi
    rm -rf "$TMP"
  else
    echo "    already installed at $MONGO_BASE"
  fi
  if [ -x "$MONGO_BASE/bin/mongod" ]; then
    mkdir -p "$MONGO_DATA"
    "$MONGO_BASE/bin/mongod" --dbpath "$MONGO_DATA" --port 27017 --bind_ip 127.0.0.1 \
      --fork --logpath "$MONGO_DATA/mongod.log" || warn "could not start mongod"
    for _ in $(seq 1 30); do
      if (echo > /dev/tcp/127.0.0.1/27017) >/dev/null 2>&1; then MONGO_UP=1; break; fi
      sleep 1
    done
    [ "$MONGO_UP" = 1 ] && echo "    mongod up on 27017 ✓"
  fi
fi

# ── 6 + 7. indexes + seed ─────────────────────────────────────────────────
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

# ── 8. next steps ─────────────────────────────────────────────────────────
API_PORT=8000

say "Seeding the Railway database"
cat <<EOF
    If your database is the one Railway hosts — the usual case — the
    cleanest way to seed it is from inside the service itself, where
    MONGODB_URL is already set to the real database:

        Railway dashboard -> your API service -> the shell tab
        cd /app && python -m scripts.seed

    That seeds the real database with all ten demo accounts and the
    demo branch, vehicle, driver, conductor and route. It needs no
    Docker, no local MongoDB and no connection string from here.

    The alternative is the HTTP bootstrap:

        curl -X POST https://<your-api>/admin/seed \\
          -H "X-Admin-Token: <ADMIN_BOOTSTRAP_TOKEN>"

    It seeds the same accounts. It can only run once — the endpoint
    locks itself after the first success — so unset
    ADMIN_BOOTSTRAP_TOKEN afterwards.

    A local MongoDB (started above) is only a throwaway database for
    working on the code. It is NOT the database the deployed app uses.
EOF

if command -v npm >/dev/null 2>&1; then
  say "EAS CLI (for over-the-air updates)"
  if command -v eas >/dev/null 2>&1; then
    echo "    $(eas --version) ✓"
  else
    echo "    installing eas-cli"
    npm install -g eas-cli >/dev/null 2>&1 \
      && echo "    $(eas --version) ✓" \
      || warn "could not install eas-cli — 'bash backend/scripts/publish_update.sh' installs it too"
  fi
fi

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
    #
    # ship a JavaScript fix to the phones already in the field
    # (no APK, no store review):
    cd frontend && eas update --channel production --message "..."
EOF
echo
echo "================================================================"
