"""Fire every frontend API call against the running app (mongomock).

The static contract check compares paths. This one *executes* the calls.

For every distinct (method, path) the frontend uses, the call is fired
against the real FastAPI app backed by mongomock, with a real session
token and a fully seeded database. The assertion is deliberately narrow
— status codes that prove the call could never work:

* **404** — the route does not exist (wrong path)
* **405** — the route exists but not for this verb
* **401** — the request was not authenticated
* **422** — the body/params do not satisfy the schema (wrong field name,
  missing required field, value the validator rejects)
* **500** — the handler blew up

A 4xx that *is* expected (403 for a role that is not allowed, 409 for a
state conflict, 400 for a semantic refusal such as "Vehicle does not
exist") is recorded and reported but not asserted on, because the fuzzer
does not know the semantic state of the data.

Why the payloads have to be *realistic*
----------------------------------------
An earlier version of this test sent ``"Test Value"`` for every string
field. That produced a wall of false positives — a non-email address, a
password that fails the strength policy, a branch code that fails its
pattern — and because 400/422 were not asserted on, **every one of them
was silently discarded**. A real regression (the front end renaming
``vehicle_id`` to ``vehicle`` and the backend rejecting it) would have
been invisible in exactly the same way.

So the generator below builds values that satisfy the schema the backend
actually declares:

* ``format: email`` → a real address
* ``pattern`` → a value that matches the pattern
* a password field → a password that satisfies the strength policy
* a ``*_id`` field → the id of a seeded document, so the lookup succeeds
  and the *success* path is exercised instead of a semantic 400
* a date field → a date in a sensible order relative to its sibling

With realistic payloads, 422 becomes a meaningful signal, and asserting
on it turns this file into a guard for the whole "the two halves
disagree about a field" class of bug.

The database is seeded with one shared ObjectId across every collection
so that a path parameter of any kind resolves to a real document, plus a
second branch so that the "origin branch must differ from destination
branch" rule can be satisfied.
"""

from __future__ import annotations

import pathlib
import re
import sys
from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId

from app.services.auth import hash_password

BACKEND = pathlib.Path(__file__).resolve().parents[2]
FRONTEND = BACKEND.parent / "frontend"
REPO = BACKEND.parent

# The payload resolver lives with the contract checker. It works out
# which body fields the front end actually sends, by following the hook
# -> mutation variable -> mutate() argument chain.
sys.path.insert(0, str(REPO / "tools" / "contract"))

from sources import iter_source_files  # noqa: E402

# One id used for every seeded document, so any path parameter resolves.
SHARED_ID = ObjectId("507f1f77bcf86cd799439011")
SHARED_ID_STR = str(SHARED_ID)

# A second id, seeded as a second branch. Two endpoints refuse a request
# whose origin and destination are the same branch (``POST /routes``) or
# whose destination branch is the vehicle's current branch
# (``POST /vehicle-transfers``); without a second branch those requests
# could only ever be exercised in their failing form.
SHARED_ID2 = ObjectId("507f1f77bcf86cd799439012")
SHARED_ID2_STR = str(SHARED_ID2)

# Satisfies app/core/security.py's policy: 10-128 chars with an
# uppercase letter, a lowercase letter, a digit and a special character.
POLICY_PASSWORD = "Transit#2026Aa"

# Endpoints that stream forever or need a live push connection.
SKIP_PATHS = {"/events/trips"}

# Endpoints whose behaviour is not route-level (OAuth-ish, file IO).
SKIP_METHODS: set[tuple[str, str]] = set()


# ─── frontend call extraction ───────────────────────────────────────────────

HELPER_METHOD = {
    "getPage": "GET", "getSingle": "GET",
    "postSingle": "POST", "postAction": "POST", "postNoContent": "POST", "postJson": "POST",
    "patchSingle": "PATCH", "patchNoContent": "PATCH", "patchJson": "PATCH",
    "putSingle": "PUT",
    "deleteNoContent": "DELETE", "deleteJson": "DELETE",
}


def _read_template(src: str, start: int):
    quote = src[start]
    i = start + 1
    depth = 0
    while i < len(src):
        ch = src[i]
        if ch == "\\":
            i += 2
            continue
        if quote == "`" and ch == "$" and i + 1 < len(src) and src[i + 1] == "{":
            depth += 1
            i += 2
            continue
        if depth and ch == "}":
            depth -= 1
            i += 1
            continue
        if depth == 0 and ch == quote:
            return src[start + 1 : i], i + 1
        i += 1
    return None, i


def _strip_comments(src: str) -> str:
    out, i, n = [], 0, len(src)
    while i < n:
        if src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j == -1 else j
            continue
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            i = n if j == -1 else j + 2
            continue
        if src[i] in "'\"`":
            q = src[i]
            j = i + 1
            while j < n:
                if src[j] == "\\":
                    j += 2
                    continue
                if src[j] == q:
                    j += 1
                    break
                j += 1
            out.append(src[i:j])
            i = j
            continue
        out.append(src[i])
        i += 1
    return "".join(out)


def frontend_calls() -> list[tuple[str, str]]:
    """Every distinct (method, path-template) the frontend calls."""
    if not FRONTEND.exists():
        return []

    found: set[tuple[str, str]] = set()
    helper_re = re.compile(
        r"(?<![.\w])(" + "|".join(HELPER_METHOD) + r")\s*(?:<[^()]*?>)?\s*\(\s*"
    )
    api_re = re.compile(
        r"\bapi\s*\.\s*(get|post|patch|put|delete)\s*(?:<[^()]*?>)?\s*\(\s*"
    )

    for p in iter_source_files(FRONTEND):
        if p.name == "api.ts":
            continue
        src = _strip_comments(p.read_text(encoding="utf-8"))

        for m in helper_re.finditer(src):
            raw, _ = _read_template(src, m.end())
            if raw is None:
                continue
            found.add((HELPER_METHOD[m.group(1)], _normalise(raw)))

        for m in api_re.finditer(src):
            raw, _ = _read_template(src, m.end())
            if raw is None:
                continue
            found.add((m.group(1).upper(), _normalise(raw)))

    return sorted(found)


def _normalise(path: str) -> str:
    path = re.sub(r"\$\{[^}]*\}", "{}", path)
    path = re.sub(r"\{[^}]*\}", "{}", path)
    path = path.split("?")[0]
    return path.rstrip("/") or "/"


# ─── schema-driven example bodies ───────────────────────────────────────────

# Fields that hold a reference to another document. The value must be the
# id of a document that exists, otherwise the request is refused with a
# semantic 400 and the success path is never reached.
_ID_SUFFIX = ("_id", "_ids")

# Fields whose value must differ from a sibling field's value.
_SECOND_BRANCH_FIELDS = {"destination_branch_id", "to_branch_id"}

# Date fields that must come after their sibling.
_LATER_DATE_FIELDS = {
    "period_end": timedelta(days=1),
    "scheduled_arrival": timedelta(hours=1),
    "expires_at": timedelta(days=365),
    "issued_at": timedelta(days=-30),
}


def _slug(name: str) -> str:
    """`full_name` -> `FULL_NAME`. Safe for a pattern like ^[A-Z0-9-]+$."""
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", name or "").strip("_")
    return (cleaned or "FIELD").upper()


def _fit(value: str, schema: dict) -> str:
    """Respect the schema's length bounds."""
    lo = schema.get("minLength") or 0
    hi = schema.get("maxLength")
    if len(value) < lo:
        value = value + "X" * (lo - len(value))
    if hi is not None and len(value) > hi:
        value = value[:hi]
    return value


def _match_pattern(pattern: str, field: str) -> str | None:
    """A value that satisfies `pattern`, or None if we cannot find one."""
    slug = _slug(field)
    candidates = [
        f"FZ-{slug}",
        slug,
        f"FZ-{slug[:6]}",
        "FZ-001",
        "ABC-123",
        "ABC",
        "123",
        "TEST",
    ]
    for cand in candidates:
        if re.match(pattern, cand):
            return cand
    return None


def _string_value(schema: dict, field: str) -> str:
    name = (field or "").lower()
    fmt = schema.get("format")

    # 1. Foreign keys — point at a document that actually exists.
    if name.endswith(_ID_SUFFIX):
        if name in _SECOND_BRANCH_FIELDS:
            return SHARED_ID2_STR
        return SHARED_ID_STR

    # 2. Passwords — satisfy the backend's own strength policy.
    if "password" in name:
        return POLICY_PASSWORD

    # 3. Emails — a real address, and unique per field so two creates in
    #    the same run cannot collide on a unique index.
    if fmt == "email" or name.endswith("email"):
        return f"{_slug(name).lower().replace('_', '.')}@example.com"

    # 4. Dates — and dates that have to come after a sibling date.
    if fmt == "date-time" or fmt == "date":
        delta = _LATER_DATE_FIELDS.get(name)
        when = datetime.now(timezone.utc) + (delta or timedelta(0))
        return when.isoformat() if fmt == "date-time" else when.date().isoformat()

    # 5. Constrained strings — satisfy the declared pattern.
    pattern = schema.get("pattern")
    if pattern:
        matched = _match_pattern(pattern, name)
        if matched is not None:
            return _fit(matched, schema)

    # 6. Everything else — a readable, non-empty value.
    label = _slug(name).replace("_", " ").title()
    return _fit(f"Fuzz {label}", schema)


def _number_value(schema: dict) -> float | int:
    lo = schema.get("ge")
    if lo is None:
        lo = schema.get("minimum")
    hi = schema.get("le")
    if hi is None:
        hi = schema.get("maximum")
    value = lo if lo is not None else 1
    if hi is not None and value > hi:
        value = hi
    return value


def _example(schema: dict, spec: dict, field: str | None = None, depth: int = 0):
    """Build a plausible, schema-valid example value for an OpenAPI schema."""
    if depth > 6 or not isinstance(schema, dict):
        return None

    if "$ref" in schema:
        ref = schema["$ref"].split("/")[-1]
        return _example(
            spec.get("components", {}).get("schemas", {}).get(ref, {}),
            spec,
            field,
            depth + 1,
        )

    for key in ("anyOf", "oneOf"):
        if key in schema and schema[key]:
            # Prefer the first non-null variant.
            for variant in schema[key]:
                if variant.get("type") != "null":
                    return _example(variant, spec, field, depth + 1)
            return _example(schema[key][0], spec, field, depth + 1)

    stype = schema.get("type")
    if "enum" in schema and schema["enum"]:
        return schema["enum"][0]
    if schema.get("default") is not None:
        return schema["default"]

    if stype == "string":
        return _string_value(schema, field or "")
    if stype == "integer":
        return int(_number_value(schema))
    if stype == "number":
        return float(_number_value(schema))
    if stype == "boolean":
        return True
    if stype == "array":
        item = _example(schema.get("items", {}), spec, field, depth + 1)
        return [item] if item is not None else []
    if stype == "object" or "properties" in schema:
        props = schema.get("properties", {})
        required = set(schema.get("required", []))
        out = {}
        for name, sub in props.items():
            if name in required:
                out[name] = _example(sub, spec, name, depth + 1)
        return out
    return None


# ─── seeding ────────────────────────────────────────────────────────────────

async def _seed(db) -> None:
    """Seed every collection with one document sharing a single _id."""
    now = datetime.now(timezone.utc)

    base = {"_id": SHARED_ID, "created_at": now, "updated_at": now}

    await db.branches.insert_one({
        **base, "name": "Fuzz Branch", "code": "FZ-01", "city": "Fuzz City",
        "state": "Fuzz State", "address": "1 Fuzz St", "status": "active",
        "manager_id": None, "is_active": True, "gps": {"lat": 6.5, "lng": 3.3},
    })
    # A second branch, so "origin != destination" can be satisfied.
    await db.branches.insert_one({
        "_id": SHARED_ID2, "name": "Fuzz Branch Two", "code": "FZ-02",
        "city": "Fuzz City Two", "state": "Fuzz State", "address": "2 Fuzz St",
        "status": "active", "manager_id": None, "is_active": True,
        "created_at": now, "updated_at": now,
    })
    await db.vehicles.insert_one({
        **base, "reg_number": "FZ-001", "type": "bus", "make": "Toyota",
        "model": "Hiace", "year": 2023, "plate_number": "FZ-PLATE",
        "status": "available", "capacity_seats": 50, "capacity_kg": 2000,
        "branch_id": SHARED_ID_STR, "current_odometer_km": 1000,
        "current_fuel_level": 80, "is_active": True,
    })
    await db.drivers.insert_one({
        **base, "user_id": SHARED_ID_STR, "full_name": "Fuzz Driver",
        "phone": "+1-555-1000", "license_no": "FZ-LIC-1",
        "license_expiry": now + timedelta(days=400), "years_experience": 5,
        "status": "active", "branch_id": SHARED_ID_STR, "is_active": True,
    })
    await db.conductors.insert_one({
        **base, "user_id": SHARED_ID_STR, "full_name": "Fuzz Conductor",
        "phone": "+1-555-2000", "badge_no": "FZ-BADGE-1",
        "status": "active", "branch_id": SHARED_ID_STR, "is_active": True,
    })
    await db.routes.insert_one({
        **base, "name": "Fuzz Route", "code": "FZ-R1", "type": "intrastate",
        "origin_branch_id": SHARED_ID_STR, "destination_branch_id": SHARED_ID2_STR,
        "origin_city": "A", "destination_city": "B", "distance_km": 20,
        "base_fare_passenger": 1000, "base_fare_cargo_per_kg": 50,
        "estimated_duration_hours": 1, "status": "active",
        "branch_id": SHARED_ID_STR, "is_active": True,
    })
    await db.trips.insert_one({
        **base, "branch_id": SHARED_ID_STR, "route_id": SHARED_ID_STR,
        "vehicle_id": SHARED_ID_STR, "driver_id": SHARED_ID_STR,
        "conductor_id": SHARED_ID_STR, "status": "planned",
        "scheduled_departure": now + timedelta(hours=2),
        "scheduled_arrival": now + timedelta(hours=6), "is_active": True,
    })
    await db.cash_ups.insert_one({
        **base, "trip_id": SHARED_ID_STR, "branch_id": SHARED_ID_STR,
        "conductor_id": SHARED_ID_STR, "declared_total": 1000,
        "expected_total": 950, "variance": 50, "status": "submitted",
        "breakdown": [], "is_active": True,
    })
    await db.expenses.insert_one({
        **base, "branch_id": SHARED_ID_STR, "vehicle_id": SHARED_ID_STR,
        "trip_id": None, "scope": "standalone", "category": "fuel",
        "amount": 5000, "occurred_at": now, "notes": "fuzz",
        "recorded_by_id": SHARED_ID_STR, "receipt_url": None,
        "vendor_name": None, "odometer_km": None, "is_active": True,
    })
    await db.fuel_logs.insert_one({
        **base, "branch_id": SHARED_ID_STR, "vehicle_id": SHARED_ID_STR,
        "liters": 40, "cost_total": 20000, "cost_per_liter": 500,
        "station_name": "Fuzz Station", "station_location": "Fuzz",
        "odometer_km": 1000, "occurred_at": now, "notes": "fuzz",
        "recorded_by_id": SHARED_ID_STR, "receipt_url": None, "is_active": True,
    })
    await db.maintenance.insert_one({
        **base, "branch_id": SHARED_ID_STR, "vehicle_id": SHARED_ID_STR,
        "type": "routine", "status": "scheduled", "title": "Fuzz Service",
        "description": "fuzz", "cost_parts": 1000, "cost_labor": 500,
        "cost_total": 1500, "odometer_km": 1000, "notes": None,
        "vendor_name": None, "next_due_date": None, "next_due_km": None,
        "scheduled_for": now + timedelta(days=5), "started_at": None,
        "completed_at": None, "is_active": True,
    })
    await db.incidents.insert_one({
        **base, "branch_id": SHARED_ID_STR, "trip_id": SHARED_ID_STR,
        "vehicle_id": SHARED_ID_STR, "severity": "minor", "category": "mechanical",
        "description": "fuzz", "photos": [], "notified": [],
        "status": "open", "reported_by": SHARED_ID_STR,
        "acknowledged_by": None, "acknowledged_at": None,
        "resolved_by": None, "resolved_at": None, "resolution_note": None,
        "is_active": True,
    })
    await db.inspections.insert_one({
        **base, "trip_id": SHARED_ID_STR, "vehicle_id": SHARED_ID_STR,
        "driver_id": SHARED_ID_STR, "items": [], "status": "draft",
        "odometer_reading": 1000, "fuel_level_pct": 80,
        "signature_confirmed": False, "submitted_at": None, "is_active": True,
    })
    await db.vehicle_documents.insert_one({
        **base, "vehicle_id": SHARED_ID_STR, "doc_type": "insurance",
        "issuer": "Fuzz Insurance", "ref_number": "FZ-DOC-1",
        "issued_at": now, "expires_at": now + timedelta(days=365),
        "alert_days": 30, "file_url": None, "is_active": True,
    })
    await db.vehicle_transfers.insert_one({
        **base, "vehicle_id": SHARED_ID_STR, "from_branch_id": SHARED_ID_STR,
        "to_branch_id": SHARED_ID2_STR, "status": "initiated",
        "reason": "fuzz", "notes": None, "initiated_at": now,
        "initiated_by": SHARED_ID_STR, "confirmed_by": None,
        "confirmed_at": None, "returned_by": None, "returned_at": None,
        "cancelled_by": None, "cancelled_at": None,
        "expected_return_at": None, "is_active": True,
    })
    await db.settlements.insert_one({
        **base, "branch_id": SHARED_ID_STR, "period_start": now - timedelta(days=30),
        "period_end": now, "driver_rate": 1000, "conductor_rate": 500,
        "notes": None, "status": "draft", "lines": [],
        "gross_revenue": 0, "trip_expenses": 0, "standalone_expenses": 0,
        "net_payable": 0, "driver_payroll": 0, "conductor_payroll": 0,
        "trip_count": 0, "submitted_at": None, "submitted_by_id": None,
        "approved_at": None, "approved_by_id": None, "paid_at": None,
        "payment_reference": None, "rejection_reason": None, "is_active": True,
    })
    await db.notifications.insert_one({
        **base, "type": "system", "severity": "info", "title": "Fuzz",
        "body": "fuzz", "entity_type": None, "entity_id": None,
        "branch_id": None, "roles": None, "source": "event",
        "dedupe_key": None, "read_by": [],
    })
    await db.push_tokens.insert_one({
        **base, "user_id": SHARED_ID_STR,
        "token": "ExponentPushToken[fuzz-token-0001]", "platform": "android",
        "device_id": "fuzz-device", "app_version": "1.0.0", "is_active": True,
    })
    await db["manifest"].insert_one({
        **base, "trip_id": SHARED_ID_STR, "type": "passenger",
        "passenger_name": "Fuzz Passenger", "passenger_phone": "+1-555-3000",
        "passenger_id_number": None, "seat_number": "1A",
        "cargo_description": None, "cargo_weight_kg": None,
        "cargo_sender_name": None, "cargo_receiver_name": None,
        "cargo_receiver_phone": None, "fare": 500,
        "payment_status": "paid", "payment_method": "cash",
        "boarded": True, "is_active": True,
    })
    await db.users.insert_one({
        **base, "email": "fuzz.member@transitos.app", "full_name": "Fuzz Member",
        "phone": None, "role": "driver", "branch_id": SHARED_ID_STR,
        "status": "active", "hire_date": None, "photo_url": None,
        "password_hash": hash_password("Fuzz#123456"), "last_login_at": None,
        "is_active": True,
    })
    await db.role_permissions.insert_one({
        **base, "role": "super_admin", "description": "fuzz", "permissions": {},
    })


# ─── path parameter substitution ────────────────────────────────────────────

# Path templates whose parameters are NOT document ids. The generic
# "replace every {} with the shared id" rule would put an ObjectId where
# a role name or an entity type belongs.
PATH_PARAMS: dict[str, list[str]] = {
    # The parameter is a role name, not a document id.
    "/role-permissions/{}": ["super_admin"],
    "/role-permissions/{}/reset": ["super_admin"],
    # The first parameter is an entity type, the second a document id.
    "/qr/generate/{}/{}": ["vehicle", SHARED_ID_STR],
}


def _fill_path(template: str) -> str:
    """Turn a path template into a concrete URL."""
    params = PATH_PARAMS.get(template)
    if params is not None:
        parts = template.split("{}")
        url = parts[0]
        for i, chunk in enumerate(parts[1:]):
            url += params[i] + chunk
        return url
    return template.replace("{}", SHARED_ID_STR)


# ─── the front end's own payloads ───────────────────────────────────────────

def frontend_payload_keys() -> dict[tuple[str, str], list[str]]:
    """The body fields the front end sends, per (method, path).

    Resolved by ``tools/contract/payloads.py``. When the front end's
    own payload cannot be traced, the entry is absent and the test falls
    back to a schema-derived body.
    """
    from payloads import scan_frontend_payloads

    out: dict[tuple[str, str], list[str]] = {}
    for p in scan_frontend_payloads():
        if not p.resolved or p.no_body or not p.keys:
            continue
        current = out.get(p.key)
        if current is None or len(p.keys) > len(current):
            out[p.key] = p.keys
    return out


# ─── the fuzz ───────────────────────────────────────────────────────────────

# Status codes that prove the call could never have worked.
FATAL_STATUSES = (404, 405, 401, 422, 500)


@pytest.mark.asyncio
async def test_every_frontend_call_reaches_a_live_route(client, db, auth_headers):
    """Fire every frontend API call and prove it reaches a live route.

    A 404, 405, 401, 422 or 500 means the call could never have worked.

    The body sent is the body the *front end* sends — the same field
    names, resolved from the application source — so a field that the
    front end and the backend disagree about fails here with a 422
    instead of passing unnoticed.
    """
    await _seed(db)

    spec = client.app.openapi() if hasattr(client, "app") else None
    if spec is None:
        from app.main import app as fastapi_app
        spec = fastapi_app.openapi()

    ops_by_key: dict[tuple[str, str], dict] = {}
    for path, item in spec.get("paths", {}).items():
        norm = re.sub(r"\{[^}]*\}", "{}", path).rstrip("/") or "/"
        for method, op in item.items():
            if method.lower() not in ("get", "post", "patch", "put", "delete"):
                continue
            ops_by_key[(method.upper(), norm)] = op

    # Dynamic action suffixes the frontend builds at runtime.
    dynamic = {
        ("POST", "/settlements/{}/{}"): ["submit", "approve", "reject", "pay"],
        ("POST", "/incidents/{}/{}"): ["resolve"],
        ("POST", "/vehicle-transfers/{}/{}"): ["cancel", "confirm", "return"],
    }

    failures: list[str] = []
    unverified: list[str] = []
    checked = 0

    sent_keys = frontend_payload_keys()

    calls = frontend_calls()
    # GETs first: the frontend's DELETE calls remove the very documents
    # a later GET needs, because every collection is seeded with the
    # same id.
    order = {"GET": 0, "PATCH": 1, "POST": 2, "PUT": 3, "DELETE": 4}
    calls.sort(key=lambda c: (order.get(c[0], 9), c[1]))

    for method, template in calls:
        if template in SKIP_PATHS or (method, template) in SKIP_METHODS:
            continue

        op = ops_by_key.get((method, template))

        if op is None and (method, template) in dynamic:
            verbs = dynamic[(method, template)]
            head = template[: template.rfind("{}")]
            resolved = [v for v in verbs if (method, head + v) in ops_by_key]
            if len(resolved) != len(verbs):
                failures.append(f"{method} {template}: missing backend action(s)")
                continue
            for v in verbs:
                op = ops_by_key[(method, head + v)]
                sub_url = head.replace("{}", SHARED_ID_STR) + v
                status = await _fire(
                    client, method, sub_url, op, spec, auth_headers,
                    sent_keys.get((method, head + v)),
                )
                checked += 1
                if status in FATAL_STATUSES:
                    failures.append(f"{method} {head}{v} -> HTTP {status}")
                elif status >= 400:
                    unverified.append(f"{method} {head}{v} -> HTTP {status}")
            continue

        if op is None:
            failures.append(f"{method} {template}: no such route")
            continue

        url = _fill_path(template)
        status = await _fire(
            client, method, url, op, spec, auth_headers,
            sent_keys.get((method, template)),
        )
        checked += 1
        if status in FATAL_STATUSES:
            failures.append(f"{method} {template} -> HTTP {status}")
        elif status >= 400:
            unverified.append(f"{method} {template} -> HTTP {status}")

    assert not failures, (
        "frontend calls that cannot work:\n  " + "\n  ".join(sorted(set(failures)))
    )
    assert checked >= 50, f"only {checked} calls exercised — the scan found too little"


def _request_body(op: dict, spec: dict, only_keys: list[str] | None):
    """The body to send.

    When the front end's own field names are known, the body carries
    exactly those fields — so a required field the front end forgets
    is genuinely missing and the request is refused with a 422.
    Otherwise a schema-derived body is used.
    """
    rb = op.get("requestBody") or {}
    schema = rb.get("content", {}).get("application/json", {}).get("schema", {})
    if "$ref" in schema:
        schema = spec.get("components", {}).get("schemas", {}).get(
            schema["$ref"].split("/")[-1], {}
        )
    props = schema.get("properties", {}) or {}

    if only_keys:
        body: dict = {}
        for key in only_keys:
            if key in props:
                body[key] = _example(props[key], spec, key)
            else:
                # A field the backend does not declare. It is dropped
                # silently, which the static `fields` check reports.
                body[key] = _example({"type": "string"}, spec, key)
        return body

    return _example(schema, spec)


async def _fire(
    client,
    method: str,
    url: str,
    op: dict,
    spec: dict,
    headers: dict,
    body_keys: list[str] | None = None,
) -> int:
    """Issue one request and return the status code."""
    params: dict = {}
    for p in op.get("parameters", []) or []:
        if p.get("in") == "query" and p.get("required"):
            params[p["name"]] = _example(p.get("schema", {}), spec, p.get("name"))

    body = None
    rb = op.get("requestBody") or {}
    if rb.get("content", {}).get("application/json"):
        body = _request_body(op, spec, body_keys)

    kwargs: dict = {"headers": headers}
    if params:
        kwargs["params"] = params
    if body is not None and method in ("POST", "PATCH", "PUT"):
        kwargs["json"] = body

    try:
        resp = await client.request(method, url, **kwargs)
    except Exception:
        # A handler that raises outside the normal error path (e.g. a
        # streaming response that fails mid-body) surfaces as an
        # exception rather than a status code. Treat it as a 500.
        return 500
    return resp.status_code
