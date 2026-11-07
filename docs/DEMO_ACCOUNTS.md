# Demo accounts — every role, in one command

## Start here — one paste, works in any Codespace

```bash
cd /workspaces/TransitOS
bash backend/scripts/setup_codespace.sh
```

That single command does everything: checks Python, creates `.venv`,
installs the backend requirements, starts MongoDB, writes
`backend/.env`, creates the indexes, and **seeds a demo account for
every role**. It prints the logins when it finishes.

It works in a **default** Codespace — it does not need `.devcontainer/`,
so it does not matter when your Codespace was created. Safe to re-run.
If the Codespace has no Docker, the script downloads the official
MongoDB build and runs it directly; no Docker and no root needed.

---

## The database that matters is Railway's

**A MongoDB started on the Codespace is a throwaway.** It is where you
develop against — it is **not** the database the deployed app uses.

The app in the field reads and writes the database Railway hosts. So
when you want the demo accounts to appear in the deployed app, seed
*that* database:

### Option 1 — from inside the Railway service (recommended)

Railway dashboard → your API service → the **shell** tab, then:

```bash
cd /app && python -m scripts.seed
```

`MONGODB_URL` is already set inside the service, so this reaches the
real database with no connection string and no Docker. It prints the
logins when it finishes.

### Option 2 — over HTTP, from anywhere

```bash
curl -X POST https://<your-api>/admin/seed \
  -H "X-Admin-Token: <your ADMIN_BOOTSTRAP_TOKEN>"
```

This seeds the same accounts and the same demo data. It can only run
**once** — the endpoint locks itself after the first success — so unset
`ADMIN_BOOTSTRAP_TOKEN` in Railway afterwards.

Both paths create the same ten accounts, because they read the same
list (`backend/app/demo_accounts.py`). A test proves they cannot drift
apart.

### For local work only

```bash
cd backend && ../.venv/bin/python -m scripts.seed
```

That prints the logins and creates the demo branch, vehicle, route and
driver/conductor profiles. It is idempotent — run it as often as you
like.

> **Note on the `.devcontainer/` directory:** it makes *new* Codespaces
> come up pre-warmed (Python, Node, MongoDB, venv, npm packages). It
> only applies to Codespaces created **after** it was committed. The
> bootstrap script above is the path that works everywhere.

---

## The accounts

| Role | Email | Password | Name | Branch-scoped |
|---|---|---|---|---|
| `super_admin` | `admin@transitos.app` | `Admin#Transit2026!` | Platform Admin | — |
| `owner` | `owner@transitos.app` | `Owner#Transit2026!` | Company Owner | — |
| `general_manager` | `gm@transitos.app` | `Gm#Transit2026!` | General Manager | — |
| `branch_manager` | `bm.lagos@transitos.app` | `Bm#Transit2026!` | Lagos Branch Manager | yes |
| `operations_manager` | `ops@transitos.app` | `Ops#Transit2026!` | Operations Manager | — |
| `fleet_manager` | `fm.lagos@transitos.app` | `Fm#Transit2026!` | Lagos Fleet Manager | yes |
| `chief_accountant` | `ca@transitos.app` | `Ca#Transit2026!` | Chief Accountant | — |
| `branch_accountant` | `ba.lagos@transitos.app` | `Ba#Transit2026!` | Lagos Branch Accountant | yes |
| `driver` | `driver1@transitos.app` | `Driver#Transit2026!` | Adebayo Ogunlesi | yes |
| `conductor` | `conductor1@transitos.app` | `Conductor#Transit2026!` | Funke Adebayo | yes |

All ten roles the permission system knows about, one account each.
Branch-scoped roles are attached to **Lagos Main Branch**
(`LOS-01`), because the API refuses to create them without a branch.

> These passwords are for local development only. Change every one of
> them before any environment that is reachable from outside.

---

## Codespace commands

### 1 · Start the API

```bash
cd backend
../.venv/bin/uvicorn app.main:app --reload --port 8000
```

Check it: `curl http://localhost:8000/healthz`

If MongoDB is not running you get `{"status":"degraded","mongo":"down"}`
— start it with `docker run -d --name transitos-mongo -p 27017:27017 mongo:7`
or `sudo service mongodb start`.

### 2 · Seed the demo accounts

```bash
cd backend
../.venv/bin/python -m scripts.seed
```

Output:

```
========================================================================
SEED COMPLETE — demo logins (dev only — change every password):

  super_admin        admin@transitos.app          Admin#Transit2026!
  owner              owner@transitos.app          Owner#Transit2026!
  ...
========================================================================
```

### 3 · Log in as one

```bash
curl -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@transitos.app","password":"Admin#Transit2026!"}'
```

Returns `access_token` + `refresh_token`.

```bash
# use it
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer <access_token>"
```

### 4 · Start the app

```bash
cd frontend
npx expo start
```

- **Web:** press `w` → `http://localhost:8081`
- **Phone:** scan the QR code with Expo Go, or press `a` for an
  Android emulator. The dev server forwards port 8081 automatically.

The API base URL is resolved by `frontend/lib/api.ts` →
`resolveBaseURL()`:

1. `process.env.EXPO_PUBLIC_API_URL`
2. `app.json` → `expo.extra.apiUrl`
3. `http://localhost:8000`

In a Codespace, `localhost:8000` on **your laptop** is not the
Codespace's API. Use the forwarded URL instead:

1. Open the **PORTS** tab in the Codespace.
2. Find port **8000** → click the **globe** icon to make it public.
3. Copy the URL — it looks like
   `https://<codespace-name>-8000.app.github.dev`.

```bash
cd frontend
EXPO_PUBLIC_API_URL="https://<codespace-name>-8000.app.github.dev" npx expo start
```

Or build it from the environment:

```bash
echo "https://${CODESPACE_NAME}-8000.app.github.dev"
```

> The forwarded URL only works from a device that can reach
> `app.github.dev` — a phone on mobile data works, a phone on a
> corporate Wi-Fi often does not. On the same LAN, use the Codespace's
> IP with plain HTTP:
> `EXPO_PUBLIC_API_URL="http://$(hostname -I | awk '{print $1}'):8000"`

### 5 · Run the checks

```bash
cd backend && ../.venv/bin/python -m pytest -q          # 215 tests
cd backend && ../.venv/bin/python ../tools/contract/check.py   # 9 checks
cd frontend && npx tsc --noEmit                          # 0 errors
cd frontend && npx expo-doctor                           # 18/18
```

---

## Manual equivalent

If you would rather not run the script, `POST /admin/seed` bootstraps
three of the roles (super_admin, owner, general_manager) over HTTP.
It needs `ADMIN_BOOTSTRAP_TOKEN` set in the environment, it is
**one-shot**, and it must be unset afterwards:

```bash
cd backend
export ADMIN_BOOTSTRAP_TOKEN=$(openssl rand -hex 32)
../.venv/bin/uvicorn app.main:app --reload --port 8000 &

curl -X POST http://localhost:8000/admin/seed \
  -H "X-Admin-Token: $ADMIN_BOOTSTRAP_TOKEN"

unset ADMIN_BOOTSTRAP_TOKEN    # the endpoint is now permanently locked
```

`scripts/seed.py` is the better option for a demo: it is repeatable and
covers all ten roles.

---

## What the seed creates besides the users

| Collection | Contents |
|---|---|
| `branches` | Lagos Main Branch (`LOS-01`), Lagos |
| `vehicles` | `LSR-001-AA` — bus, 50 seats, 5000 kg, available, 100% fuel |
| `routes` | Lagos → Ibadan Express — 120 km, ₦2,500 passenger fare, 2.5 h |
| `drivers` | Adebayo Ogunlesi — licence `LAG-DR-0001`, expires 2030-12-31 |
| `conductors` | Funke Adebayo — badge `LAG-CD-0001` |

---

## Troubleshooting

**`MongoDB not running`** — the devcontainer feature starts it, but if
you are not in a Codespace:

```bash
sudo service mongodb start
# or, with Docker:
docker run -d --name transitos-mongo -p 27017:27017 mongo:7
```

**`/healthz` returns `{"status":"degraded","mongo":"down"}`** — the API
is up but Mongo is not. See above.

**Login returns 401** — the account was not seeded. Run
`python -m scripts.seed` and check the printed table.

**The app loads but every request fails** — `EXPO_PUBLIC_API_URL` is
pointing somewhere else. The API logs the resolved URL once on the
first request; check the Metro console.

**A screen is missing for your role** — the front end gates screens in
`frontend/lib/rbac.ts` (`SCREEN_ACCESS`) and the API gates the matching
routes with `require_roles(...)`. The two are kept in step by the
`rbac` check in `tools/contract/check.py`; if you hit a screen that
403s, that check is where it should be reported.
