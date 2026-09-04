# TransitOS Sprint A — API Contract

> **Source of truth for the backend and frontend engineers.** Every
> endpoint below is implemented exactly once on the backend and
> consumed exactly once per screen on the frontend. Paths, methods,
> request shapes, response shapes, and required roles are normative
> — do not deviate.

---

## 0 · Conventions

### 0.1 Base URL
```
https://<host>/api/v1
```
In Sprint A local dev: `http://localhost:8000/api/v1`. The frontend
reads `app.json -> extra.apiUrl` and prefixes it. **The frontend
never hard-codes the host.**

### 0.2 Auth header
Every protected endpoint requires:
```
Authorization: Bearer <access_token>
```
The frontend's axios interceptor (`lib/api.ts`) adds this
automatically. On `401` the interceptor attempts `POST /auth/refresh`
once, retries the request, and only then logs the user out.

### 0.3 Content type
All requests and responses are `application/json` (except file
uploads, which arrive in Sprint B).

### 0.4 Timestamps
ISO-8601 UTC strings on the wire, e.g. `"2026-06-04T12:34:56.789Z"`.

### 0.5 ID format
All IDs are 24-char hex strings (stringified Mongo `ObjectId`).
Invalid format → `422 Validation Error` with `{ "detail":
"Invalid id format", "type": "validation_error" }`.

### 0.6 Pagination
Every list endpoint accepts these query params:

| Param  | Type | Default | Range   | Notes                          |
|--------|------|---------|---------|--------------------------------|
| page   | int  | 1       | ≥ 1     | 1-indexed                      |
| limit  | int  | 20      | 1–100   | Hard cap: 100                  |
| search | str  | —       | ≤ 80    | Case-insensitive substring     |
| sort   | str  | "created_at" | enum | "name", "created_at", "updated_at" |
| order  | str  | "desc"  | enum    | "asc" | "desc"              |
| include_inactive | bool | false | — | Owner/SuperAdmin only |

The backend translates `(page, limit)` to Mongo `skip = (page-1)*limit`
and `limit = limit`. **`skip` and `limit` are NEVER exposed to the
client** — only `page` and `limit`.

### 0.7 Response shapes

**Single resource:**
```json
{
  "data": { ... entity ... }
}
```

**List resource (paginated):**
```json
{
  "items": [ { ... }, { ... } ],
  "total": 142,
  "page": 1,
  "totalPages": 8,
  "hasMore": true
}
```

`hasMore` is `page < totalPages`. `totalPages = ceil(total / limit)`
and is `0` when `total = 0`.

**Error (any 4xx / 5xx):**
```json
{
  "detail": "Human-readable explanation.",
  "type": "validation_error"
}
```

The `type` field is one of:
- `validation_error` — Pydantic / query-param validation
- `unauthorized` — missing or invalid token
- `forbidden` — token valid but role insufficient
- `not_found` — entity id does not exist
- `conflict` — uniqueness violation (e.g. duplicate email)
- `rate_limited` — too many login attempts
- `internal_error` — 500, log-only

### 0.8 Role enum on the wire
Roles travel as snake_case strings:
```
super_admin, owner, general_manager, branch_manager,
operations_manager, fleet_manager, chief_accountant,
branch_accountant, driver, conductor
```

`super_admin` is a platform bootstrap role (see Open Decision #1 in
`SUMMARY.md`); it can do everything `owner` can plus system
administration.

### 0.9 Role check pattern
Every protected endpoint declares its required roles via a FastAPI
dependency:

```python
from app.core.rbac import get_current_user, Role

@router.get("/branches")
async def list_branches(
    user: User = Depends(get_current_user(required_roles=[
        Role.SUPER_ADMIN, Role.OWNER, Role.GENERAL_MANAGER,
        Role.BRANCH_MANAGER, Role.OPERATIONS_MANAGER,
        Role.FLEET_MANAGER, Role.CHIEF_ACCOUNTANT,
        Role.BRANCH_ACCOUNTANT,
    ])),
    db = Depends(get_db),
    page: int = 1, limit: int = 20,
    search: str | None = None, sort: str = "created_at",
    order: str = "desc", include_inactive: bool = False,
):
    ...
```

Branch-scoped roles (`branch_manager`, `branch_accountant`, `driver`,
`conductor`) only see records in **their own branch**. The
`get_current_user` dependency injects `user.branch_id`; the
service layer filters by it. See `0.10` for the per-endpoint
scoping notes.

### 0.10 Branch scoping rules
For each entity, the "scoped" column means:

| Scope      | Behavior                                                       |
|------------|----------------------------------------------------------------|
| `none`     | No branch filter.                                              |
| `self`     | `query["branch_id"] = user.branch_id` (branch-scoped roles only — HQ roles see all). |
| `all`      | HQ roles see all; branch-scoped roles see `self`.              |

---

## 1 · Auth

### 1.1 `POST /auth/login`
**Auth required**: no
**Body**:
```json
{
  "email": "user@example.com",
  "password": "string"
}
```
**Response 200**:
```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 900
}
```
- `access_token` is a JWT (HS256), 15-minute expiry.
- `refresh_token` is a JWT, 7-day expiry. Its `jti` is recorded
  in `refresh_tokens` collection.
- `expires_in` is **seconds** (900 = 15 min).
**Errors**:
- `401 unauthorized` — wrong email/password
- `429 rate_limited` — 5 attempts in 5 min
- `403 forbidden` — user is `is_active=false` or `status=suspended`
**Side effects**:
- Updates `user.last_login_at`.
- Writes audit log (`action=login` on success, `login_failed` on
  failure).

### 1.2 `POST /auth/refresh`
**Auth required**: yes (the **refresh** token in `Authorization: Bearer`)
**Body**: empty
**Response 200**: same shape as `POST /auth/login`. Old refresh token
is **rotated** — its `jti` is marked `revoked=true` and
`replaced_by=<new jti>`.
**Errors**:
- `401 unauthorized` — refresh token expired / revoked / unknown
**Side effects**:
- Writes audit log (`action=login` with `entity_type=auth`).

### 1.3 `GET /auth/me`
**Auth required**: yes
**Response 200**:
```json
{
  "data": {
    "id": "65f1a0b1c2d3e4f5a6b7c8d9",
    "email": "user@example.com",
    "full_name": "Jane Doe",
    "phone": "+2348000000000",
    "role": "branch_manager",
    "branch_id": "65f1a0b1c2d3e4f5a6b7c8e0",
    "status": "active",
    "hire_date": "2025-01-15T00:00:00.000Z",
    "photo_url": null,
    "is_active": true,
    "last_login_at": "2026-06-04T12:30:00.000Z",
    "created_at": "2025-01-15T08:00:00.000Z",
    "updated_at": "2026-06-04T12:30:00.000Z"
  }
}
```

### 1.4 `POST /auth/logout`
**Auth required**: yes
**Body**: empty
**Response 204**: empty
**Side effects**:
- Marks current `refresh_token` as `revoked=true`.
- Writes audit log (`action=logout`).

### 1.5 `POST /auth/forgot-password` *(stretch — see Open Decision #4)*
**Auth required**: no
**Body**: `{ "email": "user@example.com" }`
**Response 202**: `{ "message": "If that email exists, a reset link has been sent." }`
This is a stub in Sprint A — it writes a token to the DB and
**returns it in the response body** in dev mode so the frontend
can complete the flow. Real email delivery is Sprint B.
**Side effects**:
- Writes audit log (`action=password_reset`).

### 1.6 `POST /auth/reset-password` *(stretch)*
**Auth required**: no
**Body**: `{ "token": "string", "new_password": "string" }`
**Response 204**: empty
**Side effects**:
- Updates `user.password_hash`.
- Revokes all refresh tokens for that user.
- Writes audit log.

### 1.7 `POST /auth/me/password`
**Auth required**: yes
**Body**:
```json
{
  "current_password": "string",
  "new_password": "string"
}
```
**Response 204**: empty
**Errors**:
- `422 validation_error` — `new_password` shorter than 8 chars
- `401 unauthorized` — `current_password` does not match
**Side effects**:
- Updates `user.password_hash`.
- Revokes all refresh tokens for the current user.
- Writes audit log (`action=password_reset`); `before/after` MUST
  NOT include the password hash.

> **If time-pressed, sections 1.5–1.6 are optional in Sprint A** —
> Owner can use `POST /users/{id}/reset-password` instead. See §2.
> **Section 1.7 is mandatory** — it powers the Profile screen's
> "Reset password" flow without email delivery.

---

## 2 · Users

> User CRUD is the most privileged operation in the app. **Only
> SuperAdmin and Owner can create, update, deactivate, or assign
> roles.** Branch Managers can READ users in their own branch (for
> dispatching) but cannot mutate.

### 2.1 `GET /users`
**Auth required**: yes
**Required roles**:
`super_admin`, `owner`, `general_manager`, `branch_manager`
(read-scope for dispatch), `branch_accountant`
**Scoping**: `self` (branch-scoped roles see own branch; HQ roles see all)
**Query params**: `page`, `limit`, `search` (matches `email` or
`full_name`), `role`, `branch_id`, `status`, `include_inactive`
(`include_inactive` is only honored if user is super_admin or owner)
**Response 200**: standard list shape; each item is `UserResponse`.

### 2.2 `GET /users/{id}`
**Auth required**: yes
**Required roles**:
`super_admin`, `owner`, `general_manager`, `branch_manager`,
`branch_accountant` (subject to scoping)
**Scoping**: `self` for branch roles
**Response 200**:
```json
{ "data": { ...UserResponse... } }
```

### 2.3 `POST /users`
**Auth required**: yes
**Required roles**: `super_admin`, `owner`
**Body** (`UserCreate`):
```json
{
  "email": "newuser@example.com",
  "full_name": "John Doe",
  "phone": "+2348000000000",
  "role": "branch_manager",
  "branch_id": "65f1a0b1c2d3e4f5a6b7c8e0",
  "password": "S3curePass!",
  "status": "active",
  "hire_date": "2026-06-01",
  "photo_url": null
}
```
**Response 201**:
```json
{ "data": { ...UserResponse... } }
```
**Errors**:
- `409 conflict` — email already exists
- `422 validation_error` — branch_id missing for branch-scoped role
**Side effects**:
- Hashes password (bcrypt).
- Writes audit log (`action=create`, `entity_type=user`).

### 2.4 `PATCH /users/{id}`
**Auth required**: yes
**Required roles**: `super_admin`, `owner`
**Body** (`UserUpdate`): all fields optional
**Response 200**: standard single shape.
**Special case**: cannot change own role. → `403 forbidden`,
`type=forbidden`, `detail="Cannot change your own role."`
**Side effects**:
- Writes audit log (`action=update` with before/after diff).

### 2.5 `POST /users/{id}/deactivate`
**Auth required**: yes
**Required roles**: `super_admin`, `owner`
**Body**: empty
**Response 200**: standard single shape (now `is_active=false`,
`status=suspended`).
**Special case**: cannot deactivate self. → `403 forbidden`.
**Side effects**:
- Revokes all refresh tokens for that user.
- Writes audit log (`action=deactivate`).

### 2.6 `POST /users/{id}/activate`
**Auth required**: yes
**Required roles**: `super_admin`, `owner`
**Body**: empty
**Response 200**: standard single shape.
**Side effects**:
- Writes audit log (`action=activate`).

### 2.7 `POST /users/{id}/reset-password`
**Auth required**: yes
**Required roles**: `super_admin`, `owner` (or self — see below)
**Body**: `{ "new_password": "S3curePass!" }`
**Response 204**: empty
**Self-service rule**: a user with role `super_admin`, `owner`, or
`general_manager` can reset **their own** password. Branch-scoped
roles cannot — they must use `/auth/forgot-password` (Sprint B) or
ask an Owner.
**Side effects**:
- Hashes new password.
- Revokes all refresh tokens for that user.
- Writes audit log (`action=password_reset`); `before/after` MUST
  NOT include the password hash.

---

## 3 · Branches

### 3.1 `GET /branches`
**Auth required**: yes
**Required roles**:
`super_admin`, `owner`, `general_manager`, `branch_manager`,
`operations_manager`, `fleet_manager`, `chief_accountant`,
`branch_accountant`
**Scoping**: `self` for branch-scoped roles
**Query params**: standard pagination + `city`, `state`, `status`
**Response 200**: standard list shape; each item is `BranchResponse`.

### 3.2 `GET /branches/{id}`
**Auth required**: yes
**Required roles**: any authenticated user (subject to scoping)
**Scoping**: branch-scoped roles can only see their own branch.
**Response 200**: standard single shape.

### 3.3 `POST /branches`
**Auth required**: yes
**Required roles**: `super_admin`, `owner`
**Body** (`BranchCreate`):
```json
{
  "name": "Lagos HQ",
  "code": "LOS-01",
  "city": "Lagos",
  "state": "Lagos",
  "address": "12 Park Lane, Ojota",
  "contact_phone": "+2348000000000",
  "contact_email": "lagos@transitos.local",
  "gps": { "lat": 6.5833, "lng": 3.3500 },
  "bank_account": {
    "bank": "GTBank",
    "number": "0123456789",
    "name": "TransitOS Lagos Ltd"
  },
  "status": "active"
}
```
**Response 201**: standard single shape.
**Side effects**: writes audit log.

### 3.4 `PATCH /branches/{id}`
**Auth required**: yes
**Required roles**: `super_admin`, `owner`
**Body** (`BranchUpdate`): all fields optional.
**Response 200**: standard single shape.

### 3.5 `POST /branches/{id}/deactivate`
**Auth required**: yes
**Required roles**: `super_admin`, `owner`
**Body**: empty
**Response 200**: standard single shape.
**Side effects**:
- Sets `status=suspended`.
- Writes audit log.

### 3.6 `POST /branches/{id}/manager`
**Auth required**: yes
**Required roles**: `super_admin`, `owner`
**Body**: `{ "user_id": "65f1a0b1c2d3e4f5a6b7c8d9" }`
**Response 200**: standard single shape.
**Errors**:
- `422 validation_error` — referenced user is not a `branch_manager`
  or is not assigned to this branch.
**Side effects**: writes audit log.

---

## 4 · Vehicles

### 4.1 `GET /vehicles`
**Auth required**: yes
**Required roles**:
`super_admin`, `owner`, `general_manager`, `branch_manager`,
`operations_manager`, `fleet_manager`, `chief_accountant`,
`branch_accountant`
**Scoping**: `self`
**Query params**: standard pagination + `branch_id`, `type`, `status`,
`include_inactive`
**Response 200**: standard list shape.

### 4.2 `GET /vehicles/{id}`
**Auth required**: yes
**Required roles**: any authenticated user (subject to scoping)
**Scoping**: `self`
**Response 200**: standard single shape.

### 4.3 `POST /vehicles`
**Auth required**: yes
**Required roles**:
`super_admin`, `owner`, `general_manager`, `branch_manager`,
`fleet_manager`
**Body** (`VehicleCreate`):
```json
{
  "reg_number": "LSR-123-AB",
  "type": "bus",
  "capacity_seats": 50,
  "capacity_kg": 2000,
  "branch_id": "65f1a0b1c2d3e4f5a6b7c8e0",
  "home_terminal_id": null,
  "status": "available",
  "current_odometer_km": 0,
  "current_fuel_level": 0,
  "documents": []
}
```
**Response 201**: standard single shape.
**Errors**:
- `409 conflict` — `reg_number` already exists.
**Side effects**: writes audit log.

### 4.4 `PATCH /vehicles/{id}`
**Auth required**: yes
**Required roles**:
`super_admin`, `owner`, `general_manager`, `branch_manager`,
`fleet_manager`
**Body** (`VehicleUpdate`): all optional.
**Response 200**: standard single shape.

### 4.5 `POST /vehicles/{id}/deactivate`
**Auth required**: yes
**Required roles**:
`super_admin`, `owner`, `general_manager`, `branch_manager`,
`fleet_manager`
**Body**: empty
**Response 200**: standard single shape.

---

## 5 · Drivers

### 5.1 `GET /drivers`
**Auth required**: yes
**Required roles**:
`super_admin`, `owner`, `general_manager`, `branch_manager`,
`operations_manager`, `fleet_manager`
**Scoping**: `self` (branch-scoped roles only see their branch's drivers)
**Query params**: standard pagination + `status`, `branch_id`
**Response 200**: standard list shape; items are `DriverResponse`
(denormalized user fields included).

### 5.2 `GET /drivers/{id}`
**Auth required**: yes
**Required roles**: any authenticated user (subject to scoping)
**Scoping**: `self`
**Response 200**: standard single shape.

### 5.3 `POST /drivers`
**Auth required**: yes
**Required roles**:
`super_admin`, `owner`, `general_manager`, `branch_manager`,
`fleet_manager`
**Body** (`DriverCreate`):
```json
{
  "user_id": "65f1a0b1c2d3e4f5a6b7c8d9",
  "license_no": "LAG-DRV-00987",
  "license_expiry": "2028-06-30T00:00:00.000Z",
  "years_experience": 5,
  "status": "active"
}
```
**Errors**:
- `404 not_found` — referenced user does not exist
- `422 validation_error` — user is not a `driver` role
- `409 conflict` — driver record for this user already exists
**Side effects**:
- Denormalizes `branch_id` from the referenced user.
- Writes audit log.

### 5.4 `PATCH /drivers/{id}`
**Auth required**: yes
**Required roles**:
`super_admin`, `owner`, `general_manager`, `branch_manager`,
`fleet_manager`
**Body** (`DriverUpdate`): all optional.
**Response 200**: standard single shape.

### 5.5 `POST /drivers/{id}/deactivate`
**Auth required**: yes
**Required roles**:
`super_admin`, `owner`, `general_manager`, `branch_manager`,
`fleet_manager`
**Body**: empty
**Response 200**: standard single shape.

---

## 6 · Conductors

> Conductor management mirrors Driver management exactly. The roles
> allowed for mutations are the same set: any role that can move
> a driver (Fleet, Branch, Operations, etc.) can move a conductor.

### 6.1 `GET /conductors`
**Required roles**: `super_admin`, `owner`, `general_manager`,
`branch_manager`, `operations_manager`, `fleet_manager`
**Scoping**: `self`
**Query params**: standard pagination + `status`, `branch_id`
**Response 200**: standard list shape; items are `ConductorResponse`.

### 6.2 `GET /conductors/{id}`
**Required roles**: any authenticated user (subject to scoping)
**Scoping**: `self`
**Response 200**: standard single shape.

### 6.3 `POST /conductors`
**Required roles**:
`super_admin`, `owner`, `general_manager`, `branch_manager`,
`fleet_manager`
**Body** (`ConductorCreate`):
```json
{
  "user_id": "65f1a0b1c2d3e4f5a6b7c8d9",
  "badge_no": "COND-0042",
  "status": "active"
}
```
**Errors**: same as POST /drivers (404 user, 422 role mismatch,
409 duplicate).
**Side effects**: writes audit log.

### 6.4 `PATCH /conductors/{id}`
**Required roles**: same as POST
**Body** (`ConductorUpdate`): all optional.
**Response 200**: standard single shape.

### 6.5 `POST /conductors/{id}/deactivate`
**Required roles**: same as POST
**Body**: empty
**Response 200**: standard single shape.

---

## 7 · Routes

### 7.1 `GET /routes`
**Auth required**: yes
**Required roles**:
`super_admin`, `owner`, `general_manager`, `branch_manager`,
`operations_manager`, `fleet_manager`, `chief_accountant`,
`branch_accountant`
**Scoping**: `self` (branch-scoped roles see only their own
branch's routes; HQ roles see all)
**Query params**: standard pagination + `type`, `origin_branch_id`,
`destination_branch_id`, `include_inactive`
**Response 200**: standard list shape; items are `RouteResponse`.

### 7.2 `GET /routes/{id}`
**Auth required**: yes
**Required roles**: any authenticated user (subject to scoping)
**Scoping**: `self`
**Response 200**: standard single shape.

### 7.3 `POST /routes`
**Auth required**: yes
**Required roles**:
`super_admin`, `owner`, `general_manager`, `operations_manager`,
`branch_manager`
**Body** (`RouteCreate`):
```json
{
  "name": "Lagos → Abuja Express",
  "branch_id": "65f1a0b1c2d3e4f5a6b7c8e0",
  "type": "interstate",
  "origin_branch_id": "65f1a0b1c2d3e4f5a6b7c8e0",
  "destination_branch_id": "65f1a0b1c2d3e4f5a6b7c8e1",
  "origin_city": "Lagos",
  "destination_city": "Abuja",
  "distance_km": 750.0,
  "base_fare_passenger": 15000.0,
  "base_fare_cargo_per_kg": 250.0,
  "estimated_duration_hours": 10.0,
  "intermediate_stops": [
    { "name": "Ibadan", "lat": 7.3775, "lng": 3.9470, "eta_minutes": 120 },
    { "name": "Ilorin", "lat": 8.4790, "lng": 4.5418, "eta_minutes": 240 }
  ],
  "required_permits": ["LAG", "OGU", "OYO", "KWU", "FCT"]
}
```
**Response 201**: standard single shape.
**Errors**:
- `422 validation_error` — `origin_branch_id == destination_branch_id`.
**Side effects**: writes audit log.

### 7.4 `PATCH /routes/{id}`
**Auth required**: yes
**Required roles**: same as POST
**Body** (`RouteUpdate`): all optional. The validator
(origin != destination) only runs if **both** fields are in the
patch body.
**Response 200**: standard single shape.

### 7.5 `POST /routes/{id}/deactivate`
**Auth required**: yes
**Required roles**: same as POST
**Body**: empty
**Response 200**: standard single shape.

---

## 8 · Endpoint summary (for the integration gate)

| Method | Path                              | Required roles (short)                       |
|--------|-----------------------------------|----------------------------------------------|
| POST   | /auth/login                       | none                                         |
| POST   | /auth/refresh                     | refresh                                      |
| GET    | /auth/me                          | any auth                                     |
| POST   | /auth/logout                      | any auth                                     |
| POST   | /auth/forgot-password             | none (stretch)                               |
| POST   | /auth/reset-password              | none (stretch)                               |
| POST   | /auth/me/password                 | any auth (self only)                         |
| GET    | /users                            | sa, owner, gm, bm, ba                        |
| GET    | /users/{id}                       | any auth (scoped)                            |
| POST   | /users                            | sa, owner                                    |
| PATCH  | /users/{id}                       | sa, owner                                    |
| POST   | /users/{id}/deactivate            | sa, owner                                    |
| POST   | /users/{id}/activate              | sa, owner                                    |
| POST   | /users/{id}/reset-password        | sa, owner (or self for sa/owner/gm)          |
| GET    | /branches                         | sa, owner, gm, bm, om, fm, ca, ba            |
| GET    | /branches/{id}                    | any auth (scoped)                            |
| POST   | /branches                         | sa, owner                                    |
| PATCH  | /branches/{id}                    | sa, owner                                    |
| POST   | /branches/{id}/deactivate         | sa, owner                                    |
| POST   | /branches/{id}/manager            | sa, owner                                    |
| GET    | /vehicles                         | sa, owner, gm, bm, om, fm, ca, ba            |
| GET    | /vehicles/{id}                    | any auth (scoped)                            |
| POST   | /vehicles                         | sa, owner, gm, bm, fm                        |
| PATCH  | /vehicles/{id}                    | sa, owner, gm, bm, fm                        |
| POST   | /vehicles/{id}/deactivate         | sa, owner, gm, bm, fm                        |
| GET    | /drivers                          | sa, owner, gm, bm, om, fm                    |
| GET    | /drivers/{id}                     | any auth (scoped)                            |
| POST   | /drivers                          | sa, owner, gm, bm, fm                        |
| PATCH  | /drivers/{id}                     | sa, owner, gm, bm, fm                        |
| POST   | /drivers/{id}/deactivate          | sa, owner, gm, bm, fm                        |
| GET    | /conductors                       | sa, owner, gm, bm, om, fm                    |
| GET    | /conductors/{id}                  | any auth (scoped)                            |
| POST   | /conductors                       | sa, owner, gm, bm, fm                        |
| PATCH  | /conductors/{id}                  | sa, owner, gm, bm, fm                        |
| POST   | /conductors/{id}/deactivate       | sa, owner, gm, bm, fm                        |
| GET    | /routes                           | sa, owner, gm, bm, om, fm, ca, ba            |
| GET    | /routes/{id}                      | any auth (scoped)                            |
| POST   | /routes                           | sa, owner, gm, om, bm                        |
| PATCH  | /routes/{id}                      | sa, owner, gm, om, bm                        |
| POST   | /routes/{id}/deactivate           | sa, owner, gm, om, bm                        |

**Total: 40 endpoints in the table** + `/health` (root) = **41
endpoints total.** Role short-codes: `sa`=super_admin,
`owner`=owner, `gm`=general_manager, `bm`=branch_manager,
`om`=operations_manager, `fm`=fleet_manager, `ca`=chief_accountant,
`ba`=branch_accountant.

---

## 9 · Health check

### 9.1 `GET /health`
**Auth required**: no
**Response 200**:
```json
{ "status": "ok", "version": "0.1.0" }
```
This endpoint lives at the app root, **NOT** under `/api/v1`, so
the integration gate can hit it without prefix. The OpenAPI docs
live at `/docs` (Swagger UI) and `/redoc` — also root.

---

## 10 · What is NOT in Sprint A

The following endpoints are **explicitly out of scope** and must
NOT be implemented:

- `POST /auth/login` does **not** issue a device-bound session.
  Multiple devices per user are fine.
- No file-upload endpoint yet (`POST /vehicles/{id}/documents`,
  `POST /users/{id}/photo` are Sprint B).
- No `GET /audit-log` yet (Sprint B).
- No trip, manifest, fuel, maintenance, expense, or cash-up
  endpoints — those are Sprint B and C.
- No websocket endpoints — phase 2.
- No `GET /me/permissions` granular endpoint — role is enough in
  Sprint A.
