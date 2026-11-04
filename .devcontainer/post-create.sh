#!/usr/bin/env bash
# One-shot setup for a GitHub Codespace (and for a plain machine).
#
# Runs automatically when the Codespace is created. Safe to re-run.
#
#   backend  -> .venv with every pinned dependency + a dev .env
#   frontend -> npm ci (from the committed lockfile)
#
# MongoDB is installed and started by the `mongodb` devcontainer
# feature, so the default connection string works as-is.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> backend: virtualenv"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -r backend/requirements.txt
echo "    .venv ready"

echo "==> backend: dev .env"
if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
  # Dev-only values. ENV=dev keeps the weak-JWT guard relaxed; this is
  # a local machine, never a deployed environment.
  sed -i 's|^ENV=.*|ENV=dev|'                                  backend/.env
  sed -i 's|^MONGODB_URL=.*|MONGODB_URL=mongodb://localhost:27017|' backend/.env
  sed -i 's|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=dev-only-local-secret-not-for-production-0123456789|' backend/.env
  sed -i 's|^CORS_ORIGINS=.*|CORS_ORIGINS=*|'                  backend/.env
  sed -i 's|^FRONTEND_URL=.*|FRONTEND_URL=http://localhost:8081|' backend/.env
  echo "    wrote backend/.env (dev defaults — review it)"
else
  echo "    backend/.env already exists, left alone"
fi

echo "==> backend: indexes"
(cd backend && ../.venv/bin/python -c "
import asyncio, os, sys
sys.path.insert(0, os.getcwd())
from app.core.database import create_indexes, client
async def main():
    await create_indexes()
    print('    indexes ensured')
    client.close()
asyncio.run(main())
") || echo "    (skipped — is MongoDB running? 'sudo service mongodb start')"

echo "==> frontend: npm ci"
(cd frontend && npm ci --legacy-peer-deps)

echo
echo "=============================================================="
echo " Ready. Next:"
echo
echo "   # 1. start the API"
echo "   cd backend && ../.venv/bin/uvicorn app.main:app --reload --port 8000"
echo
echo "   # 2. seed a demo account for every role"
echo "   cd backend && ../.venv/bin/python -m scripts.seed"
echo
echo "   # 3. start the app (Expo web, phone on the same network)"
echo "   cd frontend && npx expo start"
echo "=============================================================="
