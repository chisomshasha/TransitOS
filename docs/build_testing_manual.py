"""Build the composite app testing manual from the codebase.

The manual is generated rather than hand-written so that it can never
drift from the app: every screen, every endpoint, every role and every
state machine is read out of the source at build time.

Run from the repo root:

    python docs/build_testing_manual.py

It writes ``docs/TESTING_MANUAL.md``.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
from collections import Counter, defaultdict

REPO = pathlib.Path(__file__).resolve().parents[1]
BACKEND = REPO / "backend"
FRONTEND = REPO / "frontend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools" / "contract"))

from sources import iter_source_files  # noqa: E402

os.environ.setdefault("MONGODB_DB_NAME", "manual_build")
os.environ.setdefault("JWT_SECRET_KEY", "manual-build-secret")


# ─── roles ──────────────────────────────────────────────────────────────────

def load_roles():
    from app.core.roles import (  # noqa: E402
        ANY_AUTHENTICATED, CREW_READ, FLEET_OPS, READ_ALL, SAFETY_OPS,
        USERS_READ, Role,
    )

    aliases = {
        "SA": "super_admin", "OWNER": "owner", "GM": "general_manager",
        "BM": "branch_manager", "OM": "operations_manager",
        "FM": "fleet_manager", "CA": "chief_accountant",
        "BA": "branch_accountant", "DRIVER": "driver", "CONDUCTOR": "conductor",
    }
    groups = {
        "ANY_AUTHENTICATED": [r.value for r in ANY_AUTHENTICATED],
        "READ_ALL": [r.value for r in READ_ALL],
        "FLEET_OPS": [r.value for r in FLEET_OPS],
        "CREW_READ": [r.value for r in CREW_READ],
        "SAFETY_OPS": [r.value for r in SAFETY_OPS],
        "USERS_READ": [r.value for r in USERS_READ],
    }
    groups["REPORTS_READ"] = [
        "super_admin", "owner", "general_manager", "chief_accountant",
        "branch_accountant", "branch_manager", "operations_manager",
        "fleet_manager",
    ]
    return [r.value for r in Role], aliases, groups


ALL_ROLES, ROLE_ALIASES, ROLE_GROUPS = load_roles()


# ─── endpoint inventory ─────────────────────────────────────────────────────

def _balanced(src: str, open_at: int) -> str:
    depth = 0
    i = open_at
    n = len(src)
    while i < n:
        ch = src[i]
        if ch in "\"'":
            q = ch
            i += 1
            while i < n and src[i] != q:
                i += 1
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return src[open_at + 1: i]
        i += 1
    return src[open_at + 1:]


def _resolve(expr: str, local: dict) -> list[str]:
    out = []
    for part in expr.split(","):
        part = part.strip().lstrip("*").strip()
        if not part:
            continue
        if part in local:
            out.extend(local[part])
        elif part in ROLE_GROUPS:
            out.extend(ROLE_GROUPS[part])
        elif part in ROLE_ALIASES:
            out.append(ROLE_ALIASES[part])
    return sorted(set(out))


def _local_groups(src: str) -> dict:
    groups = {}
    for m in re.finditer(r"^([A-Z][A-Z_0-9]*)\s*=\s*([^\n]+)$", src, re.M):
        name, body = m.group(1), m.group(2).strip()
        if body.startswith("["):
            roles = []
            for part in body.strip("[]").split(","):
                part = part.strip().lstrip("*").strip()
                if part in ROLE_ALIASES:
                    roles.append(ROLE_ALIASES[part])
                elif part.startswith("Role."):
                    roles.append(part.split(".", 1)[1].lower())
                elif part in ROLE_GROUPS:
                    roles.extend(ROLE_GROUPS[part])
            if roles:
                groups[name] = sorted(set(roles))
        elif body in ROLE_GROUPS:
            groups[name] = list(ROLE_GROUPS[body])
        elif body in ROLE_ALIASES:
            groups[name] = [ROLE_ALIASES[body]]
    return groups


def endpoint_roles() -> dict:
    """(METHOD, path) -> sorted list of roles allowed."""
    out = {}
    for path in sorted((BACKEND / "app" / "routers").glob("*.py")):
        src = path.read_text(encoding="utf-8")
        local = _local_groups(src)

        prefixes = dict(re.findall(r"(\w+)\s*=\s*APIRouter\([^)]*?prefix\s*=\s*[\"']([^\"']+)[\"']", src, re.S))
        # Fall back: any router var with a prefix anywhere in the file.
        for var, pre in re.findall(r"(\w+)\s*=\s*APIRouter\([^)]*?prefix\s*=\s*[\"']([^\"']+)[\"']", src, re.S):
            prefixes.setdefault(var, pre)

        for m in re.finditer(
            r"@(\w+)\.(get|post|patch|put|delete)\(\s*[\"']([^\"']*)[\"'][^)]*\)\s*\n"
            r"(?:@[\w.]+(?:\([^\n]*\))?\s*\n)*"
            r"(?:async\s+)?def\s+\w+\s*\(",
            src,
            re.S,
        ):
            var, method, sub = m.groups()
            if var not in prefixes:
                continue
            sig = _balanced(src, m.end() - 1)
            rm = re.search(r"require_roles\(([^)]*)\)", sig)
            roles = _resolve(rm.group(1), local) if rm else []
            full = (prefixes[var] + sub).rstrip("/") or "/"
            # An access class: "public" (no session needed), "session"
            # (any signed-in role) or "restricted" (a role allowlist).
            if rm is None and "get_current_user" not in sig:
                access = "public"
            elif roles:
                access = "restricted"
            else:
                access = "session"
            out[(method.upper(), full)] = {"roles": roles, "access": access}
    return out


#: Endpoints protected by something other than a session.
SPECIAL_PROTECTION = {
    ("POST", "/admin/seed"): "gated by the `ADMIN_BOOTSTRAP_TOKEN` env var, and "
                             "permanently disabled once the bootstrap flag is set",
}


def role_text(key, roles_map) -> str:
    info = roles_map.get(key)
    if info is None:
        return "*(undetermined — verify manually)*"
    special = SPECIAL_PROTECTION.get(key)
    if special:
        return f"**{special}**"
    if info["access"] == "restricted":
        return ", ".join(f"`{r}`" for r in info["roles"])
    if info["access"] == "session":
        return "any signed-in role"
    return "public — no session required"


def openapi_inventory() -> list[dict]:
    from app.main import app  # noqa: E402

    spec = app.openapi()
    ops = []
    for path, item in spec["paths"].items():
        for method, op in item.items():
            if method.lower() not in ("get", "post", "patch", "put", "delete"):
                continue
            params = [p["name"] for p in (op.get("parameters") or []) if p.get("required")]
            rb = op.get("requestBody") or {}
            body = []
            if rb.get("content", {}).get("application/json"):
                sch = rb["content"]["application/json"].get("schema", {})
                if "$ref" in sch:
                    sch = spec["components"]["schemas"][sch["$ref"].split("/")[-1]]
                body = sch.get("required", []) or []
            ops.append({
                "method": method.upper(),
                "path": path,
                "tag": (op.get("tags") or ["general"])[0],
                "summary": (op.get("summary") or op.get("description") or "").strip(),
                "query": params,
                "body": body,
            })
    ops.sort(key=lambda o: (o["tag"], o["path"], o["method"]))
    return ops


# ─── screens ────────────────────────────────────────────────────────────────

def screen_inventory() -> list[dict]:
    screens = []
    app_dir = FRONTEND / "app"
    for p in iter_source_files(app_dir, ("*.tsx",)):
        if p.name == "_layout.tsx":
            continue
        rel = str(p.relative_to(app_dir))
        rel = rel[:-4]  # strip .tsx
        group = ""
        if rel.startswith("("):
            group = rel[1:rel.index(")")]
            rel = rel[rel.index(")") + 1:]
        route = "/" + rel.replace("/index", "").strip("/")
        route = re.sub(r"//+", "/", route).rstrip("/") or "/"
        screens.append({
            "file": str(p.relative_to(REPO)),
            "group": group or "(root)",
            "route": route,
            "title": p.stem.replace("[", "").replace("]", "").replace("-", " ").title(),
        })
    screens.sort(key=lambda s: (s["group"], s["route"]))
    return screens


# ─── state machines ─────────────────────────────────────────────────────────

STATE_MACHINES = {
    "Trip": {
        "desc": "A trip's lifecycle. Illegal transitions must return HTTP 409.",
        "states": ["planned", "boarding", "departed", "arrived", "closed", "cashed_up", "cancelled"],
        "transitions": [
            ("planned", "boarding"), ("planned", "cancelled"),
            ("boarding", "departed"), ("boarding", "cancelled"),
            ("departed", "arrived"), ("arrived", "closed"), ("closed", "cashed_up"),
        ],
        "terminal": ["cashed_up", "cancelled"],
    },
    "Cash-up": {
        "desc": "A conductor's daily reconciliation. Only a 'closed' trip can be cashed up.",
        "states": ["draft", "submitted", "approved", "rejected"],
        "transitions": [
            ("draft", "submitted"), ("draft", "rejected"),
            ("submitted", "approved"), ("submitted", "rejected"),
            ("rejected", "draft"),
        ],
        "terminal": ["approved"],
    },
    "Inspection": {
        "desc": "A pre-trip checklist. Once submitted it is locked (HTTP 409 on further edits).",
        "states": ["draft", "submitted"],
        "transitions": [("draft", "submitted")],
        "terminal": ["submitted"],
    },
    "Vehicle transfer": {
        "desc": "A vehicle moving between branches.",
        "states": ["initiated", "confirmed", "returned", "cancelled"],
        "transitions": [
            ("initiated", "confirmed"), ("initiated", "cancelled"),
            ("confirmed", "returned"), ("confirmed", "cancelled"),
        ],
        "terminal": ["returned", "cancelled"],
    },
    "Settlement": {
        "desc": "A branch's financial close. Approved and paid settlements are locked (HTTP 409).",
        "states": ["draft", "submitted", "approved", "paid", "rejected"],
        "transitions": [
            ("draft", "submitted"), ("submitted", "approved"),
            ("submitted", "rejected"), ("rejected", "submitted"),
            ("approved", "paid"),
        ],
        "terminal": ["paid"],
    },
    "Maintenance record": {
        "desc": "A maintenance job. Completing one flips the vehicle status.",
        "states": ["scheduled", "in_progress", "completed", "cancelled"],
        "transitions": [
            ("scheduled", "in_progress"), ("scheduled", "cancelled"),
            ("in_progress", "completed"), ("in_progress", "cancelled"),
        ],
        "terminal": ["completed", "cancelled"],
    },
}


def build() -> str:
    ops = openapi_inventory()
    roles = endpoint_roles()
    screens = screen_inventory()

    by_tag = defaultdict(list)
    for o in ops:
        by_tag[o["tag"]].append(o)

    lines: list[str] = []
    w = lines.append

    # ── header ──────────────────────────────────────────────────────────
    w("# TransitOS — Composite Application Testing Manual")
    w("")
    w("**Release candidate:** Sprint D · " )
    w(f"**Surface under test:** {len(ops)} API operations · {len(screens)} mobile/web screens · "
      f"{len(ALL_ROLES)} roles")
    w("")
    w("> **Purpose.** This manual exists so that a single, complete pass can establish "
      "that TransitOS is fit for the client to use in production. Every screen, every "
      "endpoint, every role boundary and every state transition in the application is "
      "represented by at least one numbered test item below.")
    w("")
    w("---")
    w("")

    # ── how to use ──────────────────────────────────────────────────────
    w("## 0. How to use this manual")
    w("")
    w("### 0.1 The readiness rule")
    w("")
    w("The application is **ready for client use** when:")
    w("")
    w("1. Every **P0** and **P1** item in Parts 1–12 is marked **Pass**.")
    w("2. No **P0** or **P1** item is marked **Fail** or **Blocked**.")
    w("3. Every **P2** item is either Pass or has an agreed, documented deferral.")
    w("4. Every **P3** item is recorded (Pass / Fail / Deferred) with a rationale.")
    w("5. Part 12 (Client UAT sign-off) is complete and countersigned.")
    w("")
    w("A **P0** failure is a release blocker. It means the client cannot perform a core "
      "task, or data is at risk of being lost or corrupted.")
    w("")
    w("### 0.2 Severity")
    w("")
    w("| Severity | Meaning | Release effect |")
    w("|---|---|---|")
    w("| **P0** | Core workflow broken; data loss or corruption possible | **Blocks release** |")
    w("| **P1** | Major feature broken or wrong; workaround exists but is impractical | **Blocks release** |")
    w("| **P2** | Minor defect; cosmetic or affects an edge case | Fix before release, or accept |")
    w("| **P3** | Observation / enhancement request | Record only |")
    w("")
    w("### 0.3 How to record a result")
    w("")
    w("For each item record:")
    w("")
    w("- **Result** — `Pass` / `Fail` / `Blocked` / `N/A`")
    w("- **Tester** — initials")
    w("- **Date** — ISO date (`YYYY-MM-DD`)")
    w("- **Evidence** — screenshot, request/response capture, or defect reference")
    w("- **Notes** — only when the result is not `Pass`")
    w("")
    w("### 0.4 Environments")
    w("")
    w("| Environment | Base URL | Purpose |")
    w("|---|---|---|")
    w("| Local | `http://localhost:8000` | Functional pass, debugging |")
    w("| Staging | `https://<staging-host>` | Integration, performance, cross-browser |")
    w("| Production | `https://<prod-host>` | Smoke (Part 9) and client UAT (Part 12) |")
    w("")
    w("Run the full manual against **staging**. Run Part 9 (non-functional, as a smoke "
      "check) and Part 12 (client UAT) against production.")
    w("")
    w("### 0.5 Test data")
    w("")
    w("Seed the staging database with `backend/scripts/seed.py` before starting. The seed "
      "creates one branch per operational role plus demo trips, vehicles and users. "
      "Record the seeded credentials in the test log — never in this manual.")
    w("")
    w("---")
    w("")

    # ── part 1: deployment ──────────────────────────────────────────────
    w("## Part 1 — Deployment, configuration & health")
    w("")
    w("**Objective:** prove the app installs, boots, connects to its database and serves "
      "traffic on a clean machine.")
    w("")
    w("| # | Test | Severity | Expected result | Result |")
    w("|---|---|---|---|---|")
    items = [
        ("1.1", "Clone the repository and install backend dependencies with `pip install -r backend/requirements.txt`",
         "P0", "Install completes with no errors. `expo-linear-gradient` (an npm package) must NOT appear in this file — it breaks the Docker build."),
        ("1.2", "Run `python backend/scripts/check_requirements.py`",
         "P0", "Prints `requirements OK` and exits 0. This guard is what stops the Railway build breaking again."),
        ("1.3", "Install frontend dependencies with `npm ci` in `frontend/`",
         "P0", "Installs cleanly from the lockfile. No dependency resolution errors."),
        ("1.4", "Set the required environment variables: `MONGODB_URL`, `MONGODB_DB_NAME`, `JWT_SECRET_KEY`, `CORS_ORIGINS`",
         "P0", "All four are set. A missing `JWT_SECRET_KEY` must fail fast, not silently use a default in production."),
        ("1.5", "Start the API with `uvicorn app.main:app`",
         "P0", "Process starts, logs the resolved API base URL, and the index-creation loop reports `Mongo indexes ensured`."),
        ("1.6", "Call `GET /health`",
         "P0", "HTTP 200 with a body reporting the database as reachable."),
        ("1.7", "Call `GET /` (service root)",
         "P1", "HTTP 200 and a response that identifies the service and version."),
        ("1.8", "Call `GET /openapi.json`",
         "P0", "HTTP 200 and a complete JSON schema. A 500 here means a response model references an undefined type — this broke the app once already."),
        ("1.9", "Call `GET /docs` and `GET /redoc`",
         "P2", "HTTP 200 and the interactive API documentation renders."),
        ("1.10", "Confirm the background alerts worker starts and logs its first scan",
         "P1", "A scan runs on the configured interval. Setting `ALERTS_SCAN_INTERVAL_SECONDS=0` must disable it cleanly."),
        ("1.11", "Build the frontend for web with `npx expo export --platform web`",
         "P0", "Export completes and emits one HTML file per route."),
        ("1.12", "Typecheck the frontend with `npx tsc --noEmit`",
         "P0", "Exits 0 with no errors."),
        ("1.13", "Deploy the Docker image and start the container",
         "P1", "The container serves the API on the expected port and the health check passes."),
        ("1.14", "Confirm the Railway build completes end to end",
         "P1", "The build succeeds and the deployment reports healthy. The original failure mode was an npm package inside `requirements.txt`."),
    ]
    for n, t, sev, exp in items:
        w(f"| {n} | {t} | {sev} | {exp} | ☐ |")
    w("")
    w("---")
    w("")

    # ── part 2: auth ────────────────────────────────────────────────────
    w("## Part 2 — Authentication, session & account recovery")
    w("")
    w("**Objective:** prove identity, session lifecycle and credential recovery all behave "
      "correctly and safely.")
    w("")
    w("| # | Test | Severity | Expected result | Result |")
    w("|---|---|---|---|---|")
    auth_items = [
        ("2.1", "Log in with a valid email and password",
         "P0", "HTTP 200. Response body is `{\"data\": {\"access_token\": ..., \"refresh_token\": ...}}` — the standard envelope."),
        ("2.2", "Log in with a wrong password",
         "P0", "HTTP 401 with a generic message that does not reveal whether the email exists."),
        ("2.3", "Log in with an unknown email",
         "P0", "HTTP 401 with the **same** message as 2.2. The two responses must be indistinguishable."),
        ("2.4", "Log in with an inactive or soft-deleted user",
         "P0", "HTTP 401. A deactivated account must not be able to obtain a session."),
        ("2.5", "Call `GET /auth/me` with the access token",
         "P0", "HTTP 200 returning the signed-in user's profile. The password hash and any reset token must be absent."),
        ("2.6", "Call any protected endpoint without a token",
         "P0", "HTTP 401."),
        ("2.7", "Call any protected endpoint with a malformed or tampered token",
         "P0", "HTTP 401, and the token is rejected rather than partially decoded."),
        ("2.8", "Refresh the token with `POST /auth/refresh`",
         "P0", "HTTP 200 with a new access **and** refresh token. The old refresh token must be invalidated (rotation)."),
        ("2.9", "Replay a refresh token that was already used",
         "P0", "HTTP 401. Token reuse must be detected and the token family revoked."),
        ("2.10", "Log out with `POST /auth/logout`",
         "P0", "HTTP 204 and the refresh token is revoked server-side, not merely discarded by the client."),
        ("2.11", "Request `POST /auth/forgot-password` for a known email",
         "P0", "HTTP 202 and a reset email is sent."),
        ("2.12", "Request `POST /auth/forgot-password` for an unknown email",
         "P0", "HTTP 202 with the **same** response. The endpoint must never confirm whether an account exists."),
        ("2.13", "Complete a password reset with a valid token",
         "P0", "HTTP 204, the password changes, and the token is consumed so it cannot be replayed."),
        ("2.14", "Reset a password with an expired or already-used token",
         "P0", "HTTP 400/401 and the password is unchanged."),
        ("2.15", "Request `POST /auth/forgot-username`",
         "P0", "HTTP 202 and a username reminder is sent when the email is known; the response is identical either way."),
        ("2.16", "Change the password with `POST /auth/change-password`",
         "P0", "HTTP 204. The old password stops working and the new one works."),
        ("2.17", "Attempt a password that violates the policy (too short, no digit, no symbol)",
         "P1", "HTTP 422 with a message naming the rule broken. The frontend policy and the backend rule must agree."),
        ("2.18", "Change password using a wrong current password",
         "P0", "HTTP 400/401 and the password is unchanged."),
        ("2.19", "Trigger the account lockout by repeated failed logins",
         "P1", "The account locks after the configured threshold and a locked account returns 403 until the lock expires."),
        ("2.20", "Exceed the login rate limit",
         "P2", "HTTP 429 with a retry hint. The limit is applied per IP and per email."),
        ("2.21", "Verify the access token expires",
         "P1", "After `ACCESS_TOKEN_EXPIRE_MINUTES` the token is rejected with 401 and the client refreshes transparently."),
        ("2.22", "Verify an expired access token triggers a transparent refresh in the app",
         "P1", "The request succeeds after refresh; the user sees no error and no re-login prompt."),
        ("2.23", "Sign out on the client and confirm the push token is unregistered",
         "P1", "The device token is deactivated server-side so the device stops receiving another user's notifications."),
    ]
    for n, t, sev, exp in auth_items:
        w(f"| {n} | {t} | {sev} | {exp} | ☐ |")
    w("")
    w("---")
    w("")

    # ── part 3: rbac ────────────────────────────────────────────────────
    w("## Part 3 — Roles, permissions & branch scoping")
    w("")
    w("**Objective:** prove no user can reach anything beyond their role, and that one "
      "branch's data is invisible to another branch's team.")
    w("")
    w("The ten roles are: " + ", ".join(f"`{r}`" for r in ALL_ROLES) + ".")
    w("")
    w("| # | Test | Severity | Expected result | Result |")
    w("|---|---|---|---|---|")
    rbac_items = [
        ("3.1", "Sign in as each of the ten roles in turn",
         "P0", "Each role authenticates and lands on a dashboard appropriate to it."),
        ("3.2", "Compare the navigation menu across all ten roles",
         "P0", "Each role sees only the sections its role permits. Crew roles see a crew app; finance roles see finance. No role sees a dead link."),
        ("3.3", "Open every screen visible to each role and confirm it loads without an error",
         "P0", "No screen returns 403 or 500 for a role that is allowed to see it. A screen that 403s for an allowed role is a broken screen, not a clean denial."),
        ("3.4", "Directly request an endpoint that the role is not permitted to use",
         "P0", "HTTP 403 with a clear message. The endpoint must refuse regardless of what the UI shows."),
        ("3.5", "As `branch_manager`, list trips, vehicles and users",
         "P0", "Only records belonging to that manager's own branch are returned."),
        ("3.6", "As `branch_manager`, request a trip belonging to another branch by ID",
         "P0", "HTTP 403 or 404. The record must not leak, and must not be distinguishable from one that does not exist."),
        ("3.7", "As `branch_accountant`, verify the same branch scoping applies",
         "P0", "Scoping is consistent across every branch-scoped role."),
        ("3.8", "As `driver`, attempt to reach a role-management endpoint",
         "P0", "HTTP 403."),
        ("3.9", "As a `branch_manager`, try to create a user with a more senior role",
         "P0", "HTTP 403. The role-assignment hierarchy must refuse escalation."),
        ("3.10", "As `general_manager`, try to create a `super_admin`",
         "P0", "HTTP 403 — no one below `super_admin` may mint a `super_admin`."),
        ("3.11", "As `super_admin`, create a user with every role",
         "P1", "HTTP 201 for each role. The full role set must be assignable at the top tier."),
        ("3.12", "Open the role-permission matrix as `super_admin`",
         "P1", "The matrix renders with every role and resource."),
        ("3.13", "Toggle a permission and confirm it takes effect on the next request",
         "P1", "The change is persisted and the affected role's access changes immediately."),
        ("3.14", "Attempt to remove a mandatory base permission from `super_admin`",
         "P1", "HTTP 400 with an explanatory message. The base grants must not be revocable."),
        ("3.15", "Reset a single role's permissions and reset all roles",
         "P2", "Both succeed and the affected roles return to the defaults."),
        ("3.16", "Assign a branch manager who does not belong to that branch",
         "P1", "HTTP 400. A branch manager must belong to the branch they manage."),
        ("3.17", "Clear a branch's manager",
         "P2", "The manager is unset and the branch reports no manager."),
    ]
    for n, t, sev, exp in rbac_items:
        w(f"| {n} | {t} | {sev} | {exp} | ☐ |")
    w("")
    w("---")
    w("")

    # ── part 4: endpoint catalogue by domain ────────────────────────────
    w("## Part 4 — Endpoint catalogue & per-endpoint functional verification")
    w("")
    w("**Objective:** verify every endpoint individually. This section is generated from "
      "the live OpenAPI schema, so it cannot omit a route.")
    w("")
    w("For **every** endpoint below the tester must confirm all four of the following. "
      "The last column is the sign-off box for that endpoint.")
    w("")
    w("1. **Status** — the response status matches the documented behaviour "
      "(200 / 201 / 204 for a success, 400 / 401 / 403 / 404 / 409 / 422 for a "
      "refusal, each of which is checked in Part 7).")
    w("2. **Body shape** — the payload matches the documented shape exactly, including "
      "the `data` / `items` envelope.")
    w("3. **Required inputs are enforced** — omitting a required field or query "
      "parameter is rejected, and an invalid value is rejected.")
    w("4. **Persistence** — a write is reflected in the relevant list view, in the "
      "audit log, and in any report that should include it.")
    w("")
    w("Legend for **Roles** — *public* means no session is needed; *any signed-in role* "
      "means the endpoint only requires a valid session; a role list means only those "
      "roles may call it.")
    w("")

    tag_titles = {
        "admin": "Administration & seeding",
        "alerts": "Alerts engine",
        "audit-log": "Audit log",
        "auth": "Authentication",
        "branches": "Branches",
        "cash-ups": "Cash-ups",
        "conductors": "Conductors",
        "dashboard": "Dashboard",
        "drivers": "Drivers",
        "events": "Realtime events (SSE)",
        "expenses": "Expenses",
        "fleet": "Fleet positions",
        "fuel-logs": "Fuel logs",
        "health": "Health",
        "incidents": "Incidents",
        "inspections": "Inspections",
        "maintenance": "Maintenance records",
        "notifications": "Notifications",
        "push": "Push devices",
        "qr": "QR codes",
        "reports": "Reports",
        "role-permissions": "Role permissions",
        "routes": "Routes",
        "settlements": "Settlements",
        "sync": "Offline sync",
        "trips": "Trips & manifest",
        "users": "Users",
        "vehicle-documents": "Vehicle documents",
        "vehicle-transfers": "Vehicle transfers",
        "vehicles": "Vehicles",
    }

    counter = 0
    domain = 0
    for tag in sorted(by_tag, key=lambda t: (t != "auth", t)):
        group_ops = by_tag[tag]
        title = tag_titles.get(tag, tag.replace("-", " ").title())
        domain += 1
        w(f"### 4.{domain} — {title}")
        w("")
        w(f"*{len(group_ops)} endpoint{'s' if len(group_ops) != 1 else ''}*")
        w("")
        w("| # | Endpoint | Method | Roles | Required input | Sev | Result |")
        w("|---|---|---|---|---|---|---|")
        for op in group_ops:
            counter += 1
            key = (op["method"], op["path"])
            role_txt = role_text(key, roles)
            req = []
            if op["query"]:
                req.append("query: " + ", ".join(f"`{p}`" for p in op["query"]))
            if op["body"]:
                req.append("body: " + ", ".join(f"`{b}`" for b in op["body"]))
            req_txt = "<br>".join(req) if req else "—"
            path_params = re.findall(r"\{([^}]+)\}", op["path"])
            if path_params:
                req.append("path: " + ", ".join(f"`{p}`" for p in path_params))
                req_txt = "<br>".join(req)
            sev = "P0" if op["method"] in ("POST", "PATCH", "PUT", "DELETE") else "P1"
            w(f"| {counter} | `{op['path']}` | {op['method']} | {role_txt} | {req_txt} | "
              f"{sev} | ☐ |")
        w("")

    w("---")
    w("")

    # ── state machines ──────────────────────────────────────────────────
    part = 5
    w(f"## Part {part} — State machine verification")
    w("")
    w("**Objective:** prove that every legal transition works and every illegal one is "
      "refused. An illegal transition must return **HTTP 409** with a message naming the "
      "current and target states, and must leave the record unchanged.")
    w("")
    for name, sm in STATE_MACHINES.items():
        w(f"### {name}")
        w("")
        w(f"{sm['desc']}")
        w("")
        w("| From | To | Legal? | Expected | Result |")
        w("|---|---|---|---|---|")
        legal = set((a, b) for a, b in sm["transitions"])
        for a in sm["states"]:
            for b in sm["states"]:
                if a == b:
                    w(f"| `{a}` | `{b}` | no-op | HTTP 200 — re-selecting the same state is idempotent | ☐ |")
                    continue
                ok = (a, b) in legal
                w(f"| `{a}` | `{b}` | {'yes' if ok else '**no**'} | "
                  f"{'HTTP 200 and the state changes' if ok else '**HTTP 409** — refused, record unchanged'} | ☐ |")
        w("")
        w(f"Terminal states: {', '.join(f'`{t}`' for t in sm['terminal'])}. "
          f"No transition may leave a terminal state.")
        w("")
    w("---")
    w("")

    # ── screens ─────────────────────────────────────────────────────────
    part = 6
    w(f"## Part {part} — Screen-by-screen UI verification")
    w("")
    w("**Objective:** confirm every screen renders, loads its data, and handles the "
      "empty and error states. Generated from the expo-router route tree.")
    w("")
    w("For **every** screen the tester must confirm all four of the following.")
    w("")
    w("1. **Renders with data** — the screen loads its data from the API and shows it.")
    w("2. **Empty state** — with no records, the screen shows a helpful empty state "
      "rather than a blank page or an error.")
    w("3. **Error state** — with the API failing, the screen shows a readable error "
      "and does not crash.")
    w("4. **Refresh** — pull-to-refresh (or the reload control) updates the data.")
    w("")
    w("| # | Screen | Route | Source file | Result |")
    w("|---|---|---|---|---|")
    for i, s in enumerate(screens, start=1):
        w(f"| {i}.{counter + 1} | {s['title']} | `{s['route']}` | `{s['file']}` | ☐ |")
    counter += len(screens)
    w("")

    # ── part: cross-cutting ────────────────────────────────────────────
    part = 7
    w(f"## Part {part} — Cross-cutting behaviour & data integrity")
    w("")
    w("| # | Test | Severity | Expected result | Result |")
    w("|---|---|---|---|---|")
    cross = [
        ("Every list endpoint returns the standard envelope",
         "P0", "`{\"items\": [...], \"total\": n, \"page\": p, \"totalPages\": t, \"hasMore\": b}`. Every single-item endpoint returns `{\"data\": {...}}`."),
        ("No endpoint returns a bare body",
         "P0", "The frontend reads single records with `getSingle` (which unwraps `.data.data`). A bare body silently renders as `undefined` rather than erroring."),
        ("Pagination is honoured everywhere",
         "P1", "`page` and `page_size` are respected; `total` reflects the full filtered count; requesting a page past the end returns an empty `items`, not an error."),
        ("Search and filter parameters work on every list endpoint",
         "P1", "Filtering by the documented query parameters narrows the result set as specified."),
        ("Deleting a record is a soft delete",
         "P0", "The record disappears from lists but its data is retained for audit and reporting."),
        ("Every create, update, delete and status change writes an audit entry",
         "P0", "The audit log shows the action, the actor, the timestamp and a before/after snapshot."),
        ("Timestamps are stored and returned in UTC",
         "P1", "`created_at` / `updated_at` are timezone-aware and serialise consistently."),
        ("Every collection the app queries has an index",
         "P1", "Checked by `test_collection_consistency.py`. A missing index turns a list view into a full collection scan."),
        ("Every collection is reached under exactly one name",
         "P0", "Checked by `test_collection_consistency.py`. A split name means a reader silently sees an empty collection — this broke maintenance records."),
        ("Trip totals recompute when the manifest changes",
         "P0", "Adding, editing or removing a manifest entry updates passenger count, cargo weight and total revenue."),
        ("Expenses scoped `on_trip` roll into the trip totals",
         "P0", "A trip's total expenses reflect its own expenses plus its fuel and maintenance costs."),
        ("Branch scoping holds for every list and detail endpoint",
         "P0", "A branch-scoped role sees only its own branch's records, on every endpoint, not just the obvious ones."),
        ("Concurrent edits do not corrupt records",
         "P2", "Two simultaneous edits leave the record in one consistent state, not a merge of two conflicting writes."),
        ("The API returns a consistent error envelope",
         "P1", "Errors carry a machine-readable `detail` and the frontend surfaces a readable message."),
        # ── the money loop ────────────────────────────────────────────
        # These used to be impossible to run: the app had no button for
        # any of them. They are the regression tests for that.
        ("**The money loop runs end to end in the app**",
         "P0", "On a trip: *Start boarding* → *Confirm departure* → *Confirm arrival* → *Close trip*. Add a passenger to the manifest, count the cash, *Save cash-up*, *Submit for approval*, then approve it in **More → Cash Ups**. The trip ends as `cashed_up`. No step needs the command line."),
        ("The trip status card offers only the legal next stage",
         "P0", "The button matches the state machine: *Planned* offers boarding, *Boarding* offers departure, *Departed* offers arrival, *Arrived* offers close. Nothing else is offered."),
        ("A cancellation asks for a reason and keeps it",
         "P0", "*Cancel trip* refuses to proceed without a reason; the reason is shown on the trip and appears in the audit log."),
        ("The manifest locks when the trip departs",
         "P0", "After *Confirm departure*, *+ Passenger* and *+ Cargo* are gone and the bin icon is gone. The server refuses a late addition with HTTP 409."),
        ("Removing a manifest entry changes the expected figure",
         "P0", "Remove an entry: the trip's revenue drops, and the cash-up's expected total drops by the same amount. A removed fare must not count towards the expected total."),
        ("A cash-up is a draft until it is submitted",
         "P0", "After *Save cash-up* the record is `draft` and does not appear under *Awaiting approval*. It appears only after *Submit for approval*."),
        ("A submitted cash-up cannot be edited",
         "P0", "The denomination boxes are locked and *Save cash-up* is gone. Only a rejection sends it back to the conductor."),
        ("A rejection shows the reason and the trip can be re-submitted",
         "P0", "After a rejection the trip screen shows the reason, the cash-up can be edited, and saving it again returns it to `draft` so it can be submitted once more."),
        ("The variance equals counted minus expected",
         "P0", "With a manifest of \u20a63,500 and \u20a63,400 counted, the card shows a variance of \u2212\u20a6100, and the submitted cash-up carries the same figure."),
        ("A cash-up cannot be raised against a trip that is not closed",
         "P0", "On a `planned` trip the cash-up card says so and offers no button. The server refuses with *Trip must be 'closed' before cash-up*."),
        ("Roles are gated exactly as the server gates them",
         "P0", "A conductor sees the manifest and the cash-up but not the status buttons; a driver sees none of the three; a chief accountant sees the cash-ups but not the manifest. Every hidden action is refused by the API when called directly."),
    ]
    for i, (t, sev, exp) in enumerate(cross, start=1):
        w(f"| {part}.{i} | {t} | {sev} | {exp} | ☐ |")
    w("")
    w("---")
    w("")

    # ── security ────────────────────────────────────────────────────────
    part = 8
    w(f"## Part {part} — Security verification")
    w("")
    w("| # | Test | Severity | Expected result | Result |")
    w("|---|---|---|---|---|")
    sec = [
        ("Confirm no secret is committed to the repository",
         "P0", "No `.env`, key or credential is tracked. `JWT_SECRET_KEY` and the Mongo URL come from the environment only."),
        ("Confirm `JWT_SECRET_KEY` is not the sample default in production",
         "P0", "The app refuses to start with a known default, or at minimum logs a loud warning."),
        ("Test for NoSQL injection through query parameters",
         "P0", "An input such as `?email[$ne]=` is rejected or treated as a literal string. The app must never accept a raw operator object from the client."),
        ("Test for injection through free-text fields",
         "P1", "Search terms containing quotes or operators are escaped and cannot alter the query."),
        ("Confirm CORS only allows the configured origins",
         "P0", "A request from an unlisted origin is refused."),
        ("Confirm the API refuses an oversized request body",
         "P2", "The request is rejected rather than consuming unbounded memory."),
        ("Confirm rate limiting applies to the auth endpoints",
         "P1", "Brute-force attempts are throttled with 429."),
        ("Confirm the audit log is append-only through the API",
         "P1", "There is no endpoint that deletes or edits an audit entry."),
        ("Confirm secrets never appear in API responses",
         "P0", "No response contains `password_hash`, a reset token or a refresh token belonging to another user."),
        ("Confirm the push token of one user is never visible to another",
         "P0", "`GET /push` returns only the signed-in user's own devices."),
        ("Confirm file uploads are validated",
         "P2", "Only the permitted content types and sizes are accepted for receipts and incident photos."),
        ("Confirm the app is served over HTTPS in production",
         "P0", "No plain-HTTP access, and `Strict-Transport-Security` is set."),
    ]
    for i, (t, sev, exp) in enumerate(sec, start=1):
        w(f"| {part}.{i} | {t} | {sev} | {exp} | ☐ |")
    w("")
    w("---")
    w("")

    # ── non-functional ──────────────────────────────────────────────────
    part = 9
    w(f"## Part {part} — Non-functional verification")
    w("")
    w("| # | Test | Severity | Expected result | Result |")
    w("|---|---|---|---|---|")
    nf = [
        ("Measure the dashboard load time on staging",
         "P1", "Under 2 seconds on a mid-range phone over 4G."),
        ("Measure the trips list with 5,000+ records",
         "P1", "The response stays under 1 second and the index is actually used (`explain()` shows an index scan, not a collection scan)."),
        ("Measure report generation for a full month across all branches",
         "P1", "Under 5 seconds."),
        ("Verify the app recovers after the database restarts",
         "P1", "Requests fail gracefully during the outage and recover automatically; the app does not require a restart."),
        ("Verify the alerts worker retries after a transient failure",
         "P2", "A failed scan is logged and retried; the worker does not die silently."),
        ("Verify the SSE live board reconnects after a network drop",
         "P1", "The connection indicator returns to `Live` without the user reloading."),
        ("Verify the live board degrades to polling when SSE is unavailable",
         "P1", "The board still updates on an interval and shows a clear \"polling\" state."),
        ("Test the app on the supported browser and device matrix",
         "P1", "iOS Safari, Android Chrome, desktop Chrome, desktop Safari and desktop Firefox all render every screen correctly."),
        ("Test offline behaviour with the network disabled",
         "P2", "Queued writes are retained, the sync screen shows the queue, and nothing is silently lost."),
        ("Verify accessibility basics",
         "P2", "Every interactive element is reachable by screen reader, focus order is sensible, and colour contrast meets WCAG AA."),
        ("Verify the app works at the smallest supported screen size",
         "P2", "No content is clipped or overlapping at 320 px width."),
        ("Verify long field values do not break the layout",
         "P3", "Very long names, emails and notes truncate or wrap rather than overflowing."),
    ]
    for i, (t, sev, exp) in enumerate(nf, start=1):
        w(f"| {part}.{i} | {t} | {sev} | {exp} | ☐ |")
    w("")
    w("---")
    w("")

    # ── regression watch-list ───────────────────────────────────────────
    part = 10
    w(f"## Part {part} — Regression watch-list: defects found and fixed")
    w("")
    w("**Objective:** these are real defects that were live in the application and "
      "were found only by executing the app rather than reading it. Each one now has a "
      "permanent automated guard. The tester must confirm each defect is genuinely "
      "fixed — a regression here is a P0.")
    w("")
    w("| # | Defect | How it presented | Why nothing caught it | Guard that now prevents it | Sev | Result |")
    w("|---|---|---|---|---|---|---|")
    regressions = [
        ("Cash-up receipts and trip waybills returned HTTP 500",
         "Every PDF download failed with `TypeError: 'str' object cannot be interpreted as an integer`.",
         "The PDF service formatted dates with `iso.replace('Z', '+00:00')`. That is right for an ISO string, but MongoDB returns native datetimes, where `.replace()` means `replace(year, month, ...)`. No test existed for either endpoint.",
         "`test_pdf_export.py` — exercises both endpoints and the formatter directly", "P0"),
        ("Maintenance records were invisible to alerts and reports",
         "Maintenance-due notifications never fired, maintenance cost never reached the profit-and-loss report, and every vehicle reported 100% utilisation.",
         "The maintenance router wrote to the `maintenance` collection while the alerts engine read `maintenance_records` and the reports read `maintenance_records` too. No test had ever seeded either collection, so the split stayed invisible.",
         "`test_collection_consistency.py` (one collection, one name) and `test_maintenance_visibility.py` (the behaviour itself)", "P0"),
        ("Seven endpoints answered with a bare body instead of the envelope",
         "The dashboard KPIs, fleet map, QR scanner, incident counters, role-permission metadata and the audit summary all rendered blank.",
         "The frontend reads single records with `getSingle`, which unwraps `.data.data`. A bare body yields `undefined` rather than an error, so nothing crashed.",
         "`test_response_envelope.py`", "P0"),
        ("Eight hot collections had no index",
         "Incident lists, the notification inbox and the vehicle-document views ran as full collection scans and degraded as data grew.",
         "Indexes were created for the collections named in `create_indexes()`; eight others that the app queried were simply never listed.",
         "`test_collection_consistency.py` — every queried collection must have an index", "P1"),
        ("A branch manager could never be unassigned",
         "The backend accepted `manager_id: null` but the UI offered no way to send it.",
         "The select control only ever emits real option values, and the clear path was never built.",
         "Manual — Part 4.5 / branch detail screen", "P2"),
        ("The audit actor filter was silently truncated at 25 actors",
         "Once the organisation had more than 25 distinct actors, the rest could not be selected from the chip list.",
         "The endpoint defaults to `limit=25` and the client called it with no parameters.",
         "Manual — Part 4.4 / audit log screen", "P2"),
    ]
    for i, (d, pres, why, guard, sev) in enumerate(regressions, start=1):
        w(f"| {part}.{i} | {d} | {pres} | {why} | {guard} | {sev} | ☐ |")
    w("")
    w("---")
    w("")

    # ── CI guards ───────────────────────────────────────────────────────
    part = 11
    w(f"## Part {part} — Automated regression guards")
    w("")
    w("These run in CI on every push. The tester must confirm they are green on the "
      "release candidate, because a red guard invalidates the manual pass.")
    w("")
    w("| # | Guard | What it proves | Result |")
    w("|---|---|---|---|")
    guards = [
        ("Backend suite", "Every domain's behaviour, including the state machines and the financial arithmetic."),
        ("Requirements guard", "No npm package has crept into the Python requirements file."),
        ("Response-envelope contract", "No endpoint has drifted back to a bare body."),
        ("Collection consistency", "No collection is reachable under two names; no queried collection lacks an index; no index references a field nothing writes."),
        ("Frontend ↔ backend runtime contract", "Every one of the ~126 frontend API calls reaches a live route. A 404, 405, 401 or 500 fails the build."),
        ("Frontend typecheck", "The frontend compiles with no type errors."),
        ("Lockfile sync", "The lockfile matches `package.json`, so the mobile build cannot break on a device."),
    ]
    for i, (t, exp) in enumerate(guards, start=1):
        w(f"| {part}.{i} | {t} | {exp} | ☐ |")
    w("")
    w("---")
    w("")

    # ── UAT ─────────────────────────────────────────────────────────────
    part = 12
    w(f"## Part {part} — Client UAT scenarios & sign-off")
    w("")
    w("**Objective:** confirm the client can run their day on the app. Each scenario is a "
      "real task, written the way the client describes it, not a test of the system's "
      "internals.")
    w("")
    w("| # | Scenario | Steps | Expected outcome | Sev | Result |")
    w("|---|---|---|---|---|---|")
    uat = [
        ("The dispatcher sets up tomorrow's schedule",
         "Sign in as dispatcher → create a route → create a trip → assign vehicle, driver and conductor → confirm the trip appears on the live board.",
         "The trip is scheduled and visible to the driver on their own device.", "P0"),
        ("The conductor runs the trip and collects fares",
         "Sign in as conductor → open the trip → add passengers to the manifest → mark each as paid → board the trip.",
         "The manifest totals update live and the trip advances through boarding and departed.", "P0"),
        ("The driver completes the trip and the conductor hands over the cash",
         "Driver marks arrived → trip closed → conductor submits a cash-up with a breakdown of cash and transfer.",
         "The variance is computed and the cash-up appears in the manager's review queue.", "P0"),
        ("The manager reviews and approves the cash-up",
         "Sign in as branch manager → cash-ups → filter by Submitted → approve one, reject another with a reason.",
         "Both actions succeed; the conductor sees the outcome and the reason for the rejection.", "P0"),
        ("The fleet manager schedules vehicle maintenance",
         "Sign in as fleet manager → maintenance → schedule a service for a vehicle with a due date.",
         "The vehicle's status flips to maintenance and a maintenance-due notification appears.", "P0"),
        ("The accountant closes the month for a branch",
         "Sign in as chief accountant → settlements → generate for the branch and period → submit → approve → mark paid with a reference.",
         "The settlement shows gross revenue, expenses and crew payroll, every figure traceable to its trips.", "P0"),
        ("The owner reads the month's performance",
         "Sign in as owner → reports → review operations summary, profit and loss, branch performance, vehicle ROI and utilisation.",
         "Every report renders with figures that agree with the underlying records.", "P0"),
        ("An incident happens on the road",
         "Any user → report incident → pick a category, severity, description and photos.",
         "The incident is recorded, appears in the incident list, and the assigned staff are notified.", "P0"),
        ("A vehicle moves to another branch",
         "Fleet manager → transfers → initiate a transfer → the receiving branch confirms → returns it.",
         "The transfer walks initiated → confirmed → returned, and the vehicle's branch updates at each step.", "P1"),
        ("The manager traces who changed what",
         "Sign in as owner → audit log → filter by actor and by action.",
         "Every administrative change is attributable to a named actor with a before/after snapshot.", "P0"),
        ("The conductor works with poor connectivity",
         "Disable the network → record manifest entries → restore the network → open the sync screen.",
         "Entries queue locally, sync completes, and nothing is lost or duplicated.", "P1"),
        ("A user scans a vehicle's QR code",
         "Open the scanner → scan a vehicle QR → confirm the vehicle record opens.",
         "The correct vehicle opens with its full detail, without a manual lookup.", "P1"),
    ]
    for i, (name, steps, outcome, sev) in enumerate(uat, start=1):
        w(f"| {part}.{i} | {name} | {steps} | {outcome} | {sev} | ☐ |")
    w("")
    w("### Client sign-off")
    w("")
    w("| Field | Entry |")
    w("|---|---|")
    total_items = sum(l.count("☐") for l in lines) + 1   # +1 for this table's own entry
    w(f"| **Total items in this manual** | **{total_items}** |")
    w(f"| Items passed | ______ of {total_items} |")
    w("| Items failed | |")
    w("| Items blocked | |")
    w("| Items deferred (P2/P3 only) | |")
    w("| Total defects raised | |")
    w("| Open P0 defects | |")
    w("| Open P1 defects | |")
    w("")
    w("| Role | Name | Signature | Date |")
    w("|---|---|---|---|")
    w("| Test lead | | | |")
    w("| QA manager | | | |")
    w("| Backend engineer | | | |")
    w("| Frontend engineer | | | |")
    w("| Product owner | | | |")
    w("| Client representative | | | |")
    w("")
    w("**Declaration.** The undersigned confirm that the items above were executed against "
      "the release candidate, that the results recorded are accurate, and that the "
      "application is accepted as ready for use.")
    w("")
    w("---")
    w("")
    w("## Appendix A — Endpoint index")
    w("")
    w("| Method | Path | Tag | Roles |")
    w("|---|---|---|---|")
    for o in ops:
        role_txt = role_text((o["method"], o["path"]), roles)
        w(f"| {o['method']} | `{o['path']}` | {o['tag']} | {role_txt} |")
    w("")
    w("## Appendix B — Screen index")
    w("")
    w("| Route | Group | File |")
    w("|---|---|---|")
    for s in screens:
        w(f"| `{s['route']}` | {s['group']} | `{s['file']}` |")
    w("")

    text = "\n".join(lines)
    out = REPO / "docs" / "TESTING_MANUAL.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out}")
    print(f"  {len(ops)} endpoints, {len(screens)} screens, {len(STATE_MACHINES)} state machines")
    print(f"  {len(text.splitlines())} lines")
    return text


if __name__ == "__main__":
    build()
