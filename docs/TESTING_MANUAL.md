# TransitOS — Composite Application Testing Manual

**Release candidate:** Sprint D · 
**Surface under test:** 147 API operations · 46 mobile/web screens · 10 roles

> **Purpose.** This manual exists so that a single, complete pass can establish that TransitOS is fit for the client to use in production. Every screen, every endpoint, every role boundary and every state transition in the application is represented by at least one numbered test item below.

---

## 0. How to use this manual

### 0.1 The readiness rule

The application is **ready for client use** when:

1. Every **P0** and **P1** item in Parts 1–12 is marked **Pass**.
2. No **P0** or **P1** item is marked **Fail** or **Blocked**.
3. Every **P2** item is either Pass or has an agreed, documented deferral.
4. Every **P3** item is recorded (Pass / Fail / Deferred) with a rationale.
5. Part 12 (Client UAT sign-off) is complete and countersigned.

A **P0** failure is a release blocker. It means the client cannot perform a core task, or data is at risk of being lost or corrupted.

### 0.2 Severity

| Severity | Meaning | Release effect |
|---|---|---|
| **P0** | Core workflow broken; data loss or corruption possible | **Blocks release** |
| **P1** | Major feature broken or wrong; workaround exists but is impractical | **Blocks release** |
| **P2** | Minor defect; cosmetic or affects an edge case | Fix before release, or accept |
| **P3** | Observation / enhancement request | Record only |

### 0.3 How to record a result

For each item record:

- **Result** — `Pass` / `Fail` / `Blocked` / `N/A`
- **Tester** — initials
- **Date** — ISO date (`YYYY-MM-DD`)
- **Evidence** — screenshot, request/response capture, or defect reference
- **Notes** — only when the result is not `Pass`

### 0.4 Environments

| Environment | Base URL | Purpose |
|---|---|---|
| Local | `http://localhost:8000` | Functional pass, debugging |
| Staging | `https://<staging-host>` | Integration, performance, cross-browser |
| Production | `https://<prod-host>` | Smoke (Part 9) and client UAT (Part 12) |

Run the full manual against **staging**. Run Part 9 (non-functional, as a smoke check) and Part 12 (client UAT) against production.

### 0.5 Test data

Seed the staging database with `backend/scripts/seed.py` before starting. The seed creates one branch per operational role plus demo trips, vehicles and users. Record the seeded credentials in the test log — never in this manual.

---

## Part 1 — Deployment, configuration & health

**Objective:** prove the app installs, boots, connects to its database and serves traffic on a clean machine.

| # | Test | Severity | Expected result | Result |
|---|---|---|---|---|
| 1.1 | Clone the repository and install backend dependencies with `pip install -r backend/requirements.txt` | P0 | Install completes with no errors. `expo-linear-gradient` (an npm package) must NOT appear in this file — it breaks the Docker build. | ☐ |
| 1.2 | Run `python backend/scripts/check_requirements.py` | P0 | Prints `requirements OK` and exits 0. This guard is what stops the Railway build breaking again. | ☐ |
| 1.3 | Install frontend dependencies with `npm ci` in `frontend/` | P0 | Installs cleanly from the lockfile. No dependency resolution errors. | ☐ |
| 1.4 | Set the required environment variables: `MONGODB_URL`, `MONGODB_DB_NAME`, `JWT_SECRET_KEY`, `CORS_ORIGINS` | P0 | All four are set. A missing `JWT_SECRET_KEY` must fail fast, not silently use a default in production. | ☐ |
| 1.5 | Start the API with `uvicorn app.main:app` | P0 | Process starts, logs the resolved API base URL, and the index-creation loop reports `Mongo indexes ensured`. | ☐ |
| 1.6 | Call `GET /health` | P0 | HTTP 200 with a body reporting the database as reachable. | ☐ |
| 1.7 | Call `GET /` (service root) | P1 | HTTP 200 and a response that identifies the service and version. | ☐ |
| 1.8 | Call `GET /openapi.json` | P0 | HTTP 200 and a complete JSON schema. A 500 here means a response model references an undefined type — this broke the app once already. | ☐ |
| 1.9 | Call `GET /docs` and `GET /redoc` | P2 | HTTP 200 and the interactive API documentation renders. | ☐ |
| 1.10 | Confirm the background alerts worker starts and logs its first scan | P1 | A scan runs on the configured interval. Setting `ALERTS_SCAN_INTERVAL_SECONDS=0` must disable it cleanly. | ☐ |
| 1.11 | Build the frontend for web with `npx expo export --platform web` | P0 | Export completes and emits one HTML file per route. | ☐ |
| 1.12 | Typecheck the frontend with `npx tsc --noEmit` | P0 | Exits 0 with no errors. | ☐ |
| 1.13 | Deploy the Docker image and start the container | P1 | The container serves the API on the expected port and the health check passes. | ☐ |
| 1.14 | Confirm the Railway build completes end to end | P1 | The build succeeds and the deployment reports healthy. The original failure mode was an npm package inside `requirements.txt`. | ☐ |

---

## Part 2 — Authentication, session & account recovery

**Objective:** prove identity, session lifecycle and credential recovery all behave correctly and safely.

| # | Test | Severity | Expected result | Result |
|---|---|---|---|---|
| 2.1 | Log in with a valid email and password | P0 | HTTP 200. Response body is `{"data": {"access_token": ..., "refresh_token": ...}}` — the standard envelope. | ☐ |
| 2.2 | Log in with a wrong password | P0 | HTTP 401 with a generic message that does not reveal whether the email exists. | ☐ |
| 2.3 | Log in with an unknown email | P0 | HTTP 401 with the **same** message as 2.2. The two responses must be indistinguishable. | ☐ |
| 2.4 | Log in with an inactive or soft-deleted user | P0 | HTTP 401. A deactivated account must not be able to obtain a session. | ☐ |
| 2.5 | Call `GET /auth/me` with the access token | P0 | HTTP 200 returning the signed-in user's profile. The password hash and any reset token must be absent. | ☐ |
| 2.6 | Call any protected endpoint without a token | P0 | HTTP 401. | ☐ |
| 2.7 | Call any protected endpoint with a malformed or tampered token | P0 | HTTP 401, and the token is rejected rather than partially decoded. | ☐ |
| 2.8 | Refresh the token with `POST /auth/refresh` | P0 | HTTP 200 with a new access **and** refresh token. The old refresh token must be invalidated (rotation). | ☐ |
| 2.9 | Replay a refresh token that was already used | P0 | HTTP 401. Token reuse must be detected and the token family revoked. | ☐ |
| 2.10 | Log out with `POST /auth/logout` | P0 | HTTP 204 and the refresh token is revoked server-side, not merely discarded by the client. | ☐ |
| 2.11 | Request `POST /auth/forgot-password` for a known email | P0 | HTTP 202 and a reset email is sent. | ☐ |
| 2.12 | Request `POST /auth/forgot-password` for an unknown email | P0 | HTTP 202 with the **same** response. The endpoint must never confirm whether an account exists. | ☐ |
| 2.13 | Complete a password reset with a valid token | P0 | HTTP 204, the password changes, and the token is consumed so it cannot be replayed. | ☐ |
| 2.14 | Reset a password with an expired or already-used token | P0 | HTTP 400/401 and the password is unchanged. | ☐ |
| 2.15 | Request `POST /auth/forgot-username` | P0 | HTTP 202 and a username reminder is sent when the email is known; the response is identical either way. | ☐ |
| 2.16 | Change the password with `POST /auth/change-password` | P0 | HTTP 204. The old password stops working and the new one works. | ☐ |
| 2.17 | Attempt a password that violates the policy (too short, no digit, no symbol) | P1 | HTTP 422 with a message naming the rule broken. The frontend policy and the backend rule must agree. | ☐ |
| 2.18 | Change password using a wrong current password | P0 | HTTP 400/401 and the password is unchanged. | ☐ |
| 2.19 | Trigger the account lockout by repeated failed logins | P1 | The account locks after the configured threshold and a locked account returns 403 until the lock expires. | ☐ |
| 2.20 | Exceed the login rate limit | P2 | HTTP 429 with a retry hint. The limit is applied per IP and per email. | ☐ |
| 2.21 | Verify the access token expires | P1 | After `ACCESS_TOKEN_EXPIRE_MINUTES` the token is rejected with 401 and the client refreshes transparently. | ☐ |
| 2.22 | Verify an expired access token triggers a transparent refresh in the app | P1 | The request succeeds after refresh; the user sees no error and no re-login prompt. | ☐ |
| 2.23 | Sign out on the client and confirm the push token is unregistered | P1 | The device token is deactivated server-side so the device stops receiving another user's notifications. | ☐ |

---

## Part 3 — Roles, permissions & branch scoping

**Objective:** prove no user can reach anything beyond their role, and that one branch's data is invisible to another branch's team.

The ten roles are: `super_admin`, `owner`, `general_manager`, `branch_manager`, `operations_manager`, `fleet_manager`, `chief_accountant`, `branch_accountant`, `driver`, `conductor`.

| # | Test | Severity | Expected result | Result |
|---|---|---|---|---|
| 3.1 | Sign in as each of the ten roles in turn | P0 | Each role authenticates and lands on a dashboard appropriate to it. | ☐ |
| 3.2 | Compare the navigation menu across all ten roles | P0 | Each role sees only the sections its role permits. Crew roles see a crew app; finance roles see finance. No role sees a dead link. | ☐ |
| 3.3 | Open every screen visible to each role and confirm it loads without an error | P0 | No screen returns 403 or 500 for a role that is allowed to see it. A screen that 403s for an allowed role is a broken screen, not a clean denial. | ☐ |
| 3.4 | Directly request an endpoint that the role is not permitted to use | P0 | HTTP 403 with a clear message. The endpoint must refuse regardless of what the UI shows. | ☐ |
| 3.5 | As `branch_manager`, list trips, vehicles and users | P0 | Only records belonging to that manager's own branch are returned. | ☐ |
| 3.6 | As `branch_manager`, request a trip belonging to another branch by ID | P0 | HTTP 403 or 404. The record must not leak, and must not be distinguishable from one that does not exist. | ☐ |
| 3.7 | As `branch_accountant`, verify the same branch scoping applies | P0 | Scoping is consistent across every branch-scoped role. | ☐ |
| 3.8 | As `driver`, attempt to reach a role-management endpoint | P0 | HTTP 403. | ☐ |
| 3.9 | As a `branch_manager`, try to create a user with a more senior role | P0 | HTTP 403. The role-assignment hierarchy must refuse escalation. | ☐ |
| 3.10 | As `general_manager`, try to create a `super_admin` | P0 | HTTP 403 — no one below `super_admin` may mint a `super_admin`. | ☐ |
| 3.11 | As `super_admin`, create a user with every role | P1 | HTTP 201 for each role. The full role set must be assignable at the top tier. | ☐ |
| 3.12 | Open the role-permission matrix as `super_admin` | P1 | The matrix renders with every role and resource. | ☐ |
| 3.13 | Toggle a permission and confirm it takes effect on the next request | P1 | The change is persisted and the affected role's access changes immediately. | ☐ |
| 3.14 | Attempt to remove a mandatory base permission from `super_admin` | P1 | HTTP 400 with an explanatory message. The base grants must not be revocable. | ☐ |
| 3.15 | Reset a single role's permissions and reset all roles | P2 | Both succeed and the affected roles return to the defaults. | ☐ |
| 3.16 | Assign a branch manager who does not belong to that branch | P1 | HTTP 400. A branch manager must belong to the branch they manage. | ☐ |
| 3.17 | Clear a branch's manager | P2 | The manager is unset and the branch reports no manager. | ☐ |

---

## Part 4 — Endpoint catalogue & per-endpoint functional verification

**Objective:** verify every endpoint individually. This section is generated from the live OpenAPI schema, so it cannot omit a route.

For **every** endpoint below the tester must confirm all four of the following. The last column is the sign-off box for that endpoint.

1. **Status** — the response status matches the documented behaviour (200 / 201 / 204 for a success, 400 / 401 / 403 / 404 / 409 / 422 for a refusal, each of which is checked in Part 7).
2. **Body shape** — the payload matches the documented shape exactly, including the `data` / `items` envelope.
3. **Required inputs are enforced** — omitting a required field or query parameter is rejected, and an invalid value is rejected.
4. **Persistence** — a write is reflected in the relevant list view, in the audit log, and in any report that should include it.

Legend for **Roles** — *public* means no session is needed; *any signed-in role* means the endpoint only requires a valid session; a role list means only those roles may call it.

### 4.1 — Authentication

*8 endpoints*

| # | Endpoint | Method | Roles | Required input | Sev | Result |
|---|---|---|---|---|---|---|
| 1 | `/auth/change-password` | POST | any signed-in role | body: `current_password`, `new_password` | P0 | ☐ |
| 2 | `/auth/forgot-password` | POST | public — no session required | body: `email` | P0 | ☐ |
| 3 | `/auth/forgot-username` | POST | public — no session required | body: `email` | P0 | ☐ |
| 4 | `/auth/login` | POST | public — no session required | body: `email`, `password` | P0 | ☐ |
| 5 | `/auth/logout` | POST | any signed-in role | — | P0 | ☐ |
| 6 | `/auth/me` | GET | any signed-in role | — | P1 | ☐ |
| 7 | `/auth/refresh` | POST | public — no session required | — | P0 | ☐ |
| 8 | `/auth/reset-password` | POST | public — no session required | body: `token`, `new_password` | P0 | ☐ |

### 4.2 — Administration & seeding

*1 endpoint*

| # | Endpoint | Method | Roles | Required input | Sev | Result |
|---|---|---|---|---|---|---|
| 9 | `/admin/seed` | POST | **gated by the `ADMIN_BOOTSTRAP_TOKEN` env var, and permanently disabled once the bootstrap flag is set** | — | P0 | ☐ |

### 4.3 — Alerts engine

*1 endpoint*

| # | Endpoint | Method | Roles | Required input | Sev | Result |
|---|---|---|---|---|---|---|
| 10 | `/alerts/scan` | POST | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P0 | ☐ |

### 4.4 — Audit log

*3 endpoints*

| # | Endpoint | Method | Roles | Required input | Sev | Result |
|---|---|---|---|---|---|---|
| 11 | `/audit-log` | GET | `general_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 12 | `/audit-log/actors` | GET | `general_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 13 | `/audit-log/summary` | GET | `general_manager`, `owner`, `super_admin` | — | P1 | ☐ |

### 4.5 — Branches

*6 endpoints*

| # | Endpoint | Method | Roles | Required input | Sev | Result |
|---|---|---|---|---|---|---|
| 14 | `/branches` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 15 | `/branches` | POST | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | body: `name`, `code`, `city`, `state`, `address` | P0 | ☐ |
| 16 | `/branches/{branch_id}` | DELETE | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `branch_id`<br>path: `branch_id` | P0 | ☐ |
| 17 | `/branches/{branch_id}` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `branch_id`<br>path: `branch_id` | P1 | ☐ |
| 18 | `/branches/{branch_id}` | PATCH | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `branch_id`<br>path: `branch_id` | P0 | ☐ |
| 19 | `/branches/{branch_id}/manager` | POST | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `branch_id`<br>path: `branch_id` | P0 | ☐ |

### 4.6 — Cash-ups

*8 endpoints*

| # | Endpoint | Method | Roles | Required input | Sev | Result |
|---|---|---|---|---|---|---|
| 20 | `/cash-ups` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `general_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 21 | `/cash-ups` | POST | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `general_manager`, `owner`, `super_admin` | body: `trip_id`, `conductor_id`, `branch_id`, `declared_total` | P0 | ☐ |
| 22 | `/cash-ups/{cash_up_id}` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `general_manager`, `owner`, `super_admin` | query: `cash_up_id`<br>path: `cash_up_id` | P1 | ☐ |
| 23 | `/cash-ups/{cash_up_id}` | PATCH | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `general_manager`, `owner`, `super_admin` | query: `cash_up_id`<br>path: `cash_up_id` | P0 | ☐ |
| 24 | `/cash-ups/{cash_up_id}/approve` | POST | `branch_accountant`, `chief_accountant`, `general_manager`, `owner`, `super_admin` | query: `cash_up_id`<br>path: `cash_up_id` | P0 | ☐ |
| 25 | `/cash-ups/{cash_up_id}/pdf` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `general_manager`, `owner`, `super_admin` | query: `cash_up_id`<br>path: `cash_up_id` | P1 | ☐ |
| 26 | `/cash-ups/{cash_up_id}/reject` | POST | `branch_accountant`, `chief_accountant`, `general_manager`, `owner`, `super_admin` | query: `cash_up_id`, `reason`<br>path: `cash_up_id` | P0 | ☐ |
| 27 | `/cash-ups/{cash_up_id}/submit` | POST | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `general_manager`, `owner`, `super_admin` | query: `cash_up_id`<br>path: `cash_up_id` | P0 | ☐ |

### 4.7 — Conductors

*5 endpoints*

| # | Endpoint | Method | Roles | Required input | Sev | Result |
|---|---|---|---|---|---|---|
| 28 | `/conductors` | GET | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 29 | `/conductors` | POST | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | body: `user_id`, `badge_no` | P0 | ☐ |
| 30 | `/conductors/{conductor_id}` | DELETE | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `conductor_id`<br>path: `conductor_id` | P0 | ☐ |
| 31 | `/conductors/{conductor_id}` | GET | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `conductor_id`<br>path: `conductor_id` | P1 | ☐ |
| 32 | `/conductors/{conductor_id}` | PATCH | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `conductor_id`<br>path: `conductor_id` | P0 | ☐ |

### 4.8 — Dashboard

*1 endpoint*

| # | Endpoint | Method | Roles | Required input | Sev | Result |
|---|---|---|---|---|---|---|
| 33 | `/dashboard/summary` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P1 | ☐ |

### 4.9 — Drivers

*5 endpoints*

| # | Endpoint | Method | Roles | Required input | Sev | Result |
|---|---|---|---|---|---|---|
| 34 | `/drivers` | GET | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 35 | `/drivers` | POST | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | body: `user_id`, `license_no`, `license_expiry` | P0 | ☐ |
| 36 | `/drivers/{driver_id}` | DELETE | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `driver_id`<br>path: `driver_id` | P0 | ☐ |
| 37 | `/drivers/{driver_id}` | GET | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `driver_id`<br>path: `driver_id` | P1 | ☐ |
| 38 | `/drivers/{driver_id}` | PATCH | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `driver_id`<br>path: `driver_id` | P0 | ☐ |

### 4.10 — Realtime events (SSE)

*2 endpoints*

| # | Endpoint | Method | Roles | Required input | Sev | Result |
|---|---|---|---|---|---|---|
| 39 | `/events/status` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 40 | `/events/trips` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P1 | ☐ |

### 4.11 — Expenses

*5 endpoints*

| # | Endpoint | Method | Roles | Required input | Sev | Result |
|---|---|---|---|---|---|---|
| 41 | `/expenses` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `general_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 42 | `/expenses` | POST | `branch_accountant`, `branch_manager`, `chief_accountant`, `driver`, `general_manager`, `owner`, `super_admin` | body: `vehicle_id`, `branch_id`, `scope`, `category`, `amount`, `occurred_at` | P0 | ☐ |
| 43 | `/expenses/{expense_id}` | DELETE | `branch_accountant`, `branch_manager`, `chief_accountant`, `driver`, `general_manager`, `owner`, `super_admin` | query: `expense_id`<br>path: `expense_id` | P0 | ☐ |
| 44 | `/expenses/{expense_id}` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `general_manager`, `owner`, `super_admin` | query: `expense_id`<br>path: `expense_id` | P1 | ☐ |
| 45 | `/expenses/{expense_id}` | PATCH | `branch_accountant`, `branch_manager`, `chief_accountant`, `driver`, `general_manager`, `owner`, `super_admin` | query: `expense_id`<br>path: `expense_id` | P0 | ☐ |

### 4.12 — Fleet positions

*1 endpoint*

| # | Endpoint | Method | Roles | Required input | Sev | Result |
|---|---|---|---|---|---|---|
| 46 | `/fleet/positions` | GET | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P1 | ☐ |

### 4.13 — Fuel logs

*6 endpoints*

| # | Endpoint | Method | Roles | Required input | Sev | Result |
|---|---|---|---|---|---|---|
| 47 | `/fuel-logs` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 48 | `/fuel-logs` | POST | `branch_accountant`, `branch_manager`, `chief_accountant`, `driver`, `fleet_manager`, `general_manager`, `owner`, `super_admin` | body: `vehicle_id`, `branch_id`, `occurred_at`, `liters`, `cost_total`, `cost_per_liter`, `odometer_km` | P0 | ☐ |
| 49 | `/fuel-logs/vehicle/{vehicle_id}/efficiency` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `owner`, `super_admin` | query: `vehicle_id`<br>path: `vehicle_id` | P1 | ☐ |
| 50 | `/fuel-logs/{fuel_log_id}` | DELETE | `branch_accountant`, `branch_manager`, `chief_accountant`, `driver`, `fleet_manager`, `general_manager`, `owner`, `super_admin` | query: `fuel_log_id`<br>path: `fuel_log_id` | P0 | ☐ |
| 51 | `/fuel-logs/{fuel_log_id}` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `owner`, `super_admin` | query: `fuel_log_id`<br>path: `fuel_log_id` | P1 | ☐ |
| 52 | `/fuel-logs/{fuel_log_id}` | PATCH | `branch_accountant`, `branch_manager`, `chief_accountant`, `driver`, `fleet_manager`, `general_manager`, `owner`, `super_admin` | query: `fuel_log_id`<br>path: `fuel_log_id` | P0 | ☐ |

### 4.14 — Health

*1 endpoint*

| # | Endpoint | Method | Roles | Required input | Sev | Result |
|---|---|---|---|---|---|---|
| 53 | `/healthz` | GET | *(undetermined — verify manually)* | — | P1 | ☐ |

### 4.15 — Incidents

*7 endpoints*

| # | Endpoint | Method | Roles | Required input | Sev | Result |
|---|---|---|---|---|---|---|
| 54 | `/incidents` | GET | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 55 | `/incidents` | POST | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | body: `description` | P0 | ☐ |
| 56 | `/incidents/categories` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 57 | `/incidents/summary` | GET | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 58 | `/incidents/{incident_id}` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `incident_id`<br>path: `incident_id` | P1 | ☐ |
| 59 | `/incidents/{incident_id}/acknowledge` | POST | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `incident_id`<br>path: `incident_id` | P0 | ☐ |
| 60 | `/incidents/{incident_id}/resolve` | POST | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `incident_id`<br>path: `incident_id` | P0 | ☐ |

### 4.16 — Inspections

*6 endpoints*

| # | Endpoint | Method | Roles | Required input | Sev | Result |
|---|---|---|---|---|---|---|
| 61 | `/inspections` | GET | `branch_manager`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 62 | `/inspections` | POST | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | body: `trip_id` | P0 | ☐ |
| 63 | `/inspections/template` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 64 | `/inspections/{inspection_id}` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `inspection_id`<br>path: `inspection_id` | P1 | ☐ |
| 65 | `/inspections/{inspection_id}` | PUT | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `inspection_id`<br>body: `trip_id`<br>path: `inspection_id` | P0 | ☐ |
| 66 | `/inspections/{inspection_id}/submit` | POST | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `inspection_id`<br>path: `inspection_id` | P0 | ☐ |

### 4.17 — Maintenance records

*6 endpoints*

| # | Endpoint | Method | Roles | Required input | Sev | Result |
|---|---|---|---|---|---|---|
| 67 | `/maintenance` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 68 | `/maintenance` | POST | `branch_manager`, `fleet_manager`, `general_manager`, `owner`, `super_admin` | body: `vehicle_id`, `branch_id`, `type`, `title` | P0 | ☐ |
| 69 | `/maintenance/vehicle/{vehicle_id}/upcoming` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `owner`, `super_admin` | query: `vehicle_id`<br>path: `vehicle_id` | P1 | ☐ |
| 70 | `/maintenance/{record_id}` | DELETE | `branch_manager`, `fleet_manager`, `general_manager`, `owner`, `super_admin` | query: `record_id`<br>path: `record_id` | P0 | ☐ |
| 71 | `/maintenance/{record_id}` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `owner`, `super_admin` | query: `record_id`<br>path: `record_id` | P1 | ☐ |
| 72 | `/maintenance/{record_id}` | PATCH | `branch_manager`, `fleet_manager`, `general_manager`, `owner`, `super_admin` | query: `record_id`<br>path: `record_id` | P0 | ☐ |

### 4.18 — Notifications

*4 endpoints*

| # | Endpoint | Method | Roles | Required input | Sev | Result |
|---|---|---|---|---|---|---|
| 73 | `/notifications` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 74 | `/notifications/mark-all-read` | POST | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P0 | ☐ |
| 75 | `/notifications/unread-count` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 76 | `/notifications/{notification_id}/mark-read` | POST | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `notification_id`<br>path: `notification_id` | P0 | ☐ |

### 4.19 — Push devices

*3 endpoints*

| # | Endpoint | Method | Roles | Required input | Sev | Result |
|---|---|---|---|---|---|---|
| 77 | `/push` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 78 | `/push/register` | POST | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | body: `token` | P0 | ☐ |
| 79 | `/push/unregister` | POST | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | body: `token` | P0 | ☐ |

### 4.20 — QR codes

*2 endpoints*

| # | Endpoint | Method | Roles | Required input | Sev | Result |
|---|---|---|---|---|---|---|
| 80 | `/qr/generate/{entity_type}/{entity_id}` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `entity_type`, `entity_id`<br>path: `entity_type`, `entity_id` | P1 | ☐ |
| 81 | `/qr/lookup` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `token` | P1 | ☐ |

### 4.21 — Reports

*11 endpoints*

| # | Endpoint | Method | Roles | Required input | Sev | Result |
|---|---|---|---|---|---|---|
| 82 | `/reports/branches/performance` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 83 | `/reports/drivers/performance` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 84 | `/reports/financials/cash-flow` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 85 | `/reports/financials/profit-loss` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 86 | `/reports/fuel/summary` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 87 | `/reports/incidents/summary` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 88 | `/reports/operations/daily` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 89 | `/reports/operations/summary` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 90 | `/reports/routes/top` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 91 | `/reports/vehicles/roi` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 92 | `/reports/vehicles/utilization` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P1 | ☐ |

### 4.22 — Role permissions

*6 endpoints*

| # | Endpoint | Method | Roles | Required input | Sev | Result |
|---|---|---|---|---|---|---|
| 93 | `/role-permissions` | GET | `general_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 94 | `/role-permissions/meta` | GET | `general_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 95 | `/role-permissions/reset-all` | POST | `owner`, `super_admin` | — | P0 | ☐ |
| 96 | `/role-permissions/{role_name}` | GET | `general_manager`, `owner`, `super_admin` | query: `role_name`<br>path: `role_name` | P1 | ☐ |
| 97 | `/role-permissions/{role_name}` | PUT | `general_manager`, `owner`, `super_admin` | query: `role_name`<br>body: `permissions`<br>path: `role_name` | P0 | ☐ |
| 98 | `/role-permissions/{role_name}/reset` | POST | `general_manager`, `owner`, `super_admin` | query: `role_name`<br>path: `role_name` | P0 | ☐ |

### 4.23 — Routes

*5 endpoints*

| # | Endpoint | Method | Roles | Required input | Sev | Result |
|---|---|---|---|---|---|---|
| 99 | `/routes` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 100 | `/routes` | POST | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | body: `name`, `branch_id`, `type`, `origin_branch_id`, `destination_branch_id`, `origin_city`, `destination_city`, `distance_km`, `base_fare_passenger`, `base_fare_cargo_per_kg`, `estimated_duration_hours` | P0 | ☐ |
| 101 | `/routes/{route_id}` | DELETE | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `route_id`<br>path: `route_id` | P0 | ☐ |
| 102 | `/routes/{route_id}` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `route_id`<br>path: `route_id` | P1 | ☐ |
| 103 | `/routes/{route_id}` | PATCH | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `route_id`<br>path: `route_id` | P0 | ☐ |

### 4.24 — Settlements

*9 endpoints*

| # | Endpoint | Method | Roles | Required input | Sev | Result |
|---|---|---|---|---|---|---|
| 104 | `/settlements` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `general_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 105 | `/settlements/generate` | POST | `branch_accountant`, `chief_accountant`, `general_manager`, `owner`, `super_admin` | body: `branch_id`, `period_start`, `period_end` | P0 | ☐ |
| 106 | `/settlements/summary` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `general_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 107 | `/settlements/{settlement_id}` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `general_manager`, `owner`, `super_admin` | query: `settlement_id`<br>path: `settlement_id` | P1 | ☐ |
| 108 | `/settlements/{settlement_id}` | PATCH | `branch_accountant`, `chief_accountant`, `general_manager`, `owner`, `super_admin` | query: `settlement_id`<br>path: `settlement_id` | P0 | ☐ |
| 109 | `/settlements/{settlement_id}/approve` | POST | `chief_accountant`, `general_manager`, `owner`, `super_admin` | query: `settlement_id`<br>path: `settlement_id` | P0 | ☐ |
| 110 | `/settlements/{settlement_id}/pay` | POST | `chief_accountant`, `general_manager`, `owner`, `super_admin` | query: `settlement_id`<br>path: `settlement_id` | P0 | ☐ |
| 111 | `/settlements/{settlement_id}/reject` | POST | `chief_accountant`, `general_manager`, `owner`, `super_admin` | query: `settlement_id`<br>path: `settlement_id` | P0 | ☐ |
| 112 | `/settlements/{settlement_id}/submit` | POST | `branch_accountant`, `chief_accountant`, `general_manager`, `owner`, `super_admin` | query: `settlement_id`<br>path: `settlement_id` | P0 | ☐ |

### 4.25 — Offline sync

*3 endpoints*

| # | Endpoint | Method | Roles | Required input | Sev | Result |
|---|---|---|---|---|---|---|
| 113 | `/sync/pull` | POST | any signed-in role | — | P0 | ☐ |
| 114 | `/sync/push` | POST | any signed-in role | — | P0 | ☐ |
| 115 | `/sync/status` | GET | public — no session required | — | P1 | ☐ |

### 4.26 — Trips & manifest

*11 endpoints*

| # | Endpoint | Method | Roles | Required input | Sev | Result |
|---|---|---|---|---|---|---|
| 116 | `/trips` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 117 | `/trips` | POST | `branch_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | body: `route_id`, `vehicle_id`, `driver_id`, `conductor_id`, `scheduled_departure`, `scheduled_arrival` | P0 | ☐ |
| 118 | `/trips/{trip_id}` | DELETE | `branch_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `trip_id`<br>path: `trip_id` | P0 | ☐ |
| 119 | `/trips/{trip_id}` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `trip_id`<br>path: `trip_id` | P1 | ☐ |
| 120 | `/trips/{trip_id}` | PATCH | `branch_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `trip_id`<br>path: `trip_id` | P0 | ☐ |
| 121 | `/trips/{trip_id}/manifest` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `trip_id`<br>path: `trip_id` | P1 | ☐ |
| 122 | `/trips/{trip_id}/manifest` | POST | `branch_manager`, `conductor`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `trip_id`<br>body: `trip_id`, `type`, `fare`<br>path: `trip_id` | P0 | ☐ |
| 123 | `/trips/{trip_id}/manifest/{entry_id}` | DELETE | `branch_manager`, `conductor`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `trip_id`, `entry_id`<br>path: `trip_id`, `entry_id` | P0 | ☐ |
| 124 | `/trips/{trip_id}/manifest/{entry_id}` | PATCH | `branch_manager`, `conductor`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `trip_id`, `entry_id`<br>path: `trip_id`, `entry_id` | P0 | ☐ |
| 125 | `/trips/{trip_id}/status` | PATCH | `branch_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `trip_id`<br>body: `status`<br>path: `trip_id` | P0 | ☐ |
| 126 | `/trips/{trip_id}/waybill.pdf` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `trip_id`<br>path: `trip_id` | P1 | ☐ |

### 4.27 — Users

*5 endpoints*

| # | Endpoint | Method | Roles | Required input | Sev | Result |
|---|---|---|---|---|---|---|
| 127 | `/users` | GET | `branch_accountant`, `branch_manager`, `general_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 128 | `/users` | POST | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | body: `email`, `full_name`, `role`, `password` | P0 | ☐ |
| 129 | `/users/{user_id}` | DELETE | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `user_id`<br>path: `user_id` | P0 | ☐ |
| 130 | `/users/{user_id}` | GET | `branch_accountant`, `branch_manager`, `general_manager`, `owner`, `super_admin` | query: `user_id`<br>path: `user_id` | P1 | ☐ |
| 131 | `/users/{user_id}` | PATCH | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `user_id`<br>path: `user_id` | P0 | ☐ |

### 4.28 — Vehicle documents

*5 endpoints*

| # | Endpoint | Method | Roles | Required input | Sev | Result |
|---|---|---|---|---|---|---|
| 132 | `/vehicle-documents/expiring` | GET | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 133 | `/vehicles/{vehicle_id}/documents` | GET | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `vehicle_id`<br>path: `vehicle_id` | P1 | ☐ |
| 134 | `/vehicles/{vehicle_id}/documents` | POST | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `vehicle_id`<br>body: `doc_type`, `ref_number`, `expires_at`<br>path: `vehicle_id` | P0 | ☐ |
| 135 | `/vehicles/{vehicle_id}/documents/{doc_id}` | DELETE | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `vehicle_id`, `doc_id`<br>path: `vehicle_id`, `doc_id` | P0 | ☐ |
| 136 | `/vehicles/{vehicle_id}/documents/{doc_id}` | PATCH | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `vehicle_id`, `doc_id`<br>path: `vehicle_id`, `doc_id` | P0 | ☐ |

### 4.29 — Vehicle transfers

*6 endpoints*

| # | Endpoint | Method | Roles | Required input | Sev | Result |
|---|---|---|---|---|---|---|
| 137 | `/vehicle-transfers` | GET | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 138 | `/vehicle-transfers` | POST | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | body: `vehicle_id`, `to_branch_id` | P0 | ☐ |
| 139 | `/vehicle-transfers/{transfer_id}` | GET | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `transfer_id`<br>path: `transfer_id` | P1 | ☐ |
| 140 | `/vehicle-transfers/{transfer_id}/cancel` | POST | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `transfer_id`<br>path: `transfer_id` | P0 | ☐ |
| 141 | `/vehicle-transfers/{transfer_id}/confirm` | POST | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `transfer_id`<br>path: `transfer_id` | P0 | ☐ |
| 142 | `/vehicle-transfers/{transfer_id}/return` | POST | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `transfer_id`<br>path: `transfer_id` | P0 | ☐ |

### 4.30 — Vehicles

*5 endpoints*

| # | Endpoint | Method | Roles | Required input | Sev | Result |
|---|---|---|---|---|---|---|
| 143 | `/vehicles` | GET | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | — | P1 | ☐ |
| 144 | `/vehicles` | POST | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | body: `reg_number`, `type`, `capacity_seats`, `capacity_kg`, `branch_id` | P0 | ☐ |
| 145 | `/vehicles/{vehicle_id}` | DELETE | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `vehicle_id`<br>path: `vehicle_id` | P0 | ☐ |
| 146 | `/vehicles/{vehicle_id}` | GET | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `vehicle_id`<br>path: `vehicle_id` | P1 | ☐ |
| 147 | `/vehicles/{vehicle_id}` | PATCH | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` | query: `vehicle_id`<br>path: `vehicle_id` | P0 | ☐ |

---

## Part 5 — State machine verification

**Objective:** prove that every legal transition works and every illegal one is refused. An illegal transition must return **HTTP 409** with a message naming the current and target states, and must leave the record unchanged.

### Trip

A trip's lifecycle. Illegal transitions must return HTTP 409.

| From | To | Legal? | Expected | Result |
|---|---|---|---|---|
| `planned` | `planned` | no-op | HTTP 200 — re-selecting the same state is idempotent | ☐ |
| `planned` | `boarding` | yes | HTTP 200 and the state changes | ☐ |
| `planned` | `departed` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `planned` | `arrived` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `planned` | `closed` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `planned` | `cashed_up` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `planned` | `cancelled` | yes | HTTP 200 and the state changes | ☐ |
| `boarding` | `planned` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `boarding` | `boarding` | no-op | HTTP 200 — re-selecting the same state is idempotent | ☐ |
| `boarding` | `departed` | yes | HTTP 200 and the state changes | ☐ |
| `boarding` | `arrived` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `boarding` | `closed` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `boarding` | `cashed_up` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `boarding` | `cancelled` | yes | HTTP 200 and the state changes | ☐ |
| `departed` | `planned` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `departed` | `boarding` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `departed` | `departed` | no-op | HTTP 200 — re-selecting the same state is idempotent | ☐ |
| `departed` | `arrived` | yes | HTTP 200 and the state changes | ☐ |
| `departed` | `closed` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `departed` | `cashed_up` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `departed` | `cancelled` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `arrived` | `planned` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `arrived` | `boarding` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `arrived` | `departed` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `arrived` | `arrived` | no-op | HTTP 200 — re-selecting the same state is idempotent | ☐ |
| `arrived` | `closed` | yes | HTTP 200 and the state changes | ☐ |
| `arrived` | `cashed_up` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `arrived` | `cancelled` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `closed` | `planned` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `closed` | `boarding` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `closed` | `departed` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `closed` | `arrived` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `closed` | `closed` | no-op | HTTP 200 — re-selecting the same state is idempotent | ☐ |
| `closed` | `cashed_up` | yes | HTTP 200 and the state changes | ☐ |
| `closed` | `cancelled` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `cashed_up` | `planned` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `cashed_up` | `boarding` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `cashed_up` | `departed` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `cashed_up` | `arrived` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `cashed_up` | `closed` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `cashed_up` | `cashed_up` | no-op | HTTP 200 — re-selecting the same state is idempotent | ☐ |
| `cashed_up` | `cancelled` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `cancelled` | `planned` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `cancelled` | `boarding` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `cancelled` | `departed` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `cancelled` | `arrived` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `cancelled` | `closed` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `cancelled` | `cashed_up` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `cancelled` | `cancelled` | no-op | HTTP 200 — re-selecting the same state is idempotent | ☐ |

Terminal states: `cashed_up`, `cancelled`. No transition may leave a terminal state.

### Cash-up

A conductor's daily reconciliation. Only a 'closed' trip can be cashed up.

| From | To | Legal? | Expected | Result |
|---|---|---|---|---|
| `draft` | `draft` | no-op | HTTP 200 — re-selecting the same state is idempotent | ☐ |
| `draft` | `submitted` | yes | HTTP 200 and the state changes | ☐ |
| `draft` | `approved` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `draft` | `rejected` | yes | HTTP 200 and the state changes | ☐ |
| `submitted` | `draft` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `submitted` | `submitted` | no-op | HTTP 200 — re-selecting the same state is idempotent | ☐ |
| `submitted` | `approved` | yes | HTTP 200 and the state changes | ☐ |
| `submitted` | `rejected` | yes | HTTP 200 and the state changes | ☐ |
| `approved` | `draft` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `approved` | `submitted` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `approved` | `approved` | no-op | HTTP 200 — re-selecting the same state is idempotent | ☐ |
| `approved` | `rejected` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `rejected` | `draft` | yes | HTTP 200 and the state changes | ☐ |
| `rejected` | `submitted` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `rejected` | `approved` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `rejected` | `rejected` | no-op | HTTP 200 — re-selecting the same state is idempotent | ☐ |

Terminal states: `approved`. No transition may leave a terminal state.

### Inspection

A pre-trip checklist. Once submitted it is locked (HTTP 409 on further edits).

| From | To | Legal? | Expected | Result |
|---|---|---|---|---|
| `draft` | `draft` | no-op | HTTP 200 — re-selecting the same state is idempotent | ☐ |
| `draft` | `submitted` | yes | HTTP 200 and the state changes | ☐ |
| `submitted` | `draft` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `submitted` | `submitted` | no-op | HTTP 200 — re-selecting the same state is idempotent | ☐ |

Terminal states: `submitted`. No transition may leave a terminal state.

### Vehicle transfer

A vehicle moving between branches.

| From | To | Legal? | Expected | Result |
|---|---|---|---|---|
| `initiated` | `initiated` | no-op | HTTP 200 — re-selecting the same state is idempotent | ☐ |
| `initiated` | `confirmed` | yes | HTTP 200 and the state changes | ☐ |
| `initiated` | `returned` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `initiated` | `cancelled` | yes | HTTP 200 and the state changes | ☐ |
| `confirmed` | `initiated` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `confirmed` | `confirmed` | no-op | HTTP 200 — re-selecting the same state is idempotent | ☐ |
| `confirmed` | `returned` | yes | HTTP 200 and the state changes | ☐ |
| `confirmed` | `cancelled` | yes | HTTP 200 and the state changes | ☐ |
| `returned` | `initiated` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `returned` | `confirmed` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `returned` | `returned` | no-op | HTTP 200 — re-selecting the same state is idempotent | ☐ |
| `returned` | `cancelled` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `cancelled` | `initiated` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `cancelled` | `confirmed` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `cancelled` | `returned` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `cancelled` | `cancelled` | no-op | HTTP 200 — re-selecting the same state is idempotent | ☐ |

Terminal states: `returned`, `cancelled`. No transition may leave a terminal state.

### Settlement

A branch's financial close. Approved and paid settlements are locked (HTTP 409).

| From | To | Legal? | Expected | Result |
|---|---|---|---|---|
| `draft` | `draft` | no-op | HTTP 200 — re-selecting the same state is idempotent | ☐ |
| `draft` | `submitted` | yes | HTTP 200 and the state changes | ☐ |
| `draft` | `approved` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `draft` | `paid` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `draft` | `rejected` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `submitted` | `draft` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `submitted` | `submitted` | no-op | HTTP 200 — re-selecting the same state is idempotent | ☐ |
| `submitted` | `approved` | yes | HTTP 200 and the state changes | ☐ |
| `submitted` | `paid` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `submitted` | `rejected` | yes | HTTP 200 and the state changes | ☐ |
| `approved` | `draft` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `approved` | `submitted` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `approved` | `approved` | no-op | HTTP 200 — re-selecting the same state is idempotent | ☐ |
| `approved` | `paid` | yes | HTTP 200 and the state changes | ☐ |
| `approved` | `rejected` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `paid` | `draft` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `paid` | `submitted` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `paid` | `approved` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `paid` | `paid` | no-op | HTTP 200 — re-selecting the same state is idempotent | ☐ |
| `paid` | `rejected` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `rejected` | `draft` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `rejected` | `submitted` | yes | HTTP 200 and the state changes | ☐ |
| `rejected` | `approved` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `rejected` | `paid` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `rejected` | `rejected` | no-op | HTTP 200 — re-selecting the same state is idempotent | ☐ |

Terminal states: `paid`. No transition may leave a terminal state.

### Maintenance record

A maintenance job. Completing one flips the vehicle status.

| From | To | Legal? | Expected | Result |
|---|---|---|---|---|
| `scheduled` | `scheduled` | no-op | HTTP 200 — re-selecting the same state is idempotent | ☐ |
| `scheduled` | `in_progress` | yes | HTTP 200 and the state changes | ☐ |
| `scheduled` | `completed` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `scheduled` | `cancelled` | yes | HTTP 200 and the state changes | ☐ |
| `in_progress` | `scheduled` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `in_progress` | `in_progress` | no-op | HTTP 200 — re-selecting the same state is idempotent | ☐ |
| `in_progress` | `completed` | yes | HTTP 200 and the state changes | ☐ |
| `in_progress` | `cancelled` | yes | HTTP 200 and the state changes | ☐ |
| `completed` | `scheduled` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `completed` | `in_progress` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `completed` | `completed` | no-op | HTTP 200 — re-selecting the same state is idempotent | ☐ |
| `completed` | `cancelled` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `cancelled` | `scheduled` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `cancelled` | `in_progress` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `cancelled` | `completed` | **no** | **HTTP 409** — refused, record unchanged | ☐ |
| `cancelled` | `cancelled` | no-op | HTTP 200 — re-selecting the same state is idempotent | ☐ |

Terminal states: `completed`, `cancelled`. No transition may leave a terminal state.

---

## Part 6 — Screen-by-screen UI verification

**Objective:** confirm every screen renders, loads its data, and handles the empty and error states. Generated from the expo-router route tree.

For **every** screen the tester must confirm all four of the following.

1. **Renders with data** — the screen loads its data from the API and shows it.
2. **Empty state** — with no records, the screen shows a helpful empty state rather than a blank page or an error.
3. **Error state** — with the API failing, the screen shows a readable error and does not crash.
4. **Refresh** — pull-to-refresh (or the reload control) updates the data.

| # | Screen | Route | Source file | Result |
|---|---|---|---|---|
| 1.148 | Index | `/index` | `frontend/app/index.tsx` | ☐ |
| 2.148 | Index | `/` | `frontend/app/(app)/index.tsx` | ☐ |
| 3.148 | Audit Log | `/audit-log` | `frontend/app/(app)/audit-log.tsx` | ☐ |
| 4.148 | Index | `/branches` | `frontend/app/(app)/branches/index.tsx` | ☐ |
| 5.148 | Id | `/branches/[id]` | `frontend/app/(app)/branches/[id].tsx` | ☐ |
| 6.148 | Cash Ups | `/cash-ups` | `frontend/app/(app)/cash-ups.tsx` | ☐ |
| 7.148 | Index | `/conductors` | `frontend/app/(app)/conductors/index.tsx` | ☐ |
| 8.148 | Id | `/conductors/[id]` | `frontend/app/(app)/conductors/[id].tsx` | ☐ |
| 9.148 | Devices | `/devices` | `frontend/app/(app)/devices.tsx` | ☐ |
| 10.148 | Index | `/drivers` | `frontend/app/(app)/drivers/index.tsx` | ☐ |
| 11.148 | Id | `/drivers/[id]` | `frontend/app/(app)/drivers/[id].tsx` | ☐ |
| 12.148 | Expenses | `/expenses` | `frontend/app/(app)/expenses.tsx` | ☐ |
| 13.148 | Id | `/expenses/[id]` | `frontend/app/(app)/expenses/[id].tsx` | ☐ |
| 14.148 | Fuel | `/fuel` | `frontend/app/(app)/fuel.tsx` | ☐ |
| 15.148 | Id | `/fuel/[id]` | `frontend/app/(app)/fuel/[id].tsx` | ☐ |
| 16.148 | Incidents | `/incidents` | `frontend/app/(app)/incidents.tsx` | ☐ |
| 17.148 | Id | `/incidents/[id]` | `frontend/app/(app)/incidents/[id].tsx` | ☐ |
| 18.148 | Maintenance | `/maintenance` | `frontend/app/(app)/maintenance.tsx` | ☐ |
| 19.148 | Id | `/maintenance/[id]` | `frontend/app/(app)/maintenance/[id].tsx` | ☐ |
| 20.148 | Map | `/map` | `frontend/app/(app)/map.tsx` | ☐ |
| 21.148 | More | `/more` | `frontend/app/(app)/more.tsx` | ☐ |
| 22.148 | Notifications | `/notifications` | `frontend/app/(app)/notifications.tsx` | ☐ |
| 23.148 | Pre Trip Checklist | `/pre-trip-checklist` | `frontend/app/(app)/pre-trip-checklist.tsx` | ☐ |
| 24.148 | Profile | `/profile` | `frontend/app/(app)/profile.tsx` | ☐ |
| 25.148 | Report Incident | `/report-incident` | `frontend/app/(app)/report-incident.tsx` | ☐ |
| 26.148 | Reports | `/reports` | `frontend/app/(app)/reports.tsx` | ☐ |
| 27.148 | Role Permissions | `/role-permissions` | `frontend/app/(app)/role-permissions.tsx` | ☐ |
| 28.148 | Index | `/routes` | `frontend/app/(app)/routes/index.tsx` | ☐ |
| 29.148 | Id | `/routes/[id]` | `frontend/app/(app)/routes/[id].tsx` | ☐ |
| 30.148 | Scan | `/scan` | `frontend/app/(app)/scan.tsx` | ☐ |
| 31.148 | Index | `/settlements` | `frontend/app/(app)/settlements/index.tsx` | ☐ |
| 32.148 | Id | `/settlements/[id]` | `frontend/app/(app)/settlements/[id].tsx` | ☐ |
| 33.148 | Sync | `/sync` | `frontend/app/(app)/sync.tsx` | ☐ |
| 34.148 | Index | `/transfers` | `frontend/app/(app)/transfers/index.tsx` | ☐ |
| 35.148 | Id | `/transfers/[id]` | `frontend/app/(app)/transfers/[id].tsx` | ☐ |
| 36.148 | Index | `/trips` | `frontend/app/(app)/trips/index.tsx` | ☐ |
| 37.148 | Id | `/trips/[id]` | `frontend/app/(app)/trips/[id].tsx` | ☐ |
| 38.148 | Live | `/trips/live` | `frontend/app/(app)/trips/live.tsx` | ☐ |
| 39.148 | Index | `/users` | `frontend/app/(app)/users/index.tsx` | ☐ |
| 40.148 | Id | `/users/[id]` | `frontend/app/(app)/users/[id].tsx` | ☐ |
| 41.148 | Index | `/vehicles` | `frontend/app/(app)/vehicles/index.tsx` | ☐ |
| 42.148 | Id | `/vehicles/[id]` | `frontend/app/(app)/vehicles/[id].tsx` | ☐ |
| 43.148 | Forgot Password | `/forgot-password` | `frontend/app/(auth)/forgot-password.tsx` | ☐ |
| 44.148 | Forgot Username | `/forgot-username` | `frontend/app/(auth)/forgot-username.tsx` | ☐ |
| 45.148 | Login | `/login` | `frontend/app/(auth)/login.tsx` | ☐ |
| 46.148 | Reset Password | `/reset-password` | `frontend/app/(auth)/reset-password.tsx` | ☐ |

## Part 7 — Cross-cutting behaviour & data integrity

| # | Test | Severity | Expected result | Result |
|---|---|---|---|---|
| 7.1 | Every list endpoint returns the standard envelope | P0 | `{"items": [...], "total": n, "page": p, "totalPages": t, "hasMore": b}`. Every single-item endpoint returns `{"data": {...}}`. | ☐ |
| 7.2 | No endpoint returns a bare body | P0 | The frontend reads single records with `getSingle` (which unwraps `.data.data`). A bare body silently renders as `undefined` rather than erroring. | ☐ |
| 7.3 | Pagination is honoured everywhere | P1 | `page` and `page_size` are respected; `total` reflects the full filtered count; requesting a page past the end returns an empty `items`, not an error. | ☐ |
| 7.4 | Search and filter parameters work on every list endpoint | P1 | Filtering by the documented query parameters narrows the result set as specified. | ☐ |
| 7.5 | Deleting a record is a soft delete | P0 | The record disappears from lists but its data is retained for audit and reporting. | ☐ |
| 7.6 | Every create, update, delete and status change writes an audit entry | P0 | The audit log shows the action, the actor, the timestamp and a before/after snapshot. | ☐ |
| 7.7 | Timestamps are stored and returned in UTC | P1 | `created_at` / `updated_at` are timezone-aware and serialise consistently. | ☐ |
| 7.8 | Every collection the app queries has an index | P1 | Checked by `test_collection_consistency.py`. A missing index turns a list view into a full collection scan. | ☐ |
| 7.9 | Every collection is reached under exactly one name | P0 | Checked by `test_collection_consistency.py`. A split name means a reader silently sees an empty collection — this broke maintenance records. | ☐ |
| 7.10 | Trip totals recompute when the manifest changes | P0 | Adding, editing or removing a manifest entry updates passenger count, cargo weight and total revenue. | ☐ |
| 7.11 | Expenses scoped `on_trip` roll into the trip totals | P0 | A trip's total expenses reflect its own expenses plus its fuel and maintenance costs. | ☐ |
| 7.12 | Branch scoping holds for every list and detail endpoint | P0 | A branch-scoped role sees only its own branch's records, on every endpoint, not just the obvious ones. | ☐ |
| 7.13 | Concurrent edits do not corrupt records | P2 | Two simultaneous edits leave the record in one consistent state, not a merge of two conflicting writes. | ☐ |
| 7.14 | The API returns a consistent error envelope | P1 | Errors carry a machine-readable `detail` and the frontend surfaces a readable message. | ☐ |
| 7.15 | **The money loop runs end to end in the app** | P0 | On a trip: *Start boarding* → *Confirm departure* → *Confirm arrival* → *Close trip*. Add a passenger to the manifest, count the cash, *Save cash-up*, *Submit for approval*, then approve it in **More → Cash Ups**. The trip ends as `cashed_up`. No step needs the command line. | ☐ |
| 7.16 | The trip status card offers only the legal next stage | P0 | The button matches the state machine: *Planned* offers boarding, *Boarding* offers departure, *Departed* offers arrival, *Arrived* offers close. Nothing else is offered. | ☐ |
| 7.17 | A cancellation asks for a reason and keeps it | P0 | *Cancel trip* refuses to proceed without a reason; the reason is shown on the trip and appears in the audit log. | ☐ |
| 7.18 | The manifest locks when the trip departs | P0 | After *Confirm departure*, *+ Passenger* and *+ Cargo* are gone and the bin icon is gone. The server refuses a late addition with HTTP 409. | ☐ |
| 7.19 | Removing a manifest entry changes the expected figure | P0 | Remove an entry: the trip's revenue drops, and the cash-up's expected total drops by the same amount. A removed fare must not count towards the expected total. | ☐ |
| 7.20 | A cash-up is a draft until it is submitted | P0 | After *Save cash-up* the record is `draft` and does not appear under *Awaiting approval*. It appears only after *Submit for approval*. | ☐ |
| 7.21 | A submitted cash-up cannot be edited | P0 | The denomination boxes are locked and *Save cash-up* is gone. Only a rejection sends it back to the conductor. | ☐ |
| 7.22 | A rejection shows the reason and the trip can be re-submitted | P0 | After a rejection the trip screen shows the reason, the cash-up can be edited, and saving it again returns it to `draft` so it can be submitted once more. | ☐ |
| 7.23 | The variance equals counted minus expected | P0 | With a manifest of ₦3,500 and ₦3,400 counted, the card shows a variance of −₦100, and the submitted cash-up carries the same figure. | ☐ |
| 7.24 | A cash-up cannot be raised against a trip that is not closed | P0 | On a `planned` trip the cash-up card says so and offers no button. The server refuses with *Trip must be 'closed' before cash-up*. | ☐ |
| 7.25 | Roles are gated exactly as the server gates them | P0 | A conductor sees the manifest and the cash-up but not the status buttons; a driver sees none of the three; a chief accountant sees the cash-ups but not the manifest. Every hidden action is refused by the API when called directly. | ☐ |

---

## Part 8 — Security verification

| # | Test | Severity | Expected result | Result |
|---|---|---|---|---|
| 8.1 | Confirm no secret is committed to the repository | P0 | No `.env`, key or credential is tracked. `JWT_SECRET_KEY` and the Mongo URL come from the environment only. | ☐ |
| 8.2 | Confirm `JWT_SECRET_KEY` is not the sample default in production | P0 | The app refuses to start with a known default, or at minimum logs a loud warning. | ☐ |
| 8.3 | Test for NoSQL injection through query parameters | P0 | An input such as `?email[$ne]=` is rejected or treated as a literal string. The app must never accept a raw operator object from the client. | ☐ |
| 8.4 | Test for injection through free-text fields | P1 | Search terms containing quotes or operators are escaped and cannot alter the query. | ☐ |
| 8.5 | Confirm CORS only allows the configured origins | P0 | A request from an unlisted origin is refused. | ☐ |
| 8.6 | Confirm the API refuses an oversized request body | P2 | The request is rejected rather than consuming unbounded memory. | ☐ |
| 8.7 | Confirm rate limiting applies to the auth endpoints | P1 | Brute-force attempts are throttled with 429. | ☐ |
| 8.8 | Confirm the audit log is append-only through the API | P1 | There is no endpoint that deletes or edits an audit entry. | ☐ |
| 8.9 | Confirm secrets never appear in API responses | P0 | No response contains `password_hash`, a reset token or a refresh token belonging to another user. | ☐ |
| 8.10 | Confirm the push token of one user is never visible to another | P0 | `GET /push` returns only the signed-in user's own devices. | ☐ |
| 8.11 | Confirm file uploads are validated | P2 | Only the permitted content types and sizes are accepted for receipts and incident photos. | ☐ |
| 8.12 | Confirm the app is served over HTTPS in production | P0 | No plain-HTTP access, and `Strict-Transport-Security` is set. | ☐ |

---

## Part 9 — Non-functional verification

| # | Test | Severity | Expected result | Result |
|---|---|---|---|---|
| 9.1 | Measure the dashboard load time on staging | P1 | Under 2 seconds on a mid-range phone over 4G. | ☐ |
| 9.2 | Measure the trips list with 5,000+ records | P1 | The response stays under 1 second and the index is actually used (`explain()` shows an index scan, not a collection scan). | ☐ |
| 9.3 | Measure report generation for a full month across all branches | P1 | Under 5 seconds. | ☐ |
| 9.4 | Verify the app recovers after the database restarts | P1 | Requests fail gracefully during the outage and recover automatically; the app does not require a restart. | ☐ |
| 9.5 | Verify the alerts worker retries after a transient failure | P2 | A failed scan is logged and retried; the worker does not die silently. | ☐ |
| 9.6 | Verify the SSE live board reconnects after a network drop | P1 | The connection indicator returns to `Live` without the user reloading. | ☐ |
| 9.7 | Verify the live board degrades to polling when SSE is unavailable | P1 | The board still updates on an interval and shows a clear "polling" state. | ☐ |
| 9.8 | Test the app on the supported browser and device matrix | P1 | iOS Safari, Android Chrome, desktop Chrome, desktop Safari and desktop Firefox all render every screen correctly. | ☐ |
| 9.9 | Test offline behaviour with the network disabled | P2 | Queued writes are retained, the sync screen shows the queue, and nothing is silently lost. | ☐ |
| 9.10 | Verify accessibility basics | P2 | Every interactive element is reachable by screen reader, focus order is sensible, and colour contrast meets WCAG AA. | ☐ |
| 9.11 | Verify the app works at the smallest supported screen size | P2 | No content is clipped or overlapping at 320 px width. | ☐ |
| 9.12 | Verify long field values do not break the layout | P3 | Very long names, emails and notes truncate or wrap rather than overflowing. | ☐ |

---

## Part 10 — Regression watch-list: defects found and fixed

**Objective:** these are real defects that were live in the application and were found only by executing the app rather than reading it. Each one now has a permanent automated guard. The tester must confirm each defect is genuinely fixed — a regression here is a P0.

| # | Defect | How it presented | Why nothing caught it | Guard that now prevents it | Sev | Result |
|---|---|---|---|---|---|---|
| 10.1 | Cash-up receipts and trip waybills returned HTTP 500 | Every PDF download failed with `TypeError: 'str' object cannot be interpreted as an integer`. | The PDF service formatted dates with `iso.replace('Z', '+00:00')`. That is right for an ISO string, but MongoDB returns native datetimes, where `.replace()` means `replace(year, month, ...)`. No test existed for either endpoint. | `test_pdf_export.py` — exercises both endpoints and the formatter directly | P0 | ☐ |
| 10.2 | Maintenance records were invisible to alerts and reports | Maintenance-due notifications never fired, maintenance cost never reached the profit-and-loss report, and every vehicle reported 100% utilisation. | The maintenance router wrote to the `maintenance` collection while the alerts engine read `maintenance_records` and the reports read `maintenance_records` too. No test had ever seeded either collection, so the split stayed invisible. | `test_collection_consistency.py` (one collection, one name) and `test_maintenance_visibility.py` (the behaviour itself) | P0 | ☐ |
| 10.3 | Seven endpoints answered with a bare body instead of the envelope | The dashboard KPIs, fleet map, QR scanner, incident counters, role-permission metadata and the audit summary all rendered blank. | The frontend reads single records with `getSingle`, which unwraps `.data.data`. A bare body yields `undefined` rather than an error, so nothing crashed. | `test_response_envelope.py` | P0 | ☐ |
| 10.4 | Eight hot collections had no index | Incident lists, the notification inbox and the vehicle-document views ran as full collection scans and degraded as data grew. | Indexes were created for the collections named in `create_indexes()`; eight others that the app queried were simply never listed. | `test_collection_consistency.py` — every queried collection must have an index | P1 | ☐ |
| 10.5 | A branch manager could never be unassigned | The backend accepted `manager_id: null` but the UI offered no way to send it. | The select control only ever emits real option values, and the clear path was never built. | Manual — Part 4.5 / branch detail screen | P2 | ☐ |
| 10.6 | The audit actor filter was silently truncated at 25 actors | Once the organisation had more than 25 distinct actors, the rest could not be selected from the chip list. | The endpoint defaults to `limit=25` and the client called it with no parameters. | Manual — Part 4.4 / audit log screen | P2 | ☐ |

---

## Part 11 — Automated regression guards

These run in CI on every push. The tester must confirm they are green on the release candidate, because a red guard invalidates the manual pass.

| # | Guard | What it proves | Result |
|---|---|---|---|
| 11.1 | Backend suite | Every domain's behaviour, including the state machines and the financial arithmetic. | ☐ |
| 11.2 | Requirements guard | No npm package has crept into the Python requirements file. | ☐ |
| 11.3 | Response-envelope contract | No endpoint has drifted back to a bare body. | ☐ |
| 11.4 | Collection consistency | No collection is reachable under two names; no queried collection lacks an index; no index references a field nothing writes. | ☐ |
| 11.5 | Frontend ↔ backend runtime contract | Every one of the ~126 frontend API calls reaches a live route. A 404, 405, 401 or 500 fails the build. | ☐ |
| 11.6 | Frontend typecheck | The frontend compiles with no type errors. | ☐ |
| 11.7 | Lockfile sync | The lockfile matches `package.json`, so the mobile build cannot break on a device. | ☐ |

---

## Part 12 — Client UAT scenarios & sign-off

**Objective:** confirm the client can run their day on the app. Each scenario is a real task, written the way the client describes it, not a test of the system's internals.

| # | Scenario | Steps | Expected outcome | Sev | Result |
|---|---|---|---|---|---|
| 12.1 | The dispatcher sets up tomorrow's schedule | Sign in as dispatcher → create a route → create a trip → assign vehicle, driver and conductor → confirm the trip appears on the live board. | The trip is scheduled and visible to the driver on their own device. | P0 | ☐ |
| 12.2 | The conductor runs the trip and collects fares | Sign in as conductor → open the trip → add passengers to the manifest → mark each as paid → board the trip. | The manifest totals update live and the trip advances through boarding and departed. | P0 | ☐ |
| 12.3 | The driver completes the trip and the conductor hands over the cash | Driver marks arrived → trip closed → conductor submits a cash-up with a breakdown of cash and transfer. | The variance is computed and the cash-up appears in the manager's review queue. | P0 | ☐ |
| 12.4 | The manager reviews and approves the cash-up | Sign in as branch manager → cash-ups → filter by Submitted → approve one, reject another with a reason. | Both actions succeed; the conductor sees the outcome and the reason for the rejection. | P0 | ☐ |
| 12.5 | The fleet manager schedules vehicle maintenance | Sign in as fleet manager → maintenance → schedule a service for a vehicle with a due date. | The vehicle's status flips to maintenance and a maintenance-due notification appears. | P0 | ☐ |
| 12.6 | The accountant closes the month for a branch | Sign in as chief accountant → settlements → generate for the branch and period → submit → approve → mark paid with a reference. | The settlement shows gross revenue, expenses and crew payroll, every figure traceable to its trips. | P0 | ☐ |
| 12.7 | The owner reads the month's performance | Sign in as owner → reports → review operations summary, profit and loss, branch performance, vehicle ROI and utilisation. | Every report renders with figures that agree with the underlying records. | P0 | ☐ |
| 12.8 | An incident happens on the road | Any user → report incident → pick a category, severity, description and photos. | The incident is recorded, appears in the incident list, and the assigned staff are notified. | P0 | ☐ |
| 12.9 | A vehicle moves to another branch | Fleet manager → transfers → initiate a transfer → the receiving branch confirms → returns it. | The transfer walks initiated → confirmed → returned, and the vehicle's branch updates at each step. | P1 | ☐ |
| 12.10 | The manager traces who changed what | Sign in as owner → audit log → filter by actor and by action. | Every administrative change is attributable to a named actor with a before/after snapshot. | P0 | ☐ |
| 12.11 | The conductor works with poor connectivity | Disable the network → record manifest entries → restore the network → open the sync screen. | Entries queue locally, sync completes, and nothing is lost or duplicated. | P1 | ☐ |
| 12.12 | A user scans a vehicle's QR code | Open the scanner → scan a vehicle QR → confirm the vehicle record opens. | The correct vehicle opens with its full detail, without a manual lookup. | P1 | ☐ |

### Client sign-off

| Field | Entry |
|---|---|
| **Total items in this manual** | **448** |
| Items passed | ______ of 448 |
| Items failed | |
| Items blocked | |
| Items deferred (P2/P3 only) | |
| Total defects raised | |
| Open P0 defects | |
| Open P1 defects | |

| Role | Name | Signature | Date |
|---|---|---|---|
| Test lead | | | |
| QA manager | | | |
| Backend engineer | | | |
| Frontend engineer | | | |
| Product owner | | | |
| Client representative | | | |

**Declaration.** The undersigned confirm that the items above were executed against the release candidate, that the results recorded are accurate, and that the application is accepted as ready for use.

---

## Appendix A — Endpoint index

| Method | Path | Tag | Roles |
|---|---|---|---|
| POST | `/admin/seed` | admin | **gated by the `ADMIN_BOOTSTRAP_TOKEN` env var, and permanently disabled once the bootstrap flag is set** |
| POST | `/alerts/scan` | alerts | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/audit-log` | audit-log | `general_manager`, `owner`, `super_admin` |
| GET | `/audit-log/actors` | audit-log | `general_manager`, `owner`, `super_admin` |
| GET | `/audit-log/summary` | audit-log | `general_manager`, `owner`, `super_admin` |
| POST | `/auth/change-password` | auth | any signed-in role |
| POST | `/auth/forgot-password` | auth | public — no session required |
| POST | `/auth/forgot-username` | auth | public — no session required |
| POST | `/auth/login` | auth | public — no session required |
| POST | `/auth/logout` | auth | any signed-in role |
| GET | `/auth/me` | auth | any signed-in role |
| POST | `/auth/refresh` | auth | public — no session required |
| POST | `/auth/reset-password` | auth | public — no session required |
| GET | `/branches` | branches | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| POST | `/branches` | branches | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| DELETE | `/branches/{branch_id}` | branches | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/branches/{branch_id}` | branches | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| PATCH | `/branches/{branch_id}` | branches | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| POST | `/branches/{branch_id}/manager` | branches | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/cash-ups` | cash-ups | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `general_manager`, `owner`, `super_admin` |
| POST | `/cash-ups` | cash-ups | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `general_manager`, `owner`, `super_admin` |
| GET | `/cash-ups/{cash_up_id}` | cash-ups | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `general_manager`, `owner`, `super_admin` |
| PATCH | `/cash-ups/{cash_up_id}` | cash-ups | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `general_manager`, `owner`, `super_admin` |
| POST | `/cash-ups/{cash_up_id}/approve` | cash-ups | `branch_accountant`, `chief_accountant`, `general_manager`, `owner`, `super_admin` |
| GET | `/cash-ups/{cash_up_id}/pdf` | cash-ups | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `general_manager`, `owner`, `super_admin` |
| POST | `/cash-ups/{cash_up_id}/reject` | cash-ups | `branch_accountant`, `chief_accountant`, `general_manager`, `owner`, `super_admin` |
| POST | `/cash-ups/{cash_up_id}/submit` | cash-ups | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `general_manager`, `owner`, `super_admin` |
| GET | `/conductors` | conductors | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| POST | `/conductors` | conductors | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| DELETE | `/conductors/{conductor_id}` | conductors | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/conductors/{conductor_id}` | conductors | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| PATCH | `/conductors/{conductor_id}` | conductors | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/dashboard/summary` | dashboard | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/drivers` | drivers | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| POST | `/drivers` | drivers | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| DELETE | `/drivers/{driver_id}` | drivers | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/drivers/{driver_id}` | drivers | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| PATCH | `/drivers/{driver_id}` | drivers | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/events/status` | events | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/events/trips` | events | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/expenses` | expenses | `branch_accountant`, `branch_manager`, `chief_accountant`, `general_manager`, `owner`, `super_admin` |
| POST | `/expenses` | expenses | `branch_accountant`, `branch_manager`, `chief_accountant`, `driver`, `general_manager`, `owner`, `super_admin` |
| DELETE | `/expenses/{expense_id}` | expenses | `branch_accountant`, `branch_manager`, `chief_accountant`, `driver`, `general_manager`, `owner`, `super_admin` |
| GET | `/expenses/{expense_id}` | expenses | `branch_accountant`, `branch_manager`, `chief_accountant`, `general_manager`, `owner`, `super_admin` |
| PATCH | `/expenses/{expense_id}` | expenses | `branch_accountant`, `branch_manager`, `chief_accountant`, `driver`, `general_manager`, `owner`, `super_admin` |
| GET | `/fleet/positions` | fleet | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/fuel-logs` | fuel-logs | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `owner`, `super_admin` |
| POST | `/fuel-logs` | fuel-logs | `branch_accountant`, `branch_manager`, `chief_accountant`, `driver`, `fleet_manager`, `general_manager`, `owner`, `super_admin` |
| GET | `/fuel-logs/vehicle/{vehicle_id}/efficiency` | fuel-logs | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `owner`, `super_admin` |
| DELETE | `/fuel-logs/{fuel_log_id}` | fuel-logs | `branch_accountant`, `branch_manager`, `chief_accountant`, `driver`, `fleet_manager`, `general_manager`, `owner`, `super_admin` |
| GET | `/fuel-logs/{fuel_log_id}` | fuel-logs | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `owner`, `super_admin` |
| PATCH | `/fuel-logs/{fuel_log_id}` | fuel-logs | `branch_accountant`, `branch_manager`, `chief_accountant`, `driver`, `fleet_manager`, `general_manager`, `owner`, `super_admin` |
| GET | `/healthz` | health | *(undetermined — verify manually)* |
| GET | `/incidents` | incidents | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| POST | `/incidents` | incidents | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/incidents/categories` | incidents | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/incidents/summary` | incidents | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/incidents/{incident_id}` | incidents | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| POST | `/incidents/{incident_id}/acknowledge` | incidents | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| POST | `/incidents/{incident_id}/resolve` | incidents | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/inspections` | inspections | `branch_manager`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| POST | `/inspections` | inspections | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/inspections/template` | inspections | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/inspections/{inspection_id}` | inspections | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| PUT | `/inspections/{inspection_id}` | inspections | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| POST | `/inspections/{inspection_id}/submit` | inspections | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/maintenance` | maintenance | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `owner`, `super_admin` |
| POST | `/maintenance` | maintenance | `branch_manager`, `fleet_manager`, `general_manager`, `owner`, `super_admin` |
| GET | `/maintenance/vehicle/{vehicle_id}/upcoming` | maintenance | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `owner`, `super_admin` |
| DELETE | `/maintenance/{record_id}` | maintenance | `branch_manager`, `fleet_manager`, `general_manager`, `owner`, `super_admin` |
| GET | `/maintenance/{record_id}` | maintenance | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `owner`, `super_admin` |
| PATCH | `/maintenance/{record_id}` | maintenance | `branch_manager`, `fleet_manager`, `general_manager`, `owner`, `super_admin` |
| GET | `/notifications` | notifications | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| POST | `/notifications/mark-all-read` | notifications | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/notifications/unread-count` | notifications | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| POST | `/notifications/{notification_id}/mark-read` | notifications | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/push` | push | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| POST | `/push/register` | push | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| POST | `/push/unregister` | push | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/qr/generate/{entity_type}/{entity_id}` | qr | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/qr/lookup` | qr | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/reports/branches/performance` | reports | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/reports/drivers/performance` | reports | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/reports/financials/cash-flow` | reports | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/reports/financials/profit-loss` | reports | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/reports/fuel/summary` | reports | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/reports/incidents/summary` | reports | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/reports/operations/daily` | reports | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/reports/operations/summary` | reports | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/reports/routes/top` | reports | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/reports/vehicles/roi` | reports | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/reports/vehicles/utilization` | reports | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/role-permissions` | role-permissions | `general_manager`, `owner`, `super_admin` |
| GET | `/role-permissions/meta` | role-permissions | `general_manager`, `owner`, `super_admin` |
| POST | `/role-permissions/reset-all` | role-permissions | `owner`, `super_admin` |
| GET | `/role-permissions/{role_name}` | role-permissions | `general_manager`, `owner`, `super_admin` |
| PUT | `/role-permissions/{role_name}` | role-permissions | `general_manager`, `owner`, `super_admin` |
| POST | `/role-permissions/{role_name}/reset` | role-permissions | `general_manager`, `owner`, `super_admin` |
| GET | `/routes` | routes | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| POST | `/routes` | routes | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| DELETE | `/routes/{route_id}` | routes | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/routes/{route_id}` | routes | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| PATCH | `/routes/{route_id}` | routes | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/settlements` | settlements | `branch_accountant`, `branch_manager`, `chief_accountant`, `general_manager`, `owner`, `super_admin` |
| POST | `/settlements/generate` | settlements | `branch_accountant`, `chief_accountant`, `general_manager`, `owner`, `super_admin` |
| GET | `/settlements/summary` | settlements | `branch_accountant`, `branch_manager`, `chief_accountant`, `general_manager`, `owner`, `super_admin` |
| GET | `/settlements/{settlement_id}` | settlements | `branch_accountant`, `branch_manager`, `chief_accountant`, `general_manager`, `owner`, `super_admin` |
| PATCH | `/settlements/{settlement_id}` | settlements | `branch_accountant`, `chief_accountant`, `general_manager`, `owner`, `super_admin` |
| POST | `/settlements/{settlement_id}/approve` | settlements | `chief_accountant`, `general_manager`, `owner`, `super_admin` |
| POST | `/settlements/{settlement_id}/pay` | settlements | `chief_accountant`, `general_manager`, `owner`, `super_admin` |
| POST | `/settlements/{settlement_id}/reject` | settlements | `chief_accountant`, `general_manager`, `owner`, `super_admin` |
| POST | `/settlements/{settlement_id}/submit` | settlements | `branch_accountant`, `chief_accountant`, `general_manager`, `owner`, `super_admin` |
| POST | `/sync/pull` | sync | any signed-in role |
| POST | `/sync/push` | sync | any signed-in role |
| GET | `/sync/status` | sync | public — no session required |
| GET | `/trips` | trips | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| POST | `/trips` | trips | `branch_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| DELETE | `/trips/{trip_id}` | trips | `branch_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/trips/{trip_id}` | trips | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| PATCH | `/trips/{trip_id}` | trips | `branch_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/trips/{trip_id}/manifest` | trips | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| POST | `/trips/{trip_id}/manifest` | trips | `branch_manager`, `conductor`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| DELETE | `/trips/{trip_id}/manifest/{entry_id}` | trips | `branch_manager`, `conductor`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| PATCH | `/trips/{trip_id}/manifest/{entry_id}` | trips | `branch_manager`, `conductor`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| PATCH | `/trips/{trip_id}/status` | trips | `branch_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/trips/{trip_id}/waybill.pdf` | trips | `branch_accountant`, `branch_manager`, `chief_accountant`, `conductor`, `driver`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/users` | users | `branch_accountant`, `branch_manager`, `general_manager`, `owner`, `super_admin` |
| POST | `/users` | users | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| DELETE | `/users/{user_id}` | users | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/users/{user_id}` | users | `branch_accountant`, `branch_manager`, `general_manager`, `owner`, `super_admin` |
| PATCH | `/users/{user_id}` | users | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/vehicle-documents/expiring` | vehicle-documents | `branch_accountant`, `branch_manager`, `chief_accountant`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/vehicles/{vehicle_id}/documents` | vehicle-documents | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| POST | `/vehicles/{vehicle_id}/documents` | vehicle-documents | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| DELETE | `/vehicles/{vehicle_id}/documents/{doc_id}` | vehicle-documents | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| PATCH | `/vehicles/{vehicle_id}/documents/{doc_id}` | vehicle-documents | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/vehicle-transfers` | vehicle-transfers | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| POST | `/vehicle-transfers` | vehicle-transfers | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/vehicle-transfers/{transfer_id}` | vehicle-transfers | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| POST | `/vehicle-transfers/{transfer_id}/cancel` | vehicle-transfers | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| POST | `/vehicle-transfers/{transfer_id}/confirm` | vehicle-transfers | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| POST | `/vehicle-transfers/{transfer_id}/return` | vehicle-transfers | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/vehicles` | vehicles | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| POST | `/vehicles` | vehicles | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| DELETE | `/vehicles/{vehicle_id}` | vehicles | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| GET | `/vehicles/{vehicle_id}` | vehicles | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |
| PATCH | `/vehicles/{vehicle_id}` | vehicles | `branch_manager`, `fleet_manager`, `general_manager`, `operations_manager`, `owner`, `super_admin` |

## Appendix B — Screen index

| Route | Group | File |
|---|---|---|
| `/index` | (root) | `frontend/app/index.tsx` |
| `/` | app | `frontend/app/(app)/index.tsx` |
| `/audit-log` | app | `frontend/app/(app)/audit-log.tsx` |
| `/branches` | app | `frontend/app/(app)/branches/index.tsx` |
| `/branches/[id]` | app | `frontend/app/(app)/branches/[id].tsx` |
| `/cash-ups` | app | `frontend/app/(app)/cash-ups.tsx` |
| `/conductors` | app | `frontend/app/(app)/conductors/index.tsx` |
| `/conductors/[id]` | app | `frontend/app/(app)/conductors/[id].tsx` |
| `/devices` | app | `frontend/app/(app)/devices.tsx` |
| `/drivers` | app | `frontend/app/(app)/drivers/index.tsx` |
| `/drivers/[id]` | app | `frontend/app/(app)/drivers/[id].tsx` |
| `/expenses` | app | `frontend/app/(app)/expenses.tsx` |
| `/expenses/[id]` | app | `frontend/app/(app)/expenses/[id].tsx` |
| `/fuel` | app | `frontend/app/(app)/fuel.tsx` |
| `/fuel/[id]` | app | `frontend/app/(app)/fuel/[id].tsx` |
| `/incidents` | app | `frontend/app/(app)/incidents.tsx` |
| `/incidents/[id]` | app | `frontend/app/(app)/incidents/[id].tsx` |
| `/maintenance` | app | `frontend/app/(app)/maintenance.tsx` |
| `/maintenance/[id]` | app | `frontend/app/(app)/maintenance/[id].tsx` |
| `/map` | app | `frontend/app/(app)/map.tsx` |
| `/more` | app | `frontend/app/(app)/more.tsx` |
| `/notifications` | app | `frontend/app/(app)/notifications.tsx` |
| `/pre-trip-checklist` | app | `frontend/app/(app)/pre-trip-checklist.tsx` |
| `/profile` | app | `frontend/app/(app)/profile.tsx` |
| `/report-incident` | app | `frontend/app/(app)/report-incident.tsx` |
| `/reports` | app | `frontend/app/(app)/reports.tsx` |
| `/role-permissions` | app | `frontend/app/(app)/role-permissions.tsx` |
| `/routes` | app | `frontend/app/(app)/routes/index.tsx` |
| `/routes/[id]` | app | `frontend/app/(app)/routes/[id].tsx` |
| `/scan` | app | `frontend/app/(app)/scan.tsx` |
| `/settlements` | app | `frontend/app/(app)/settlements/index.tsx` |
| `/settlements/[id]` | app | `frontend/app/(app)/settlements/[id].tsx` |
| `/sync` | app | `frontend/app/(app)/sync.tsx` |
| `/transfers` | app | `frontend/app/(app)/transfers/index.tsx` |
| `/transfers/[id]` | app | `frontend/app/(app)/transfers/[id].tsx` |
| `/trips` | app | `frontend/app/(app)/trips/index.tsx` |
| `/trips/[id]` | app | `frontend/app/(app)/trips/[id].tsx` |
| `/trips/live` | app | `frontend/app/(app)/trips/live.tsx` |
| `/users` | app | `frontend/app/(app)/users/index.tsx` |
| `/users/[id]` | app | `frontend/app/(app)/users/[id].tsx` |
| `/vehicles` | app | `frontend/app/(app)/vehicles/index.tsx` |
| `/vehicles/[id]` | app | `frontend/app/(app)/vehicles/[id].tsx` |
| `/forgot-password` | auth | `frontend/app/(auth)/forgot-password.tsx` |
| `/forgot-username` | auth | `frontend/app/(auth)/forgot-username.tsx` |
| `/login` | auth | `frontend/app/(auth)/login.tsx` |
| `/reset-password` | auth | `frontend/app/(auth)/reset-password.tsx` |
