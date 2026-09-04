# TransitOS Sprint A — Data Model

> **Source of truth for the backend engineer.** Every entity in this
> document is implemented exactly once in `/workspace/transitos/backend/app/models/`.
> Do not invent fields the blueprint didn't ask for; do not omit fields
> the blueprint requires. The audit log is mandatory — every mutation
> must write to it.

---

## 0 · Conventions

### 0.1 ObjectId strategy
MongoDB `_id` is always a native `ObjectId`. **Never** exposed to the
client as an `ObjectId`. Every Pydantic response model has an `id: str`
field that is the stringified `ObjectId`. The mapping is:

| DB field         | API field                |
|------------------|--------------------------|
| `_id` (ObjectId) | `id` (str)               |
| `password_hash`  | **omitted from responses** |
| `__v`            | **omitted from responses** |

### 0.2 Soft delete
Every mutable entity has `is_active: bool = True` and `deleted_at:
Optional[datetime] = None`. **No endpoint performs a hard delete.**
List endpoints filter `{"is_active": True}` by default; the query
param `?include_inactive=true` is allowed for Owner/SuperAdmin only
and is documented per-endpoint. A future "purge" admin tool (out of
Sprint A scope) is the only path to hard delete.

### 0.3 Timestamps
Every mutable entity carries:
- `created_at: datetime` — server-set on insert
- `updated_at: datetime` — server-set on every update

Both are UTC, ISO-8601 strings on the wire.

### 0.4 Pydantic style
Pydantic v2 with `model_config = ConfigDict(populate_by_name=True,
arbitrary_types_allowed=True)`. Field aliases use snake_case on the
wire (no camelCase).

### 0.5 Role values
Roles are a closed enum. Sprint A implements **10 role values** (see
Open Decision #1 in `SUMMARY.md`): `super_admin`, `owner`,
`general_manager`, `branch_manager`, `operations_manager`,
`fleet_manager`, `chief_accountant`, `branch_accountant`, `driver`,
`conductor`. The blueprint's §1.2 lists 9 user-facing roles; we
include `super_admin` for platform bootstrap.

### 0.6 ID validation helper
Backend must validate any incoming `branch_id`, `manager_id`, etc.
as 24-char hex (valid `ObjectId`) before constructing an
`ObjectId(...)`. Invalid → 422 with `{ "detail": "Invalid id format",
"type": "validation_error" }`.

---

## 1 · Branch

Mongo collection: **`branches`**

```python
from datetime import datetime
from typing import Annotated, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

class GPS(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)

class BankAccount(BaseModel):
    bank: str = Field(min_length=2, max_length=80)
    number: str = Field(min_length=6, max_length=20)  # store as-is; display masked
    name: str = Field(min_length=2, max_length=120)

class BranchStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"

class BranchBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    code: str = Field(min_length=2, max_length=10, pattern=r"^[A-Z0-9-]+$")
    city: str = Field(min_length=1, max_length=80)
    state: str = Field(min_length=1, max_length=80)
    address: str = Field(min_length=2, max_length=240)
    contact_phone: Optional[str] = Field(default=None, max_length=20)
    contact_email: Optional[EmailStr] = None
    gps: Optional[GPS] = None
    bank_account: Optional[BankAccount] = None
    status: BranchStatus = BranchStatus.ACTIVE

class BranchCreate(BranchBase):
    """All fields required EXCEPT gps, contact_*, bank_account (optional)."""
    pass

class BranchUpdate(BaseModel):
    """PATCH — every field optional."""
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    code: Optional[str] = Field(default=None, min_length=2, max_length=10,
                                 pattern=r"^[A-Z0-9-]+$")
    city: Optional[str] = Field(default=None, min_length=1, max_length=80)
    state: Optional[str] = Field(default=None, min_length=1, max_length=80)
    address: Optional[str] = Field(default=None, min_length=2, max_length=240)
    contact_phone: Optional[str] = Field(default=None, max_length=20)
    contact_email: Optional[EmailStr] = None
    gps: Optional[GPS] = None
    bank_account: Optional[BankAccount] = None
    status: Optional[BranchStatus] = None
    manager_id: Optional[str] = None  # set manager separately via dedicated action

class BranchInDB(BranchBase):
    id: str = Field(alias="_id")
    manager_id: Optional[str] = None
    is_active: bool = True
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(populate_by_name=True)

class BranchResponse(BranchInDB):
    """Returned by API. Identical to BranchInDB but explicitly the wire shape."""
    pass
```

### Branch indexes
| Index                          | Purpose                                |
|--------------------------------|----------------------------------------|
| `{ code: 1 }` unique           | Uniqueness of branch code              |
| `{ is_active: 1, name: 1 }`    | List + sort by name                    |
| `{ city: 1, state: 1 }`        | Filter by location                     |
| `{ manager_id: 1 }`            | Look up branch-by-manager              |

### Branch field rules
- `code` is uppercase, alphanumeric + dash, **unique per company**.
- `manager_id` points at a User whose role must be `branch_manager`.
  Enforced in service layer; not at DB level.

---

## 2 · User

Mongo collection: **`users`**

```python
class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    OWNER = "owner"
    GENERAL_MANAGER = "general_manager"
    BRANCH_MANAGER = "branch_manager"
    OPERATIONS_MANAGER = "operations_manager"
    FLEET_MANAGER = "fleet_manager"
    CHIEF_ACCOUNTANT = "chief_accountant"
    BRANCH_ACCOUNTANT = "branch_accountant"
    DRIVER = "driver"
    CONDUCTOR = "conductor"

class UserStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"  # invited but never logged in

class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=20)
    role: UserRole
    branch_id: Optional[str] = None  # required for branch-scoped roles
    status: UserStatus = UserStatus.ACTIVE
    hire_date: Optional[datetime] = None
    photo_url: Optional[str] = None

    @field_validator("branch_id")
    @classmethod
    def branch_required_for_branch_roles(cls, v, info):
        branch_scoped = {
            UserRole.BRANCH_MANAGER, UserRole.BRANCH_ACCOUNTANT,
            UserRole.DRIVER, UserRole.CONDUCTOR,
        }
        if info.data.get("role") in branch_scoped and not v:
            raise ValueError("branch_id is required for this role")
        return v

class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)

class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=20)
    role: Optional[UserRole] = None
    branch_id: Optional[str] = None
    status: Optional[UserStatus] = None
    hire_date: Optional[datetime] = None
    photo_url: Optional[str] = None
    # password change is a separate endpoint: POST /users/{id}/reset-password

class UserInDB(UserBase):
    id: str = Field(alias="_id")
    password_hash: str   # never returned in responses
    is_active: bool = True
    deleted_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(populate_by_name=True)

class UserResponse(BaseModel):
    """Wire shape — NEVER includes password_hash."""
    id: str
    email: EmailStr
    full_name: str
    phone: Optional[str]
    role: UserRole
    branch_id: Optional[str]
    status: UserStatus
    hire_date: Optional[datetime]
    photo_url: Optional[str]
    is_active: bool
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
```

### User indexes
| Index                          | Purpose                                  |
|--------------------------------|------------------------------------------|
| `{ email: 1 }` unique          | Login lookup, uniqueness                 |
| `{ is_active: 1, role: 1 }`    | List-by-role                             |
| `{ branch_id: 1, role: 1 }`    | "Users in my branch"                     |
| `{ status: 1 }`                | Filter pending/active/suspended          |

### User field rules
- `email` lowercased on write.
- `password_hash` is bcrypt; `password` field exists **only** in
  `UserCreate` and the reset-password endpoint body, never in
  `UserResponse`.
- A user **cannot deactivate themselves** — enforced in
  `users.py` service layer.
- `branch_id` is **required** for `branch_manager`, `branch_accountant`,
  `driver`, `conductor`. For HQ roles (`owner`, `general_manager`,
  `operations_manager`, `fleet_manager`, `chief_accountant`,
  `super_admin`) it is optional and typically `None`.
- `last_login_at` is set on every successful `POST /auth/login`.

---

## 3 · Vehicle

Mongo collection: **`vehicles`**

```python
class VehicleType(str, Enum):
    BUS = "bus"
    MINIBUS = "minibus"
    TRUCK = "truck"

class VehicleStatus(str, Enum):
    AVAILABLE = "available"
    ON_TRIP = "on_trip"
    MAINTENANCE = "maintenance"
    GROUNDED = "grounded"

class VehicleDocument(BaseModel):
    """Each document tracks a single paper with expiry."""
    document_type: str = Field(min_length=2, max_length=40)
    # e.g. "insurance", "roadworthiness", "hackney_permit"
    reference_no: Optional[str] = Field(default=None, max_length=80)
    issued_at: Optional[datetime] = None
    expires_at: datetime
    file_url: Optional[str] = None

class VehicleBase(BaseModel):
    reg_number: str = Field(min_length=3, max_length=20,
                             pattern=r"^[A-Z0-9-]+$")
    type: VehicleType
    capacity_seats: int = Field(ge=1, le=200)
    capacity_kg: int = Field(ge=0, le=50000)
    branch_id: str
    home_terminal_id: Optional[str] = None
    status: VehicleStatus = VehicleStatus.AVAILABLE
    current_odometer_km: int = Field(ge=0, default=0)
    current_fuel_level: float = Field(ge=0, le=100, default=0)  # percent
    documents: list[VehicleDocument] = Field(default_factory=list)

class VehicleCreate(VehicleBase):
    pass

class VehicleUpdate(BaseModel):
    reg_number: Optional[str] = Field(default=None, min_length=3, max_length=20,
                                       pattern=r"^[A-Z0-9-]+$")
    type: Optional[VehicleType] = None
    capacity_seats: Optional[int] = Field(default=None, ge=1, le=200)
    capacity_kg: Optional[int] = Field(default=None, ge=0, le=50000)
    home_terminal_id: Optional[str] = None
    status: Optional[VehicleStatus] = None
    current_odometer_km: Optional[int] = Field(default=None, ge=0)
    current_fuel_level: Optional[float] = Field(default=None, ge=0, le=100)
    documents: Optional[list[VehicleDocument]] = None

class VehicleInDB(VehicleBase):
    id: str = Field(alias="_id")
    is_active: bool = True
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(populate_by_name=True)

class VehicleResponse(VehicleInDB):
    pass
```

### Vehicle indexes
| Index                          | Purpose                              |
|--------------------------------|--------------------------------------|
| `{ reg_number: 1 }` unique     | Plate uniqueness                     |
| `{ branch_id: 1, status: 1 }`  | "Available buses at my branch"       |
| `{ is_active: 1, type: 1 }`    | List-by-type                         |
| `{ "documents.expires_at": 1 }` | Document-expiry alerts (Sprint B)   |

### Vehicle field rules
- `branch_id` is the owning branch (where it's registered, who maintains it).
- `home_terminal_id` is the gate it parks at — typically equal to
  `branch_id` but allows a Lagos HQ branch to have a satellite terminal
  as a `home_terminal`. If omitted, defaults to `branch_id`.
- `documents` is an array. Sprint A **reads and writes** the array as
  a whole on update; **adding a single document** is a Sprint B
  endpoint (`POST /vehicles/{id}/documents`) — for now, the entire
  array is replaced on PATCH.

---

## 4 · Driver

Mongo collection: **`drivers`**

```python
class DriverStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ON_LEAVE = "on_leave"

class DriverBase(BaseModel):
    user_id: str
    license_no: str = Field(min_length=3, max_length=40)
    license_expiry: datetime
    years_experience: int = Field(ge=0, le=60, default=0)
    status: DriverStatus = DriverStatus.ACTIVE

class DriverCreate(DriverBase):
    """user_id refers to an existing User with role=driver."""
    pass

class DriverUpdate(BaseModel):
    license_no: Optional[str] = Field(default=None, min_length=3, max_length=40)
    license_expiry: Optional[datetime] = None
    years_experience: Optional[int] = Field(default=None, ge=0, le=60)
    status: Optional[DriverStatus] = None

class DriverInDB(DriverBase):
    id: str = Field(alias="_id")
    branch_id: Optional[str] = None   # denormalized from user; convenience for queries
    is_active: bool = True
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(populate_by_name=True)

class DriverResponse(BaseModel):
    """Response includes the user snapshot — see Open Decision #2."""
    id: str
    user_id: str
    license_no: str
    license_expiry: datetime
    years_experience: int
    status: DriverStatus
    branch_id: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # Optional denormalized user fields — populated on read:
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
```

### Driver indexes
| Index                          | Purpose                                |
|--------------------------------|----------------------------------------|
| `{ user_id: 1 }` unique        | One driver per user                    |
| `{ license_no: 1 }`            | Lookup by license                      |
| `{ is_active: 1, status: 1 }`  | List filter                            |
| `{ license_expiry: 1 }`        | Expiry alerts (Sprint B)               |
| `{ branch_id: 1 }`             | Drivers-in-branch queries              |

### Driver field rules
- `user_id` points at a User whose role is `driver`. The corresponding
  User is **created first** via `POST /users`; the Driver is then
  created referencing that user. Service layer enforces role match.
- `branch_id` is denormalized from `user.branch_id` at write time so
  branch-scoped queries don't have to join.
- `license_expiry` is a hard requirement at create time.

---

## 5 · Conductor

Mongo collection: **`conductors`**

```python
class ConductorStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ON_LEAVE = "on_leave"

class ConductorBase(BaseModel):
    user_id: str
    badge_no: str = Field(min_length=2, max_length=20,
                           pattern=r"^[A-Z0-9-]+$")
    status: ConductorStatus = ConductorStatus.ACTIVE

class ConductorCreate(ConductorBase):
    pass

class ConductorUpdate(BaseModel):
    badge_no: Optional[str] = Field(default=None, min_length=2, max_length=20,
                                     pattern=r"^[A-Z0-9-]+$")
    status: Optional[ConductorStatus] = None

class ConductorInDB(ConductorBase):
    id: str = Field(alias="_id")
    branch_id: Optional[str] = None
    is_active: bool = True
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(populate_by_name=True)

class ConductorResponse(BaseModel):
    id: str
    user_id: str
    badge_no: str
    status: ConductorStatus
    branch_id: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
```

### Conductor indexes
| Index                          | Purpose                                |
|--------------------------------|----------------------------------------|
| `{ user_id: 1 }` unique        | One conductor per user                 |
| `{ badge_no: 1 }` unique       | Badge uniqueness                       |
| `{ is_active: 1, status: 1 }`  | List filter                            |
| `{ branch_id: 1 }`             | Conductors-in-branch                   |

### Conductor field rules
- Same user-then-conductor pattern as Driver.
- `badge_no` is the physical badge the conductor carries; it's the
  visible identifier in field operations.

---

## 6 · Route

Mongo collection: **`routes`**

```python
class RouteType(str, Enum):
    INTRASTATE = "intrastate"
    INTERSTATE = "interstate"

class IntermediateStop(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    eta_minutes: int = Field(ge=0, le=1440)  # minutes from origin

class RouteBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    branch_id: str  # operating branch (which branch "owns" this route)
    type: RouteType
    origin_branch_id: str
    destination_branch_id: str
    origin_city: str = Field(min_length=1, max_length=80)
    destination_city: str = Field(min_length=1, max_length=80)
    distance_km: float = Field(ge=0, le=10000)
    base_fare_passenger: float = Field(ge=0, le=10_000_000)   # NGN
    base_fare_cargo_per_kg: float = Field(ge=0, le=1_000_000) # NGN
    estimated_duration_hours: float = Field(ge=0, le=72)
    intermediate_stops: list[IntermediateStop] = Field(default_factory=list)
    required_permits: list[str] = Field(default_factory=list)  # state codes
    is_active: bool = True

class RouteCreate(RouteBase):
    pass

class RouteUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    type: Optional[RouteType] = None
    origin_city: Optional[str] = Field(default=None, min_length=1, max_length=80)
    destination_city: Optional[str] = Field(default=None, min_length=1, max_length=80)
    distance_km: Optional[float] = Field(default=None, ge=0, le=10000)
    base_fare_passenger: Optional[float] = Field(default=None, ge=0)
    base_fare_cargo_per_kg: Optional[float] = Field(default=None, ge=0)
    estimated_duration_hours: Optional[float] = Field(default=None, ge=0, le=72)
    intermediate_stops: Optional[list[IntermediateStop]] = None
    required_permits: Optional[list[str]] = None
    is_active: Optional[bool] = None

class RouteInDB(RouteBase):
    id: str = Field(alias="_id")
    is_active: bool = True
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(populate_by_name=True)

class RouteResponse(RouteInDB):
    pass
```

### Route indexes
| Index                                       | Purpose                                |
|---------------------------------------------|----------------------------------------|
| `{ branch_id: 1, is_active: 1, name: 1 }`  | List, sort by name                     |
| `{ origin_branch_id: 1, destination_branch_id: 1 }` | "Routes between two branches" |
| `{ type: 1, is_active: 1 }`                 | Filter by interstate / intrastate      |

### Route field rules
- `origin_branch_id != destination_branch_id` — validated in service
  layer (a route must connect two distinct branches).
- `intermediate_stops` is an array; stops have ordering implicit by
  their position. `eta_minutes` is minutes from the route's origin
  (so the first stop is `eta_minutes > 0`).
- `required_permits` is a list of state codes (e.g. `["LAG", "OGU",
  "ANM"]` for Lagos→Anambam) for interstate compliance. **Sprint A
  just stores them; the alert logic is Sprint B/C.**
- For now, **no `is_active` filter override** — inactive routes are
  hidden from list. Owner can see them via `?include_inactive=true`.

---

## 7 · Audit Log

Mongo collection: **`audit_log`**

The audit log is **immutable**. Append-only. No endpoint mutates or
deletes log entries. Owner + SuperAdmin can read it; that read
endpoint is a Sprint B concern. Sprint A **only writes** to it.

```python
class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"          # soft delete
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"
    LOGIN = "login"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    PASSWORD_RESET = "password_reset"
    ROLE_CHANGE = "role_change"

class AuditLogEntry(BaseModel):
    id: str = Field(alias="_id")
    actor_id: str                # user who performed the action
    actor_email: str             # denormalized for forensic reads
    actor_role: str              # denormalized
    ts: datetime                 # UTC, server time
    action: AuditAction
    entity_type: str             # "branch" | "user" | "vehicle" |
                                 # "driver" | "conductor" | "route" |
                                 # "auth"
    entity_id: Optional[str]     # null for collection-level events
    before: Optional[dict]       # entity state before (None on create)
    after: Optional[dict]        # entity state after (None on delete)
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    reason: Optional[str] = None  # free-text for things like "deactivate"
```

### Audit log indexes
| Index                              | Purpose                                |
|------------------------------------|----------------------------------------|
| `{ ts: -1 }`                       | Most-recent first                      |
| `{ actor_id: 1, ts: -1 }`          | "Everything this user did"             |
| `{ entity_type: 1, entity_id: 1, ts: -1 }` | "History of this entity"        |
| `{ action: 1, ts: -1 }`            | "All login_failed events"              |

### Audit log writing rules
- Every `POST` (create) → log with `before=None`, `after=<new entity>`.
- Every `PATCH` (update) → log with `before=<old>`, `after=<new>`.
  Only fields that actually changed are stored (see Open Decision #3).
- Every `DELETE` (soft) → log with `before=<old>`, `after=None`.
- `POST /auth/login` (success) → log action=`login`, `entity_type="auth"`,
  `entity_id=<user_id>`, `after=None`. (We do NOT log the password or
  the JWT.)
- `POST /auth/login` (failure) → log action=`login_failed`, `after=None`.
  `actor_id` is the attempted email (or `None` if user not found).
- `POST /auth/logout` → log action=`logout`.
- `POST /users/{id}/reset-password` → log action=`password_reset`,
  `before/after` must NOT include the password hash.

### Audit log API contract (write-only in Sprint A)
Sprint A only has the **write** path: `services/audit.py` exposes
`write_audit_log(...)`. There is **no GET endpoint** in Sprint A —
read access is the Owner/SuperAdmin audit-viewer screen in Sprint B.

---

## 8 · Refresh token store

Mongo collection: **`refresh_tokens`**

Required to support `POST /auth/refresh` and `POST /auth/logout`.

```python
class RefreshTokenInDB(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    jti: str                       # JWT ID — unique per refresh token
    expires_at: datetime
    revoked: bool = False
    revoked_at: Optional[datetime] = None
    replaced_by: Optional[str] = None  # jti of the token that replaced this one
    user_agent: Optional[str] = None
    ip: Optional[str] = None
    created_at: datetime
```

### Refresh token indexes
| Index                              | Purpose                                |
|------------------------------------|----------------------------------------|
| `{ jti: 1 }` unique                | Lookup by token id                     |
| `{ user_id: 1, revoked: 1 }`       | "Active sessions for this user"        |
| `{ expires_at: 1 }`                | TTL index — expired tokens purged      |

Refresh tokens are **rotated on every `/auth/refresh`**: the old
`jti` is marked `revoked=True` and `replaced_by=<new jti>`. Logout
revokes the current refresh token.

---

## 9 · Login-attempt rate-limit store (in-memory for Sprint A)

Not a Mongo collection — a simple in-memory dict in
`routers/auth.py`:

```python
_attempts: dict[str, list[datetime]] = {}
# key: lowercased email
# value: list of attempt timestamps in the last 5 minutes
```

**Limit**: 5 attempts per email per 5-minute window. On the 6th
attempt, return `429` with `{ "detail": "Too many login attempts.
Try again in 5 minutes.", "type": "rate_limited" }`.

This is in-memory by design — Sprint A is single-instance. The
Redis-backed version is a Sprint B hardening task.

---

## 10 · Seed data (one-time, at first boot)

The backend MUST ship a `scripts/seed_admin.py` (called by both the
README and a one-shot `python -m app.scripts.seed_admin`) that
inserts a SuperAdmin user with:

```
email:     admin@transitos.local
password:  ChangeMe123!    (printed once, immediately changeable)
role:      super_admin
branch_id: None
```

The seed is **idempotent** — running it twice does not duplicate.
The seed script also creates the 6 indexes listed in §1–§6 and the
2 audit-log indexes.

---

## 11 · What is NOT in Sprint A

The following collections exist in the blueprint but are **not
implemented** in Sprint A. Backend must NOT create collections,
endpoints, or models for them:

- `trips` (Sprint B)
- `manifest_entries` (Sprint B)
- `fuel_logs` (Sprint B)
- `maintenance_records` (Sprint B)
- `expenses` (Sprint C)
- `cash_ups` (Sprint B — the variance feature)
- `expense_categories` (Sprint C)

**If the verifier sees a `trips` collection, model, or router in
Sprint A, the spec has been violated.**
