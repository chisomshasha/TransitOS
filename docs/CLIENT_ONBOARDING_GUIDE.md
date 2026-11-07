# TransitOS — Branch Onboarding & Operations Guide

**Audience:** the client team — head office, branch managers, fleet and
finance staff.
**Applies to:** TransitOS v1.2.0 (Expo app + TransitOS API).
**Date:** 3 November 2026.
**Companion:** *Role Design & Operating Model* — why the app is shaped
the way it is, and what each role is accountable for.

> You already have the *User Manual*, which explains what every screen
> looks like. This document is the other half: **what to do, in what
> order, by whom** — so you can open a branch and start running trips on
> it. Use this to set up; use the User Manual to look things up.

---

## 0 · How to read this

| Part | What it is | Who does it | How often |
|---|---|---|---|
| **1** | Before you start — what you need and who does what | Head office | Once |
| **2** | Company setup — the first branch, the first accounts | Head office | Once |
| **3** | Onboarding a branch | Branch manager | **Per branch** |
| **4** | Daily operations — the working day | Everyone | Every day |
| **5** | The money loop | Finance + branch manager | Every trip |
| **6** | When something goes wrong | Everyone | As needed |
| **A–C** | Role matrix, trip life cycle, glossary | — | Reference |

Every step says **"You need: <role>"**. If you do not have that role,
the screen is not on your phone — that is by design, not a fault.

### How the app is laid out

The app has a bar of **tabs** along the bottom and a **More** menu
holding everything else.

* **Tabs:** Home · Trips · Vehicles · More · Reports · Profile
* **More** groups its tiles into four sections:
  **Operations** (Trips, Vehicles, Branches, Users, Conductors, Routes,
  Live trips, Live map, Transfers) · **Finance** (Cash Ups, Expenses,
  Settlements) · **Fleet** (Fuel, Maintenance, Incidents) · **System**
  (Notifications, Audit log, Role permissions, My devices, Sync).

Which tabs and tiles you get depends on your role — see **Appendix A**.
Not everything is everywhere: a driver gets Home, Trips, More and Profile
and nothing else.

---

# Part 1 · Before you start

## 1.1 What you need from us (the developers)

Three things must be in place before any branch can start. Without them
the app opens but every request fails.

| # | What | Why it matters | Who provides |
|---|---|---|---|
| 1 | **A live TransitOS API URL** and the sign-in details for your first account | Every screen talks to this server. | Developers → head office |
| 2 | **The Android APK** (or an Expo Go install with the app) | The app itself. | Developers → branch managers |
| 3 | **Your first three accounts** — see 1.3 | Nobody can create accounts without one of these. | Developers → head office |

## 1.2 The ten roles, in plain English

| Role | Think of them as | Day-to-day work |
|---|---|---|
| `super_admin` | The developers' operator | Rarely used by you. First account only. |
| `owner` | The owner of the company | Signs off on everything |
| `general_manager` | The operations director | Runs the whole company from one screen |
| `branch_manager` | **The owner of one branch** | **Runs their branch day to day** |
| `operations_manager` | The dispatcher | Plans trips, watches the fleet |
| `fleet_manager` | The fleet supervisor | Vehicles, drivers, conductors, maintenance |
| `chief_accountant` | The group accountant | Cash-ups and settlements, company-wide |
| `branch_accountant` | The branch bookkeeper | Cash-ups and settlements for one branch |
| `driver` | The driver | Their own trip, pre-trip check |
| `conductor` | The conductor | Their own trip, passenger manifest, cash-up |

**Start with three people per branch:** a branch manager, a conductor and
a driver. Add the rest later.

## 1.3 The first three accounts

| Email | Password | Role |
|---|---|---|
| `admin@transitos.app` | `Admin#Transit2026!` | Platform admin |
| `owner@transitos.app` | `Owner#Transit2026!` | Company owner |
| `gm@transitos.app` | `Gm#Transit2026!` | General manager |

> **Change these passwords on first login.** They are printed in this
> document and in the developer handover — treat them as temporary.

**First sign-in:** open TransitOS → enter email and password → you land
on the **Home** screen. "Invalid email or password" means the email was
typed with capitals, Caps Lock is on, or the account is not Active.

---

# Part 2 · Company setup (do once)

> **You need: `owner`, `general_manager` or `super_admin`.**

## 2.1 Create the first branch

Your first branch must exist before you can create staff, because four
roles are **branch-scoped** — the app will not create them without a
branch.

**More → Operations → Branches → tap "Add branch"**

| Field | Rule | Example |
|---|---|---|
| Name | The name people will say out loud | Lagos Island Terminal |
| Code | **Short, uppercase, unique.** Appears on every trip, cash-up and settlement. | LOS |
| City | | Lagos |
| State | | Lagos |
| Address | | 1 Marina Road, Lagos Island |
| Phone | | +234 800 000 0001 |
| Email | | lagos@transitos.app |

> **The code is permanent.** It identifies the branch on every trip,
> cash-up and settlement forever. "LOS-01" is better than "LAGOS" if you
> will ever open a second Lagos branch.

> **Tip:** the **Home** screen also has a **Branch** quick action that
> opens the same form — handy once you are used to the app.

## 2.2 Review the permission matrix

**More → System → Role permissions** lists what each of the ten roles
can do. You do not need to change anything — just open it once and
confirm the rows you expect are there.

## 2.3 Create the company-level accounts

**More → Operations → Users → tap "Invite user"**

Create these first — everyone else depends on them:

| Person | Role |
|---|---|
| Head of operations | `general_manager` |
| Group accountant | `chief_accountant` |
| Fleet supervisor | `fleet_manager` |

**How to fill the form:**

1. **Full name** — as it should appear on approvals and audit logs.
2. **Email** — this is their username. Lower case, no spaces.
3. **Phone** — optional but recommended; it shows on the live board.
4. **Role** — pick from the list.
5. **Branch** — leave blank for company-wide roles (`owner`,
   `general_manager`, `operations_manager`, `fleet_manager`,
   `chief_accountant`). **Required** for `branch_manager`,
   `branch_accountant`, `driver` and `conductor`.
6. **Temporary password** — the app generates one. Tap **Regenerate**
   until it is something you can read out over the phone, then tap
   **Invite user**.

> **Give the password securely** — a phone call, not a group chat — and
> ask them to change it on first login. Every action is written to the
> audit log against the person's name.

---

# Part 3 · Onboarding a branch

> **Repeat this part for every branch.** About 30 minutes for the first
> one, 15 minutes after that.
>
> **You need: `branch_manager` (or `general_manager` / `owner`).**

Do these in order — each step depends on the one before.

## 3.1 The branch record

**More → Operations → Branches → tap your branch.**

Check the name, code, city, address and phone. If the branch manager is
not set yet, you will be offered to set one — skip that for now, we come
back in 3.4.

## 3.2 Vehicles

**Vehicles tab → tap "Add vehicle"**
*(also: More → Operations → Vehicles)*

Every vehicle that will carry passengers or cargo needs a record before
it can be assigned to a trip.

| Field | Rule | Notes |
|---|---|---|
| Registration number | **Unique**, uppercase | e.g. `LAG-123-XY`. Appears on the live board and the waybill. |
| Type | Bus / Minibus / Truck | Pick the closest match |
| Seats | Number | Passenger capacity |
| Cargo (kg) | Optional | Leave 0 if the vehicle carries no freight |
| Branch | Your branch | |
| Status | Available | **Only "Available" vehicles can be assigned to a trip.** |

> **Keep the status honest.** A vehicle left on "Available" while it is in
> the workshop can be booked for a trip that cannot happen. Change the
> status when the vehicle goes off the road.

## 3.3 Drivers and conductors

**Drivers:** the **Home** screen → tap the **"Drivers on duty"** tile
(for the list) or the **"Driver"** quick action (to add one) → **"Add driver"**.
**Conductors:** **More → Operations → Conductors → "Add conductor"**.

| | Driver | Conductor |
|---|---|---|
| Full name | ✔ | ✔ |
| Phone | ✔ | ✔ |
| Branch | ✔ | ✔ |
| **Licence number** | **Required** | — |
| **Licence expiry** | **Required** | — |
| Years of experience | Optional | — |
| **Badge number** | — | **Required** |

> **Licence expiry drives the app.** The alerts engine watches it and
> raises a notification before it lapses. Enter the real date. The same
> applies to **vehicle documents** (roadworthiness, insurance) — check
> **Vehicles → your vehicle** and fill them in.

## 3.4 Staff accounts for this branch

**More → Operations → Users → "Invite user"**

| Person | Role | Branch |
|---|---|---|
| The branch's boss | `branch_manager` | this branch |
| The branch's bookkeeper | `branch_accountant` | this branch |
| Crew | `driver` | this branch |
| Crew | `conductor` | this branch |

**Then set the branch manager:**

**More → Operations → Branches → tap your branch → set manager** → pick
the person you just created.

This matters: it is what makes the branch's cash-ups and reports show up
under that branch rather than company-wide.

## 3.5 Routes

**More → Operations → Routes → "Add route"**

A route is a **journey**, not a street. "Lagos → Ibadan Express" is a
route. If the same road runs three ways with different stops, that is
three routes.

| Field | Rule |
|---|---|
| Name | The name the crew will recognise |
| Type | Inter-state / Intra-state / Commuter / Special — this drives the permit rules |
| Origin branch / Destination branch | Tap to select. **They must be different.** |
| Origin city / Destination city | |
| Distance (km) | Used to compute fuel and expected revenue |
| Duration (hrs) | **Used to auto-fill the trip's scheduled arrival.** Get this right and trip scheduling works itself. |
| Passenger fare | Per seat |
| Cargo fare /kg | Per kilogram |

> **Set the duration accurately.** TransitOS calculates a trip's
> scheduled arrival from this number. A wrong duration means trips show
> up "late" or "early" on the live board — the first thing a dispatcher
> will complain about.

**Inter-state routes also need permits.** The route form asks which
permits the vehicle must hold (for example `interstate_license`). Check
them against the vehicle's documents before the first trip.

## 3.6 Your branch is live

You now have a branch, its vehicles, its crew, its staff accounts and
its routes. **Part 4 starts.**

---

# Part 4 · Daily operations

## 4.1 The daily loop at a glance

```
Morning   Fleet manager      → log fuel for each vehicle going out
           Operations manager → create the day's trips
           Driver             → pre-trip checklist
           Conductor          → add the passengers and cargo to the manifest
During    Branch manager     → Start boarding → Confirm departure
           Operations manager → live board / live map
           Anyone             → report an incident
End of day Branch manager   → Confirm arrival → Close trip
           Conductor          → count the cash → Save cash-up → Submit for approval
           Chief accountant   → approve or reject the cash-up
```

The four evening steps — *Close trip*, *Save cash-up*, *Submit for
approval*, *Approve* — are the money loop, and they are explained
step by step in **Part 5**.

## 4.2 Log fuel — before the vehicle moves

**You need:** `fleet_manager`, `branch_manager`, `general_manager`,
`owner`, `super_admin`.

**More → Fleet → Fuel → tap "Log fuel"**

Record the odometer and fuel level for each vehicle going out. TransitOS
uses the logs to calculate efficiency per vehicle and to warn about low
fuel.

## 4.3 Create the day's trips

**You need:** `operations_manager`, `branch_manager`, `fleet_manager`,
`general_manager`, `owner`, `super_admin`.

**Trips tab → tap "New trip"**

| Field | Where it comes from |
|---|---|
| Route | The routes you set up in 3.5 |
| Vehicle | **Only vehicles with status "Available" are listed.** If one is missing, check its status. |
| Driver | From your branch's drivers |
| Conductor | From your branch's conductors |
| Date, Departure time | The actual plan |
| Scheduled arrival | **Filled in for you** from the route's duration. Check it — it is what the live board shows. |

> **Only "Available" vehicles appear in the list.** This is deliberate —
> it stops you booking a vehicle that is in the workshop. If a vehicle
> you expected is missing, open the **Vehicles** tab and check its
> status.

**Trips tab → search box** finds a trip later. Tap any trip to open it.

## 4.4 The pre-trip checklist

**You need:** the `driver` on that trip (also open to supervisors).

**Trips → tap a trip → Pre-trip checklist**

Ten points, each marked Pass or Fail:

1. Tires & wheels
2. Brakes & lights
3. Mirrors & signals
4. First-aid kit
5. Fire extinguisher
6. Fuel level
7. Vehicle documents
8. Odometer reading
9. Engine oil & coolant
10. Driver signature

The screen shows progress ("4 of 10 complete") and flags a **Fail**
loudly. **A failed item should stop the trip.** If a vehicle fails
inspection, tell the branch manager, set the vehicle's status to
`Maintenance`, and report it — do not depart.

## 4.5 The live board and the live map

**You need:** `operations_manager`, `branch_manager`, `fleet_manager`,
`general_manager`, `owner`, `super_admin`.

**More → Operations → Live trips** — every active trip and where it is.
**More → Operations → Live map** — the same on a map, plus vehicle
positions. The Home screen also has a map card and an "Open full map"
button.

> **The map needs internet.** It draws map tiles from OpenStreetMap over
> the mobile network. Everything else in the app works without it — only
> the map goes blank. In poor signal, use the **Live trips** board
> instead; it works offline.

## 4.6 Scanning QR codes

**You need:** the `driver`, `conductor`, or any supervisor.

Tap the **QR-code button in the bottom-right corner of the Home
screen** to open the scanner. Point the camera at the QR code on a
vehicle or a driver's document to pull up their record.

> The camera asks for permission the first time — allow it. If the
> camera does not open, check **phone Settings → Apps → TransitOS →
> Camera**.

## 4.7 Report an incident

**You need:** `driver`, `conductor`, `branch_manager`, `operations_manager`,
`fleet_manager`, `general_manager`, `owner`, `super_admin`.

**Trips → tap a trip → Report incident**, or **More → Fleet →
Incidents → "Report incident"**.

Describe what happened. Incidents appear under **More → Fleet →
Incidents** with a status; the branch manager acknowledges and resolves
them.

## 4.8 Record expenses

**You need:** `branch_manager`, `chief_accountant`, `branch_accountant`,
`general_manager`, `owner`, `super_admin`.

**More → Finance → Expenses → tap "Record expense"** — branch expenses
(fuel top-up, maintenance, tolls). Expenses are included in the
settlement figures.

## 4.9 Log maintenance

**You need:** `fleet_manager`, `branch_manager`, `general_manager`,
`owner`, `super_admin`.

**More → Fleet → Maintenance → tap "Log maintenance"** — schedule or log
work on a vehicle. The alerts engine raises a notification when
maintenance falls due.

## 4.10 The app updates itself

**You do not need to install anything when we fix a problem.**

When we correct something, the corrected version is downloaded to your
phone in the background while you are using the app. It is applied the
**next time you open the app**.

So if a screen still looks like the old one:

1. Close the app completely — swipe it away from your phone's app
   switcher, not just the home button.
2. Open TransitOS again.
3. If it still looks the old one, open it once more. The first open
   after the fix downloads it; the second applies it.

Your trips, cash-ups and vehicle records are never affected by an
update — they live on the server, not on the phone.

> **If you are on a test build**, the dashboard shows a yellow
> **Preview build** strip. Test builds receive test fixes and must not
> be used for live operations.

---

# Part 5 · The money loop

> **Read this part before you go live.** It is the part of the app that
> carries money, and it is the part that changed most recently.

## 5.1 How the money flows

```
Trip created                     status: planned
  ↓  Start boarding  → Confirm departure  → Confirm arrival  → Close trip
Conductor adds the passengers and cargo to the manifest
  ↓
Cash-up saved                    status: draft
  ↓  Submit for approval
Cash-up submitted                 status: submitted
  ↓  Approve / Reject
Cash-up approved                  status: approved
  ↓
Trip marked                       status: cashed_up
Settlement                        ready for payment
```

Every arrow in that diagram is a button in the app. Nothing has to be
done through the command line.

## 5.2 The five screens

| What you want to do | Where the button is |
|---|---|
| Move a trip to its next stage | **Trips → tap the trip** → the **Trip status** card at the top |
| Add a passenger or a parcel | **Trips → tap the trip** → **Manifest** → **+ Passenger** / **+ Cargo** |
| Remove a passenger who did not turn up | **Trips → tap the trip** → **Manifest** → the bin icon on that entry |
| Count the day's takings and declare them | **Trips → tap the trip** → the **Cash-up** card at the bottom |
| Send the cash-up for approval | On the trip screen (**Submit for approval**) or on **More → Cash Ups** |
| Approve or reject a cash-up | **More → Cash Ups** → tap a cash-up marked *Awaiting approval* |

## 5.3 Step by step: a trip from `planned` to `cashed up`

**Step 1 — open the trip.** Go to the **Trips** tab and tap the trip.

**Step 2 — move it along.** The **Trip status** card at the top of the
screen carries the current status and one button for the next stage:

| The card says | Press | What happens |
|---|---|---|
| `Planned` | **Start boarding** | Passengers are getting on. |
| `Boarding` | **Confirm departure** | The vehicle left the terminal; the actual departure time is stamped automatically. |
| `Departed` | **Confirm arrival** | The vehicle reached the destination; the actual arrival time is stamped automatically. |
| `Arrived` | **Close trip** | The journey is over. The cash-up can now be recorded. |
| `Boarding` or `Planned` | **Cancel trip** | The trip is called off. You are asked for a reason, and it is kept on the trip and in the audit log. A reason is mandatory. |

The order is enforced by the server: you cannot skip from *Planned* to
*Departed*, and a closed trip cannot be reopened.

> **Who can move a trip:** branch manager, operations manager, general
> manager, owner and super admin. Everyone else sees the status card in
> read-only form.

**Step 3 — fill in the manifest.** Still on the trip screen, in the
**Manifest** section:

- **+ Passenger** opens a form for a passenger: name, phone, seat
  number, the fare they paid, and whether it was paid on board or paid
  in advance.
- **+ Cargo** opens a form for a parcel: what it is, how many kilograms,
  the sender, the receiver's phone, the freight charge, and the payment
  status.
- The **bin icon** on any entry removes it. (This is how you correct a
  mistake — remove the entry and add it again.)

The manifest **locks when the trip departs**, because a passenger
cannot board a vehicle that has already left.

> **Who can edit the manifest:** conductor, branch manager, operations
> manager, general manager, owner and super admin.

**Step 4 — count the money.** Scroll to the **Cash-up** card at the
bottom of the trip screen. Enter how many notes and coins of each
denomination the conductor is holding:

```
₦1,000   ₦500   ₦200   ₦100   ₦50   Coins (₦)
```

The card shows three figures as you type:

- **Expected (system)** — the sum of the manifest fares. This is what
  the trip *should* have collected.
- **Counted (physical)** — your denominations added up.
- **Variance** — counted minus expected. Green means the count is at or
  above expectation; red means a shortage.

**Step 5 — save the draft.** Press **Save cash-up**. The cash-up is
saved as a **draft**: it is recorded against the trip but nobody in
finance can see it yet. You can save it again to correct the count.

**Step 6 — submit it.** Press **Submit for approval**. The app asks the
server for the official expected figure, works out the variance at that
moment, and moves the cash-up to **submitted**. It now appears on
**More → Cash Ups** under *Awaiting approval*.

You can also submit from the cash-ups list: **More → Cash Ups → Draft**
→ **Submit for approval** on the row.

> **Who can declare and submit:** conductor, branch manager, branch
> accountant, chief accountant, general manager, owner and super admin.

**Step 7 — approve.** **More → Cash Ups** → tap the cash-up. The review
sheet shows the declared amount, the expected amount, the variance and
the breakdown. Press **Approve** or **Reject**. A rejection needs a
reason; the conductor sees it on the trip screen and can correct the
count and submit again.

When a cash-up is approved, the trip flips to **cashed up** by itself.

> **Who can approve:** chief accountant, branch accountant, general
> manager, owner and super admin.

## 5.4 Where the "expected" figure comes from

The app compares what the conductor declared against what the manifest
says the trip should have earned. So the variance is only as honest as
the manifest.

- If the manifest is empty, the expected figure is **zero** and every
  cash-up will look like a large overage.
- If a passenger is removed with the bin icon, their fare stops counting
  at once — the trip's revenue, the waybill PDF and the cash-up's
  expected figure all drop together.

**Rule of thumb:** fill in the manifest before the vehicle departs, and
correct it before the trip closes. Once the trip is closed, the manifest
is locked and the cash-up is measured against exactly what was recorded.

## 5.5 Who can do what in the money loop

| Action | Roles |
|---|---|
| Move a trip through its stages | Branch manager, Operations manager, General manager, Owner, Super admin |
| Cancel a trip (reason required) | The same list as above |
| Add or remove manifest entries | Conductor, Branch manager, Operations manager, General manager, Owner, Super admin |
| Save and submit a cash-up | Conductor, Branch manager, Branch accountant, Chief accountant, General manager, Owner, Super admin |
| Approve or reject a cash-up | Branch accountant, Chief accountant, General manager, Owner, Super admin |
| Read the cash-ups list | Everyone above, plus the branch roles that belong to that branch |

Branch-scoped roles — branch manager, branch accountant and fleet
manager — only ever see and change **their own branch's** records. A
branch accountant in Lagos cannot open a cash-up belonging to Abuja.

## 5.6 If the numbers do not agree

| What you see | What it means | What to do |
|---|---|---|
| "Trip must be 'closed' before cash-up, not 'planned'" | The trip has not been closed yet | Move the trip to *Closed* on the trip screen (**5.3**, step 2) |
| "Cannot add manifest to a trip in status 'departed'" | The trip has already left | The manifest is locked from *Departed* onwards. If the trip is not yet on the road, move it back is not possible — ask your dispatcher to correct the record |
| The expected figure is zero | The manifest is empty | Add the passengers and cargo while the trip is still *Planned* or *Boarding* |
| A negative variance | The conductor counted less than the manifest expected | Normal for a passenger who paid on board and did not pay. Check the manifest entry for that passenger — if it should have been *Cancelled*, remove it before the trip closes |
| "A cash-up already exists for this trip" | The trip already has a cash-up | Open the trip and **Save cash-up** again to correct it; do not create a second one |
| "Breakdown sum does not match declared_total" | The figures sent do not add up | This is a server-side refusal. Retake the count and save again |

---

# Part 6 · When something goes wrong

| What you see | What it means | What to do |
|---|---|---|
| "Invalid email or password" | Wrong email, wrong case, or Caps Lock | Type the email in lower case. If it still fails, ask the branch manager to check the account is Active. |
| "Trip must be 'closed' before cash-up" | The trip has not been closed | Open the trip and press **Close trip** in the **Trip status** card (**5.3**). |
| A vehicle is missing from the trip form | Its status is not "Available" | **Vehicles tab** → set it to Available (only if it genuinely is) |
| "You cannot assign a role more senior than your own" | A branch manager tried to create a manager-level account | Only `owner` / `general_manager` / `super_admin` can create branch managers and above. |
| "branch_id is required for this role" | A driver or conductor was created without a branch | Pick the branch. These four roles must belong to a branch. |
| A section is missing from the More menu | Your role does not have it | See **Appendix A**. Ask your branch manager or head office. |
| The map is blank but everything else works | No data connection for the map tiles | Use **More → Operations → Live trips** instead. |
| The camera will not open | Permission denied | **phone Settings → Apps → TransitOS → Camera → Allow** |
| A request hangs, then fails | No connection to the API server | Check your signal; tell the developers if it happens on Wi-Fi too. |
| The app shows stale data | Cached data | **More → System → Sync**, then reopen the screen. |
| A screen still shows the old version after we fixed it | The corrected version has been downloaded but not applied yet | Close the app completely and open it again — twice if needed. See **4.10**. |
| The app behaves oddly after hours open | Long-lived session | Close the app fully and reopen it. |

---

# Appendix A · Who can see and do what

**Sections** — which role finds which part of the app:

| Section | Where it is | Roles |
|---|---|---|
| Branches | More → Operations | SA, owner, GM, BM, OM |
| Users | More → Operations | SA, owner, GM, BM |
| Vehicles | Vehicles tab / More → Operations | SA, owner, GM, BM, OM, FM |
| Drivers | Home → "Drivers on duty" | SA, owner, GM, BM, OM, FM |
| Conductors | More → Operations | SA, owner, GM, BM, OM, FM |
| Routes | More → Operations | SA, owner, GM, BM, OM, FM |
| Trips | Trips tab | everyone, including driver and conductor |
| Live trips / Live map | More → Operations | SA, owner, GM, OM, BM, FM |
| Cash-ups | More → Finance | SA, owner, GM, BM, CA, BA, conductor |
| Expenses | More → Finance | SA, owner, GM, BM, CA, BA |
| Settlements | More → Finance | SA, owner, GM, BM, CA, BA |
| Reports | Reports tab | SA, owner, GM, BM, OM, FM, CA, BA |
| Fuel / Maintenance | More → Fleet | SA, owner, GM, BM, FM |
| Incidents, Transfers | More → Fleet | SA, owner, GM, OM, BM, FM |
| Audit log, Role permissions | More → System | SA, owner, GM |
| Notifications, My devices, Sync | More → System | everyone |

**Who can create what** — the button only appears for these roles:

| What | Button | Roles that can create it |
|---|---|---|
| A branch | Add branch | SA, owner, GM, BM |
| A user | Invite user | SA, owner, GM, BM |
| A vehicle | Add vehicle | SA, owner, GM, BM, OM, FM |
| A driver | Add driver | SA, owner, GM, BM, OM, FM |
| A conductor | Add conductor | SA, owner, GM, BM, OM, FM |
| A route | Add route | SA, owner, GM, BM, OM, FM |
| A trip | New trip | SA, owner, GM, BM, OM, FM |
| A fuel log | Log fuel | SA, owner, GM, BM, FM |
| A maintenance record | Log maintenance | SA, owner, GM, BM, FM |
| An expense | Record expense | SA, owner, GM, BM, CA, BA |

**Bottom tabs** — what each role sees on the home bar:

| Role | Tabs |
|---|---|
| SA, owner, GM, BM, OM, FM | Home · Trips · Vehicles · More · Reports · Profile |
| chief accountant | Home · More · Reports · Profile |
| branch accountant | Home · Trips · More · Reports · Profile |
| driver, conductor | Home · Trips · More · Profile |

**Cash-up approval** is restricted to `super_admin`, `owner`,
`general_manager`, `chief_accountant` and `branch_manager`.

> **One role, one screen.** If someone asks for a role they do not need,
> they will see less of the app — and that is the point. A conductor sees
> their own trips, not the company's.

---

# Appendix B · The life of a trip

```
planned  ──►  boarding  ──►  departed  ──►  arrived  ──►  closed  ──►  cashed_up
   │            │                                                  (final)
   └────────────┴────────────────►  cancelled
                              (final)
```

| Status | What it means | Who moves it | The button |
|---|---|---|---|
| `planned` | Scheduled, not yet started | Created by the dispatcher | — |
| `boarding` | Passengers boarding | Branch manager, Ops manager, GM, Owner, Super admin | **Start boarding** |
| `departed` | On the road | Same | **Confirm departure** |
| `arrived` | At the destination | Same | **Confirm arrival** |
| `closed` | Journey finished, ready to count the money | Same | **Close trip** |
| `cashed_up` | Money counted, submitted and approved | The system, when the cash-up is approved | — |
| `cancelled` | Trip will not run | Same | **Cancel trip** (a reason is required) |

The order is enforced by the server: an out-of-order move is refused.
`cashed_up` is not set by hand — the app sets it when a cash-up is
approved, so a trip can never reach it without the money being
accounted for. See **Part 5.3** for the step-by-step.

---

# Appendix C · Words you will meet

| Word | Meaning |
|---|---|
| **Branch** | One operating location — a depot or terminal. Everything in the app belongs to a branch. |
| **Route** | A journey between two places, with its distance, duration and fares. |
| **Trip** | One vehicle, one driver, one conductor, one route, one departure. The operational unit of the app. |
| **Manifest** | The list of passengers and cargo on a trip. It is what the expected revenue is calculated from. |
| **Cash-up** | The money the conductor counted at the end of a trip, broken down by payment method (cash, transfer, POS). |
| **Variance** | The difference between what was declared and what the app expected. Negative = a shortage. |
| **Settlement** | What the company owes a branch or a crew member once trips, expenses and cash-ups are netted off. |
| **Pre-trip checklist** | The ten-point vehicle inspection the driver completes before departure. |
| **Live board** | The screen showing all active trips and where they are. |
| **Scanning** | Reading a QR code on a vehicle or document with the phone's camera. |
| **Audit log** | A permanent record of who did what, and when. Only head office can read it. |
| **Alerts** | Notifications raised automatically — expiring licences, due maintenance, low fuel. |
| **Branch-scoped role** | A role that belongs to one branch and only sees that branch's records. |

---

## A last word

The app is strong on **fleet, people and journeys**: vehicles, drivers,
conductors, routes, trips, the live board, inspections, incidents,
maintenance, fuel, documents and alerts all work and are audited.

It is now **strong on money as well**. The money loop described in
Part 5 runs end to end inside the app: the trip moves through its
stages, the manifest records who travelled and what they paid, the
conductor counts the takings and declares them, an accountant approves
or rejects the declaration, and the trip closes as *cashed up*.

Two habits keep the numbers honest:

1. **Fill in the manifest before the vehicle departs.** It locks after
   that, and the cash-up is measured against it.
2. **Declare the cash the same day the trip closes.** A draft cash-up
   is invisible to finance until it is submitted.

Until finance signs off on the app as the system of record for cash,
keep reconciling against your existing cash sheet for the first month.

If anything in this guide does not match what you see on the phone,
**tell us which screen and what you expected** — that is the fastest way
to get it fixed, and we would rather fix it than have you work around it.
