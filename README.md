# TransitOS

Role-based transport company management platform — full app (Sprint A → E).

## What's in this repo

```
transitos/
├── backend/          FastAPI + MongoDB + JWT + RBAC (Python 3.11)
│   ├── app/
│   │   ├── core/     config, database, security, rbac, rate limit
│   │   ├── models/   Pydantic domain models (23 entities, 100 classes)
│   │   ├── routers/  29 routers, 147 API operations
│   │   ├── services/ audit log, auth, trip state machine, cash-up variance,
│   │   │             alerts engine, email delivery, PDF generation,
│   │   │             settlements, event broker (SSE)
│   │   ├── schemas/  request/response shapes
│   │   ├── tests/    pytest suite (228 tests, all passing)
│   │   └── main.py   FastAPI entry point + background alerts worker
│   ├── scripts/      seed.py — bootstrap demo data
│   │                 check_requirements.py — CI guard (no npm packages here)
│   ├── requirements.txt
│   ├── pytest.ini
│   └── Dockerfile
├── frontend/         Expo SDK 54 (React Native 0.81.5, Hermes) — mobile + web
│   ├── app/          expo-router screens (46 screens)
│   │   ├── (auth)/   login, forgot-password, forgot-username
│   │   └── (app)/    dashboard, trips, branches, users, vehicles, drivers,
│   │                conductors, routes, fuel, maintenance, expenses,
│   │                cash-ups, reports, incidents, inspections, transfers,
│   │                notifications, audit log, role permissions, map, scan,
│   │                sync, profile, devices, settlements, live trips
│   ├── components/   UI kit (18 primitives) + admin modals
│   ├── lib/          api client (axios + refresh interceptor), auth context,
│   │                 RBAC, TanStack Query, password policy, push registration,
│   │                 SSE client, query hooks
│   ├── stores/       minimal Zustand auth store
│   ├── assets/       icons, splash
│   ├── app.json
│   ├── package.json
│   └── tsconfig.json
├── docs/             TESTING_MANUAL.md (436 test items) + its generator
│                    and the distributable DOCX
│                    USER_MANUAL.md — the client-facing user manual
│                    (general + 10 role manuals, 103 real screen captures)
│                    IT-DEVELOPER-GUIDE.md — project-agnostic guide to
│                    briefing, building and verifying an AI-assisted
│                    codebase (see §"IT-DEVELOPER-GUIDE.md")
│                    mockup/ — the capture harness: a seeded demo API, a
│                    static server for the web build, and the Playwright
│                    script that photographs the real screens
├── tools/contract/   check.py — frontend↔backend contract checker
│                    (routes, params, body fields, reachability, RBAC
│                    incl. call→hook→screen, screens)
│                    payloads.py — resolves the request body the front
│                    end actually sends (hook → mutation → mutate())
│                    check_styling.py — guards the styling toolchain
├── specs/            product blueprint + design specs
├── .github/workflows/ci.yml
├── README.md
└── .gitignore
```

## Features by sprint

### Sprint A — Foundation
- **Auth**: login, refresh-token rotation, logout, /me, change-password, forgot/reset password, forgot username
- **RBAC**: 10 roles (super_admin, owner, gm, bm, om, fm, ca, ba, driver, conductor)
- **Branches, Users, Vehicles, Drivers, Conductors, Routes**: full CRUD with branch-scoping, soft delete, audit log

### Sprint B — Money Loop
- **Trips**: state machine `planned → boarding → departed → arrived → closed → cashed_up` (or `cancelled`); foreign-key validation; auto-totals from manifest
- **Manifest**: per-trip passenger + cargo entries, with payment status
- **Cash-ups**: conductor's daily reconciliation — declares cash, breakdown by payment method; **variance** = declared − expected; submit → approve → reject flow
- **Expenses**: fuel, tolls, maintenance, permits, meals, accommodation; scoped `on_trip` or `standalone`; trip totals recompute on changes

### Sprint C — Owner View
- **Fuel logs** + per-vehicle km/L efficiency analytics
- **Maintenance records**: scheduled/in-progress/completed/cancelled lifecycle; auto-flip vehicle status
- **Reports**: operations summary + daily timeline, branch performance, vehicle ROI & utilization, fuel summary, profit/loss, cash flow, driver performance, top routes, incident summary

### Phases 1–8 — Operations & fleet
- **Notifications inbox** backed by a live alerts engine (expiring documents & licences, due maintenance, low fuel) — scanned automatically every 5 minutes by a background worker
- **Push notifications**: device token registration against `/push/register`, unregistered on logout
- **Incidents**: report, acknowledge, resolve, category + summary
- **Inspections**: pre-trip checklists with templates, draft → submit lifecycle
- **Vehicle transfers**: cross-branch handover with confirm / return / cancel
- **QR**: generate + scan vehicle/driver QR codes for fast lookup
- **Live fleet map** + position reporting
- **Audit log** with actor roll-ups, **role-permission matrix** editor
- **Offline sync**: pull/push queue + status

### Sprint D — Record lifecycle, settlements & live board
- **Record lifecycle**: expense, fuel log and maintenance records each got a working create form, a detail screen with edit + delete, and a single-record read endpoint (`GET /expenses/{id}`, `GET /fuel-logs/{id}`, `GET /maintenance/{id}`)
- **Incident detail**: a full incident screen (timeline, acknowledgement, resolution) and API-driven categories — the category list now comes from `GET /incidents/categories` instead of a hard-coded array
- **Inspection templates**: `GET /inspections/template` drives the pre-trip checklist, so the items are editable on the server rather than frozen in the app
- **Device manager**: users register, name and revoke the push devices attached to their account
- **Branch-manager assignment**: a branch's manager is assignable from the branch screen
- **Audit actor filter**: the audit log filters by actor, driven by `GET /audit-log/actors`
- **Settlements**: a branch's financial close — revenue minus expenses, plus crew payroll per trip. `draft → submitted → approved → paid`, with `rejected` re-editable; approved and paid settlements are locked. Every headline figure is traceable to the per-trip lines it came from
- **Live trip board**: Server-Sent Events push trip changes to the board in real time, with an automatic polling fallback when the stream cannot be established

**Total: 147 API operations, 228 passing tests, 46 frontend screens.**

### Deep analysis pass — what static checks miss

The contract above is checked three ways in CI, because each layer
catches what the others cannot:

| Check | Lives in | Catches |
|---|---|---|
| Response envelope | `test_response_envelope.py` | an endpoint answering with a bare body while the frontend reads `getSingle` |
| Collection consistency | `test_collection_consistency.py` | one collection reached under two names; a queried collection with no index; an index on a field nothing writes |
| Runtime contract | `test_frontend_runtime_contract.py` | every frontend API call fired against the running app (mongomock) — a 404, 405, 401 or 500 fails the build |

That last one earned its keep. It fires all ~125 distinct frontend calls
with a seeded database and a real session token. Findings it produced:

- **Both PDF exports were broken.** `_fmt_date` formatted dates with
  `iso.replace("Z", "+00:00")` — correct for an ISO string, but Mongo
  returns native datetimes, where `.replace()` means
  `replace(year, month, ...)`. Every cash-up receipt and trip waybill
  returned a 500.
- **Maintenance records were invisible.** The router wrote to
  `db["maintenance"]` while the alerts engine scanned
  `db.maintenance_records` and the reports read
  `db["maintenance_records"]`. Maintenance-due notifications never fired,
  maintenance cost never reached the P&L, and every vehicle looked 100%
  utilised. No test had ever seeded either collection, so nothing
  noticed.
- **Eight hot collections had no index** — incidents, inspections,
  notifications, role_permissions, vehicle_documents, vehicle_transfers
  and more.

### Role design & operating model

`docs/ROLE_DESIGN.md` (and the rendered
`docs/TransitOS-Role-Design.pdf`) is the document that explains the
*design*: why there are ten roles, what each one is accountable for,
what it can and cannot see, and how the trips, manifests, cash-ups and
settlements combine into one view of the business.

It is generated from the same source of truth as the app — the
permission matrix, the role scopes and the screen map — and
`backend/app/tests/test_role_design_doc.py` fails the build if the
document and the code disagree.

Render it with the same pipeline as the other client documents:

```bash
python3 tools/docs/build_client_guide_pdf.py \
  --markdown docs/ROLE_DESIGN.md \
  --title "Role Design & Operating Model" \
  --eyebrow "SYSTEM DESIGN" \
  --header "ROLE DESIGN & OPERATING MODEL" \
  --footer "Role Design & Operating Model" \
  --pdf /workspace/output/TransitOS-Role-Design.pdf
```

### User manual

`docs/USER_MANUAL.md` — and the distributable
`docs/TransitOS-User-Manual.docx` — is the manual the client actually
reads. A general manual (signing in, the dashboard, navigation, your
profile, notifications, the interface) followed by **ten role manuals**,
one per role, each with the screens that role works in.

Every one of the **103 screenshots is a real capture of the shipped
front end**, driven through headless Chromium against a seeded demo
backend — not a hand-drawn mock-up. The app's own logo asset
(`frontend/assets/transitos-logo.png`, the same file as the app icon and
the splash screen) is the only branding used.

The capture harness lives in `docs/mockup/` and is reproducible:

```bash
# 1. a seeded in-memory backend on :8000
PYTHONPATH=/workspace/pylibs3 python3 docs/mockup/demo_server.py
# 2. the web build pointed at it (patches app.json, always restores it)
bash docs/mockup/build_web.sh http://127.0.0.1:8000
# 3. serve it
python3 docs/mockup/serve_dist.py frontend/dist 8080
# 4. photograph the screens
python3 docs/mockup/capture.py
# 5. rebuild the manual
python3 docs/build_user_manual.py && bash docs/build_manual.sh
```

Building the manual also surfaced **five real access defects** that a
green test suite had missed — the fleet manager was shown a Fuel screen
the API refused, the driver could not load the checklist they were given,
and a cash-up card showed the word "Conductor" instead of a name. They
are fixed, pinned by `backend/app/tests/test_role_access_regressions.py`,
and now caught automatically by `tools/contract/check.py`.

### Composite app testing manual

`docs/TESTING_MANUAL.md` — and the distributable
`docs/TransitOS-App-Testing-Manual.docx` — is the client-readiness
checklist. **436 numbered test items** across 12 parts, covering every
endpoint, every screen, every role boundary, every state transition,
the security posture and the non-functional behaviour.

| Part | Coverage |
|---|---|
| 1–3 | Deployment & health, authentication & account recovery, roles & branch scoping |
| 4 | Every one of the 147 API operations, with its allowed roles and required input |
| 5 | Exhaustive transition matrix for all 6 state machines — every legal move and every illegal one |
| 6 | All 45 screens, with the four checks each must pass |
| 7–9 | Cross-cutting data integrity, security, non-functional |
| 10 | The defects found during the analysis pass, with the guard that now prevents each |
| 11 | The automated CI guards that must be green |
| 12 | Client UAT scenarios and the sign-off sheet |

The manual is **generated from the codebase**, so it cannot drift:

```
python docs/build_testing_manual.py       # regenerate the Markdown
```

`test_testing_manual_coverage.py` fails the build if any endpoint or
screen is missing from it.

### Maintenance records and the alerts engine

The maintenance router and the alerts engine must agree on one
collection name. `test_maintenance_visibility.py` pins the behaviour —
a record due in five days raises a notification, a record due in 400
days does not, and completed maintenance shows up in the P&L and
reduces vehicle utilization.


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
| `ALERTS_SCAN_INTERVAL_SECONDS` | no (default `300`) | `0` disables the alerts worker |
| `EVENTS_POLL_INTERVAL_SECONDS` | no (default `5`) | how often the SSE broker checks for trip changes |

Railway already reads `railway.toml` from the repo root, so no UI changes
are needed — it points at the **root** `Dockerfile` (`backend/Dockerfile` is
kept as an identical copy for parity; do not point Railway at it, because
the build context is the repo root).

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
- `expo.extra.apiUrl`: the backend URL (API is mounted at root; no `/api/v1` prefix).
  `EXPO_PUBLIC_API_URL` overrides it per EAS build profile — see
  [`docs/PRE-BUILD-CHECKLIST.md`](docs/PRE-BUILD-CHECKLIST.md)

### Demo logins (after seed)

`python -m scripts.seed` creates one account for **each of the ten
roles** — the full table, and the one-command walkthrough, are in
[`docs/DEMO_ACCOUNTS.md`](docs/DEMO_ACCOUNTS.md).

| Email                    | Password                   | Role               |
|--------------------------|----------------------------|--------------------|
| admin@transitos.app      | `Admin#Transit2026!`       | super_admin        |
| owner@transitos.app      | `Owner#Transit2026!`       | owner              |
| gm@transitos.app         | `Gm#Transit2026!`          | general_manager    |
| bm.lagos@transitos.app   | `Bm#Transit2026!`          | branch_manager     |
| ops@transitos.app        | `Ops#Transit2026!`         | operations_manager |
| fm.lagos@transitos.app   | `Fm#Transit2026!`          | fleet_manager      |
| ca@transitos.app         | `Ca#Transit2026!`          | chief_accountant   |
| ba.lagos@transitos.app   | `Ba#Transit2026!`          | branch_accountant  |
| driver1@transitos.app    | `Driver#Transit2026!`      | driver             |
| conductor1@transitos.app | `Conductor#Transit2026!`   | conductor          |

### GitHub Codespace

One command bootstraps everything — Python check, venv, dependencies,
MongoDB in Docker, `backend/.env`, indexes and the demo accounts:

```bash
cd /workspaces/TransitOS
bash backend/scripts/setup_codespace.sh
```

It works in a **default** Codespace, so it does not matter when yours
was created. `.devcontainer/` additionally pre-warms *new* Codespaces
(Python 3.11, Node 20, MongoDB 7, the venv, the npm packages).

Then:

```bash
cd backend && ../.venv/bin/uvicorn app.main:app --reload --port 8000   # API
cd backend && ../.venv/bin/python -m scripts.seed                      # demo accounts
cd frontend && npx expo start                                        # app
```

Full walkthrough: [`docs/DEMO_ACCOUNTS.md`](docs/DEMO_ACCOUNTS.md).

## API surface (147 operations)

### Auth (8)
- `POST /auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/change-password`
- `POST /auth/forgot-password`, `/auth/reset-password`, `/auth/forgot-username`
- `GET  /auth/me`
- `GET  /healthz`

### Resources (CRUD)
- `/branches`, `/users`, `/vehicles`, `/drivers`, `/conductors`, `/routes`
- `/trips`, `/cash-ups`, `/expenses`, `/fuel-logs`, `/maintenance`
- `/incidents`, `/inspections`, `/vehicle-transfers`, `/notifications`, `/push`

### Sub-resources
- `POST /branches/{id}/manager`
- `GET/POST /trips/{id}/manifest`, `PATCH/DELETE /trips/{id}/manifest/{entry_id}`
- `GET/POST /vehicles/{id}/documents`, `PATCH/DELETE /vehicles/{id}/documents/{doc_id}`
- `GET  /vehicle-documents/expiring`
- `GET  /fleet/positions`

### Special actions
- `POST /cash-ups/{id}/submit`, `/approve`, `/reject`
- `GET  /cash-ups/{id}/pdf`, `GET /trips/{id}/waybill.pdf`
- `PATCH /trips/{id}/status`
- `POST /incidents/{id}/acknowledge`, `/resolve`
- `POST /inspections/{id}/submit`
- `POST /vehicle-transfers/{id}/confirm`, `/return`, `/cancel`
- `POST /notifications/{id}/mark-read`, `/mark-all-read`
- `POST /push/register`, `/push/unregister`
- `POST /alerts/scan`
- `GET  /fuel-logs/vehicle/{id}/efficiency`
- `GET  /maintenance/vehicle/{id}/upcoming`
- `GET  /qr/lookup`, `GET /qr/generate/{type}/{id}`

### Reports (11)
- `GET /reports/operations/summary`, `/operations/daily`
- `GET /reports/branches/performance`
- `GET /reports/vehicles/roi`, `/vehicles/utilization`
- `GET /reports/fuel/summary`, `/reports/incidents/summary`
- `GET /reports/financials/profit-loss`, `/financials/cash-flow`
- `GET /reports/drivers/performance`, `/reports/routes/top`

### Admin & platform
- `GET /dashboard/summary`, `GET /audit-log`, `/audit-log/actors`, `/audit-log/summary`
- `GET/PUT /role-permissions`, `/role-permissions/meta`, `/role-permissions/{role}/reset`, `/reset-all`
- `POST /sync/pull`, `/sync/push`, `GET /sync/status`
- `POST /admin/seed` (disabled unless `ADMIN_BOOTSTRAP_TOKEN` is set)

OpenAPI spec at `/openapi.json`, docs at `/docs` — both are **disabled in
staging/prod** (only `ENV=dev` exposes them).

## Deployment notes

### Railway (backend)

The `Dockerfile` at the **repo root** is the one Railway builds
(`railway.toml` → `builder = "DOCKERFILE"`, `dockerfilePath = "Dockerfile"`).
It installs `backend/requirements.txt` and starts `backend/start.sh`, which
resolves `$PORT` and `exec`s uvicorn so SIGTERM reaches it cleanly.

> **The requirements file must contain Python packages only.**
> `backend/scripts/check_requirements.py` (run in CI) fails the build if an
> npm/Expo package such as `expo-linear-gradient` ever appears there — pip
> cannot install those and the image build dies with
> `ERROR: Could not find a version that satisfies the requirement …`.
> Frontend dependencies belong in `frontend/package.json`.

### Mobile (frontend)

The Expo app is built with EAS (`frontend/eas.json`), not by Railway.
`npm ci` is strict about `frontend/package-lock.json` matching
`frontend/package.json` — CI verifies this with `npm ci --dry-run`.
Regenerate the lockfile with `./transitos-regen-lockfile.sh` after changing
dependencies.

The API URL the app talks to comes from `frontend/app.json` →
`expo.extra.apiUrl` (currently `https://transitos-production.up.railway.app`).

### Over-the-air updates

The app receives JavaScript and asset fixes over the air, so a bug fix
does not need a new APK and the crew does not reinstall anything.

```bash
# from the repository root — installs Node and the EAS CLI if missing,
# and checks you are signed in as the account that owns the project
bash backend/scripts/publish_update.sh preview    "What it fixes"
bash backend/scripts/publish_update.sh production "What it fixes"
```

The npm scripts (`cd frontend && npm run update:production`) do the
same thing if you already have Node and the EAS CLI.

`expo-updates` is installed, the update server and the runtime version
are configured, and the `preview` / `production` / `development` channels
are declared in `frontend/eas.json`. **One OTA-capable APK has to be
built and distributed first** — the update client is native code and
lives inside the APK. After that, JavaScript and asset fixes ship with
one command; native changes (a new permission, a new native package)
still need a new APK.

The full playbook — what can and cannot go over the air, how the runtime
version works, staged rollouts for the fleet, and how to roll back — is
in **[`docs/OTA_UPDATES.md`](docs/OTA_UPDATES.md)**.

`python tools/contract/check_updates.py` fails the build if the update
configuration is incoherent (wrong update URL, missing channel, two
profiles sharing a channel, disagreeing version numbers).


## What's next

Suggested follow-ups:
- Native barcode scanning for manifest entry
- Offline-first sync for the conductor app
- PWA web build for low-end Android devices

Settlements and the real-time trip board were Sprint D and are now built.
The remaining items were in the original blueprint but were deferred until
the core app was live.
