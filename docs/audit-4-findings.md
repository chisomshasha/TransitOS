# Fourth-pass audit — findings and fixes

**Date:** 2026-10-31
**Method:** the three-pass method in `docs/IT-DEVELOPER-GUIDE.md` — A (compiles),
B (the two halves agree), C (does it actually run) — followed by the §5
pre-delivery gate.

**Surface:** 147 API operations · 45 screens · 10 roles · 6 state machines.

---

## 0 · Summary

| | |
|---|---|
| Backend suite | **255 passed** (was 201; 54 new regression tests) |
| Static contract checks | **10 / 10 PASS** (was 4 — 6 new) |
| Frontend typecheck | **0 errors** |
| Android JS bundle | **built**, 4.53 MB, `dist/_expo/static/js/android/` |
| Clean install from lockfile | **passes** in a fresh directory |
| Defects found | **21** (4 shipped-broken features, 1 security, 1 CI, 8 hardening, 3 money-loop, 2 money-loop side-effects, 2 dead buttons) |
| New guards | **8** (`fields`, `reachable`, `webview`, `url`, `matrix`, `guards`, + `styling`) |

Every guard added below was proved to **fail** when the defect it covers is
re-introduced. A check that cannot fail is worse than no check.

---

## 1 · Defects found and fixed

### 1.1 — Trip creation was 100 % broken (P0)

`CreateTripModal.tsx` sent a body the API rejects:

```
POST /trips  →  422  {"detail": "Field required", "type": "validation_error",
                        "errors": [{"loc": "body → branch_id", ...},
                                   {"loc": "body → scheduled_arrival", ...}]}
```

`TripBase` required `branch_id` and `scheduled_arrival`; the screen sent
neither. It also sent `fare_override` and `cargo_rate_override`, which the
API does not declare — the Pydantic models do not forbid unknown fields, so
those values were **silently dropped**.

Nothing caught it: `tsc` compares the front end's types against themselves;
the backend suite builds its own payloads; the static checker could not see
the body (see §2); the runtime contract test sent a body it derived from the
OpenAPI schema, so it agreed with the backend by construction.

**Fix**
* `backend/app/models/trip.py` — `branch_id` is now optional on `TripCreate`.
  The router already derives it from the route and the vehicle
  (`get_branch_id_for`) and overwrites whatever arrives.
* `frontend/components/admin/CreateTripModal.tsx` — sends
  `scheduled_arrival`, derived from the route's `estimated_duration_hours`.
  The fare / cargo / status inputs are **gone**: the API stores none of
  them, so collecting them was collecting data that is thrown away.
  A trip is created in `Planned`, which is where the state machine starts.
* Two regression tests in `backend/app/tests/test_trips.py`.

### 1.2 — The money loop was unreachable from the app (P0) — **FIXED**

Three endpoints exist, work, are tested — and **no screen could reach them**:

| Endpoint | Consequence |
|---|---|
| `PATCH /trips/{id}/status` | a trip could never advance, so it could never reach `closed` |
| `POST /trips/{id}/manifest` | the manifest could never be filled, so `total_revenue` was always 0 |
| `POST /cash-ups/{id}/submit` | a cash-up stayed a draft, so it could never be approved |

The chain, end to end: `POST /cash-ups` requires `trip.status == "closed"`
→ a trip can only become `closed` through `PATCH /trips/{id}/status` → which
the app never called. And even with a closed trip, `POST /cash-ups` creates a
**draft**, and only `POST /cash-ups/{id}/submit` makes it reviewable — also
never called. Revenue comes from the manifest
(`app/services/trips.py`: *"Recompute … total_revenue from manifest"*), and
the manifest could not be populated.

So the cash-up → approval → settlement chain could not complete, and every
settlement figure derived from `trip.total_revenue` was zero.

#### The fix

The money loop is now a set of screens, not a set of endpoints:

| What | Where | File |
|---|---|---|
| Trip status panel — *Start boarding*, *Confirm departure*, *Confirm arrival*, *Close trip*, *Cancel trip* (reason required) | Trips → tap a trip | `frontend/components/TripStatusPanel.tsx` |
| Manifest editor — *+ Passenger*, *+ Cargo*, remove an entry | Trips → tap a trip | `frontend/components/ManifestEditor.tsx` |
| Cash-up — *Save cash-up* (draft), *Submit for approval*, and the rejection reason | Trips → tap a trip | `frontend/components/CashUpSection.tsx` |
| *Submit for approval* on a draft row | More → Cash Ups | `frontend/app/(app)/cash-ups.tsx` |

Supporting changes:

- `frontend/lib/money-loop.ts` — the transition table and the role lists,
  mirrored from the backend, so the app can never offer a move the server
  would refuse.
- `frontend/lib/queries.ts` — a `useUpdateCashUp` hook. The screen already
  had an *"Update cash-up"* button, but it called `POST /cash-ups`, which
  the server refuses with *a cash-up already exists for this trip*. The
  button had never worked.
- The misleading toast — creating a cash-up said *"Cash-up submitted"* when
  it had only saved a draft. Now it says *"Cash-up saved as a draft"*.

#### Two backend defects the new screens exposed

1. **A removed manifest entry still counted towards the expected total.**
   `compute_expected_total()` read *every* manifest entry, including the
   soft-deleted ones, while the trip's own revenue, the manifest list and
   the waybill PDF all filtered them out. A conductor who removed a
   passenger who did not turn up was then judged against a fare nobody was
   going to pay — a false shortage on every such cash-up.
   Fixed in `app/services/cash_up.py`; regression test in
   `app/tests/test_trips.py`.
2. **The trip response dropped `cash_up_id`.** The approval service writes
   it onto the trip, and the front end has carried the field since the
   first release, but the response model did not declare it — so the app
   could never link a trip to its cash-up. Fixed in `app/models/trip.py`.

#### The guards

- `backend/app/tests/test_money_loop_frontend.py` — 26 tests: every
  money-loop endpoint is called from the app, none of them sits in the
  `KNOWN_UNREACHABLE` baseline, the front end's role lists and transition
  table match the back end's, and the whole loop runs end to end against
  the live API with the exact bodies the app sends. Three of the tests are
  **negative**: they remove the status panel, or hand the checker a guard
  table that offers a refused role, and assert the guard fires.
- `tools/contract/check.py` — the reachability check now follows the
  import closure, so a mutation owned by a *component* (not a screen) is
  no longer invisible to it. A new `guards` check reads the
  `ENDPOINT_GUARDS` table in `frontend/lib/rbac.ts` and fails if it offers
  an action to a role the server refuses, names a route that does not
  exist, or lists an endpoint no screen calls.
- The four `KNOWN_UNREACHABLE` entries for the money loop are **removed**,
  so the reachability guard covers them from now on.

### 1.3 — Stored XSS in both map WebViews (P0, security)

`app/(app)/map.tsx` and `components/ui/MapModal.tsx` build an HTML document
as a string and hand it to `react-native-webview`. Two injection points:

```js
var points = ${JSON.stringify(enriched)};              // 1. </script> breakout
m.bindPopup('<strong>' + p.label + '</strong>' + desc); // 2. HTML injection
```

* `JSON.stringify` does not escape `<`, so a value containing `</script>`
  closes the script block early.
* `p.label` (a vehicle's registration number), `p.driver_name` and the
  branch name are **free text a user can type** and were rendered as HTML.

The WebView runs JavaScript, loads remote Leaflet and OSM tiles, and can
post messages back into the app through `window.ReactNativeWebView`.

**Fix** — `frontend/lib/html.ts`:
* `jsonForScript()` escapes `<`, `>`, `&`, U+2028 and U+2029 (still valid
  JSON, cannot close the tag);
* `esc()` escapes `& < > " '` for the HTML context.

Both maps now use them, and `check.py`'s `webview` check stops the pattern
coming back.

### 1.4 — CI was silently skipping the RBAC regression test (P1)

`.github/workflows/ci.yml` had a missing line continuation:

```yaml
python -m pytest -q \
  app/tests/test_frontend_runtime_contract.py \
  app/tests/test_collection_consistency.py \
  app/tests/test_response_envelope.py
  app/tests/test_role_access_regressions.py     # ← no trailing "\"
```

The last line became a **second shell command**. The step exited 127, so
CI was red — and `test_role_access_regressions.py` (the guard for the 403
wall) was never executed. Fixed, and the job now also builds the Android
bundle and asserts the entry point exists.

### 1.5 — The routes screen shipped unstyled (P1)

`app/(app)/routes/index.tsx` was the only file in the app written with
NativeWind classes. **NativeWind was never wired**: no `nativewind/babel`
preset, no `withNativeWind` in Metro, and neither `react-native-worklets`
nor `react-native-reanimated` installed. React Native silently drops an
unknown `className` prop, so all 19 of its styles were dead — the build
passed, the typecheck passed, and the screen rendered with no flex, no
background and no spacing.

**Fix** — the screen now uses `StyleSheet.create`, exactly like its sibling
`app/(app)/vehicles/index.tsx`. The unusable toolchain (`nativewind`,
`tailwindcss`, `autoprefixer`, `postcss`, `clsx`, `tailwind-merge`) is
removed, the dead `className?: string` prop is removed from seven UI
primitives that silently ignored it, and `tools/contract/check_styling.py`
fails the build if a `className=` ever returns.

### 1.6 — Validation errors answered 400, not the documented 422 (P1)

`specs/api-contract.md`, `docs/TESTING_MANUAL.md` (the client-signature
document), `specs/data-model.md` and the frontend's own comments all
specify **422** for a body that fails validation. The backend overrode
FastAPI's handler to return **400**, so a client's UAT script would fail
against a correct build.

**Fix** — the handler now returns **422** with the contract's shape:

```json
{ "detail": "Password must be 10–128 characters and contain …",
  "type": "validation_error",
  "errors": [ { "loc": "body → new_password", "msg": "…", "type": "value_error" } ] }
```

`detail` names the first rule broken, so the toast the user sees is the
actual problem rather than "Validation error". `type` makes the existing
`getErrorType()` helper work for the first time. The router-level **400**
s for *semantic* refusals ("Vehicle does not exist", "Invalid trip_id") are
a deliberate, documented convention (`app/routers/_common.py`) and were left
alone — the specs were corrected to match them.

### 1.7 — `EXPO_PUBLIC_API_URL` was dead configuration (P1)

`resolveBaseURL()` preferred `app.json`'s `extra.apiUrl` over
`process.env.EXPO_PUBLIC_API_URL`, so the per-profile `env` blocks in
`eas.json` could never take effect — an operator changing the URL for a
build profile would get a binary that still pointed at the old backend.
Fixed: the environment variable wins (it is the only per-build knob), and
`eas.json` is aligned with `app.json`.

> **Both configured Railway URLs currently answer `404 Application not found`.**
> The backend is not deployed. See §4.

### 1.8 — The front-end scanner walked into `node_modules` (P1)

Every static check and the runtime contract test scan the front end's
TypeScript. They all did it with `Path.rglob()`, which descends into
`node_modules` and *then* discards the results with an
`if "node_modules" in p.parts` filter — a filter applied **after** the
walk. Two consequences, both measured:

**It was slow.** One scan of `frontend/` took **20.5 seconds** because it
walked hundreds of megabytes of installed packages.

**It crashed.** `rglob()` raises `FileNotFoundError` if a directory
disappears while it is walking. Running the backend suite while `npm ci`
was installing killed the test:

```
FileNotFoundError: .../frontend/node_modules/fsevents
```

This was found by exporting the codebase and re-running the suite from
the extracted copy — the first attempt at "does this archive actually
work?" failed.

**Fix** — `tools/contract/sources.py`: one walker that prunes the skipped
directories *before* descending, built on `os.walk` (which ignores a
directory vanishing mid-walk). Every scanner now uses it.

```
old rglob  : CRASH: FileNotFoundError (3.6s)
new walker : OK (107 files, 0.0s)
```

Pinned by `backend/app/tests/test_source_scanner.py` (5 tests), which
also asserts that the scanner still finds the real screens — a scanner
that returns nothing has silently stopped working.

### 1.9 — The API base URL was resolved twice, with opposite precedence (P1)

`lib/api.ts` resolved the backend URL as
`EXPO_PUBLIC_API_URL || extra.apiUrl || localhost`. `lib/auth-context.tsx`
— which makes the two bare `fetch` calls to `/auth/login` and
`/auth/refresh` — resolved it as `extra.apiUrl || EXPO_PUBLIC_API_URL`.
**Opposite order.**

The moment you use EAS build profiles to point at different backends,
login went to `app.json`'s URL while every other request went to the
profile's env var: the app authenticated against one backend and called
another. `eas.json` even carried a comment saying the two had to stay
in sync — which is exactly the kind of comment that stops being true.

**Fix** — `lib/auth-context.tsx` imports `resolveBaseURL()` from
`lib/api.ts`. One resolver, one source of truth. `tools/contract/check.py`
→ `url` fails the build if any other file resolves the URL itself.

This was found while preparing the pre-build checklist — i.e. by the
exact workflow the user was about to run.

### 1.10 — The password-reset email linked to a route that did not exist (P1)

`backend/app/services/auth.py` built the link as:

```python
f"{settings.frontend_url.rstrip('/')}/(auth)/reset-password?token={token}"
```

Two faults, both fatal to the link:

1. **Expo Router groups are not URL segments.** `(auth)` is a group;
   `app/(auth)/reset-password.tsx` is served at `/reset-password`. A URL
   containing `/(auth)/` 404s.
2. **There was no `reset-password` route at all.** The app only had a
   "forgot password" screen that could complete the flow if the user
   pasted the code by hand — the link in the email was dead.

**Fix**

* `backend/app/services/auth.py` → `build_reset_link()` strips the group
  and preserves a deep-link scheme (`transitos://` keeps its double
  slash). The email body now also contains the code itself, so the flow
  still completes if the web build is not deployed.
* `frontend/app/(auth)/reset-password.tsx` *(new)* reads `?token=` and
  opens the "set a new password" form with the code pre-filled.
  `forgot-password.tsx` now takes `initialMode` / `initialToken`.

Pinned by `backend/app/tests/test_password_reset_link.py`, which asserts
the link format **and** that the path in the email resolves to a screen
that exists in the app — the check that would have caught the original.

### 1.11 — The demo seed covered only 7 of the 10 roles (P1)

`backend/scripts/seed.py` created accounts for super_admin, owner,
general_manager, branch_manager, fleet_manager, driver and conductor.
**`operations_manager`, `chief_accountant` and `branch_accountant` had
no demo account at all** — three of the ten roles the permission system
knows could not be demoed without hand-creating a user through the
admin UI, which needs an account you do not have yet.

**Fix** — all ten roles are seeded. `seed_database(db)` was split out
of `main()` so it can be driven against an in-memory Mongo, and
`DEMO_ACCOUNTS` is the single source of truth the summary prints.

Pinned by `backend/app/tests/test_seed_script.py`, which seeds an
in-memory Mongo and then **logs in as every account**, asserting each
one gets its own role back from `/auth/me`.

### 1.12 — A duplicate dict key in the permissions matrix (P1)

`DEFAULT_PERMISSIONS["conductor"]` defined `audit_log` **twice**:

```python
"audit_log": ["read"],   # line 205
...
"audit_log": [],         # line 216 — this one always won
```

Python keeps the **last** value in a repeated dict key — silently, with
no warning. The role never had the audit-log read the file appeared to
grant, and the matrix the admin screen renders disagreed with the file
by inspection. A copy-paste slip Python accepts without a murmur.

**Fix** — the stray line is gone. `backend/app/tests/test_no_duplicate_dict_keys.py`
parses every module in the backend and fails if any dict literal
repeats a key, so the whole class is closed.

### 1.13 — The permissions matrix had drifted from the API on 25 pairs (P1)

The `role_permissions` collection is **display-only**: it seeds the
matrix the admin screen edits, but no route ever consults it. Access is
enforced by hard-coded `require_roles(...)` lists, and the front end
gates screens with `lib/rbac.ts` — and those two agree with each other.

The matrix was the odd one out, on **25 (role, resource) pairs**: it
promised `audit_log` read to `operations_manager`, `cash_ups` read to
`fleet_manager`, `vehicles` read to `driver`, and so on — all of them
denied by the API. An administrator would be shown permissions that
have no effect.

`tools/contract/check.py` → `matrix` now compares the matrix against
the roles each endpoint actually allows. The 25 existing entries are
frozen in `KNOWN_MATRIX_DRIFT` with the reason; **any new divergence
fails the build**. Closing the gap properly means making the API
enforce the matrix — a policy decision, not a bug fix, so it is
reported rather than done.

### 1.14 — Ten of twenty settings were undocumented in `.env.example` (P1)

`.env.example` is what an operator copies to `.env` and fills in. It
documented ten of the twenty `Settings` fields. The ten it missed
included **`FRONTEND_URL`** — which builds the password-reset link —
and every email-delivery setting (`RESEND_API_KEY`, `EMAIL_FROM`, the
five `SMTP_*` variables) and `EVENTS_POLL_INTERVAL_SECONDS`.

An operator reading the example file could not know those settings
existed, so they stayed unset: reset emails linked to `localhost:8081`
and no email was ever sent.

**Fix** — all twenty are documented. `backend/app/tests/test_env_example.py`
walks the `Settings` model and fails if any field has no entry in
`.env.example`, so a new setting cannot be added without documenting
it.

### 1.15 — `POST /branches` sent a field the API does not have (P2)

`is_active: true` was sent and silently dropped (the server sets it). It
also carried an `as any` cast that was hiding exactly this. Both removed.

---

### 1.16 — A crew member could not see the crew on their own trip (P1)

The trip screen shows who is on the trip. It looked the names up in
`GET /drivers` and `GET /conductors` — and those endpoints are closed to
drivers and conductors **on purpose** (`CREW_READ` is the supervisory
tier only; a crew member has no business browsing the staff list). The
backend answered 403, so the screen fell back to its placeholder and
every driver and conductor saw:

```
Driver ·            —              ← the em-dash placeholder
Conductor · Badge   —
```

The fix follows the pattern the cash-ups already used: the crew names
are **denormalised onto the trip** (`driver_name`, `conductor_name`),
joined from the crew record to its user in two batched queries. The
directory stays closed; the names travel with the trip.

* `app/models/trip.py` — two optional fields on the trip response.
* `app/routers/trips.py` — `_attach_crew_names()`, called from the list,
  the detail and the status-change responses.
* `frontend/app/(app)/trips/[id].tsx` — uses the trip's own names, and
  falls back to the directory when the reader is allowed to see it.
* `app/tests/test_crew_trip_access.py` — a regression test that asserts
  the directory still returns 403 **and** that the trip carries the
  names. Both halves, so the fix cannot be "just open the directory".

### 1.17 — The test suite failed when pytest was run from the repo root (P1)

`pytest` with no path argument, started from the repository root, finds
no configuration file: the rootdir becomes the repository root, no ini
is loaded, and pytest-asyncio falls back to **strict** mode. In strict
mode the async fixtures that the test modules declare with a plain
`@pytest.fixture` are never awaited, and 18 tests fail with

```
TypeError: 'coroutine' object is not subscriptable
```

Nothing is broken — the suite is fine when it is run from `backend/`,
which is what CI does. But the failure looks exactly like a broken
suite, and a reader would have no way to tell the difference.

Fixed with a root `pytest.ini` carrying the same settings as
`backend/pytest.ini`. Both directories now behave identically.

### 1.18 — A fielded app that could not be updated without a new APK (P1)

`expo-updates` was linked into the native project but **disabled**:
the generated manifest carried `expo.modules.updates.ENABLED = false`,
and the app config had no `updates.url` at all. The `channel` on the
three `eas.json` profiles and the `runtimeVersion` in `app.json` were
present but inert.

The consequence was not a bug but a constraint: **every fix — a
mis-spelled label, a wrong variance calculation, a crash on the cash-up
screen — needed a new APK**, a new store submission and a re-install on
every phone in the fleet. For an app whose crew is on the road all day,
that is the difference between a fix landing today and a fix landing
next week.

Now configured:

- `expo-updates` 29.0.20 (the SDK 54 build) installed;
- `updates.url` pointing at this project's update server, with
  `checkAutomatically: ON_LOAD` and `fallbackToCacheTimeout: 0`;
- `runtimeVersion: { policy: "appVersion" }` — the runtime version
  follows the app version, so a native change (new APK, new version)
  automatically moves the update target and a JavaScript-only fix does
  not;
- the `preview` / `production` / `development` channels aligned across
  the three build profiles and the publish scripts;
- the app version in `package.json` brought in line with `app.json`
  (1.1.0 → 1.2.0) — the runtime version is derived from `app.json`,
  and two different version numbers in the repository are a trap for
  whoever publishes the first update.

**The honest limit.** `expo-updates` is a *native* library: the update
client lives inside the APK. So the next APK has to be the OTA-capable
one, and **no APK built before it can receive an update**. After that
build, JavaScript and asset fixes go over the air; native changes still
need a new APK.

**The guard.** `tools/contract/check_updates.py` runs in CI and fails
the build when the dependency is missing, the update URL does not match
the project's update server, no runtime version is declared, the two
version numbers disagree, a build profile has no channel, two profiles
share a channel, or a publish script targets a channel nobody listens
to. `backend/app/tests/test_update_config.py` proves each of those
checks actually fires.

**The playbook** is `docs/OTA_UPDATES.md` — what can and cannot go over
the air, how the runtime version works, how to roll a fix out to the
fleet in stages, and the three different rollback commands.

The app also now says which channel it is on: a build that is not
production shows a **Preview build** strip on the dashboard, so a
tester cannot show an internal build to the client by mistake.

### 1.19 — The two seeders had drifted apart (P1)

There are two ways to seed a TransitOS database, and they carried
**separate account lists**:

| | Accounts it created |
|---|---|
| `python -m scripts.seed` | 10 — every role |
| `POST /admin/seed` | 3 — super_admin, owner, general_manager |

The script was extended to all ten roles during the 4th pass; the HTTP
endpoint was not. The pre-build checklist told the owner to seed with
``curl -X POST .../admin/seed`` — so following the checklist would have
produced a **third of the demo accounts**, with nothing in the response
to say which were missing. The endpoint's ``credentials`` block named
seven roles, two of which it never created.

Both now read ``app/demo_accounts.py``, so they cannot drift again:

- the HTTP endpoint creates all ten accounts, with the branch-scoped
  ones attached to the seeded branch (the branch is now created
  *before* the users, because a branch-scoped role needs a branch);
- its ``credentials`` block is generated from the same list;
- ``backend/app/tests/test_seed_accounts.py`` (7 tests) proves the two
  agree, that the list covers every role the permission system knows,
  and that the branch-scoped accounts really are on the branch.

### 1.20 — The Codespace bootstrap gave up without Docker (P2)

``setup_codespace.sh`` started MongoDB with Docker, then with a local
``mongod``, and otherwise printed *"Neither Docker nor mongod is
available"* and skipped the seed. A Codespace created without the
Docker feature hits exactly that.

Two things were wrong with it:

1. **No fallback.** The official MongoDB build runs from a tarball
   with no Docker, no root and no systemd. The script now downloads and
   starts it as a last resort — verified end to end.
2. **It assumed the local database was the one that matters.** It is
   not: the deployed app reads the database **Railway** hosts. The
   script now reads ``MONGODB_URL`` from ``backend/.env`` first, and
   when it points at a remote host it seeds that database directly
   instead of starting a local throwaway.

The Railway path is now the documented one, in both
``docs/DEMO_ACCOUNTS.md`` and ``docs/PRE-BUILD-CHECKLIST.md``:

```bash
# Railway dashboard -> your API service -> the shell tab
cd /app && python -m scripts.seed
```

``MONGODB_URL`` is already set inside the service, so it reaches the
real database with no connection string and no Docker.

### 1.21 — Every role saw the Super Admin's dashboard (P0)

The home screen rendered **one** dashboard for everybody: the same four
company-wide figures (revenue, trips today, active fleet, cash
variance), the same eight counters, the same fleet map, the same "quick
actions" row — with only the quick actions and the scan button gated by
role.

A driver's home screen showed the whole company's revenue. A branch
manager's showed the company, not their branch. A conductor's showed the
fleet. The User Manual had promised something else for years — *"your
dashboard covers your branch only"*, *"your dashboard shows the trips you
are working"* — so the manual and the app disagreed.

Worse, the data behind it was not scoped. Two endpoints leaked:

| Endpoint | Before |
|---|---|
| `GET /dashboard/summary` | scoped only the management tiers, so a driver was shown the whole company's fleet, incidents and cash-ups |
| `GET /cash-ups` | scoped only the management tiers, so a conductor was shown **every cash-up in the business** — other branches' takings included |

And two write endpoints had the same hole: a conductor could **edit**
and **submit** another conductor's cash-up, and could file a cash-up in
someone else's name.

**The fix**, in two halves:

*Data.* The dashboard counters are scoped by `BRANCH_SCOPED_ROLES` —
which includes drivers and conductors, not just the management tiers —
and vehicle transfers are matched on the branch they leave. A
conductor's cash-up list, read, edit, submit and PDF export are all
scoped to the cash-ups they declared, with a **404** rather than a 403
so another conductor's cash-up is not discoverable by guessing an id.

*Screens.* `frontend/lib/dashboard-view.ts` is now the single place
that says which view a role gets: the company view for the platform
tiers, a branch view, an operations view, a fleet view, finance views
for the two accountant tiers, and a crew view for drivers and
conductors — their trips, their duty state, their passenger count, and
nothing else. The screen renders that table; it decides nothing itself.

The app also stopped asking for what it would be refused: a driver no
longer requests the fleet, the branch list or the reports summary, so
there is no 403 in the log and no card reading zero because the
request had failed.

**The guards.** `backend/app/tests/test_dashboard_roles.py` (13 tests)
covers the scoping and checks the view table — that every role has a
view, that the crew view shows no company figure, and that the crew
view does not ask for the fleet. The existing `screens` contract check
caught a real regression during this work: rebuilding the card
catalogue dropped the dashboard's navigation targets, and **/drivers**
became unreachable from anywhere.

## 2 · The gap that hid most of the above

The static contract checker compared the backend's required body fields
against the body fields the front end sends — but only for calls whose body
is a **literal object at the call site**:

```ts
postSingle('/expenses', { amount: 500 })   // checkable
postSingle('/expenses', body)              // NOT checkable
```

Almost no mutation is written that way. They go through a TanStack-Query
hook and the payload is assembled in the screen:

```ts
// lib/queries.ts
export function useCreateExpense() {
  return useMutation({ mutationFn: (body) => postSingle('/expenses', body) });
}
// app/(app)/expenses.tsx
await create.mutateAsync({ amount: amt, vehicle_id: vehicleId, … });
```

**51 of the 60 mutating calls could not be checked at all.** A field renamed
on either side of the boundary was invisible to every check in the
repository — and, because unknown fields are not forbidden, it was not even
an error: it was silently discarded.

**`tools/contract/payloads.py`** resolves the payload the way the
application assembles it — *hook → mutation variable → `mutate()` argument →
the keys of that object* — and follows the import graph so a hook counts as
used only when a screen really calls it.

It now resolves **42 of 54** bodies. The rest are honest gaps (a
free-form `Record<string, unknown>` payload, a scalar argument, or a hook
that no screen uses) and are reported as such rather than guessed at.

---

## 3 · New guards

| Guard | Catches |
|---|---|
| `check.py fields` | a required body field the front end never sends (→ 422), and a field the front end sends that the backend does not declare (→ silently dropped) |
| `check.py reachable` | an endpoint no screen can reach — a feature that is not in the app. Now follows the **import closure**, so a mutation owned by a component is covered too |
| `test_money_loop_frontend.py` | the money loop losing a button: a trip that cannot advance, a cash-up that cannot be submitted, a manifest that cannot be filled — plus the front end's role lists and transition table drifting from the back end's |
| `check.py webview` | unescaped data interpolated into a WebView's HTML or `<script>` block |
| `check_styling.py` | a `className=` in a project with no working styling toolchain — a build that passes and a UI that is broken |
| `test_frontend_runtime_contract.py` (rewritten) | now fires the front end's **own** body, so a field the two halves disagree about fails with a 422 |

`test_frontend_runtime_contract.py` also changed its payload generator: it
used to send `"Test Value"` for every string, which produced 21 false
positives that the old assertion set (404 / 405 / 401 / 500) discarded.
The generator now produces schema-valid values — real emails, values that
match their pattern, policy-compliant passwords, ids of seeded documents —
so **422 is a meaningful signal**. 2xx responses rose from 92/131 to 113/131
and the remaining non-2xx are 4 semantic conflicts and 4 legitimate 400s.

Proof the guard works:

```
$ # remove scheduled_arrival from the trip payload
$ pytest app/tests/test_frontend_runtime_contract.py
E   AssertionError: frontend calls that cannot work:
E       POST /trips -> HTTP 422
```

---

## 4 · Open items — not fixed, need an owner

1. **The backend is not deployed.** `https://transitos-production.up.railway.app`
   and `https://transitos-production-4b46.up.railway.app` both answer
   `404 {"status":"error","code":404,"message":"Application not found"}`
   from Railway's edge. An APK built today would reach no API at all. The
   URL is right in one place only — `frontend/app.json` → `extra.apiUrl`
   (and mirrored in `eas.json`) — so there is a single place to change it.
2. **~~The three dead endpoints in §1.2~~ — FIXED in this pass.** The trip
   can be moved, the manifest can be filled and the cash-up can be
   submitted, all from the app.
3. **17 endpoints in `KNOWN_UNREACHABLE`** — mostly single-record reads and
   report screens the app does not surface yet. Each is a feature gap, not
   a defect.
4. **The native APK was not built.** EAS/Gradle and the Android SDK are not
   available here, so the gate covers the Metro bundle (the part that
   breaks on a bad import, a missing asset or a broken `package.json`) and
   the typecheck — not the Gradle build.
5. **`ENV=prod` is not the default.** The README documents `ENV` as
   optional, defaulting to `dev` — which leaves the insecure JWT default
   and `CORS_ORIGINS=*` in force if an operator forgets it. The config
   validator refuses to start in `staging`/`prod` with a weak secret, but
   only when `ENV` is set.

---

## 5 · Files changed

**Backend**
`app/main.py` · `app/models/trip.py` · `app/services/cash_up.py` ·
`app/tests/test_auth.py` ·
`app/tests/test_openapi_contract.py` · `app/tests/test_routes.py` ·
`app/tests/test_trips.py` · `app/tests/test_users.py` ·
`app/tests/test_frontend_runtime_contract.py` ·
`app/tests/test_money_loop_frontend.py` *(new)* ·
`app/tests/test_source_scanner.py` *(new)* ·
`app/tests/test_password_reset_link.py` *(new)* ·
`app/tests/test_seed_script.py` *(new)* ·
`app/tests/test_no_duplicate_dict_keys.py` *(new)* ·
`app/tests/test_env_example.py` *(new)* ·

**Frontend**
`app/(app)/routes/index.tsx` · `app/(app)/map.tsx` ·
`app/(app)/trips/[id].tsx` · `app/(app)/cash-ups.tsx` ·
`components/TripStatusPanel.tsx` *(new)* ·
`components/ManifestEditor.tsx` *(new)* ·
`components/CashUpSection.tsx` ·
`components/admin/CreateTripModal.tsx` · `components/admin/CreateBranchModal.tsx` ·
`components/ui/MapModal.tsx` · `components/ui/{Badge,Card,EmptyState,Field,Input,PageHeader,SearchBar,Button}.tsx` ·
`lib/api.ts` · `lib/html.ts` *(new)* · `lib/password.ts` ·
`lib/money-loop.ts` *(new)* · `lib/rbac.ts` · `lib/queries.ts` ·
`lib/auth-context.tsx` · `app/(auth)/forgot-password.tsx` ·
`app/(auth)/reset-password.tsx` *(new)* ·
`app.json` · `eas.json` · `package.json` · `package-lock.json` · `tsconfig.json` ·
*removed:* `tailwind.config.js` · `postcss.config.js` · `global.css` ·
`nativewind-env.d.ts` · `components/ui/cn.ts`

**Tooling**
`tools/contract/check.py` · `tools/contract/payloads.py` *(new)* ·
`tools/contract/check_styling.py` *(new)* · `tools/contract/sources.py` *(new)* ·
`backend/scripts/seed.py` · `.github/workflows/ci.yml`

**Codespace**
`.devcontainer/devcontainer.json` *(new)* · `.devcontainer/post-create.sh` *(new)* ·
`.devcontainer/README.md` *(new)* · `docs/DEMO_ACCOUNTS.md` *(new)*

**Docs**
`README.md` · `specs/api-contract.md` · `specs/data-model.md` ·
`specs/design-tokens.md` · `specs/sprint-a-tasks.md` ·
`docs/CLIENT_ONBOARDING_GUIDE.md` · `docs/USER_MANUAL.md` ·
`docs/mockup/build_web.sh`
