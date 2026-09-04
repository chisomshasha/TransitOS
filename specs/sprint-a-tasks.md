# TransitOS Sprint A — Tasks, File Layout & Screen Specs

> **Source of truth for the backend and frontend engineers.** This
> is the longest of the four spec files. It lays out exactly what
> files to create, what every screen looks like, and how the auth
> flow stitches them together. Backend and frontend engineers
> should each read the section that applies to them, then read
> `data-model.md` and `api-contract.md` for the wire shapes.

---

## 1 · Project root layout

```
/workspace/transitos/
├── README.md                  // human-facing: what's where, how to run both halves
├── INTEGRATION-REPORT.md      // written by the integration gate
├── backend/
│   ├── DELIVERABLE.md         // written by the backend engineer
│   ├── README.md
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .env.example
│   ├── pytest.ini
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── security.py
│   │   │   └── rbac.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── branch.py
│   │   │   ├── user.py
│   │   │   ├── vehicle.py
│   │   │   ├── driver.py
│   │   │   ├── conductor.py
│   │   │   ├── route.py
│   │   │   └── audit.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── branch.py
│   │   │   ├── user.py
│   │   │   ├── vehicle.py
│   │   │   ├── driver.py
│   │   │   ├── conductor.py
│   │   │   ├── route.py
│   │   │   └── common.py            // pagination request/response models
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── branches.py
│   │   │   ├── users.py
│   │   │   ├── vehicles.py
│   │   │   ├── drivers.py
│   │   │   ├── conductors.py
│   │   │   ├── routes.py
│   │   │   └── health.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py              // login/refresh/logout logic
│   │   │   └── audit.py             // write_audit_log helper
│   │   ├── scripts/
│   │   │   ├── __init__.py
│   │   │   └── seed_admin.py        // idempotent super-admin bootstrap
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── conftest.py          // shared fixtures, test DB, test client
│   │       ├── test_auth.py
│   │       ├── test_branches.py
│   │       ├── test_users.py
│   │       ├── test_vehicles.py
│   │       ├── test_drivers.py
│   │       ├── test_conductors.py
│   │       ├── test_routes.py
│   │       └── test_audit.py
│   └── scripts/
│       └── run_dev.sh               // `uvicorn app.main:app --reload --port 8000`
└── frontend/
    ├── DELIVERABLE.md               // written by the frontend engineer
    ├── README.md
    ├── app.json
    ├── package.json
    ├── tsconfig.json
    ├── tailwind.config.js
    ├── babel.config.js
    ├── metro.config.js
    ├── app/
    │   ├── _layout.tsx
    │   ├── index.tsx                // hydration gate
    │   ├── (auth)/
    │   │   ├── _layout.tsx
    │   │   └── login.tsx
    │   └── (tabs)/
    │       ├── _layout.tsx          // role-gated tab bar
    │       ├── dashboard.tsx
    │       ├── branches.tsx
    │       ├── users.tsx
    │       ├── vehicles.tsx
    │       ├── drivers.tsx
    │       ├── conductors.tsx
    │       ├── routes.tsx
    │       └── profile.tsx
    ├── components/
    │   ├── ui/                      // see design-tokens.md §7
    │   └── icons/
    │       └── index.tsx            // lucide-react-native re-exports
    ├── lib/
    │   ├── api.ts                   // axios instance + interceptors
    │   ├── query-client.ts          // TanStack Query client
    │   ├── auth-context.tsx         // useAuth() provider/hook
    │   ├── rbac.ts                  // canAccess(role, required[])
    │   ├── storage.ts               // expo-secure-store wrapper
    │   └── format.ts                // currency, date, odometer formatters
    ├── stores/
    │   └── authStore.ts             // minimal: { user, accessToken, refreshToken }
    ├── hooks/
    │   ├── useBranches.ts           // useQuery + useMutation wrappers
    │   ├── useUsers.ts
    │   ├── useVehicles.ts
    │   ├── useDrivers.ts
    │   ├── useConductors.ts
    │   └── useRoutes.ts
    └── assets/
        ├── icon.png                 // placeholder; owner will replace
        ├── splash.png
        └── adaptive-icon.png
```

> **The "5 Sprint A screens" reference in the brief is treated
> liberally here** — we have 6 entity-management screens
> (Branches, Users, Vehicles, Drivers, Conductors, Routes), plus
> Dashboard, Profile, and Login. The 5 named in the brief are
> likely Branches, Users, Vehicles, Drivers, Conductors (the five
> explicit management surfaces). We cover all of them in detail
> below; the same pattern repeats, so the implementer can
> extrapolate.

---

## 2 · Backend file responsibilities

### 2.1 `app/main.py`
- Build the `FastAPI()` app.
- Add CORS middleware with `allow_origins=settings.cors_origins`
  (default `["*"]` in dev; restrict in prod).
- Add a request-logging middleware that emits one INFO line per
  request: `method path status duration_ms`.
- Add a `security_headers` middleware that sets
  `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: strict-origin-when-cross-origin`.
- Add a global exception handler that converts uncaught exceptions
  to `{"detail": "Internal server error", "type": "internal_error"}`
  with status 500, and logs the traceback.
- `app.include_router(health.router)` at the **root** prefix.
- `app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])`.
- `app.include_router(branches.router, prefix="/api/v1/branches", tags=["branches"])`.
- (and so on for the other six routers).
- `@app.on_event("startup")` → `await create_indexes()` that creates
  every index from `data-model.md` §1–§7 and §8.

### 2.2 `app/core/config.py`
- `class Settings(BaseSettings)` with `model_config = SettingsConfigDict(env_file=".env", extra="ignore")`.
- Fields:
  - `mongodb_url: str = "mongodb://localhost:27017"`
  - `mongodb_db_name: str = "transitos"`
  - `jwt_secret_key: str` (required, no default — fail loud if missing)
  - `jwt_algorithm: str = "HS256"`
  - `access_token_expire_minutes: int = 15`
  - `refresh_token_expire_days: int = 7`
  - `cors_origins: list[str] = ["*"]`
  - `env: Literal["dev", "staging", "prod"] = "dev"`
  - `log_level: str = "INFO"`
- Singleton: `settings = Settings()`.

### 2.3 `app/core/database.py`
- `client: AsyncIOMotorClient = AsyncIOMotorClient(settings.mongodb_url)`
- `db = client[settings.mongodb_db_name]`
- `def get_db() -> AsyncIOMotorDatabase: return db`
- `async def create_indexes():` — declares the 13+ indexes from
  `data-model.md` (use `await collection.create_index(...)`).
- **Test isolation**: tests override `get_db` to point at
  `transitos_test` database, dropped between tests.

### 2.4 `app/core/security.py`
- `pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")`
- `def get_password_hash(p: str) -> str`
- `def verify_password(p: str, hashed: str) -> bool`
- `def create_access_token(sub: str, claims: dict) -> str` — JWT
  with `exp`, `iat`, `jti`, `sub`.
- `def create_refresh_token(sub: str) -> tuple[str, str]` —
  returns `(jwt, jti)`. The jti is a `uuid4().hex`.
- `def verify_token(token: str, expected_type: Literal["access","refresh"]) -> dict`
- `async def get_current_user(...)` — FastAPI dependency. Reads
  the `Authorization: Bearer ...` header, validates the JWT,
  loads the user from the DB, returns `UserInDB`. Optional
  `required_roles: list[Role] = None` param: if set, raises 403
  when the user's role isn't in the list.

### 2.5 `app/core/rbac.py`
- `class Role(str, Enum)` with the 10 values.
- `def require_roles(*roles)` — factory that returns a
  `Depends(get_current_user(required_roles=list(roles)))` for
  ergonomic route declarations. (Optional; the dependency above
  is sufficient.)

### 2.6 `app/models/`
- One file per entity, plus an `__init__.py` that re-exports all.
- Models are Pydantic v2, exactly as written in `data-model.md`.
- **No `bson.ObjectId` in models** — always `str`. The conversion
  happens in the response serialization layer.

### 2.7 `app/schemas/`
- Per-entity files with three classes: `*Create`, `*Update`, `*Response`.
- Common: `class Page(BaseModel, Generic[T])` with `items`, `total`,
  `page`, `totalPages`, `hasMore`.
- Common: `class SingleResponse(BaseModel, Generic[T])` with
  `data: T`.
- Auth: `LoginRequest`, `LoginResponse`, `RefreshResponse`,
  `ForgotPasswordRequest`, `ResetPasswordRequest`.

### 2.8 `app/services/auth.py`
- `async def login(db, email, password) -> LoginResponse` —
  verifies, enforces rate limit, updates `last_login_at`, writes
  audit log, creates tokens, stores refresh `jti`.
- `async def refresh(db, refresh_token) -> LoginResponse` — verifies,
  revokes old jti, creates new pair, writes audit log.
- `async def logout(db, refresh_token) -> None` — revokes jti,
  writes audit log.
- `async def change_password(db, user_id, new_password, actor) -> None`.

### 2.9 `app/services/audit.py`
- `async def write_audit_log(db, *, actor_id, actor_email, actor_role,
  action, entity_type, entity_id=None, before=None, after=None,
  ip=None, user_agent=None, request_id=None, reason=None) -> None`.
- Resolves `actor_email` / `actor_role` from the user record (or
  accepts `None` for failed-login events where the email isn't
  in the DB).
- `before`/`after` are deep-copied dicts; the helper **strips
  password_hash** if present.

### 2.10 `app/routers/*.py`
- Each router declares `router = APIRouter()`.
- Endpoints exactly as listed in `api-contract.md` §2–§7.
- All `POST/PATCH/DELETE` endpoints call `write_audit_log`.
- Branch-scoped endpoints add `query["branch_id"] = user.branch_id`
  in the service layer for `branch_manager`, `branch_accountant`,
  `driver`, `conductor`.
- The `Driver` and `Conductor` create endpoints accept only
  `user_id`; the service layer looks up the user and copies
  `branch_id` into the denormalized field.

### 2.11 `app/scripts/seed_admin.py`
- Idempotent. Inserts/updates a super_admin user.
- Prints the password **once** to stdout (in dev mode only).
- Creates the indexes by calling `await create_indexes()`.
- Wired into the README as `python -m app.scripts.seed_admin`.

### 2.12 `app/tests/`
- `conftest.py` provides:
  - `event_loop` (asyncio)
  - `db` fixture — `transitos_test`, dropped on teardown
  - `client` fixture — `httpx.AsyncClient(app=app, base_url="http://test")`
  - `super_admin_token`, `owner_token`, `branch_manager_token` —
    pre-built users with tokens for RBAC tests
- Tests follow FastAPI conventions, using `pytest-asyncio`.

### 2.13 Backend test inventory (minimum, per `verify_prompt`)
1. **Auth**
   - login with correct credentials → 200, returns tokens
   - login with wrong password → 401
   - login with non-existent email → 401 (does not leak existence)
   - login 6 times in 5 min → 429 on the 6th
   - login with `is_active=False` user → 403
   - `/me` with valid token → 200, returns user
   - `/me` with no token → 401
   - `/me` with malformed token → 401
   - `refresh` with valid token → new pair, old token rejected on next refresh
   - `logout` → 204; subsequent `refresh` of the same token → 401
2. **Branches**
   - list as Owner → 200
   - create as Owner → 201, code is unique
   - create as Driver → 403
   - list as branch_manager → only own branch returned
   - deactivate branch → 200, list with `include_inactive=true` includes it
3. **Users**
   - create as Owner → 201, password hash stored, response excludes hash
   - create with duplicate email → 409
   - create with role=driver and no branch_id → 422
   - list as branch_manager → only own-branch users
   - deactivate as Owner → 200
   - deactivate self → 403
   - change own role to "driver" → 403
4. **Vehicles / Drivers / Conductors / Routes**
   - create + list happy path for each
   - create as unauthorized role → 403
   - branch-scoping: branch_manager only sees own branch
   - route origin == destination → 422
   - driver create with user_id pointing at non-driver User → 422
5. **Audit log**
   - create branch writes a `create` log entry with `actor_id`,
     `after` payload, no `before`
   - update branch writes `update` with diff
   - soft-delete writes `delete` with `before`, no `after`
   - login failure writes `login_failed` with `actor_id=null` for
     non-existent email

Total: **~35 test cases.** All must pass.

---

## 3 · Frontend file responsibilities

### 3.1 `app/_layout.tsx`
- Root `<Stack>` with one screen at startup (`index.tsx`).
- Wraps everything in:
  ```tsx
  <QueryClientProvider client={queryClient}>
    <SafeAreaProvider>
      <AuthProvider>
        <Toast />
        <Stack screenOptions={{ headerShown: false }} />
      </AuthProvider>
    </SafeAreaProvider>
  </QueryClientProvider>
  ```

### 3.2 `app/index.tsx`
- The hydration gate. Renders `<Spinner size="lg" />` full-screen.
- Inside `<AuthProvider>`'s `useEffect`, on mount:
  1. Read `access_token` from secure store.
  2. If present, call `GET /auth/me`. On success, populate
     `authStore` and `router.replace("/(tabs)/dashboard")`. On
     401, try `POST /auth/refresh`. On success, retry `/me`. On
     failure, `authStore.logout()` and `router.replace("/(auth)/login")`.
  3. If no token, `router.replace("/(auth)/login")`.

### 3.3 `app/(auth)/_layout.tsx`
- `<Stack screenOptions={{ headerShown: false }} />`.

### 3.4 `app/(auth)/login.tsx`
See §4.1 below for the full spec.

### 3.5 `app/(tabs)/_layout.tsx`
- Role-gated tab bar. **The fix for the original TransHub "blank
  dashboard" bug** lives here:
  ```tsx
  const { user, isLoading, isAuthenticated } = useAuth();
  if (isLoading) return <Spinner size="lg" />;
  if (!isAuthenticated) {
    return <Redirect href="/(auth)/login" />;
  }
  return <Tabs /* ... see below ... */ />;
  ```
- The visible tabs are computed from the user's role:
  | Tab        | Roles allowed                                                  |
  |------------|----------------------------------------------------------------|
  | Dashboard  | all                                                            |
  | Branches   | sa, owner, gm, bm, om, fm, ca, ba                              |
  | Users      | sa, owner, gm, bm, ba                                          |
  | Vehicles   | sa, owner, gm, bm, om, fm, ca, ba                              |
  | Drivers    | sa, owner, gm, bm, om, fm                                      |
  | Conductors | sa, owner, gm, bm, om, fm                                      |
  | Routes     | sa, owner, gm, bm, om, fm, ca, ba                              |
  | Profile    | all                                                            |
  (Where `sa` = super_admin, `owner` = owner, `gm` = general_manager,
  `bm` = branch_manager, `om` = operations_manager, `fm` = fleet_manager,
  `ca` = chief_accountant, `ba` = branch_accountant.)
- Drivers and Conductors do **not** see the entity-management tabs
  in Sprint A — their app is "My Trip", which is Sprint B.

### 3.6 `lib/api.ts`
- `export const api = axios.create({ baseURL: extra.apiUrl, timeout: 15000 })`.
- Request interceptor: read `access_token` from auth store, attach
  `Authorization: Bearer <token>` if present.
- Response interceptor on 401:
  1. Read `refresh_token` from auth store.
  2. If absent → `authStore.logout()` + `router.replace("/(auth)/login")`.
  3. POST `/auth/refresh` with the refresh token in `Authorization`.
  4. On success, update store, retry original request.
  5. On failure, logout + redirect.
- A request-dedupe lock prevents parallel 401s from triggering
  multiple refresh calls (a `RefreshInFlight` promise singleton).

### 3.7 `lib/auth-context.tsx`
- The `AuthProvider` is mounted in `_layout.tsx`.
- On mount, kicks off the hydration flow described in §3.2.
- Exposes:
  ```ts
  interface AuthContextValue {
    user: UserResponse | null;
    isLoading: boolean;          // true while hydrating
    isAuthenticated: boolean;
    login: (email: string, password: string) => Promise<void>;
    logout: () => Promise<void>;
    refresh: () => Promise<void>;
  }
  ```

### 3.8 `lib/rbac.ts`
- `export function canAccess(userRole: Role, required: Role[]): boolean`
- `export const TABS_BY_ROLE: Record<Role, TabId[]>` — single
  source of truth for which tabs a role sees.
- The `(tabs)/_layout.tsx` imports `TABS_BY_ROLE` and filters.

### 3.9 `stores/authStore.ts`
- Minimal Zustand store:
  ```ts
  interface AuthStore {
    user: UserResponse | null;
    accessToken: string | null;
    refreshToken: string | null;
    setSession: (u, at, rt) => void;
    updateUser: (u) => void;
    clear: () => void;
  }
  ```
- **No fetch logic** lives here. Server state lives in TanStack
  Query, not Zustand. This is the architectural rule that
  separates us from the original TransHub's sprawl.

### 3.10 `hooks/useBranches.ts` (and the five siblings)
- `useBranchesList(params)` — wraps `useQuery(['branches', params], () => api.get(...))`.
- `useCreateBranch()` — `useMutation` that invalidates `['branches']`.
- `useUpdateBranch()` — invalidates `['branches']` and `['branches', id]`.
- `useDeactivateBranch()` — same.
- Same pattern for `useUsers`, `useVehicles`, `useDrivers`,
  `useConductors`, `useRoutes`.

### 3.11 `lib/format.ts`
- `formatNGN(amount: number): string` — `"₦15,000.00"` (Nigerian
  Naira, 2 decimals, comma thousands).
- `formatDate(iso: string): string` — `"Jun 4, 2026"`.
- `formatDateTime(iso: string): string` — `"Jun 4, 2026 · 12:34"`.
- `formatOdometer(km: number): string` — `"12,345 km"`.

---

## 4 · Screen specs

Every screen follows the same template:
- **Header** — screen title + (sometimes) "+ Add" button in the
  top-right. The header is provided by the screen itself (Expo
  Router `<Stack.Screen options={{ title }} />` is acceptable for
  non-tabbed screens).
- **Loading state** — 3–5 `<Skeleton />` lines matching the
  expected list shape.
- **Error state** — full-screen retry: icon + "Couldn't load" + a
  primary `<Button label="Retry" onPress={refetch} />`.
- **Empty state** — `<EmptyState />` with copy per screen.
- **List** — `<FlatList>` (or `<ScrollView>` for short lists)
  with `<Card>` items.

### 4.1 `(auth)/login.tsx`

**What the user sees**
- Centered TransitOS logo (the `icon.png` asset), 96pt, on a
  white surface.
- "Welcome back" `text-h1` title, "Sign in to your account"
  `text-caption` subtitle.
- `<Field label="Email" required>` wrapping `<Input
  keyboardType="email-address" autoCapitalize="none" />`.
- `<Field label="Password" required>` wrapping `<Input
  secureTextEntry />`.
- A "Forgot password?" link below the password field — Sprint A
  stub: tapping shows a `<Toast message="Password reset is coming
  in Sprint B. Ask your administrator for now." variant="info" />`.
- `<Button label="Sign in" fullWidth loading={isPending} />`.
- Below the form, in `text-caption text-neutral-500`:
  "Need an account? Contact your administrator." — Sprint A has
  no self-signup.

**API calls on mount**: none.

**Mutations possible**:
- `POST /auth/login` on submit. On success, populate
  `authStore`, `router.replace("/(tabs)/dashboard")`.

**Errors**:
- 401 (wrong credentials) → inline error: "Email or password is
  incorrect." + a `<Toast variant="error" />`.
- 429 (rate-limited) → inline error mirrors the backend `detail`
  verbatim.
- 403 (account suspended) → inline error: "This account is
  suspended. Contact your administrator."
- network error → inline error: "No internet connection. Try again."
  + Toast.

**Form validation (Zod + react-hook-form)**:
- `email` — valid email
- `password` — min 1 char (we don't enforce client-side complexity;
  the server is the source of truth)

### 4.2 `(tabs)/dashboard.tsx`

**What the user sees**
- Greeting card: "Hello, {full_name}" `text-h2`, "{roleLabel}" in
  a `<Badge variant="primary" />`, "{branchName}" in
  `text-caption text-neutral-500` (omitted if user has no branch).
- Quick actions row: 2–4 `<Card>` tiles, each linking to a tab
  the user has access to. Sprint A ships three tiles: "Branches",
  "Vehicles", "Routes" (filtered to those the role can see).
- An "About this build" card at the bottom: "TransitOS v0.1.0 ·
  Sprint A · {env label}" in `text-caption text-neutral-400`.

**API calls on mount**
- `GET /auth/me` is hydrated globally by `AuthProvider` — this
  screen does **not** re-fetch.
- `GET /branches?limit=1` to confirm the API is reachable (and
  show "X branches" if the user can read branches).
- `GET /vehicles?limit=1` and `GET /routes?limit=1` similarly
  (only the ones the role can see).

**Mutations possible**: none. This is read-only.

**Empty state copy**: this screen never goes empty — if all quick
actions are unavailable, show: "Nothing to manage yet. Ask an
administrator to assign you a role."

### 4.3 `(tabs)/branches.tsx`

**What the user sees**
- Header: "Branches" + "+ Add branch" `<Button variant="primary"
  size="sm" />` visible **only** to super_admin and owner.
- A `<SearchBar>` (an Input with a search icon) — filters by name,
  city, or code. (The "SearchBar" is a one-off in this screen; we
  don't promote it to a primitive in Sprint A.)
- List of `<Card>` items:
  - Top row: branch name (`text-body-strong`) + a `<Badge>` for
    status (`active` = success, `suspended` = warning).
  - Middle row: "{code} · {city}, {state}" `text-caption`.
  - Bottom row: optional "Manager: {manager_name}" if assigned.
- Tapping a card opens a read-only `<Modal>` with full branch
  details + an "Edit" button (super_admin/owner only) and a
  "Set manager" button (super_admin/owner only).
- Long-press (or a kebab menu on the card) shows: Edit, Set
  Manager, Deactivate (super_admin/owner only). Driver/Conductor
  roles never reach this screen.

**API calls on mount**:
- `GET /branches?page=1&limit=20&search={query}`.
- `GET /users?role=branch_manager&limit=100` (for the "Set
  manager" picker) — only when the modal is opened, not on mount.

**Mutations possible** (super_admin / owner only):
- `POST /branches` (from the "Add" button → form modal)
- `PATCH /branches/{id}` (from the Edit modal)
- `POST /branches/{id}/deactivate`
- `POST /branches/{id}/manager` (assign a branch manager)

**Add/Edit form fields**:
- name (required)
- code (required, uppercase, alphanumeric + dash, unique)
- city (required)
- state (required)
- address (required)
- contact_phone (optional)
- contact_email (optional)
- gps.lat, gps.lng (optional, two numeric fields)
- bank_account.{bank, number, name} (optional, three fields)

**Empty state copy**:
> **"No branches yet"** `text-h3`
>
> "Branches are the gate where trips start and end. Add your first
> branch to begin managing vehicles and routes."
>
> [Add branch] (visible only to super_admin/owner)

For branch-scoped roles who have no branch assigned (shouldn't
happen, but defensively):
> "You aren't assigned to a branch yet. Contact your administrator."

### 4.4 `(tabs)/users.tsx`

**What the user sees**
- Header: "Users" + "+ Add user" button (super_admin/owner only).
- Search bar — matches email or full_name.
- Role filter `<Select>`: "All roles", "Owner", "Branch Manager",
  "Driver", etc. Multi-select comes in Sprint B.
- List of `<Card>` items:
  - Top: avatar (initials, 40pt circle) + full_name +
    `<Badge variant="primary">{roleLabel}</Badge>`.
  - Middle: email `text-caption`.
  - Bottom: "{branchName}" (or "— HQ —" if no branch) +
    "Last login: {formatDateTime(last_login_at)}" or "Never".
- Tapping a card opens a read-only modal with all fields + a
  kebab menu: Activate, Deactivate, Reset password.
- The logged-in user cannot deactivate themselves — the UI greys
  out their own row and the "Deactivate" option is disabled with
  a tooltip "You can't deactivate your own account."

**API calls on mount**:
- `GET /users?page=1&limit=20&search={q}&role={r}`.
- `GET /branches?limit=100` (to resolve branch_id → branch.name
  in the list rendering).

**Mutations possible** (super_admin/owner only):
- `POST /users` (from the Add modal)
- `PATCH /users/{id}` (from the Edit modal)
- `POST /users/{id}/activate`
- `POST /users/{id}/deactivate`
- `POST /users/{id}/reset-password` (with a confirm modal: "Reset
  password for {name}? They'll be logged out and emailed a new
  one." — Sprint A: just generates one inline and shows it once
  in a Toast for the admin to copy.)

**Add/Edit form fields**:
- email (required, valid email, unique)
- full_name (required)
- phone (optional)
- role (required, `<Select>` from the 10 role enum values)
- branch_id (required iff role is branch-scoped; rendered as a
  `<Select>` populated from `GET /branches`)
- password (required on create, hidden on edit; separate
  "Reset password" flow on the kebab)
- hire_date (optional, date string)
- photo_url (optional, plain text input — file picker is Sprint B)

**Empty state copy**:
> **"No users yet"** `text-h3`
>
> "Add drivers, conductors, branch managers, and HQ staff. They'll
> get an email with a sign-in link."
>
> [Add user] (visible only to super_admin/owner)

### 4.5 `(tabs)/vehicles.tsx`

**What the user sees**
- Header: "Vehicles" + "+ Add vehicle" button (sa/owner/gm/bm/fm).
- Filter row: `<Select>` for `type` (bus/minibus/truck/all) and
  `<Select>` for `status` (available/on_trip/maintenance/grounded/all).
- List of `<Card>` items:
  - Top row: reg_number `text-body-strong` + `<Badge>` for status.
  - Middle: "{type} · {capacity_seats} seats · {capacity_kg}kg".
  - Bottom row: "Branch: {branchName} · Odometer: {km} km".
  - A small warning icon (lucide `AlertTriangle`) appears at the
    right of the card if any document in `documents` expires
    within 30 days. Tapping the warning shows the expiry date.
- Tapping a card opens a read-only modal with all fields +
  kebab: Edit, Deactivate.

**API calls on mount**:
- `GET /vehicles?page=1&limit=20&type={t}&status={s}`.
- `GET /branches?limit=100` (for branch name resolution).

**Mutations possible**:
- `POST /vehicles`
- `PATCH /vehicles/{id}`
- `POST /vehicles/{id}/deactivate`

**Add/Edit form fields**:
- reg_number (required, uppercase)
- type (required, Select)
- capacity_seats (required, integer ≥ 1)
- capacity_kg (required, integer ≥ 0)
- branch_id (required, Select; defaults to user's branch for
  branch-scoped roles)
- home_terminal_id (optional, Select from branches)
- status (required, Select)
- current_odometer_km (optional, integer ≥ 0)
- current_fuel_level (optional, 0–100, percent)
- documents: Sprint A: empty list. The "Add document" UI is
  Sprint B.

**Empty state copy**:
> **"No vehicles registered"** `text-h3`
>
> "Add your buses, minibuses, and trucks. Each vehicle is tied to
> a branch and a terminal."
>
> [Add vehicle]

### 4.6 `(tabs)/drivers.tsx`

**What the user sees**
- Header: "Drivers" + "+ Add driver" button (sa/owner/gm/bm/fm).
- Search bar — matches driver name or license_no.
- Filter row: `<Select>` for `status` (active/suspended/on_leave/all).
- List of `<Card>` items:
  - Top row: full_name `text-body-strong` + status `<Badge>`.
  - Middle: "License: {license_no} · Expires: {formatDate(license_expiry)}".
  - Bottom: "{years_experience} yrs · {branchName}".
  - A warning icon appears if `license_expiry` is within 30 days.
- Tapping opens a read-only modal + kebab: Edit, Deactivate.

**API calls on mount**:
- `GET /drivers?page=1&limit=20&search={q}&status={s}`.
- `GET /users?role=driver&limit=100` (for the "Add driver" picker
  — the admin picks an existing driver User, then fills in
  license info).

**Mutations possible**:
- `POST /drivers` (the user_id is selected from existing
  driver-role users; the rest is license info)
- `PATCH /drivers/{id}`
- `POST /drivers/{id}/deactivate`

**Add/Edit form fields**:
- user_id (required, Select — **filtered to users whose role is
  `driver`**; on edit, locked)
- license_no (required)
- license_expiry (required, date)
- years_experience (required, integer)
- status (required, Select)

**Empty state copy**:
> **"No drivers registered"** `text-h3`
>
> "Drivers are the people behind the wheel. Add a user with the
> Driver role first, then add their license details here."
>
> [Add driver]

### 4.7 `(tabs)/conductors.tsx`

**What the user sees**
- Header: "Conductors" + "+ Add conductor" button.
- Search bar — matches name or badge_no.
- List of `<Card>` items:
  - Top row: full_name `text-body-strong` + status `<Badge>`.
  - Middle: "Badge: {badge_no}".
  - Bottom: "{branchName}".
- Tapping opens a read-only modal + kebab: Edit, Deactivate.

**API calls on mount**:
- `GET /conductors?page=1&limit=20&search={q}`.
- `GET /users?role=conductor&limit=100` (for the "Add conductor"
  picker).

**Mutations possible**:
- `POST /conductors` (user_id picked from conductor-role users)
- `PATCH /conductors/{id}`
- `POST /conductors/{id}/deactivate`

**Add/Edit form fields**:
- user_id (required, Select filtered to conductor-role users)
- badge_no (required, unique, uppercase)
- status (required, Select)

**Empty state copy**:
> **"No conductors registered"** `text-h3`
>
> "Conductors are the people collecting cash on the bus. Add a
> user with the Conductor role first, then issue them a badge."
>
> [Add conductor]

### 4.8 `(tabs)/routes.tsx`

**What the user sees**
- Header: "Routes" + "+ Add route" button (sa/owner/gm/om/bm).
- Filter row: `<Select>` for `type` (intrastate/interstate/all).
- List of `<Card>` items:
  - Top row: route name `text-body-strong` + `<Badge>` for type
    (interstate = primary, intrastate = neutral).
  - Middle: "{originCity} → {destinationCity} · {distance_km} km
    · {estimated_duration_hours} h".
  - Bottom: "Base fare: {formatNGN(base_fare_passenger)} pax ·
    {formatNGN(base_fare_cargo_per_kg)}/kg".
  - Stops count: "{stops.length} intermediate stops" — tappable
    in the modal.
- Tapping opens a read-only modal with all fields (including the
  full stops list and required permits) + kebab: Edit, Deactivate.

**API calls on mount**:
- `GET /routes?page=1&limit=20&type={t}`.
- `GET /branches?limit=100` (to resolve branch names in the
  origin/destination pickers).

**Mutations possible**:
- `POST /routes`
- `PATCH /routes/{id}`
- `POST /routes/{id}/deactivate`

**Add/Edit form fields**:
- name (required)
- branch_id (required, Select; the operating branch)
- type (required, Select)
- origin_branch_id (required, Select)
- destination_branch_id (required, Select; **must differ from
  origin** — error inline)
- origin_city, destination_city (required)
- distance_km (required, number ≥ 0)
- base_fare_passenger (required, NGN, ≥ 0)
- base_fare_cargo_per_kg (required, NGN, ≥ 0)
- estimated_duration_hours (required, ≥ 0)
- intermediate_stops: list of `{name, lat, lng, eta_minutes}` —
  rendered as a "stops" sub-form; "+ Add stop" appends a row.
  Each row has 4 fields. Tap the trash icon to remove.
- required_permits: list of state codes (free text input that
  uppercases on blur; chip list with X to remove).

**Empty state copy**:
> **"No routes defined"** `text-h3`
>
> "Routes connect two branches. Define a route to start scheduling
> trips on it."
>
> [Add route]

### 4.9 `(tabs)/profile.tsx`

**What the user sees**
- Top: avatar circle (initials, 80pt) + full_name `text-h2` +
  role `<Badge variant="primary" />` + email + phone (if any).
- Section "Branch": branch name + city (or "No branch assigned").
- Section "Account":
  - "Member since {formatDate(created_at)}"
  - "Last login {formatDateTime(last_login_at)}"
- Section "Security":
  - "Reset password" button → opens a modal with a single
    password field. On submit, calls `POST /auth/reset-password`
    **(self only, with current password) — see Open Decision #4**.
    The user already has a token; we don't need the email-flow
    version in Sprint A. The reset endpoint we ship is
    `POST /auth/me/password` (not the `/auth/reset-password`
    public one), and it requires the **current password** for
    verification. (The backend must add this small route — it's
    listed in `api-contract.md` §1.7 as a Sprint A addition.)
- A "Sign out" `<Button variant="danger" fullWidth label="Sign out" />`
  at the bottom.

**API calls on mount**:
- `GET /auth/me` is already cached by the AuthProvider — no
  re-fetch.

**Mutations possible**:
- `POST /auth/logout` (from the Sign out button).
- `POST /auth/me/password` (from the Reset password modal).

**Empty state copy**: not applicable.

### 4.10 `index.tsx` (the hydration gate)

**What the user sees**:
- Full-screen `<Spinner size="lg" />` centered on a `bg-neutral-50`
  surface, with the TransitOS logo above it (subtle, 56pt,
  `opacity-60`).

**API calls on mount**:
- Reads `access_token` from secure store.
- If present: `GET /auth/me`. On 401, `POST /auth/refresh`,
  retry `/me`.
- If not present: redirect to login.
- **No manual refetch is exposed.** A pull-to-refresh on the
  Dashboard refreshes `/auth/me` once.

**Mutations possible**: none.

**Empty state copy**: not applicable — this screen never shows
content, only a spinner and a redirect.

---

## 5 · Auth flow — end to end

### 5.1 Login form
- See §4.1. Uses `react-hook-form` + `zod` (`email` and `password`
  schemas).
- On submit:
  1. Set `isSubmitting=true` (RHF state). The button shows
     `loading`.
  2. Call `authContext.login(email, password)`.
  3. On success: `router.replace("/(tabs)/dashboard")`.
  4. On error: display inline, clear the password field, keep
     focus on the password field.

### 5.2 Token storage
- `accessToken` and `refreshToken` are stored in `expo-secure-store`
  via `lib/storage.ts`. Keys: `transitos.accessToken`,
  `transitos.refreshToken`. The `user` object is **not** persisted
  — it is rehydrated from `GET /auth/me` on every cold start.

### 5.3 Redirect rules
| Source state                          | Target on hydration                |
|---------------------------------------|------------------------------------|
| No token in secure store              | `/(auth)/login`                    |
| Token present, `/me` 200              | `/(tabs)/dashboard`                |
| Token present, `/me` 401              | `POST /auth/refresh` → retry       |
| Refresh 200, `/me` 200                | `/(tabs)/dashboard`                |
| Refresh 401 (token revoked/expired)   | Clear store, `/(auth)/login`       |
| Network error during hydration        | Stay on splash + `<Toast>` "No internet. Tap to retry." (a tap-on-splash retries) |
| Authenticated user navigates to login (e.g. via back button)  | `router.replace("/(tabs)/dashboard")` (the auth layout has no back button) |
| Unauthenticated user navigates to a tab | `router.replace("/(auth)/login")` |

The `(tabs)/_layout.tsx` gate is the **authoritative** check on
every screen render. Even if a stale navigation tries to render
a tab, the gate kicks in.

### 5.4 Role-based menu visibility
The tab bar in `(tabs)/_layout.tsx` is the primary menu.
Permissions are read from `TABS_BY_ROLE` in `lib/rbac.ts`:

```ts
export const TABS_BY_ROLE: Record<Role, TabId[]> = {
  super_admin:        ['dashboard','branches','users','vehicles','drivers','conductors','routes','profile'],
  owner:              ['dashboard','branches','users','vehicles','drivers','conductors','routes','profile'],
  general_manager:    ['dashboard','branches','users','vehicles','drivers','conductors','routes','profile'],
  branch_manager:     ['dashboard','branches','users','vehicles','drivers','conductors','routes','profile'],
  operations_manager: ['dashboard','branches','vehicles','drivers','conductors','routes','profile'],
  fleet_manager:      ['dashboard','branches','vehicles','drivers','conductors','routes','profile'],
  chief_accountant:   ['dashboard','branches','vehicles','routes','profile'],
  branch_accountant:  ['dashboard','branches','users','vehicles','routes','profile'],
  driver:             ['dashboard','profile'],
  conductor:          ['dashboard','profile'],
};
```

Notes:
- `users` is in branch_manager's tab list so they can see who's
  on their team (for dispatch) but the **mutations** on Users are
  still super_admin/owner-only — the server enforces that.
- `driver` and `conductor` see a near-empty app in Sprint A. Their
  real screen ("My Trip") arrives in Sprint B.

The `canAccess` helper is for in-page checks:
```ts
canAccess(user.role, ['super_admin', 'owner'])  // → boolean
```

### 5.5 Logout
- Triggered from `(tabs)/profile.tsx` "Sign out" button (and from
  any 401 the interceptor can't recover from).
- `authContext.logout()`:
  1. `POST /auth/logout` (with current access token).
  2. Clear secure store (`removeItem` for both token keys).
  3. `authStore.getState().clear()` — wipe Zustand state.
  4. `queryClient.clear()` — wipe TanStack Query cache.
  5. `router.replace("/(auth)/login")`.
- Network failure during the `POST /auth/logout` is **not** a
  blocker — we still clear local state and redirect. The backend
  is idempotent; the token will simply expire naturally.

---

## 6 · React Query conventions

- `staleTime: 30_000` for list queries.
- `gcTime: 5 * 60_000` (default is fine).
- All list queries are `['entity', params]` so `invalidateQueries`
  can target them.
- All detail queries are `['entity', id]`.
- Mutations on success call
  `queryClient.invalidateQueries({ queryKey: ['entity'] })` and,
  for the affected item, also `['entity', id]`.
- Optimistic updates are **not** used in Sprint A — the financial
  implications are too high; the user sees a brief loading state
  on the affected card and that's fine.
- `refetchOnWindowFocus: true` (default) is kept; the offline
  experience is graceful — TanStack Query serves stale data and
  shows a small "Updated {time}" caption.

---

## 7 · Network error UX

Anywhere `useQuery` returns an error, the screen renders a
full-page error state:
- lucide `WifiOff` icon, 48pt, `text-neutral-400`.
- "Couldn't reach the server" `text-h3`.
- "Check your connection and try again." `text-caption`.
- `<Button label="Retry" onPress={refetch} />`.
- A Toast at the top with the same message and a "Dismiss" action.

For 5xx errors, the message is "Something went wrong on our end.
Our team has been notified." — we **never** leak the backend
traceback to the user.

---

## 8 · What ships in Sprint A — checklist

Backend (per `verify_prompt` checks):
- [ ] `app/main.py` boots with `uvicorn app.main:app`
- [ ] All 7 routers are mounted under `/api/v1`
- [ ] 13+ Mongo indexes are created on startup
- [ ] 35+ pytest cases pass
- [ ] No hardcoded secrets
- [ ] `requirements.txt` pins versions
- [ ] `GET /health` returns 200

Frontend (per `verify_prompt` checks):
- [ ] `npx tsc --noEmit` produces 0 errors
- [ ] `npx expo export --no-bytecode --platform android` produces a JS bundle
- [ ] `app.json` has name, scheme, bundleIdentifier, jsEngine=jsc
- [ ] All 9 Sprint A screens exist and export defaults
- [ ] 12 design-system primitives in `components/ui/`
- [ ] `lib/query-client.ts` and `lib/api.ts` are real
- [ ] `(tabs)/_layout.tsx` gates on `isLoading`/`isAuthenticated`
- [ ] `(tabs)/users.tsx` (or layout) hides Users tab for non-Owner
- [ ] **Zero** raw `useEffect + fetch` in component bodies
- [ ] All data fetching goes through TanStack Query

If the verifier finds anything outside this checklist, it's a
defect.
