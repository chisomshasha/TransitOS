# TransitOS

Role-based transport company management platform — full app, Sprint A + B + C.

## What's in this repo

```
transitos/
├── backend/          FastAPI + MongoDB + JWT + RBAC (Python 3.11)
│   ├── app/
│   │   ├── core/     config, database, security, rbac
│   │   ├── models/   Pydantic domain models (13 entities)
│   │   ├── routers/  13 routers, 44 endpoints
│   │   ├── services/ audit log, auth, trip state machine, cash-up variance
│   │   ├── schemas/  request/response shapes
│   │   ├── tests/    pytest suite (50 tests, all passing)
│   │   └── main.py   FastAPI entry point
│   ├── scripts/      seed.py — bootstrap demo data
│   ├── requirements.txt
│   ├── pytest.ini
│   └── Dockerfile
├── frontend/         Expo SDK 54 (React Native 0.81.5, JSC) — mobile + web
│   ├── app/          expo-router screens
│   │   ├── (auth)/   login
│   │   └── (app)/    12+ screens with bottom tab nav
│   │       ├── index            dashboard with 30-day KPIs
│   │       ├── trips/           list + detail (state machine, manifest, cash-up)
│   │       ├── branches/        list + detail
│   │       ├── users/           list + detail
│   │       ├── vehicles/        list
│   │       ├── drivers/         list
│   │       ├── conductors/      list
│   │       ├── routes/          list
│   │       ├── fuel.tsx         refuel logs + efficiency
│   │       ├── maintenance.tsx  service records + state
│   │       ├── reports.tsx      30/60/90-day analytics
│   │       └── profile.tsx      user + change password
│   ├── components/ui Button, Input, Card, Field, Select, Modal, Toast, Badge,
│   │                EmptyState, Spinner, SearchBar, PageHeader, BottomTabs
│   ├── components/   CashUpSection (the cash-up modal)
│   ├── lib/          api client (axios + refresh interceptor), auth context,
│   │                 RBAC, TanStack Query, types
│   ├── stores/       minimal Zustand auth store
│   ├── assets/       icons, splash
│   ├── app.json
│   ├── package.json
│   ├── tailwind.config.js
│   └── tsconfig.json
├── specs/            product blueprint + design specs
├── README.md
└── .gitignore
```

## Features by sprint

### Sprint A — Foundation (delivered)
- **Auth**: login, refresh-token rotation, logout, /me, change-password, forgot/reset
- **RBAC**: 10 roles (super_admin, owner, gm, bm, om, fm, ca, ba, driver, conductor)
- **Branches, Users, Vehicles, Drivers, Conductors, Routes**: full CRUD with branch-scoping, soft delete, audit log
- **9 frontend screens** with the design system (13 primitives)
- **21 API endpoints**

### Sprint B — Money Loop (delivered)
- **Trips**: state machine `planned → boarding → departed → arrived → closed → cashed_up` (or `cancelled`); foreign-key validation; auto-totals from manifest
- **Manifest**: per-trip passenger + cargo entries, with payment status
- **Cash-ups**: conductor's daily reconciliation — declares cash, breakdown by payment method; **variance** = declared − expected; submit → approve → reject flow
- **Expenses**: fuel, tolls, maintenance, permits, meals, accommodation; scoped `on_trip` or `standalone`; trip totals recompute on changes
- **+13 API endpoints** + frontend screens for trip list, trip detail (with manifest editor + cash-up modal), manifest management

### Sprint C — Owner View (delivered)
- **Fuel logs**: per-vehicle refueling events with liters, cost, odometer, station
- **Fuel efficiency endpoint**: `km/L` analytics per vehicle
- **Maintenance records**: scheduled/in-progress/completed/cancelled lifecycle; auto-flip vehicle status
- **Reports endpoints** (5):
  - `GET /reports/operations/summary` — totals + by-status breakdown
  - `GET /reports/operations/daily` — daily timeline (day or week bucket)
  - `GET /reports/branches/performance` — branch comparison
  - `GET /reports/vehicles/roi` — per-vehicle ROI
  - `GET /reports/fuel/summary` — fleet fuel costs
- **Owner dashboard**: 30-day headline KPIs, native bar chart for revenue vs expenses, branch ranking, vehicle ROI table, fuel summary
- **+10 API endpoints** + frontend screens for fuel, maintenance, reports

**Total: 44 API endpoints, 50 passing tests, 12+ frontend screens, bottom-tab navigation, full mobile + web.**

## Local dev

### Railway deployment (recommended)

Two deployment flavors work out of the box:

**Option 1 — Railway's MongoDB plugin**
1. In your Railway project, click **+ New** → **Database** → **MongoDB**
2. Once provisioned, attach it to your TransitOS service
3. Set the rest of the env vars below — the plugin's `MONGO_URL` / `MONGO_DB` are picked up automatically

**Option 2 — MongoDB Atlas**
1. Provision a free M0 cluster at https://www.mongodb.com/cloud/atlas
2. Add a database user, allow `0.0.0.0/0` network access
3. Set `MONGODB_URL` to the SRV connection string

Then set these in the service's **Variables** tab:

| Variable | Required | Example |
|---|---|---|
| `MONGODB_URL` *or* `MONGO_URL` | yes | from plugin or Atlas |
| `MONGODB_DB_NAME` *or* `MONGO_DB` | yes | `transitos` |
| `JWT_SECRET_KEY` | yes | `openssl rand -hex 32` |
| `CORS_ORIGINS` | yes | `["https://your-app.com"]` |
| `ENV` | no (default `dev`) | `prod` |
| `LOG_LEVEL` | no (default `INFO`) | `INFO` / `WARNING` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no (default `15`) | tweak if you want |
| `REFRESH_TOKEN_EXPIRE_DAYS` | no (default `7`) | tweak if you want |

The Dockerfile in `backend/Dockerfile` is Railway-ready — just point Railway at it.

### Local dev

### Backend

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt "bcrypt==4.0.1" mongomock-motor

# In-memory tests (no MongoDB needed)
python -m pytest

# Boot the API (requires MongoDB at localhost:27017)
export MONGODB_URL=mongodb://localhost:27017
export MONGODB_DB_NAME=transitos
export JWT_SECRET_KEY="$(openssl rand -hex 32)"
uvicorn app.main:app --reload --port 8000

# Seed demo data
python -m scripts.seed
```

### Frontend

```bash
cd frontend
npm install --legacy-peer-deps
npx expo start                  # opens Metro
# or: npx expo run:android, run:ios, export --platform web
```

App config (in `app.json`):
- `expo.android.package`: `com.transitos.app`
- `expo.ios.bundleIdentifier`: `com.transitos.app`
- `expo.scheme`: `transitos`
- `expo.extra.apiUrl`: `http://localhost:8000` (API is mounted at root; no `/api/v1` prefix)

### Demo logins (after seed)

| Email                         | Password              | Role            |
|-------------------------------|----------------------|-----------------|
| admin@transitos.app           | `Admin#Transit2026!` | super_admin     |
| owner@transitos.app           | `Owner#Transit2026!` | owner           |
| gm@transitos.app              | `Gm#Transit2026!`    | general_manager |
| bm.lagos@transitos.app        | `Bm#Transit2026!`    | branch_manager  |
| fm.lagos@transitos.app        | `Fm#Transit2026!`    | fleet_manager   |
| driver1@transitos.app         | `Driver#Transit2026!`| driver          |
| conductor1@transitos.app      | `Conductor#Transit2026!` | conductor   |

## API surface (44 endpoints)

### Auth (8)
- `POST /auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/change-password`, `/auth/forgot-password`, `/auth/reset-password`
- `GET  /auth/me`
- `GET  /healthz`

### Resources (CRUD × 7 = 28)
- `/branches`, `/users`, `/vehicles`, `/drivers`, `/conductors`, `/routes` (Sprint A)
- `/trips` (Sprint B), `/cash-ups` (Sprint B), `/expenses` (Sprint B)
- `/fuel-logs` (Sprint C), `/maintenance` (Sprint C)

### Sub-resources (5)
- `POST /branches/{id}/manager`
- `GET/POST /trips/{id}/manifest`, `PATCH/DELETE /trips/{id}/manifest/{entry_id}`
- `PATCH /trips/{id}/status`

### Special actions (4)
- `POST /cash-ups/{id}/submit`, `/approve`, `/reject`
- `GET  /fuel-logs/vehicle/{id}/efficiency`
- `GET  /maintenance/vehicle/{id}/upcoming`

### Reports (5)
- `GET /reports/operations/summary`
- `GET /reports/operations/daily`
- `GET /reports/branches/performance`
- `GET /reports/vehicles/roi`
- `GET /reports/fuel/summary`

OpenAPI spec at `/openapi.json`, docs at `/docs`.

## What's next

Suggested follow-ups:
- Settlements (paying branches, payroll for driver/conductor trips)
- Real-time trip board with WebSocket / Server-Sent Events
- Native barcode scanning for manifest entry
- Offline-first sync for the conductor app
- PWA web build for low-end Android devices

These were in the original blueprint but the user asked to complete the core app first; they can be added as Sprint D when the product is live.
