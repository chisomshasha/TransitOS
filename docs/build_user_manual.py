#!/usr/bin/env python3
"""
Generate the TransitOS User Manual (Markdown) from the codebase.

The manual is *generated*, not hand-written, so its access tables and
reference sections cannot drift away from the code. Prose that describes
a workflow lives here; anything that can be read out of the source
(roles, tab access, screen access, status enums, role labels) is
extracted at build time.

Screenshots are real captures of the shipped front end, taken by
``docs/mockup/capture.py``. Every captured screenshot is placed exactly
once: shared screens in Part 1, role screens in Part 2.

Output: docs/USER_MANUAL.md
"""

from __future__ import annotations

import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FRONTEND = os.path.join(ROOT, "frontend")
BACKEND = os.path.join(ROOT, "backend")
SHOTS = os.path.join(ROOT, "docs", "mockup", "shots")
OUT = os.path.join(ROOT, "docs", "USER_MANUAL.md")


# ── extract from the front end ──────────────────────────────────────────────
def read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def parse_role_labels() -> dict[str, str]:
    src = read(os.path.join(FRONTEND, "lib", "types.ts"))
    block = re.search(r"ROLE_LABELS[^=]*=\s*\{(.*?)\}", src, re.S)
    if not block:
        return {}
    return dict(re.findall(r"[\"']?([a-z_]+)[\"']?\s*:\s*'([^']+)'", block.group(1)))


def parse_tabs_by_role() -> dict[str, list[str]]:
    src = read(os.path.join(FRONTEND, "lib", "rbac.ts"))
    block = re.search(r"TABS_BY_ROLE[^=]*=\s*\{(.*?)\n\};", src, re.S)
    if not block:
        return {}
    out: dict[str, list[str]] = {}
    for role, body in re.findall(r"([a-z_]+)\s*:\s*(\[[^\]]*\]|ALL_TAB_IDS)", block.group(1)):
        if body == "ALL_TAB_IDS":
            out[role] = ["home", "trips", "vehicles", "more", "reports", "profile"]
        else:
            out[role] = re.findall(r"'([a-z]+)'", body)
    return out


def parse_screen_access() -> list[tuple[str, list[str]]]:
    src = read(os.path.join(FRONTEND, "lib", "rbac.ts"))
    block = re.search(r"SCREEN_ACCESS[^=]*=\s*\[(.*?)\n\];", src, re.S)
    if not block:
        return []
    # "roles: ALL_ROLES" means every role; resolve it from the same file.
    all_roles = re.findall(
        r"'([a-z_]+)'",
        re.search(r"ALL_ROLES[^=]*=\s*\[(.*?)\]", src, re.S).group(1),
    )
    out = []
    for prefix, roles in re.findall(
        r"prefix:\s*'([^']+)'\s*,\s*roles:\s*(\[.*?\]|ALL_ROLES)", block.group(1), re.S
    ):
        if roles.strip() == "ALL_ROLES":
            out.append((prefix, list(all_roles)))
        else:
            out.append((prefix, re.findall(r"'([a-z_]+)'", roles)))
    return out


def parse_enums() -> dict[str, list[str]]:
    """Read the backend's enum classes so the reference table is exact."""
    models = os.path.join(BACKEND, "app", "models")
    out: dict[str, list[str]] = {}
    for name in sorted(os.listdir(models)):
        if not name.endswith(".py"):
            continue
        src = read(os.path.join(models, name))
        for cls, body in re.findall(
            r"class (\w+)\(str, Enum\):(.*?)(?=\nclass |\Z)", src, re.S
        ):
            values = re.findall(r"=\s*[\"']([^\"']+)[\"']", body)
            if values:
                out[cls] = values
    return out


# ── mockup helper ───────────────────────────────────────────────────────────
def shot(name: str, caption: str) -> str:
    path = os.path.join(SHOTS, f"{name}.png")
    if not os.path.isfile(path):
        return f"> *(screen capture unavailable: {name})*"
    return f"![{caption}](mockup/shots/{name}.png)\n\n*{caption}*"


ROLE_ORDER = [
    "super_admin", "owner", "general_manager", "branch_manager",
    "operations_manager", "fleet_manager", "chief_accountant",
    "branch_accountant", "driver", "conductor",
]

TAB_NAMES = {
    "home": "Home", "trips": "Trips", "vehicles": "Vehicles",
    "more": "More", "reports": "Reports", "profile": "Profile",
}

ROLE_INTRO = {
    "super_admin": {
        "persona": "Platform Administrator",
        "who": "The person who owns the TransitOS platform itself: accounts, "
               "branches, role permissions and the audit trail. Usually one or "
               "two people, and often outside the operating company.",
        "owns": [
            "Every user account in the system, across every branch",
            "Branch creation and branch configuration",
            "The role-permission matrix — what each role may do",
            "The audit log of every recorded action",
            "Fleet, route, trip and incident records company-wide",
        ],
        "cannot": [
            "Nothing is hidden from you, but every action you take is written to "
            "the audit log with your name, your role, the time and your IP "
            "address.",
        ],
    },
    "owner": {
        "persona": "Company Owner",
        "who": "The principal of the transport company. You are interested in "
               "the numbers: revenue, cost, utilisation and what each branch is "
               "contributing.",
        "owns": [
            "The company-wide dashboard and financial reports",
            "Settlement approvals and the settlement history",
            "Every branch's performance side by side",
        ],
        "cannot": [
            "You do not normally edit operational records day to day — you "
            "review them and direct the managers who do.",
        ],
    },
    "general_manager": {
        "persona": "General Manager",
        "who": "The person running operations across the whole company. You "
               "turn the owner's direction into trips, vehicles, routes and "
               "staff.",
        "owns": [
            "The company-wide operations dashboard",
            "Creating and scheduling trips across all branches",
            "Branches, routes, vehicles, drivers and conductors",
            "Incident acknowledgement and resolution",
            "The live trip board for every bus in the fleet",
        ],
        "cannot": [
            "You cannot change the role-permission matrix — that is reserved "
            "for the platform administrator.",
        ],
    },
    "branch_manager": {
        "persona": "Branch Manager",
        "who": "The person in charge of one branch. You run the day-to-day at "
               "your own depot and see only your branch's data.",
        "owns": [
            "Your branch's trips, vehicles, staff and cash-ups",
            "Your branch's users and their roles",
            "The branch record itself and its assigned manager",
            "Your branch's settlements",
        ],
        "cannot": [
            "You cannot see or edit records belonging to another branch — the "
            "restriction is enforced by the server, not just hidden in the app.",
        ],
    },
    "operations_manager": {
        "persona": "Operations Manager",
        "who": "The person coordinating the day's transport: where the buses "
               "are, which trips are running, and what went wrong.",
        "owns": [
            "The live fleet map and the live trip board",
            "Trip scheduling and status changes",
            "Reporting incidents and tracking them to resolution",
        ],
        "cannot": [
            "Financial screens are outside your role — settlements and expenses "
            "are not part of your view.",
        ],
    },
    "fleet_manager": {
        "persona": "Fleet Manager",
        "who": "The person responsible for the vehicles: their condition, their "
               "fuel, their maintenance and their paperwork.",
        "owns": [
            "Vehicle records and their documents",
            "Fuel logs and maintenance records",
            "Incident reports for fleet vehicles",
            "The fleet map",
        ],
        "cannot": [
            "You do not handle money — expenses, cash-ups and settlements "
            "belong to the finance roles.",
        ],
    },
    "chief_accountant": {
        "persona": "Chief Accountant",
        "who": "The person responsible for the company's money: what came in, "
               "what went out, and what is owed to the crew.",
        "owns": [
            "Expenses across the whole company",
            "Settlement generation, approval and payment",
            "Financial and operational reports",
            "Reconciliation of cash-ups against trip revenue",
        ],
        "cannot": [
            "You do not schedule trips or edit vehicles — that is the "
            "operations and fleet side.",
        ],
    },
    "branch_accountant": {
        "persona": "Branch Accountant",
        "who": "The person doing the books for one branch. You see your "
               "branch's costs and cash, not other branches'.",
        "owns": [
            "Your branch's expenses and cash-ups",
            "Your branch's settlements",
            "Branch-scoped reports",
        ],
        "cannot": [
            "You cannot see another branch's figures, and you cannot approve a "
            "settlement — approval sits with the chief accountant.",
        ],
    },
    "driver": {
        "persona": "Driver",
        "who": "The person behind the wheel. Your job in the app is to confirm "
               "the vehicle is roadworthy and to report problems the moment they "
               "happen.",
        "owns": [
            "The pre-trip checklist for your assigned vehicle",
            "Reporting incidents from the road",
            "Your own trips and their live status",
        ],
        "cannot": [
            "You see your own trips and your own vehicle — not the fleet, the "
            "finances or other people's records.",
        ],
    },
    "conductor": {
        "persona": "Conductor",
        "who": "The person who sells the tickets, counts the money and hands "
               "the cash in at the end of the trip.",
        "owns": [
            "Declaring the trip's cash-up and submitting it for approval",
            "Your own trips and their live status",
            "Reporting incidents on board",
        ],
        "cannot": [
            "You cannot approve your own cash-up — a manager reviews it.",
        ],
    },
}

# ── role walkthroughs ────────────────────────────────────────────────────────
# Every captured screenshot appears exactly once: shared screens in Part 1,
# role screens in Part 2. The coverage test enforces this.
ROLE_WALKTHROUGHS = {
    "super_admin": [
        ("super_admin-audit-log", "The audit log",
         "The audit log is your record of everything that has happened. Filter "
         "by actor to see one person's activity, or by action type to see every "
         "change, deletion or sign-in. Use it to answer a question like *who "
         "changed this vehicle's status?* without guessing."),
        ("super_admin-role-permissions", "Role permissions",
         "This screen defines what each role may do. Select a role to review its "
         "permissions, change them and save. The change applies from the next "
         "sign-in, so ask the affected person to sign out and back in. "
         "Resetting **every** role to its defaults is offered only to the Super "
         "Admin and the Owner."),
        ("super_admin-users", "User accounts",
         "Create a user with **Invite user**, then assign a role. You can only "
         "grant roles at or below your own seniority — a branch manager cannot "
         "create an owner. Assign a branch to make the account branch-scoped."),
        ("super_admin-user-detail", "A user record",
         "Open a user to see their details, their role, the branch they belong "
         "to and their status. Change the role here, or suspend the account "
         "without deleting its history."),
        ("super_admin-branches", "Branches",
         "A branch is a depot. Create the branch first, because vehicles, staff, "
         "trips and money all belong to one. On a branch record you can also "
         "assign or clear the branch manager."),
        ("super_admin-branch-detail", "A branch record",
         "Open a branch to see its address, contact details and GPS position, "
         "and to assign or clear the branch manager. Use **Clear manager** to "
         "hand a branch back to the pool without deleting it."),
        ("super_admin-vehicles", "Vehicles",
         "The vehicle list shows every vehicle across the company with its "
         "status, odometer and fuel level."),
        ("super_admin-vehicle-detail", "A vehicle record",
         "A vehicle record carries its registration, capacity, current odometer "
         "and fuel, and every document attached to it. Documents that are about "
         "to expire are called out so you can renew them before they lapse."),
        ("super_admin-drivers", "Drivers",
         "Driver records carry the licence number and expiry date. The app "
         "warns you before a licence lapses, which is why the expiry date "
         "matters."),
        ("super_admin-driver-detail", "A driver record",
         "Open a driver to see their full record, licence and years of "
         "experience."),
        ("super_admin-conductors", "Conductors",
         "Conductor records carry the badge number and employment status."),
        ("super_admin-conductor-detail", "A conductor record",
         "Open a conductor to see the badge number and status."),
        ("super_admin-routes", "Routes",
         "Routes describe a journey: origin and destination, distance, base "
         "fares and estimated duration."),
        ("super_admin-route-detail", "A route record",
         "Open a route to see the full journey definition, including the base "
         "passenger fare, the cargo rate per kilogram and any permits the route "
         "requires."),
        ("super_admin-trips", "Trips",
         "The trips list is the day's work. Filter by status, branch or "
         "vehicle; open a trip to see the vehicle, the crew and the money."),
        ("super_admin-trip-detail", "A trip",
         "A trip screen shows the schedule, the assigned vehicle and crew, "
         "passenger numbers and the revenue and expenses accrued against it."),
        (None, "Trip status",
         "The **Trip status** card at the top of the trip carries the stage the "
         "trip is at and the button that moves it on: **Start boarding**, "
         "**Confirm departure**, **Confirm arrival**, **Close trip**. "
         "**Cancel trip** calls the journey off and asks for a reason, which is "
         "kept on the trip and in the audit log. The server enforces the order "
         "— a trip cannot skip a stage, and a closed trip cannot be reopened. "
         "Branch managers, operations managers and above can move a trip; "
         "everyone else sees the card read-only."),
        ("super_admin-trip-manifest", "The manifest",
         "The **Manifest** section lists the passengers and cargo booked onto the "
         "trip, and the fare each one contributes. **+ Passenger** and "
         "**+ Cargo** add an entry, and the bin icon removes one. The list "
         "locks once the trip departs — a passenger cannot board a vehicle that "
         "has already left. This list is what the app uses to work out what the "
         "trip *should* have collected, so it is the basis of every variance "
         "figure in the app."),
        ("super_admin-trip-cash-up", "The cash-up on a trip",
         "The **Cash-up** card at the bottom of the trip is where the conductor "
         "declares the day's takings. The denominations are entered as counts of "
         "notes and coins, and the card shows the expected figure (from the "
         "manifest), the counted figure and the variance between them. "
         "**Save cash-up** records the declaration as a draft that only the "
         "conductor can see; **Submit for approval** sends it to finance, and "
         "the server fixes the expected figure and the variance at that moment. "
         "A submitted cash-up cannot be edited; if an approver rejects it, the "
         "conductor sees the reason, corrects the count and submits again."),
        ("super_admin-trip-draft-cash-up", "Declaring a cash-up",
         "A cash-up that has been saved but not yet sent to finance is a "
         "**draft**. It shows a *draft* badge, and only the person who "
         "saved it can see or change it. Enter the counts of notes and "
         "coins, then **Save cash-up** to keep it as a draft, or "
         "**Submit for approval** to send it to finance — the server "
         "fixes the expected figure and the variance at that moment."),
        ("super_admin-trip-closed", "A completed trip",
         "Once a trip has closed, it shows its final passenger count, revenue "
         "and expenses — the figures that feed the reports and the settlements."),
        ("super_admin-live-board", "The live trip board",
         "The live board updates itself over a live connection as trips move "
         "between planned, boarding, departed and arrived. A green badge means "
         "the live connection is up."),
        ("super_admin-incidents", "Incidents",
         "The counters along the top show how many incidents are severe, "
         "moderate, minor and closed. Open an incident to acknowledge it — which "
         "tells the reporter someone has seen it — or to resolve it with a note "
         "explaining what was done."),
        ("super_admin-incident-detail", "An incident",
         "The incident screen carries the full report, photos, who was "
         "notified, and the acknowledge and resolve actions."),
        ("super_admin-report-incident", "Reporting an incident",
         "The category list comes from the server, so it always matches what "
         "the system accepts: mechanical, accident, theft, passenger dispute, "
         "cargo damage, weather or other."),
        ("super_admin-fuel", "Fuel",
         "Every fuel purchase: litres, total cost, price per litre and the "
         "odometer at the time."),
        ("super_admin-maintenance", "Maintenance",
         "Scheduled, in-progress and completed maintenance, with parts, labour "
         "and the next due distance."),
        ("super_admin-expenses", "Expenses",
         "Expenses are either on-trip costs — fuel, tolls, permits, meals tied "
         "to a specific journey — or standalone branch overheads. Both reach "
         "the profit-and-loss report, but only the trip-linked ones are "
         "traceable to a journey."),
        ("super_admin-cash-ups", "Cash-ups",
         "The cash-up list is the reconciliation queue: what each conductor "
         "declared against what the trip expected, and who has approved it. "
         "Filter it by *Awaiting approval*, *Approved*, *Rejected* or *Draft*. "
         "A draft can be sent for approval from the list itself; a submitted "
         "one opens the review sheet, where **Approve** and **Reject** (with a "
         "reason) sit. Approving a cash-up marks its trip as *cashed up*."),
        ("super_admin-settlements", "Settlements",
         "A settlement is a branch's payroll for a period. Each one holds one "
         "line per completed trip, with the gross revenue, the trip expenses "
         "and what each crew member is owed."),
        ("super_admin-settlement-detail", "A settlement",
         "The settlement detail shows the headline figures and the per-trip "
         "lines behind them. Every figure on the summary can be traced to a "
         "line, and an approved or paid settlement is locked."),
        ("super_admin-reports", "Reports",
         "Financial and operational reporting over 7, 30 or 90 days, with PDF "
         "export."),
        ("super_admin-transfers", "Vehicle transfers",
         "Moving a vehicle between branches, through initiated, confirmed, "
         "returned or cancelled."),
        ("super_admin-map", "The live fleet map",
         "Every vehicle's live position, with counts by status along the top."),
    ],
    "owner": [
        ("owner-home", "Your dashboard",
         "The dashboard opens on the company's headline figures: revenue, "
         "active buses, cash variance and open incidents."),
        ("owner-reports", "Reading the reports",
         "The reports screen is your view of the business. Switch between 7, "
         "30 and 90 days to see the trend, then export the PDF for the board "
         "pack."),
        ("owner-settlements", "Settlements",
         "A settlement is what a branch owes its crew for a period. Read the "
         "summary to see the gross revenue, the costs deducted and the net "
         "payable, then open one to check the per-trip lines behind the "
         "headline figures."),
        ("owner-more", "The More menu",
         "Everything that does not need its own tab lives in the More menu, "
         "grouped by area."),
    ],
    "general_manager": [
        ("general_manager-home", "Your dashboard",
         "The dashboard greets you with your role and shows the company's "
         "operations at a glance. Pull down to refresh it at any time."),
        ("general_manager-trips", "Scheduling trips",
         "Tap **New trip**, choose the route, vehicle, driver and conductor, "
         "and set the departure and arrival times. The trip appears in the list "
         "as **planned** and becomes **boarding**, then **departed**, as the "
         "crew update it from the road."),
        ("general_manager-trip-detail", "A trip",
         "Open a trip to see the schedule, the vehicle, the named crew and the "
         "money that has accrued against it."),
        ("general_manager-trip-manifest", "The manifest",
         "The **Manifest** section lists the passengers and cargo booked onto the "
         "trip, and the fare each one contributes. **+ Passenger** and "
         "**+ Cargo** add an entry, and the bin icon removes one. The list "
         "locks once the trip departs — a passenger cannot board a vehicle that "
         "has already left. This list is what the app uses to work out what the "
         "trip *should* have collected, so it is the basis of every variance "
         "figure in the app."),
        ("general_manager-trip-cash-up", "The cash-up on a trip",
         "The **Cash-up** card at the bottom of the trip carries the day's "
         "declaration: the expected figure from the manifest, what the "
         "conductor counted, and the variance between them. Once a cash-up has "
         "been submitted the server owns those figures and the card is locked "
         "for reading; only a rejection sends it back to the conductor to "
         "correct."),
        ("general_manager-live-board", "The live trip board",
         "The live board is the shortest path to knowing where the fleet is. "
         "Each card is one trip, and cards move between states as the crew "
         "update the trip. A green **Live** badge means the connection is up; "
         "if it turns amber the app falls back to periodic refresh."),
        ("general_manager-vehicles", "The fleet",
         "Every vehicle with its status, odometer and fuel level. A vehicle "
         "that is not **available** cannot be scheduled onto a new trip."),
        ("general_manager-branches", "Branches",
         "Your branches, with their addresses and assigned managers."),
        ("general_manager-users", "People",
         "The people across the company and the roles they hold."),
        ("general_manager-incidents", "Incidents",
         "Severity counters across the top, a filter row beneath, and the list "
         "of incidents beneath that."),
        ("general_manager-incident-detail", "An incident",
         "Acknowledge it to confirm you have seen it, or resolve it with a "
         "note explaining what was done. Both actions are recorded."),
        ("general_manager-report-incident", "Reporting an incident",
         "Choose a category from the list the server provides, set the "
         "severity honestly, describe what happened and attach photos if you "
         "have them."),
        ("general_manager-map", "The fleet map",
         "The map shows every vehicle's live position, with counts by status "
         "along the top. Use it to answer *where is the bus?* before anyone "
         "calls you."),
        ("general_manager-reports", "Reports",
         "Financial and operational reporting over 7, 30 or 90 days, with PDF "
         "export."),
        ("general_manager-settlements", "Settlements",
         "See what each branch owes its crew for the period, and open a "
         "settlement to check the per-trip lines behind the headline figures."),
        ("general_manager-more", "The More menu",
         "Your operations, finance, fleet and system tools, in one place."),
        ("general_manager-profile", "Your profile",
         "Your details, your password, and the device you are signed in on."),
    ],
    "branch_manager": [
        ("branch_manager-home", "Your dashboard",
         "Your dashboard covers your branch only. The greeting and the figures "
         "beneath it are your branch's: the revenue, the trips, the fleet and "
         "the cash variance for your branch, then the drivers on duty, what is "
         "in maintenance, the paperwork expiring and the incidents and cash-ups "
         "waiting on your branch."),
        ("branch_manager-trips", "Your branch's trips",
         "Every trip that belongs to your branch, and nothing from another "
         "branch. The restriction is enforced by the server, not just hidden in "
         "the app."),
        ("branch_manager-trip-status", "Moving a trip along",
         "Open a trip and use the **Trip status** card at the top: "
         "**Start boarding**, **Confirm departure**, **Confirm arrival**, "
         "**Close trip**, and **Cancel trip** with a reason. You can also "
         "correct the manifest of a trip that has not departed yet, and declare "
         "or submit a cash-up once the trip is closed."),
        ("branch_manager-trip-cash-up", "Declaring a cash-up",
         "Once the trip is closed, the **Cash-up** card at the bottom of the "
         "screen is where the day's takings are declared. Enter the counts of "
         "notes and coins, check the variance against the expected figure, "
         "then **Save cash-up** and **Submit for approval**."),
        ("branch_manager-branches", "Your branch",
         "You see only your own branch. Open a branch record to update its "
         "details, or to assign or clear the branch manager."),
        ("branch_manager-branch-detail", "Your branch record",
         "Open the branch to see its address, contact details and assigned "
         "manager, and to assign or clear the branch manager."),
        ("branch_manager-users", "Your branch's people",
         "Create accounts for your branch's staff and assign the roles you are "
         "entitled to — branch accountant, driver and conductor."),
        ("branch_manager-settlements", "Your branch's settlements",
         "What your branch owes its crew for the period. Approval itself sits "
         "with the chief accountant."),
        ("branch_manager-more", "The More menu",
         "Your branch's tools, grouped by area."),
    ],
    "operations_manager": [
        ("operations_manager-home", "Your dashboard",
         "The day's operational picture: trips today, the active fleet, the "
         "drivers currently on duty and the open incidents. The money is "
         "finance's view, not yours — you get the operations picture."),
        ("operations_manager-trips", "Trips",
         "Schedule and manage the day's work across the company."),
        ("operations_manager-live-board", "The live trip board",
         "Live trip states, updating as the crews report them."),
        ("operations_manager-incidents", "Incidents",
         "Everything reported on the road, with severity counters to triage "
         "it."),
        ("operations_manager-map", "The fleet map",
         "Every vehicle's live position, with counts by status. This is the "
         "screen you will use most often."),
        ("operations_manager-more", "The More menu",
         "Your operational tools, grouped by area."),
    ],
    "fleet_manager": [
        ("fleet_manager-home", "Your dashboard",
         "The state of the fleet at a glance: how many vehicles are available "
         "or on the road, how many are in maintenance, and whose documents and "
         "licences expire in the next thirty days."),
        ("fleet_manager-vehicles", "The fleet",
         "The vehicle list is sorted by what needs attention: status, odometer "
         "and fuel level for every vehicle in your scope. A vehicle in "
         "**maintenance** or **grounded** is not available for scheduling."),
        ("fleet_manager-vehicle-detail", "A vehicle record",
         "The vehicle's registration, capacity, odometer, fuel and documents. "
         "Everything the vehicle needs is on this one screen."),
        ("fleet_manager-fuel", "Fuel logs",
         "Log every fill-up: litres, the total paid, the odometer and the "
         "station. The cost per litre is calculated for you, so a pricing "
         "dispute can be checked against the receipt."),
        ("fleet_manager-maintenance", "Maintenance",
         "Schedule maintenance with a due date or a due distance. The app "
         "raises a notification when servicing falls due, and keeps the next "
         "due distance on the record so the reminder comes automatically."),
        ("fleet_manager-incidents", "Incidents",
         "Mechanical and accident reports for your vehicles."),
        ("fleet_manager-map", "The fleet map",
         "Where every vehicle is, and how many are available, on trip, in "
         "maintenance or grounded."),
        ("fleet_manager-more", "The More menu",
         "Your fleet tools, grouped by area."),
    ],
    "chief_accountant": [
        ("chief_accountant-home", "Your dashboard",
         "The company's financial position at a glance: the revenue, the cash "
         "variance, the trips behind them, and how many cash-ups are waiting "
         "for you to approve."),
        ("chief_accountant-expenses", "Expenses",
         "Expenses are either **on-trip** costs — fuel, tolls, permits, meals "
         "charged to a specific journey — or **standalone** branch overheads. "
         "Both reach the profit-and-loss report, but only the trip-linked ones "
         "are traceable to a journey."),
        ("chief_accountant-settlements", "Settlements",
         "Generate a settlement for a branch and period, and TransitOS builds "
         "one line per completed trip with the gross revenue, the trip expenses "
         "and the net. Set the driver and conductor pay rates, then submit it "
         "for approval. A settlement that has been approved or paid is locked "
         "and cannot be edited."),
        ("chief_accountant-settlement-detail", "A settlement",
         "The headline figures and the per-trip lines behind them. Every figure "
         "on the summary can be traced to a line, so a question about a number "
         "always has an answer."),
        ("chief_accountant-reports", "Reports and export",
         "Reports show revenue, cost and operational performance over 7, 30 or "
         "90 days. Export the PDF for the month-end pack."),
        ("chief_accountant-more", "The More menu",
         "Your finance tools, grouped by area."),
    ],
    "branch_accountant": [
        ("branch_accountant-home", "Your dashboard",
         "Your branch's financial position. You see your branch's data only."),
        ("branch_accountant-expenses", "Your branch's expenses",
         "You see only your own branch's costs. Record each expense against "
         "the vehicle it belongs to and, where it is trip-linked, the journey "
         "it was incurred on."),
        ("branch_accountant-cash-ups", "Cash-ups",
         "Cash-ups show what each conductor declared against what the trip "
         "expected. Check the variance before you approve anything. Tap a "
         "cash-up marked *Awaiting approval* to open the review sheet: it shows "
         "the declared amount, the expected amount, the variance and the "
         "breakdown by payment method. **Approve** accepts it — the trip is "
         "then marked as *cashed up* — and **Reject** sends it back with a "
         "reason the conductor can act on."),
        ("branch_accountant-reports", "Branch-scoped reports",
         "The same reporting as the chief accountant, limited to your branch."),
        ("branch_accountant-more", "The More menu",
         "Your branch's finance tools, grouped by area."),
    ],
    "driver": [
        ("driver-home", "Your dashboard",
         "Your dashboard shows the work that is yours: how many trips are "
         "assigned to you, whether you are on duty right now, and the trips "
         "themselves. There are no company figures on it — they are not yours "
         "to see."),
        ("driver-trips", "Your trips",
         "The trips assigned to you, with their current status."),
        ("driver-trip-detail", "Your trip",
         "The schedule, the route, the vehicle and the passenger numbers "
         "recorded so far."),
        ("driver-trip-status", "The trip status",
         "The **Trip status** card at the top of the trip shows which stage the "
         "trip is at. A driver can read it but not move the trip — the button "
         "is for a branch manager, an operations manager or the head office."),
        ("driver-live-board", "The live trip board",
         "Your live board shows the trips assigned to you and their current "
         "state, updating as the day progresses."),
        ("driver-checklist", "The pre-trip checklist",
         "Run the checklist before every trip. Work down the template, marking "
         "each item pass or fail. A failed item is not a problem to hide — it "
         "is the whole point of the checklist. Add a note, report it as an "
         "incident if it affects safety, and tell your manager before the "
         "vehicle moves."),
        ("driver-report-incident", "Reporting a problem",
         "If something goes wrong on the road, report it while it is fresh. "
         "Choose the category that fits, set the severity honestly, describe "
         "what happened and attach a photo if it helps."),
        ("driver-more", "The More menu",
         "The tools available to you, grouped by area."),
        ("driver-profile", "Your profile",
         "Your details, your password, and the device you are signed in on."),
    ],
    "conductor": [
        ("conductor-home", "Your dashboard",
         "Your dashboard shows the trips you are working and their state: how "
         "many trips you have, whether you are on duty, and the passengers you "
         "have recorded so far. There are no company figures on it — they are "
         "not yours to see."),
        ("conductor-trips", "Your trips",
         "The trips assigned to you, with their current status."),
        ("conductor-trip-detail", "Your trip",
         "The trip screen shows the route, the schedule, the vehicle and the "
         "passenger numbers recorded so far."),
        ("conductor-trip-manifest", "Recording your manifest",
         "As passengers board, add each one to the **Manifest** on the trip "
         "screen: **+ Passenger** for a fare, **+ Cargo** for a parcel. This "
         "list is what the app uses to work out what the trip should have "
         "collected, so it is what you are measured against. The list locks "
         "when the trip departs. If you record someone who did not travel, "
         "remove the entry with the bin icon before the trip closes."),
        ("conductor-trip-cash-up", "Declaring your cash-up",
         "At the end of a trip, declare what you collected. Enter the counts of "
         "notes and coins in the **Cash-up** card, and the app shows the "
         "expected figure from your manifest, what you have counted, and the "
         "variance between them."),
        ("conductor-cash-ups", "The cash-ups list",
         "Your cash-ups, and the ones waiting for approval. A draft of yours "
         "can be sent for approval from here as well as from the trip screen. "
         "The breakdown by "
         "payment method is shown for each cash-up, together with what the trip "
         "expected and the variance. Your manager reviews it; a variance is "
         "raised with you, not against you.\n\n"
         "Press **Save cash-up** to record your count as a draft — only you "
         "can see it, and you can save it again to correct the count. Press "
         "**Submit for approval** when the count is final; the app then fixes "
         "the expected figure and the variance and sends it to finance. You "
         "cannot edit a submitted cash-up. If an approver sends it back, the "
         "reason appears on your trip screen — correct the count, save and "
         "submit again."),
        ("conductor-more", "The More menu",
         "The tools available to you, grouped by area."),
        ("conductor-profile", "Your profile",
         "Your details, your password, and the device you are signed in on."),
    ],
}

GLOSSARY = [
    ("Branch", "A depot. Vehicles, staff, trips and money belong to a branch."),
    ("Cash-up", "A conductor's declaration of the money collected on a trip, "
                "compared against what the trip expected."),
    ("Cash variance", "The difference between the cash declared and the cash "
                      "expected. Negative means a shortage."),
    ("Draft", "A cash-up that has been saved but not sent for approval yet. "
              "Only the conductor who saved it can see it, and only they can "
              "change it."),
    ("Category", "The type of an expense — fuel, toll, maintenance, permit, "
                 "meal, accommodation or other."),
    ("Expense", "A cost. On-trip if it belongs to a journey, standalone if it "
                "is branch overhead."),
    ("Expected total", "What the app calculates the trip should have "
                       "collected — the sum of the fares on its manifest. It "
                       "is the figure a cash-up is measured against."),
    ("Fuel log", "A record of one fill-up: litres, cost, price per litre and "
                 "odometer."),
    ("Incident", "A report of something that happened on the road — mechanical, "
                 "accident, theft, passenger dispute, cargo damage, weather or "
                 "other."),
    ("Live board", "The screen that updates trip states automatically over a "
                   "live connection."),
    ("Maintenance", "Work on a vehicle, scheduled or in progress, with parts "
                    "and labour cost and the next due distance."),
    ("Manifest", "The passenger or cargo list for a trip. It is what the "
                 "expected total is calculated from, and it locks when the "
                 "trip departs."),
    ("On-trip expense", "A cost incurred on a specific journey."),
    ("Pre-trip checklist", "The standard inspection a crew walks through "
                           "before a vehicle carries passengers."),
    ("Role", "What a person is permitted to see and do. Ten roles exist, from "
             "Super Admin down to Driver and Conductor."),
    ("Scope", "The records you can reach. Branch-scoped roles see only their "
              "own branch."),
    ("Settlement", "A branch's payroll for a period, built from one line per "
                   "completed trip."),
    ("Standalone expense", "A branch overhead not tied to a journey."),
    ("Trip", "One scheduled journey of one vehicle with a named driver and "
             "conductor."),
    ("Vehicle transfer", "Moving a vehicle from one branch to another."),
]

TROUBLESHOOTING = [
    ("\"Network Error\" when signing in",
     "The app cannot reach the server.",
     "Check your connection and try again. If you are on office Wi-Fi, try your "
     "phone's data."),
    ("\"Offline\" badge in the header",
     "The app has lost the connection to the server.",
     "Keep working — the app retries. Do not close it if you are mid-entry; "
     "your draft is kept."),
    ("A screen says *not found*",
     "The record was deleted, or it belongs to a branch outside your scope.",
     "Go back to the list and refresh. If you should have access, ask your "
     "administrator to check your branch assignment."),
    ("A list is empty",
     "Either there is nothing recorded yet, or everything is filtered out.",
     "Clear the filters first. If it is genuinely empty, the yellow button on "
     "that screen creates the first record."),
    ("You cannot see a screen in the More menu",
     "Your role does not include it.",
     "See Part 3.2 for who can open what, and ask your administrator if you "
     "believe the access is wrong."),
    ("A settlement will not edit",
     "Approved and paid settlements are locked.",
     "That is deliberate. Ask the chief accountant if a correction is needed."),
    ("\"Trip must be 'closed' before cash-up\"",
     "The trip has not been closed yet.",
     "Open the trip and use the **Trip status** card to move it on to "
     "**Close trip**. A cash-up can only be raised on a closed trip."),
    ("\"Cannot add manifest to a trip in status 'departed'\"",
     "The manifest locks once the trip has left.",
     "That is deliberate — a passenger cannot board a vehicle that has already "
     "gone. Fill the manifest before the trip departs."),
    ("The expected figure is zero",
     "The manifest is empty, so the app has nothing to compare the cash "
     "against.",
     "Add the passengers and cargo to the trip's manifest while it is still "
     "planned or boarding."),
    ("\"A cash-up already exists for this trip\"",
     "The trip already has a cash-up — a second one cannot be created.",
     "Open the trip and **Save cash-up** to correct the one that is there, "
     "rather than creating another."),
    ("A cash-up will not submit",
     "It has already been submitted, or it has been approved.",
     "Only a draft can be submitted. A submitted cash-up is waiting for an "
     "accountant; a rejected one is back with the conductor to correct."),
    ("A password change is refused",
     "The new password does not meet the policy.",
     "Use at least 8 characters with an upper-case letter, a lower-case "
     "letter, a digit and a special character."),
    ("Push notifications stopped arriving",
     "The device may have been unregistered, or it may no longer be registered "
     "at all.",
     "Open **My devices** under Profile and register the phone again."),
]


def build() -> str:
    labels = parse_role_labels()
    tabs = parse_tabs_by_role()
    access = parse_screen_access()
    enums = parse_enums()

    L: list[str] = []
    w = L.append

    # ── cover ────────────────────────────────────────────────────────────────
    w("# TransitOS User Manual")
    w("")
    w("**Transport Operations · Unified**")
    w("")
    w("Version 1.1 · General user manual and role-based manuals for every role "
      "in the TransitOS platform.")
    w("")
    w("Read Part 1 once, then the section in Part 2 that matches your role. "
      "Every screenshot in this manual is a real capture of the shipped "
      "application running against live data.")
    w("")
    w("---")
    w("")

    # ── Part 0 ───────────────────────────────────────────────────────────────
    w("## Part 0 — About this manual")
    w("")
    w("### 0.1 Who this manual is for")
    w("")
    w("This manual is written for the people who use TransitOS every day: "
      "dispatchers, branch managers, fleet managers, accountants, drivers and "
      "conductors, and the managers who supervise them.")
    w("")
    w("It has two halves:")
    w("")
    w("- **Part 1 — the general manual.** Signing in, the dashboard, "
      "navigation, your profile, notifications and the everyday things you do "
      "in the app. Read this once; it applies to everybody.")
    w("- **Part 2 — the role manuals.** One section per role, describing "
      "exactly what that role can reach and how to do the work that belongs to "
      "it. Read the section for your own role, and skim the one above you if "
      "you need to know what your manager sees.")
    w("")
    w("### 0.2 How the manual is organised")
    w("")
    w("Every screenshot in this manual is a **real capture of the shipped "
      "app**, taken against a live database containing realistic data. Nothing "
      "is drawn by hand. When a screen in the app differs from the picture "
      "here, the app is right and the manual is out of date.")
    w("")
    w("| Part | Contents | Who reads it |")
    w("|---|---|---|")
    w("| Part 1 | General manual | Everyone |")
    w("| Part 2 | Role manuals | The role that owns the section |")
    w("| Part 3 | Reference tables and troubleshooting | When you need a lookup |")
    w("")
    w("### 0.3 Reading the screenshots")
    w("")
    w("Screenshots show the app on a phone. Where a screen has a coloured badge "
      "or chip, its colour carries meaning — Part 3.1 lists every colour used.")
    w("")
    w("### 0.4 Getting help")
    w("")
    w("If something in the app does not behave as this manual describes, "
      "contact your branch manager or the platform administrator. For access "
      "problems (a locked account, a forgotten password), see Part 1.1.")
    w("")
    w("---")
    w("")

    # ── Part 1 ───────────────────────────────────────────────────────────────
    w("## Part 1 — General user manual")
    w("")
    w("### 1.1 Signing in")
    w("")
    w("The TransitOS app opens on the sign-in screen.")
    w("")
    w(shot("login", "The TransitOS sign-in screen"))
    w("")
    w("Enter the **email address** your administrator gave you and your "
      "**password**, then tap **Sign In**.")
    w("")
    w("> **First time?** Your administrator creates your account and tells you "
      "the address and a temporary password. Change it from **Profile** after "
      "your first sign-in — see Part 1.4.")
    w("")
    w("#### If you have forgotten your password")
    w("")
    w(shot("forgot-password", "Reset your password"))
    w("")
    w("Tap **Forgot password?**, enter your email address and the app sends a "
      "reset link. The link opens your browser, where you set a new password.")
    w("")
    w("#### If you have forgotten your username")
    w("")
    w(shot("forgot-username", "Recover your username"))
    w("")
    w("Tap **Forgot username?**, enter your email address and the app emails "
      "you the address you sign in with.")
    w("")
    w("#### Signing out")
    w("")
    w("Open **Profile** and tap **Sign Out**. You will need to sign in again to "
      "reach your data. Always sign out on a shared device — for example a "
      "depot terminal used by more than one person.")
    w("")
    w("#### Your session")
    w("")
    w("TransitOS keeps you signed in between sessions so you do not have to "
      "sign in on every trip. If your session expires while you are using the "
      "app, it signs you back in automatically with a refreshed token. If it "
      "cannot, you are returned to the sign-in screen and nothing you were "
      "editing is lost.")
    w("")
    w("---")
    w("")

    w("### 1.2 Your dashboard")
    w("")
    w("The dashboard is the first screen after sign-in. The navy header "
      "greets you by name and shows your role; below it are the figures that "
      "matter for your job.")
    w("")
    w(shot("super_admin-home", "The dashboard"))
    w("")
    w("| Tile | What it tells you |")
    w("|---|---|")
    w("| Revenue | Money taken across the trips in scope. |")
    w("| Active buses | How many vehicles are on a trip against the total "
      "fleet. |")
    w("| Cash variance | Whether the money declared on cash-ups matches what "
      "the trips expected. |")
    w("| Open incidents | Problems still awaiting a response. |")
    w("")
    w("The greeting changes with the time of day. Pull the screen down to "
      "refresh the figures — useful after you or someone else has just "
      "recorded something. Each role sees the tiles that apply to it, so your "
      "dashboard may differ from the one pictured here.")
    w("")
    w("---")
    w("")

    w("### 1.3 Getting around")
    w("")
    w("#### The tab bar")
    w("")
    w("The bar along the bottom is your main navigation. Which tabs appear "
      "depends on your role.")
    w("")
    w("| Tab | What is on it |")
    w("|---|---|")
    w("| **Home** | The dashboard. |")
    w("| **Trips** | The trip list and live board. |")
    w("| **Vehicles** | The fleet. |")
    w("| **Reports** | Financial and operational reporting. |")
    w("| **More** | Everything else, grouped by area. |")
    w("| **Profile** | Your details and security settings. |")
    w("")
    w("#### The More menu")
    w("")
    w(shot("super_admin-more", "The More menu"))
    w("")
    w("The More menu is grouped into **Operations**, **Finance**, **Fleet** and "
      "**System**. Tiles your role cannot use are not shown — if you cannot "
      "see a tile, you do not have that responsibility. Your branch scope is "
      "stated under your name: *Branch scoped* means you see only your own "
      "branch, *All branches* means you see the whole company.")
    w("")
    w("#### Which tabs your role gets")
    w("")
    w("| Role | Tabs |")
    w("|---|---|")
    for role in ROLE_ORDER:
        if role in tabs:
            names = ", ".join(TAB_NAMES.get(t, t) for t in tabs[role])
            w(f"| {labels.get(role, role)} | {names} |")
    w("")
    w("---")
    w("")

    w("### 1.4 Your profile and security")
    w("")
    w(shot("super_admin-profile", "Your profile"))
    w("")
    w("From **Profile** you can review your own details, change your password "
      "and review the devices signed in to your account.")
    w("")
    w("#### Changing your password")
    w("")
    w("Tap **Change password** and enter your current password and your new "
      "one. The new password must meet the company's rules: at least 8 "
      "characters, with an upper-case letter, a lower-case letter, a digit and "
      "a special character. The app tells you which rule you have not met "
      "rather than just refusing the change.")
    w("")
    w("#### Your devices")
    w("")
    w(shot("super_admin-devices", "Registered devices"))
    w("")
    w("Every phone that registers for push notifications appears here with its "
      "platform and the app version. If you sell your phone or replace it, tap "
      "**Unregister** on the old one — otherwise it keeps receiving alerts "
      "that nobody reads.")
    w("")
    w("---")
    w("")

    w("### 1.5 Notifications")
    w("")
    w(shot("super_admin-notifications", "The notification inbox"))
    w("")
    w("The inbox collects what the system raises automatically: a licence about "
      "to expire, servicing that has fallen due, a vehicle low on fuel, a "
      "severe incident, a cash-up awaiting approval. Unread items are "
      "highlighted; opening one marks it read.")
    w("")
    w("You are only notified about things that affect you. A crew member sees "
      "their own trips; a fleet manager sees servicing and fuel; finance sees "
      "cash-ups and settlements.")
    w("")
    w("---")
    w("")

    w("### 1.6 The interface at a glance")
    w("")
    w("TransitOS uses one consistent visual language, so once you know it you "
      "can read any screen.")
    w("")
    w("| Element | What it means |")
    w("|---|---|")
    w("| **Card** | A white panel holding one record or one group of facts. |")
    w("| **Badge / Chip** | A small coloured label carrying a status. The "
      "colour is meaningful — see Part 3.1. |")
    w("| **Button (yellow)** | The primary action on a screen. There is "
      "usually only one. |")
    w("| **Button (outline / ghost)** | A secondary action. |")
    w("| **Button (danger)** | A destructive action, such as deleting. |")
    w("| **Field** | A labelled box you type into. A line under the label "
      "tells you what to enter; an error appears beneath the box. |")
    w("| **Select** | A dropdown. Tap it, then tap the option you want. |")
    w("| **Modal** | A panel that opens over the screen for a short task. Tap "
      "outside it to dismiss it without saving. |")
    w("| **Empty state** | The message shown when there is nothing to list "
      "yet, with the button that creates the first one. |")
    w("| **Spinner** | Work in progress. |")
    w("| **Online / Offline badge** | Whether the app can currently reach the "
      "server. |")
    w("")
    w("---")
    w("")

    w("### 1.7 Everyday tasks")
    w("")
    w("#### Finding something")
    w("")
    w("Long lists have a filter row across the top. Tap a filter to narrow the "
      "list — status, branch, vehicle or date. Most lists page: scroll to the "
      "bottom to load the next page.")
    w("")
    w("#### Adding a record")
    w("")
    w("Tap the yellow button on the screen — **Add vehicle**, **Record "
      "expense**, **New trip**, and so on. Fill in the form and save. Required "
      "fields are marked; the app will not let you save an incomplete record, "
      "and it tells you which field is the problem rather than failing "
      "silently.")
    w("")
    w("#### Editing a record")
    w("")
    w("Open the record from its list and tap its edit control. The control "
      "is named for what it changes: **Edit details** on a vehicle, "
      "**Edit** on an expense, a fuel log or a maintenance record, and "
      "**Edit pay rates** on a settlement.")
    w("")
    w("Two records are changed where they live rather than on their own "
      "screen. A **cash-up** is corrected on the trip it belongs to — "
      "**Save cash-up** — and an **incident** is closed with **Acknowledge** "
      "or **Resolve incident**.")
    w("")
    w("A **trip** cannot be edited. Its route, vehicle, crew and schedule "
      "are set when it is created; to change one, cancel the trip and "
      "create another.")
    w("")
    w("#### Deleting a record")
    w("")
    w("Open the record, tap **Delete**, and confirm. **Delete** is not "
      "everywhere: it appears on vehicles, users, expenses, fuel logs and "
      "maintenance records. A trip, a cash-up, an incident and a "
      "settlement are not deleted from the app — a trip is cancelled, and "
      "a settlement is settled or disputed.")
    w("")
    w("Deleting is a soft delete: the record leaves the list but its data "
      "is kept server-side for audit and reporting. Nothing in the app "
      "brings it back, so if you delete something by mistake, tell an "
      "administrator rather than re-creating it.")
    w("")
    w("#### Exporting a report")
    w("")
    w("Open **Reports**, choose a period — 7, 30 or 90 days — and tap the "
      "export button. TransitOS produces a PDF you can save, email or print.")
    w("")
    w("---")
    w("")

    # ── Part 2 ───────────────────────────────────────────────────────────────
    w("## Part 2 — Role manuals")
    w("")
    w("Each section below describes one role: who it is for, what it can reach, "
      "how the daily work is done, and where its authority stops.")
    w("")
    w("Use **Part 3.2** for the full screen-by-role access table.")
    w("")

    for idx, role in enumerate(ROLE_ORDER, start=1):
        meta = ROLE_INTRO.get(role, {})
        label = labels.get(role, role)
        w(f"### 2.{idx} {meta.get('persona', label)}")
        w("")
        w(f"*Role code: `{role}`*")
        w("")
        w(f"**Who this role is for.** {meta.get('who', '')}")
        w("")
        w("**What you are responsible for**")
        w("")
        for item in meta.get("owns", []):
            w(f"- {item}")
        w("")
        w("**What you can reach**")
        w("")
        role_tabs = tabs.get(role, [])
        if role_tabs:
            w(f"Tab bar: {', '.join(TAB_NAMES.get(t, t) for t in role_tabs)}.")
        screens = [p for p, roles in access if role in roles]
        if screens:
            w("")
            w("Screens: " + ", ".join(f"`{p}`" for p in screens) + ".")
        w("")

        for shot_name, heading, body in ROLE_WALKTHROUGHS.get(role, []):
            # A ``None`` screenshot means "prose only" — a section that
            # describes something the screen does, but has no capture of
            # its own. The money-loop screens are written that way.
            if shot_name is not None and not os.path.isfile(
                os.path.join(SHOTS, f"{shot_name}.png")
            ):
                continue
            w(f"#### {heading}")
            w("")
            w(body)
            w("")
            if shot_name is not None:
                w(shot(shot_name, heading))
                w("")

        for item in meta.get("cannot", []):
            w(f"> **Boundary.** {item}")
            w("")
        w("---")
        w("")

    # ── Part 3 ───────────────────────────────────────────────────────────────
    w("## Part 3 — Reference")
    w("")
    w("### 3.1 Status colours")
    w("")
    w("TransitOS uses the same colours everywhere, so a colour always means the "
      "same thing.")
    w("")
    w("| Colour | Meaning | Where you see it |")
    w("|---|---|---|")
    w("| Green | Good, active, complete, available | Vehicle available, trip "
      "departed, cash-up approved |")
    w("| Blue | In progress, planned, informational | Trip planned or boarding, "
      "informational notices |")
    w("| Amber | Needs attention but not yet urgent | Service due, low fuel, "
      "trip delayed |")
    w("| Red | Serious, blocked or refused | Severe incident, overdue, "
      "rejected |")
    w("| Grey | Inactive, closed or no longer current | Closed trip, retired "
      "vehicle, rejected cash-up |")
    w("| Navy | TransitOS brand colour, primary actions | Header, primary "
      "buttons |")
    w("| Yellow | Accent, the primary action on a screen | Sign In button, "
      "status underline |")
    w("")
    if "TripStatus" in enums:
        w("**Trip statuses.** " + ", ".join(f"`{v}`" for v in enums["TripStatus"]) + ".")
        w("")
    if "VehicleStatus" in enums:
        w("**Vehicle statuses.** " + ", ".join(f"`{v}`" for v in enums["VehicleStatus"]) + ".")
        w("")
    if "CashUpStatus" in enums:
        w("**Cash-up statuses.** " + ", ".join(f"`{v}`" for v in enums["CashUpStatus"]) + ".")
        w("")
    if "SettlementStatus" in enums:
        w("**Settlement statuses.** " + ", ".join(f"`{v}`" for v in enums["SettlementStatus"]) + ".")
        w("")
    w("---")
    w("")

    w("### 3.2 Roles and access at a glance")
    w("")
    w("This is the authoritative view of who can open what. It is generated "
      "directly from the application configuration, so it always matches the "
      "running app.")
    w("")
    w("| Screen | Roles that can open it |")
    w("|---|---|")
    for prefix, roles in access:
        names = ", ".join(labels.get(r, r) for r in roles)
        w(f"| `{prefix}` | {names} |")
    w("")
    w("---")
    w("")

    w("### 3.3 Glossary")
    w("")
    w("| Term | Meaning |")
    w("|---|---|")
    for term, meaning in GLOSSARY:
        w(f"| **{term}** | {meaning} |")
    w("")
    w("---")
    w("")

    w("### 3.4 Troubleshooting")
    w("")
    w("| What you see | What it means | What to do |")
    w("|---|---|---|")
    for symptom, meaning, action in TROUBLESHOOTING:
        w(f"| {symptom} | {meaning} | {action} |")
    w("")
    w("---")
    w("")

    w("### 3.5 Version")
    w("")
    w("| | |")
    w("|---|---|")
    w("| Application | TransitOS 1.1.0 |")
    w("| Manual | User Manual 1.1 |")
    w("| Roles | 10 |")
    w("")
    return "\n".join(L) + "\n"


def main() -> int:
    text = build()
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"wrote {OUT}")
    print(f"  lines: {text.count(chr(10))}   screenshots embedded: {text.count('![')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
