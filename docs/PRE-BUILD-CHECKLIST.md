# Pre-build checklist — what to change before `eas build`

Everything below was verified against the repo, not assumed. Line numbers
refer to the state at the time of writing.

Verified as of the last sweep: **215 backend tests pass · 8/8 contract
checks pass · `tsc` 0 errors · `expo-doctor` 18/18 · Android JS bundle
builds**.

---

## 1 · BLOCKERS — the build or the app will not work without these

### 1.1 The backend URL is dead, in four places

`https://transitos-production.up.railway.app/healthz` returns Railway's
own `404 {"status":"error","code":404,"message":"Application not
found"}`. The app is deployed nowhere.

| File | Line | Current value |
|---|---|---|
| `frontend/app.json` | `expo.extra.apiUrl` | `https://transitos-production.up.railway.app` |
| `frontend/eas.json` | `build.development.env.EXPO_PUBLIC_API_URL` | same |
| `frontend/eas.json` | `build.preview.env.EXPO_PUBLIC_API_URL` | same |
| `frontend/eas.json` | `build.production.env.EXPO_PUBLIC_API_URL` | same |

Replace **all four**. `EXPO_PUBLIC_API_URL` wins over `extra.apiUrl`
(`frontend/lib/api.ts` → `resolveBaseURL()`), and since the fix in this
pass there is exactly **one** resolver — `lib/auth-context.tsx` now
imports it instead of resolving the URL a second time. Before the fix
the two had *opposite* precedence, so login went to `app.json` while
every other call went to the profile's env var.

`tools/contract/check.py` → `url` fails the build if a second resolver
appears.

### 1.2 Backend environment variables (Railway service → Variables)

Source of truth: `backend/.env.example` and
`backend/app/core/config.py`.

| Variable | Current default | What to set |
|---|---|---|
| `ENV` | `dev` | `prod` |
| `MONGODB_URL` | `mongodb://localhost:27017` | your Atlas / Railway Mongo URI (`MONGO_URL` also accepted) |
| `MONGODB_DB_NAME` | `transitos` | your database name (`MONGO_DB` also accepted) |
| `JWT_SECRET_KEY` | `dev-only-not-for-production-please-change-me` | `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `CORS_ORIGINS` | `*` | explicit origins, e.g. `https://app.yourdomain.com` |
| `FRONTEND_URL` | `http://localhost:8081` | the public base URL of the deployed web build |
| `ADMIN_BOOTSTRAP_TOKEN` | *(unset — endpoint disabled)* | a random secret → seed → **then unset it again** |

`ENV=prod` makes two of these **fail loudly at boot** rather than run
insecurely (`Settings._reject_insecure_settings_in_non_dev`):

* a weak or default `JWT_SECRET_KEY` → `RuntimeError`
* `CORS_ORIGINS=*` → `RuntimeError`

So if the backend starts with `ENV=prod` and no secrets set, it will not
start. That is intentional.

**`FRONTEND_URL` matters more than it looks** — it builds the
password-reset link in `backend/app/services/auth.py`:

```python
reset_link = build_reset_link(settings.frontend_url, token)
```

Left at `http://localhost:8081`, every reset email links to the
developer's own machine.

### 1.3 Push notifications will not arrive

There is **no Firebase wiring at all**. Confirmed by generating the
native project: no `google-services` in `android/app/build.gradle`, no
`com.google.gms` in the manifest.

| Item | Where | Status |
|---|---|---|
| `google-services.json` | `frontend/google-services.json` | **missing** |
| `expo.android.googleServicesFile` | `frontend/app.json` → `expo.android` | **missing** |
| FCM v1 service-account key | EAS → project → Credentials → Android → FCM V1 | **not uploaded** |
| Firebase Android app id | must equal `com.transitos.app` | to create |

Add to `frontend/app.json`:

```json
"android": {
  "package": "com.transitos.app",
  "googleServicesFile": "./google-services.json",
  "permissions": ["CAMERA"]
}
```

The app degrades gracefully — `frontend/lib/push.ts` catches the failure
and returns `false` — so **nothing crashes**. But no driver will ever
receive a dispatch push, and the "Request sent" success state on the
forgot-password screen is the only feedback the user gets.

`expo-notifications` is already in the `plugins` array ✓ and
`extra.eas.projectId` is already set ✓, so the token registration path
is ready once FCM exists.

### 1.4 `eas submit` will fail on missing credentials

`frontend/eas.json` → `submit.production`:

| Key | Current | Action |
|---|---|---|
| `android.serviceAccountKeyPath` | `./secrets/play-store-service-account.json` | `frontend/secrets/` **does not exist** |
| `ios.ascAppId` | `REPLACE_WITH_YOUR_APPLE_APP_STORE_CONNECT_APP_ID` | fill in, or delete the iOS block |
| `ios.appleTeamId` | `REPLACE_WITH_YOUR_APPLE_TEAM_ID` | fill in, or delete the iOS block |

`eas build` ignores the `submit` block entirely, so this only bites when
you submit to the stores. Fill it in or delete the block.

### 1.5 `.gitignore` does not cover `frontend/secrets/`

The root `.gitignore` ignores `.env`, `.env.local`, `.env.*.local` —
but **not** `secrets/` and not `*-service-account.json`.

If you create `frontend/secrets/play-store-service-account.json` and
commit it, **the Play publishing key is in your git history**. Add this
to the root `.gitignore` *before* you create the file:

```gitignore
# Play Store / service-account keys
frontend/secrets/
*-service-account.json
google-services.json
```

---

## 2 · IDENTITY — must match your EAS / store accounts

| File | Key | Current | Check |
|---|---|---|---|
| `frontend/app.json` | `expo.owner` | `chisomshasha` | must be the account you are logged into as (`eas whoami`) |
| `frontend/app.json` | `expo.extra.eas.projectId` | `81b16dd7-e438-4b35-9792-01f5076ebda6` | must be **your** EAS project; `eas init` regenerates it |
| `frontend/app.json` | `expo.android.package` | `com.transitos.app` | must be unique on Play; must equal the Firebase Android app id |
| `frontend/app.json` | `expo.ios.bundleIdentifier` | `com.transitos.app` | must be unique in the Apple Developer portal |
| `frontend/app.json` | `expo.version` | `1.2.0` | `package.json` says `1.1.0` — app.json wins; make them agree |
| `frontend/eas.json` | `cli.appVersionSource` | `remote` | EAS owns the version + build number; `production` has `autoIncrement: true` |

If `owner` does not match your EAS login, `eas build` will not find the
project and may create a new one with a **different** `projectId` — which
then breaks the push-token registration in `lib/push.ts`.

---

## 3 · ANDROID MANIFEST — decisions to make before you ship

The generated `AndroidManifest.xml` currently declares:

```
CAMERA   INTERNET   VIBRATE
READ_EXTERNAL_STORAGE   WRITE_EXTERNAL_STORAGE
RECORD_AUDIO   SYSTEM_ALERT_WINDOW
```

| Permission | Why it is there | Recommendation |
|---|---|---|
| `INTERNET` | axios + the map WebView | keep |
| `CAMERA` | QR scanning (`expo-camera`) | keep |
| `VIBRATE` | push notifications | keep |
| `RECORD_AUDIO` | **`expo-camera` adds it by default** | **drop it** — the app only scans QR codes |
| `READ/WRITE_EXTERNAL_STORAGE` | `expo-image-picker`, `expo-file-system` | consider `blockedPermissions` |
| `SYSTEM_ALERT_WINDOW` | **`expo-dev-client` / `expo-dev-menu`** | see below |

### 3.1 Drop `RECORD_AUDIO`

`expo-camera`'s config plugin adds it unless told not to. The app never
records video — `frontend/components/ui/BarcodeScanner.tsx` only calls
`CameraView` with `barcodeScannerSettings`. In `frontend/app.json`:

```json
[
  "expo-camera",
  {
    "cameraPermission": "Allow TransitOS to access your camera to scan QR codes.",
    "recordAudioAndroid": false
  }
]
```

`RECORD_AUDIO` is a *dangerous* permission and Play asks why a fleet
dispatch app wants the microphone.

### 3.2 `SYSTEM_ALERT_WINDOW` comes from `expo-dev-client`

`expo-dev-client` is in `dependencies`, and `expo-modules-autolinking
resolve` confirms these are linked into **every** build:

```
expo-dev-client, expo-dev-launcher, expo-dev-menu, expo-dev-menu-interface
```

The dev-*client* plugin is not in `app.json`'s `plugins` array, so the
dev launcher is not the entry activity — but the native modules are
compiled in, and `expo-dev-menu` declares `SYSTEM_ALERT_WINDOW` (the
floating dev overlay).

* **Keeping it:** needed for the `development` profile
  (`developmentClient: true`) — that build needs a dev server.
* **Dropping it:** remove `expo-dev-client` from `frontend/package.json`
  and delete the `development` profile from `eas.json`. The app still
  builds standalone; you just lose the on-device dev menu.

`SYSTEM_ALERT_WINDOW` is a *special* permission — Play does not grant
it automatically and it can be a review flag. For a Play release, the
cleaner path is to drop `expo-dev-client`.

### 3.3 Storage permissions

`READ/WRITE_EXTERNAL_STORAGE` are legacy (ignored on Android 13+, but
requested on older devices). If the app does not read or write the
user's shared storage, block them:

```json
"android": {
  "blockedPermissions": [
    "android.permission.READ_EXTERNAL_STORAGE",
    "android.permission.WRITE_EXTERNAL_STORAGE"
  ]
}
```

---

## 4 · OVER-THE-AIR UPDATES — now configured, one APK to go

`expo-updates` is installed and the update server, the runtime version
and the three channels are configured. See
**`docs/OTA_UPDATES.md`** for the full playbook.

* **The next APK must be the OTA-capable one.** `expo-updates` is a
  native library — the update client lives inside the APK, so the
  build you are about to make is the one that carries it. No APK built
  before this can receive an update.
* After that, a JavaScript or asset fix ships with
  `npm run update:production` and reaches the crew's phones on their
  next launch. **No new APK.**
* A **native** change — a new permission, a new native package, a
  change to `app.json`'s plugin section — still needs a new APK.
* **Bump `version` in `frontend/app.json` when you publish a build,
  never for a JavaScript-only fix.** The runtime version follows the app
  version, so bumping it for a JS-only fix cuts the field off from
  every update until the next APK.
* `python tools/contract/check_updates.py` runs in CI and fails the
  build if the configuration is incoherent.


---

## 5 · THE MAP NEEDS THE INTERNET — and a tile provider

`frontend/app/(app)/map.tsx` and `frontend/components/ui/MapModal.tsx`
load, at runtime, from third-party CDNs:

```
https://unpkg.com/leaflet@1.9.4/dist/leaflet.js
https://unpkg.com/leaflet@1.9.4/dist/leaflet.css
https://tile.openstreetmap.org/{z}/{x}/{y}.png
```

* The device needs internet or the map is a blank box. The rest of the
  app works offline, so this is easy to miss in testing.
* The OpenStreetMap **tile usage policy** does not permit heavy
  production use of the public tile servers by a commercial app. For a
  real fleet deployment, switch to a commercial provider (MapTiler,
  Mapbox) or self-host the tiles. Only two URLs change — both in those
  two files.
* The WebView runs with `originWhitelist={['*']}`.

---

## 6 · FIXED IN THIS PASS — you do not need to touch these

| What | Where |
|---|---|
| The API URL is resolved in **one** place, so per-profile env vars work | `frontend/lib/api.ts` → `resolveBaseURL()`; `frontend/lib/auth-context.tsx` imports it |
| Trip creation sends a body the API accepts (it was always 422) | `frontend/components/admin/CreateTripModal.tsx` |
| The reset email links to a route that **exists** | `frontend/app/(auth)/reset-password.tsx` (new) + `backend/app/services/auth.py` → `build_reset_link()` |
| WebView HTML injection closed | `frontend/lib/html.ts` → `jsonForScript()`, `esc()` |
| `className=` styling works (it was shipping unstyled) | `frontend/app/(app)/routes/index.tsx` |

---

## 7 · VERIFIED OK — no action

* `npx expo-doctor` → **18/18 checks passed**
* `npx tsc --noEmit` → 0 errors
* `npm ci` from a clean checkout → 830 packages, exit 0
* `npx expo export --platform android` → bundle built
* `expo-notifications` plugin present ✓
* `expo-camera` plugin present with a permission string ✓
* iOS `NSCameraUsageDescription` present ✓
* `expo.build-properties` → Hermes on both platforms ✓
* `scheme: "transitos"` → deep links work ✓
* `newArchEnabled: false` → old architecture, consistent with the SDK 54 pin

---

## 8 · STILL OPEN — product decisions, not build config

1. ~~**The three dead endpoints.**~~ **RESOLVED in this pass.** The
   money loop is now in the app: `PATCH /trips/{id}/status`,
   `POST`/`DELETE /trips/{id}/manifest` and `POST /cash-ups/{id}/submit`
   all have screens, and the four `KNOWN_UNREACHABLE` entries for them
   have been removed so the reachability guard covers them.
2. **Fare / cargo override fields.** The trip-creation form used to
   collect values the API never stored. They are removed. If the
   business wants them, that is a backend schema change first.
3. **17 further endpoints** in `KNOWN_UNREACHABLE` — mostly single-record
   reads and reports the app does not surface yet.

---

## 9 · COMMAND SEQUENCE

```bash
# 1 — backend first: the app is useless without it
cd backend
cp .env.example .env          # then fill in every value in §1.2
uvicorn app.main:app --reload # or deploy to Railway with the Dockerfile

# 2 — deploy the backend, then set the real URL in all four places (§1.1)

# 3 — seed the database
#
# The database Railway hosts is the one the app uses, so seed that one.
# From the Railway dashboard: your API service -> the shell tab, then
#
#     cd /app && python -m scripts.seed
#
# That seeds all ten demo accounts plus the demo branch, vehicle,
# driver, conductor and route. It needs no Docker and no connection
# string from your machine — MONGODB_URL is already set inside the
# service.
#
# The HTTP bootstrap does the same thing from anywhere:
#
#     curl -X POST https://<your-api>/admin/seed \\
#       -H "X-Admin-Token: <secret>"
#
# It can only run once — the endpoint locks itself after the first
# success — so unset ADMIN_BOOTSTRAP_TOKEN afterwards.
#
# For LOCAL work only, `bash backend/scripts/setup_codespace.sh` starts a
# throwaway MongoDB and seeds that. It is not the deployed database.

# 4 — front end
cd ../frontend
npm ci
npx tsc --noEmit
npx expo-doctor

# 5 — build
eas login
eas whoami                                    # must match expo.owner
eas build --platform android --profile preview

# 6 — the OTA-capable production build (§4)
#    This is the APK the field gets. It is the first one that can
#    receive an over-the-air update, so build it before distributing.
eas build --platform android --profile production

# 7 — after that, a JavaScript fix needs no APK at all
bash backend/scripts/publish_update.sh preview "What it fixes"    # testers
bash backend/scripts/publish_update.sh production "What it fixes"  # the field
```

> **The publish script installs what it needs.** A Codespace created
> before `.devcontainer/` existed has no Node and no EAS CLI, so
> `npm run update:production` fails with *npm: command not found* and
> `eas update` fails with *eas: command not found*. Use
> `backend/scripts/publish_update.sh` instead — it installs Node 20 and
> the EAS CLI if they are missing, checks you are signed in as the
> account that owns the project, and prints the update-group id you
> need for a staged rollout.

> **Publish the first update to `preview` and try it on a real phone
> before you put it on `production`.** Force-close the app and reopen
> it — twice if needed — and check the change is there. See
> `docs/OTA_UPDATES.md` §8.

`preview` gives you an installable APK via a shareable link.
`production` is the same build with `autoIncrement` and the `production`
channel. Use `development` only if you keep `expo-dev-client` (§3.2).
