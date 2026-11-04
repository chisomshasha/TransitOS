# TransitOS — User Manual

**Built by Exit Media Solutions**
**For the Client Company**

---

## Welcome

TransitOS is a role-based transport management platform that helps you run your fleet, track trips, collect cash, and report on operations — all from one place. It's a mobile app (Android & iOS) backed by a cloud API.

This manual walks you through everything you need to know as a daily user. It's organized the way you'd actually use the app: from logging in, to running trips, to reading the numbers at the end of the day.

---

## 1. Quick Start

### 1.1 Install the app

- **Android**: download the APK from your IT team and install, or get it from the Play Store once it's published
- **iOS**: download from the App Store, or install via TestFlight (internal testing)

### 1.2 Log in

1. Open **TransitOS**
2. Enter your **email** and **password**
3. Tap **Log in**

You'll land on the **Dashboard** with a personalized greeting and headline numbers from the last 30 days.

> **First-time deployment? Bootstrap the Owner/GM/Super Admin via API.** Owner/admin accounts must exist before anyone can log in. The backend ships with a one-shot `POST /admin/seed` endpoint — see [§ 19 — Admin bootstrap](#19-admin-bootstrap) for the exact curl command. After it succeeds, **unset `ADMIN_BOOTSTRAP_TOKEN`** to lock the endpoint forever.

### 1.3 Navigate the app

The bottom tab bar has your five main sections:

| Tab | What it shows |
|---|---|
| **Home** | Dashboard with 30-day KPIs and quick links |
| **Trips** | All trips (planned, in progress, completed) |
| **Vehicles** | Your fleet, with status and seat capacity |
| **Reports** | Revenue, expenses, variance, branch ranking |
| **Me** | Your profile, change password, log out |

The other resources (branches, users, drivers, conductors, routes, fuel, maintenance) live behind the **Me → Settings** or are accessible from contextual buttons on the dashboard.

---

## 2. Roles & Permissions

TransitOS has 10 roles. Your role determines what you can see and do.

| Role | Who typically uses it | What they can do |
|---|---|---|
| **Super Admin** | Exit Media Solutions support | Full access; only used for platform-level setup |
| **Owner** | Business owner | Everything, all branches |
| **General Manager** | HQ operations | Everything across branches |
| **Operations Manager** | HQ ops | Schedule, view reports, no money edit |
| **Fleet Manager** | Fleet / workshop | Vehicles, drivers, conductors, maintenance, fuel |
| **Chief Accountant** | HQ finance | All reports + approve cash-ups, see variance |
| **Branch Manager** | Branch lead | Everything in their branch only |
| **Branch Accountant** | Branch bookkeeper | Cash-ups + reports in their branch |
| **Driver** | Driver on the road | Their trips, manifest, mark departed/arrived |
| **Conductor** | Conductor on board | Manifest entry, cash-up |

If something is greyed out or you get a "Forbidden" message, your role doesn't allow that action. Talk to your branch manager or the owner.

---

## 3. Dashboard

The **Home** tab shows you, at a glance:

- **6 tile cards**: Trips, Branches, Users, Vehicles, Drivers, Conductors — each with a live count
- **Last 30 days summary card**: Revenue, Expenses, Net (all in your local currency), plus a Variance badge if there are unsettled cash-ups
- **"View reports" link**: jumps to the full Reports screen

Pull down on the dashboard to refresh.

---

## 4. Branches

A **branch** is a physical location — a depot, terminal, or office — where you store vehicles and base staff.

### 4.1 View branches

- Tap the **Branches** card on the dashboard
- See a searchable list of all branches
- Tap the **Map** icon (top right) to see all branches on a map

### 4.2 View a single branch

Tap any branch row to see:

- Name, code, address, city/state
- Status (active / suspended)
- Contact info (phone, email)
- Bank account (if set)
- **Inline map** showing the branch location, with an "Expand" button for full-screen

### 4.3 What you can do

- **Owner / GM / BM**: create, edit, suspend branches
- **Others**: read-only

---

## 5. Users

A **user** is anyone with a login: owner, manager, driver, conductor, accountant. Users have a role, a status, and (for branch-scoped roles) a home branch.

### 5.1 User statuses

- **Active** — can log in
- **Pending** — created but hasn't set a password yet
- **Suspended** — locked out temporarily
- **Deactivated** — soft-deleted; can't log in

### 5.2 View a user

Tap any user row to see their profile, role, branch, contact info, and last login time.

### 5.3 What you can do

- **Owner / GM / BM**: create new users, change roles, reset passwords, deactivate
- **Branch Manager**: can create users in **their branch only** (drivers, conductors, branch accountants)

---

## 6. Vehicles, Drivers, Conductors

These three resources represent your fleet and crew.

### 6.1 Vehicles

Each vehicle has:
- **Registration number** (e.g. `LSR-001-AA`)
- **Type**: bus, minibus, or truck
- **Capacity** (seats + cargo kg)
- **Status**: available, on_trip, maintenance, grounded
- **Odometer** (current km)
- **Fuel level** (0–100%)

The vehicle status flips automatically when trips start/end or maintenance is opened/closed.

### 6.2 Drivers

A driver is a **user with role "driver"** plus a driver profile that tracks:
- License number + expiry
- Years of experience
- Status (active, on leave, suspended)

⚠️ **Heads up:** the app warns you when a driver's license is about to expire (within 90 days).

### 6.3 Conductors

A conductor is a **user with role "conductor"** plus a profile with a **badge number** (their unique identifier on the manifest).

---

## 7. Routes

A **route** is a defined path between two branches — e.g. "Lagos → Ibadan Express". Routes store:

- Origin and destination branches
- Distance (km) and estimated duration (hours)
- Base fare (per passenger) and cargo rate (per kg)
- **Intermediate stops** with their own GPS coordinates and ETA offsets
- Required permits (e.g. interstate license)

### 7.1 View routes

- Tap the Routes screen from any list
- Each route shows: name, origin → destination cities, type (intrastate / interstate), distance, duration, number of intermediate stops
- Tap a route to see the **full map view** with origin (green pin) → numbered waypoints (yellow) → destination (red pin), all connected by a line
- Below the map: every intermediate stop with its coordinates and ETA offset

### 7.2 What you can do

- **Owner / GM / BM / FM**: create, edit, activate/deactivate routes
- **Others**: read-only

---

## 8. Trips (the heart of the app)

A **trip** is one scheduled run: one vehicle, one driver, one conductor, one route, departing at a specific time. Trips move through a strict state machine.

### 8.1 Trip states

```
planned → boarding → departed → arrived → closed → cashed_up
   ↘         ↘
    cancelled
```

| State | What it means | Who can set it |
|---|---|---|
| **Planned** | Trip is scheduled, no action yet | (initial) |
| **Boarding** | Passengers are getting on at the origin | Driver / Conductor / BM |
| **Departed** | Vehicle has left the origin | Driver / Conductor / BM |
| **Arrived** | Vehicle reached the destination | Driver / Conductor / BM |
| **Closed** | Trip is done, manifest is complete | BM / Conductor |
| **Cashed up** | Money has been reconciled and approved | System (after approval) |
| **Cancelled** | Trip is called off (only pre-departure) | BM |

You can only move **forward** through the states. You can't go from `closed` back to `boarding`, for example.

### 8.2 Create a trip

1. Tap **Trips** in the bottom bar → **+ New** (top right)
2. Select:
   - **Route** (must exist, must be active)
   - **Vehicle** (must be available — not already on a trip)
   - **Driver** (must be active, in the same branch)
   - **Conductor** (must be active, in the same branch)
   - **Scheduled departure** and **arrival** (arrival must be after departure)
3. Tap **Create**

The trip appears in the list with status `planned`.

### 8.3 View a trip

Tap any trip row to see:

- Trip header: scheduled times, status badge
- **Inline map** of the route (origin → stops → destination)
- 4 stat tiles: Passengers, Cargo, Revenue, Expenses
- State machine buttons (e.g. "→ Boarding", "→ Departed", "→ Arrived")
- Manifest (passenger + cargo entries)
- Cash-up section (appears when status is `closed`)

### 8.4 Advance a trip

On the trip detail screen, the **Advance trip** card shows the next available state(s). Tap the button (e.g. "→ Departed") to move the trip forward. The system records the actual time automatically.

### 8.5 Cancel a trip

Available only from `planned` or `boarding` (i.e. before the vehicle leaves). Use sparingly — once departed, you can't cancel.

---

## 9. Manifest

The **manifest** is the list of passengers and cargo booked on a specific trip. The conductor typically adds entries as people board.

### 9.1 Add a manifest entry

1. Open the trip
2. Tap **Add** next to "Manifest"
3. Choose type:
   - **Passenger** — for a person
   - **Cargo** — for a parcel
4. Fill in name (or description, for cargo) and fare
5. Tap **Save entry**

The trip's passenger count, cargo weight, and revenue total update automatically.

### 9.2 Remove an entry

Tap the red **X** next to the entry. Available only while the trip is `planned` or `boarding`.

---

## 10. Cash-Up

The **cash-up** is the conductor's daily reconciliation — what they actually collected vs what the manifest said they should collect. This is where shortages or overages are caught.

### 10.1 Open cash-up

Available only when the trip status is `closed`.

1. Open the closed trip
2. Tap **Open cash-up** (at the bottom)
3. Add one line per payment method:
   - **Method**: `cash`, `transfer`, `pos`, etc.
   - **Amount**: what was collected in that method
4. The **Declared total** updates live as you type
5. Add optional notes
6. Tap **Create cash-up**

### 10.2 Submit for approval

1. Once the cash-up is created, tap **Submit for approval**
2. The system computes the **variance** = (declared − expected manifest total)
3. The status moves from `draft` → `submitted`

You'll see the variance — a positive number means you collected more than expected (overage), negative means you collected less (shortage).

### 10.3 Approve or reject

The **branch accountant or owner** reviews the submitted cash-up:

- **Approve**: status → `approved`, the trip moves to `cashed_up`
- **Reject**: status → `rejected`, with a reason; the conductor can edit and resubmit

---

## 11. Expenses

**Expenses** are money spent on a vehicle — fuel, tolls, maintenance, permits, meals, accommodation, other. There are two scopes:

- **On-trip**: linked to a specific trip (e.g. a toll paid during the run)
- **Standalone**: branch/vehicle overhead (e.g. monthly parking at the depot)

Expenses on trips automatically update the trip's expense total.

### 11.1 Log an expense

1. Go to **Vehicles** → tap a vehicle → **Log expense**
2. Choose:
   - **Category**: fuel, toll, maintenance, permit, meal, accommodation, other
   - **Scope**: on-trip (link to a trip) or standalone
   - **Amount**
   - **Vendor name** (optional, e.g. "Toll Gate 5", "TotalEnergies")
   - **Odometer km** (optional, for fuel)
3. Tap **Save**

---

## 12. Fuel

**Fuel logs** are refueling events. They power the **fuel efficiency** analytics (km per liter per vehicle).

### 12.1 Log a refuel

1. Go to **Vehicles** → tap a vehicle → **Log refuel**
2. Fill in:
   - **Liters**
   - **Total cost**
   - **Odometer km**
   - **Station name** (optional)
3. The cost-per-liter auto-computes
4. Tap **Save**

The vehicle's odometer and fuel level update automatically.

### 12.2 Fuel efficiency

For any vehicle, the system calculates **km / liter** from the odometer delta between successive fuel logs. View it on the vehicle detail screen or in **Reports → Fuel costs**.

---

## 13. Maintenance

**Maintenance records** track routine service, repairs, inspections, and recalls for each vehicle.

### 13.1 Schedule a service

1. Go to **Vehicles** → tap a vehicle → **Schedule maintenance**
2. Fill in:
   - **Type**: routine, repair, inspection, recall
   - **Title**: e.g. "Oil change", "Brake pad replacement"
   - **Scheduled for** (date)
3. Tap **Save**

The vehicle's status stays `available` until you start the work.

### 13.2 Lifecycle

```
scheduled → in_progress → completed
              ↓
          cancelled
```

- **Start**: tap "Start" on the row → vehicle flips to `maintenance` (can't be assigned to a trip)
- **Complete**: tap "Complete" → fill in parts cost, labor cost → vehicle flips back to `available`
- **Cancel**: from the row, if the work isn't going to happen

The total cost is auto-calculated as `parts + labor`.

---

## 14. Reports

The **Reports** tab gives you the operational picture across any time window.

### 14.1 Choose a window

Tap **7d**, **30d**, or **90d** at the top of the Reports screen to switch the period.

### 14.2 What you see

1. **KPI tiles**: Trips, Revenue, Expenses, Net, Variance, Passengers
2. **Daily revenue vs expenses chart**: green = revenue, red = expenses, day by day
3. **Branch performance**: each branch's trips, revenue, expenses, net, passengers
4. **Vehicle ROI**: per-vehicle breakdown of trips, revenue, expenses, net, cargo kg
5. **Fuel costs**: total liters, total cost, average cost per liter

### 14.3 Use cases

- **"How is the business doing?"** → check the KPI tiles and the daily chart
- **"Which branch is performing best?"** → scroll to Branch performance
- **"Which vehicle is most profitable?"** → Vehicle ROI
- **"Are we losing money on cash handling?"** → KPI tile: Variance (and dig into the daily chart)

Pull down to refresh. Reports cache for 30 seconds; explicit pull-to-refresh forces a recompute.

---

## 15. Map features

Many screens include maps. Maps use OpenStreetMap tiles — no API keys, no billing, works offline-ish once loaded.

| Where | What you see |
|---|---|
| **Branches list → Map button** | All branches with GPS as pins, color-coded by status |
| **Branch detail** | Inline map of just that branch |
| **Route detail** | Full route polyline: origin (green) → waypoints (yellow, numbered) → destination (red) |
| **Trip detail** | The trip's route on a map |

To expand any inline map to full screen, tap the **Expand** or **Map** button.

---

## 16. Profile & Account

### 16.1 View your profile

Tap the **Me** tab → see your name, email, role, branch, status, last login.

### 16.2 Change your password

1. Tap **Me**
2. Tap **Change password**
3. Enter your **current** password
4. Enter your **new** password (min 8 characters)
5. Re-enter the new password to confirm
6. Tap **Save**

You'll be logged out and must log in with the new password.

### 16.3 Log out

Tap **Me** → **Log out** → confirm.

⚠️ Logging out clears your session. You'll need to log back in to use the app.

### 16.4 Forgot your password?

On the login screen, tap **Forgot password?** (coming soon — for now, ask your branch manager to reset it from the Users screen).

---

## 17. Common tasks (quick recipes)

### "Run a full day's operation"

1. **Morning**: open Trips, advance each planned trip to **boarding** as the vehicle arrives at the terminal
2. **Boarding**: conductors add manifest entries as passengers and cargo come on
3. **Departure**: advance to **departed** when the vehicle leaves
4. **In transit**: drivers can log fuel stops and tolls as Expenses if needed
5. **Arrival**: advance to **arrived** at the destination
6. **End of trip**: advance to **closed** when everyone is off
7. **Cash-up**: conductor opens cash-up, declares what was collected, submits
8. **Approval**: branch accountant reviews and approves → trip becomes **cashed_up**
9. **Repeat** for the next trip

### "End of month — pull reports for the owner"

1. Go to **Reports** → tap **30d** (or 90d for a wider view)
2. Review the KPI tiles and the daily chart
3. Scroll to **Branch performance** to see which branch performed best
4. Scroll to **Vehicle ROI** to see fleet profitability
5. Take screenshots or note the numbers — the report is the source of truth

### "Driver's license is about to expire"

The app shows a yellow "License expiry" badge on any driver whose license is within 90 days of expiry. To handle:

1. Open the **Drivers** screen
2. Find the driver with the yellow badge
3. Ask them to renew their license
4. Open the driver profile, tap **Edit**, update the new `license_expiry` date, save

### "Vehicle is grounded and we need to use it"

A vehicle in `grounded` status can't be assigned to a trip. To un-ground:

1. Open the vehicle detail
2. If there's an open maintenance record, complete or cancel it
3. If not, edit the vehicle and change status back to `available`

---

## 18. FAQ

**Q: I tapped "→ Departed" by accident. Can I undo?**
A: No — the state machine is one-way. Talk to your branch manager; they can adjust the trip manually if needed.

**Q: The map is blank. What gives?**
A: Either your branch hasn't had GPS coordinates set, or the route's origin/destination branches don't have GPS. Ask the owner/GM to add lat/lng to the branch.

**Q: I see a variance of -5000 on a cash-up. What does that mean?**
A: The conductor collected ₦5,000 less than the manifest said they should. They declared 5000 short. The branch accountant should investigate (some passengers may not have paid, or there may be an error).

**Q: Why is the manifest read-only after departure?**
A: Once the vehicle leaves, you can't keep adding or removing entries — that would mess up the cash-up calculation. Make all manifest changes during boarding.

**Q: I can't see a branch / vehicle / driver in the list.**
A: Branch-scoped roles (BM, BA) only see records in their own branch. If you need broader access, ask the owner to change your role.

**Q: How do I reset a user's password?**
A: Owner / GM / BM can edit a user and update the password field. The user will be able to log in with the new password.

---

## 19. Troubleshooting

| Problem | Try this |
|---|---|
| App won't open | Force-close and re-open. If still broken, reinstall |
| Login fails with "Invalid email or password" | Check caps lock. Reset via the user profile if you can |
| Login fails with "Account is suspended" | Contact your branch manager — your account was disabled |
| List is stuck on "Loading…" | Pull down to refresh. If still stuck, log out and back in |
| "Forbidden" / "Insufficient role" message | Your role can't do this action. Ask your branch manager or owner |
| Trip won't advance state | Check that the state is the next valid one (you can't skip states) |
| Cash-up variance is huge | Check the manifest for incorrect fares, then re-submit |

---

## 20. Support

**Built by:** Exit Media Solutions
**For:** The Client Company

If you need help, find a bug, or want a new feature:

- **Internal support channel**: contact your branch manager first
- **Critical issues**: escalate to the owner / GM
- **Platform bugs / feature requests**: contact Exit Media Solutions support at [your-support-email]

---

## Appendix A: Demo logins (for training only)

⚠️ **These are training accounts. Never use them in production.**

| Role | Email | Password |
|---|---|---|
| Super Admin | `admin@transitos.app` | `Admin#Transit2026!` |
| Owner | `owner@transitos.app` | `Owner#Transit2026!` |
| General Manager | `gm@transitos.app` | `Gm#Transit2026!` |
| Branch Manager (Lagos) | `bm.lagos@transitos.app` | `Bm#Transit2026!` |
| Fleet Manager (Lagos) | `fm.lagos@transitos.app` | `Fm#Transit2026!` |
| Driver (Lagos) | `driver1@transitos.app` | `Driver#Transit2026!` |
| Conductor (Lagos) | `conductor1@transitos.app` | `Conductor#Transit2026!` |

**Change all of these before going live.**

---

## Appendix B: Glossary

- **Branch**: a physical location (depot, terminal, office) where you store vehicles and base staff
- **Cash-up**: the conductor's reconciliation at the end of a trip — what was actually collected vs the manifest
- **Conductor**: the crew member responsible for ticket collection and on-board operations
- **Manifest**: the list of passengers and cargo booked on a specific trip
- **Route**: a defined path between two branches with a known distance, duration, and fare
- **Trip**: one scheduled run: one vehicle, one driver, one conductor, one route
- **Variance**: the difference between declared cash and expected manifest total (positive = overage, negative = shortage)
- **Vehicle**: a bus, minibus, or truck in your fleet

---

*End of manual. © Exit Media Solutions. All rights reserved.*

---

## 19. Admin bootstrap

The very first time you deploy TransitOS, there are no users in the database. The app's
login screen needs at least one account to verify. Rather than asking you to install
Python and run a script on your laptop, the backend ships with a one-shot admin endpoint
that creates the core accounts (Super Admin, Owner, General Manager) plus a demo branch,
vehicle, driver, conductor and route — directly into your deployed MongoDB.

**Important:** this endpoint is **disabled by default**. You must explicitly enable it
in your deployment environment, hit it once, then disable it again.

### 19.1 Enable the endpoint

In **Railway** → your service → **Variables** tab, add:

| Variable | Value |
|---|---|
| `ADMIN_BOOTSTRAP_TOKEN` | `<a long random string>` (e.g. `openssl rand -hex 32`) |

Railway will redeploy automatically.

### 19.2 Hit the endpoint

From any terminal with curl:

```bash
curl -X POST https://transitos-production-4b46.up.railway.app/admin/seed \
     -H "X-Admin-Token: <the secret you just set>"
```

A successful response looks like:

```json
{
  "data": {
    "status": "ok",
    "summary": {
      "created": {
        "users": ["admin@transitos.app", "owner@transitos.app", "gm@transitos.app", "driver1@transitos.app", "conductor1@transitos.app"],
        "branches": ["LOS-01"],
        "vehicles": ["LSR-001-AA"],
        "drivers": ["..."],
        "conductors": ["..."],
        "routes": ["Lagos Marina Loop"]
      },
      "skipped": { "users": [], "branches": [], ... }
    },
    "credentials": {
      "note": "CHANGE ALL PASSWORDS BEFORE GOING LIVE.",
      "super_admin": { "email": "admin@transitos.app", "password": "Admin#Transit2026!" },
      "owner": { "email": "owner@transitos.app", "password": "Owner#Transit2026!" },
      "general_manager": { "email": "gm@transitos.app", "password": "Gm#Transit2026!" }
    }
  }
}
```

The endpoint is **idempotent** — calling it again is safe; existing accounts are skipped
and the response shows them in `skipped` instead of `created`.

### 19.3 Log in and rotate passwords

Open the app and log in as the owner:

- **Email**: `owner@transitos.app`
- **Password**: `Owner#Transit2026!`

Immediately go to **Me → Change password** and set a strong, unique password. Repeat for
the General Manager and the Super Admin.

### 19.4 Lock the endpoint

Once the demo accounts are in place and you've rotated the Owner/GM passwords, **delete
the `ADMIN_BOOTSTRAP_TOKEN` variable in Railway**. The endpoint will then return `403
Forbidden` to every request, forever. This is the single most important step before
going live.

### 19.5 What if I lose the token?

That's fine — the endpoint is disabled and there's no way back in. But you can re-enable
it any time by setting `ADMIN_BOOTSTRAP_TOKEN` to a new value, deploying, and hitting
the endpoint again. The seed is idempotent, so it won't create duplicates.

### 19.6 Local development (alternative)

If you prefer to seed from your laptop instead of via the API:

```bash
cd backend
pip install -r requirements.txt
MONGODB_URL="<your-railway-or-atlas-mongo-url>" \
MONGODB_DB_NAME="transitos" \
python -m scripts.seed
```

The `scripts/seed.py` script does exactly what the endpoint does. Use whichever is
easier for your workflow.

