"""
Self-check for the demo server.

Fires every GET endpoint the front end uses at the seeded demo API and
reports any non-2xx response, so a seeding mistake (wrong collection
name, wrong enum value, wrong field shape) shows up as a failed endpoint
rather than as an empty screen in a mockup.

Usage:
    PYTHONPATH=/workspace/pylibs3 python3 docs/mockup/selfcheck.py
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"

# Ids are derived exactly as demo_server.py builds them, so a mismatch
# here can only be a routing bug — never a hand-typed hex typo.
_PREFIX = "652f3a1b9c4d2e0011aa"
KIND = {
    "branch": "b0", "vehicle": "b1", "driver": "b2", "conductor": "b3",
    "route": "b4", "trip": "b5", "expense": "b6", "fuel": "b7",
    "maintenance": "b8", "incident": "b9", "notification": "ba",
    "cash_up": "bb", "settlement": "bc", "audit": "bd", "inspection": "be",
    "user": "bf", "push_token": "c0",
}


def mkid(kind: str, n: int) -> str:
    return f"{_PREFIX}{KIND[kind]}{n:02x}"


GET_PATHS = [
    "/dashboard/summary", "/fleet/positions", "/branches", "/users",
    "/vehicles", "/drivers", "/conductors", "/routes", "/trips",
    "/fuel-logs", "/maintenance", "/expenses", "/cash-ups",
    "/incidents", "/incidents/categories", "/incidents/summary",
    "/inspections/template", "/audit-log", "/audit-log/actors",
    "/role-permissions", "/vehicle-transfers", "/settlements",
    "/settlements/summary", "/notifications", "/events/status",
    "/vehicle-documents/expiring",
]

DETAIL_PATHS = [
    f"/branches/{mkid('branch', 1)}",
    f"/users/{mkid('user', 1)}",
    f"/vehicles/{mkid('vehicle', 1)}",
    f"/drivers/{mkid('driver', 1)}",
    f"/conductors/{mkid('conductor', 1)}",
    f"/routes/{mkid('route', 1)}",
    f"/trips/{mkid('trip', 3)}",
    f"/fuel-logs/{mkid('fuel', 1)}",
    f"/maintenance/{mkid('maintenance', 1)}",
    f"/expenses/{mkid('expense', 1)}",
    f"/cash-ups/{mkid('cash_up', 1)}",
    f"/incidents/{mkid('incident', 2)}",
    f"/settlements/{mkid('settlement', 1)}",
]


def call(path: str, token: str) -> tuple[int, str]:
    req = urllib.request.Request(
        f"{BASE}{path}", headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, resp.read().decode()[:160]
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()[:160]
    except Exception as exc:  # noqa: BLE001
        return 0, str(exc)[:160]


def main() -> int:
    body = json.dumps({"email": "admin@transitos.app",
                       "password": "Admin#Transit2026!"}).encode()
    req = urllib.request.Request(f"{BASE}/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        token = json.loads(resp.read())["data"]["access_token"]

    failures = 0
    for path in GET_PATHS + DETAIL_PATHS:
        status, text = call(path, token)
        if status != 200:
            failures += 1
            print(f"  FAIL {status:>3}  {path:<44} {text[:110]}")
        else:
            print(f"  ok   200  {path}")

    print()
    if failures:
        print(f"{failures} endpoint(s) failed — fix the seed before capturing.")
        return 1
    print("All demo endpoints responded 200. Ready to capture.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
