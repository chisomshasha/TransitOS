"""
Demo server for the TransitOS User Manual mockups.

Runs the *real* FastAPI application against an in-memory MongoDB
(``mongomock-motor``) seeded with realistic fleet data, so the manual's
screenshots are genuine renders of the shipped front end — not hand-drawn
mock-ups.

Every seeded document uses an explicit ``_id`` (a Mongo ObjectId) because
the routers look records up by ``_id`` — never by a separate ``id``
field — and because deterministic ids let the capture script address
detail pages by URL.

Usage:
    PYTHONPATH=/workspace/pylibs3 python3 docs/mockup/demo_server.py

Then point the web build at it with the mockup build script:
    bash docs/mockup/build_web.sh http://127.0.0.1:8000
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "backend")
sys.path.insert(0, os.path.abspath(BACKEND))

os.environ.setdefault("MONGODB_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("MONGODB_DB_NAME", "transitos_demo")
os.environ.setdefault("JWT_SECRET_KEY", "demo-secret-not-for-production-use-only")
os.environ.setdefault("ENV", "dev")
os.environ.setdefault("ALERTS_SCAN_INTERVAL_SECONDS", "0")

import uvicorn  # noqa: E402
from bson import ObjectId  # noqa: E402
from mongomock_motor import AsyncMongoMockClient  # noqa: E402

from app.core import database as database_module  # noqa: E402
from app.core.database import get_db  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402
from app.main import app  # noqa: E402
from app.services.auth import hash_password  # noqa: E402

limiter.enabled = False

UTC = timezone.utc
NOW = datetime(2026, 10, 30, 9, 40, tzinfo=UTC)


def ts(days: float = 0.0, hours: float = 0.0) -> datetime:
    return NOW - timedelta(days=days, hours=hours)


# ─── deterministic ObjectIds ─────────────────────────────────────────────────
# 20 hex prefix + 2 hex "kind" + 2 hex counter = 24 hex = a valid ObjectId.
_PREFIX = "652f3a1b9c4d2e0011aa"
KIND = {
    "branch": "b0", "vehicle": "b1", "driver": "b2", "conductor": "b3",
    "route": "b4", "trip": "b5", "expense": "b6", "fuel": "b7",
    "maintenance": "b8", "incident": "b9", "notification": "ba",
    "cash_up": "bb", "settlement": "bc", "audit": "bd", "inspection": "be",
    "user": "bf", "push_token": "c0", "vehicle_transfer": "c1",
    "manifest": "c2",
}


def mkid(kind: str, n: int) -> str:
    return f"{_PREFIX}{KIND[kind]}{n:02x}"


def oid(kind: str, n: int) -> ObjectId:
    return ObjectId(mkid(kind, n))


def s(kind: str, n: int) -> str:
    """The wire form of an id (what the API returns and URLs use)."""
    return mkid(kind, n)


# ─── users ───────────────────────────────────────────────────────────────────
# (email, full name, role, branch index or None, password)
USERS = [
    ("admin@transitos.app", "Chisom Nwosu", "super_admin", None, "Admin#Transit2026!"),
    ("owner@transitos.app", "Emeka Nwosu", "owner", None, "Owner#Transit2026!"),
    ("gm@transitos.app", "Tunde Bakare", "general_manager", None, "Gm#Transit2026!"),
    ("bm.lagos@transitos.app", "Aisha Lawal", "branch_manager", 1, "Bm#Transit2026!"),
    ("bm.abuja@transitos.app", "Sani Idris", "branch_manager", 2, "Bm2#Transit2026!"),
    ("om@transitos.app", "Emeka Obi", "operations_manager", None, "Om#Transit2026!"),
    ("fm.lagos@transitos.app", "Ibrahim Musa", "fleet_manager", 1, "Fm#Transit2026!"),
    ("ca@transitos.app", "Grace Eze", "chief_accountant", None, "Ca#Transit2026!"),
    ("ba.lagos@transitos.app", "Peter Okoro", "branch_accountant", 1, "Ba#Transit2026!"),
    ("driver1@transitos.app", "Adebayo Ogunlesi", "driver", 1, "Driver#Transit2026!"),
    ("driver2@transitos.app", "Chinedu Nwosu", "driver", 1, "Driver#Transit2026!"),
    ("driver3@transitos.app", "Sani Ibrahim", "driver", 2, "Driver#Transit2026!"),
    ("conductor1@transitos.app", "Funke Adebayo", "conductor", 1, "Conductor#Transit2026!"),
    ("conductor2@transitos.app", "Blessing Eze", "conductor", 1, "Conductor#Transit2026!"),
]

BRANCHES = [
    {"_id": oid("branch", 1), "name": "Lagos Main Branch", "code": "LOS-01", "city": "Lagos",
     "state": "Lagos", "address": "1 Marina Road, Lagos Island",
     "contact_phone": "+234-800-000-0001", "contact_email": "lagos@transit-os.app",
     "gps": {"lat": 6.5244, "lng": 3.3792}, "status": "active", "is_active": True,
     "created_at": ts(400), "updated_at": ts(2)},
    {"_id": oid("branch", 2), "name": "Abuja Central Branch", "code": "ABJ-01", "city": "Abuja",
     "state": "FCT", "address": "14 Ahmadu Bello Way, Abuja",
     "contact_phone": "+234-800-000-0002", "contact_email": "abuja@transit-os.app",
     "gps": {"lat": 9.0765, "lng": 7.3986}, "status": "active", "is_active": True,
     "created_at": ts(380), "updated_at": ts(1)},
    {"_id": oid("branch", 3), "name": "Port Harcourt Branch", "code": "PHC-01", "city": "Port Harcourt",
     "state": "Rivers", "address": "7 Aba Road, Port Harcourt",
     "contact_phone": "+234-800-000-0003", "contact_email": "phc@transit-os.app",
     "gps": {"lat": 4.8156, "lng": 7.0498}, "status": "active", "is_active": True,
     "created_at": ts(300), "updated_at": ts(5)},
]

VEHICLES = [
    {"_id": oid("vehicle", 1), "reg_number": "LSR-001-AA", "type": "bus",
     "capacity_seats": 50, "capacity_kg": 5000, "branch_id": s("branch", 1),
     "status": "available", "current_odometer_km": 128400, "current_fuel_level": 82.0,
     "documents": [], "is_active": True, "created_at": ts(390), "updated_at": ts(1)},
    {"_id": oid("vehicle", 2), "reg_number": "LSR-002-AB", "type": "bus",
     "capacity_seats": 50, "capacity_kg": 5000, "branch_id": s("branch", 1),
     "status": "on_trip", "current_odometer_km": 96520, "current_fuel_level": 54.0,
     "documents": [], "is_active": True, "created_at": ts(380), "updated_at": ts(0)},
    {"_id": oid("vehicle", 3), "reg_number": "LSR-003-AC", "type": "minibus",
     "capacity_seats": 15, "capacity_kg": 900, "branch_id": s("branch", 1),
     "status": "maintenance", "current_odometer_km": 210770, "current_fuel_level": 22.0,
     "documents": [], "is_active": True, "created_at": ts(370), "updated_at": ts(2)},
    {"_id": oid("vehicle", 4), "reg_number": "ABJ-011-AD", "type": "bus",
     "capacity_seats": 50, "capacity_kg": 5000, "branch_id": s("branch", 2),
     "status": "available", "current_odometer_km": 64310, "current_fuel_level": 91.0,
     "documents": [], "is_active": True, "created_at": ts(350), "updated_at": ts(3)},
    {"_id": oid("vehicle", 5), "reg_number": "PHC-021-AE", "type": "truck",
     "capacity_seats": 3, "capacity_kg": 12000, "branch_id": s("branch", 3),
     "status": "grounded", "current_odometer_km": 189220, "current_fuel_level": 12.0,
     "documents": [], "is_active": True, "created_at": ts(300), "updated_at": ts(8)},
]

DRIVERS = [
    {"_id": oid("driver", 1), "user_id": s("user", 10), "license_no": "LAG-DR-0001",
     "license_expiry": ts(-1200), "years_experience": 8, "status": "active",
     "branch_id": s("branch", 1), "is_active": True, "created_at": ts(380), "updated_at": ts(10)},
    {"_id": oid("driver", 2), "user_id": s("user", 11), "license_no": "LAG-DR-0002",
     "license_expiry": ts(-900), "years_experience": 5, "status": "active",
     "branch_id": s("branch", 1), "is_active": True, "created_at": ts(350), "updated_at": ts(4)},
    {"_id": oid("driver", 3), "user_id": s("user", 12), "license_no": "LAG-DR-0003",
     "license_expiry": ts(-40), "years_experience": 12, "status": "active",
     "branch_id": s("branch", 2), "is_active": True, "created_at": ts(340), "updated_at": ts(20)},
]

CONDUCTORS = [
    {"_id": oid("conductor", 1), "user_id": s("user", 13), "badge_no": "LAG-CD-0001",
     "status": "active", "branch_id": s("branch", 1), "is_active": True,
     "created_at": ts(370), "updated_at": ts(6)},
    {"_id": oid("conductor", 2), "user_id": s("user", 14), "badge_no": "LAG-CD-0002",
     "status": "active", "branch_id": s("branch", 1), "is_active": True,
     "created_at": ts(340), "updated_at": ts(3)},
]

ROUTES = [
    {"_id": oid("route", 1), "name": "Lagos → Ibadan Express", "type": "interstate",
     "branch_id": s("branch", 1), "origin_branch_id": s("branch", 1),
     "destination_branch_id": s("branch", 2), "origin_city": "Lagos",
     "destination_city": "Ibadan", "distance_km": 120.0, "base_fare_passenger": 2500.0,
     "base_fare_cargo_per_kg": 50.0, "estimated_duration_hours": 2.5,
     "intermediate_stops": [], "required_permits": ["interstate_license"], "is_active": True,
     "created_at": ts(360), "updated_at": ts(9)},
    {"_id": oid("route", 2), "name": "Lagos Island Circular", "type": "intrastate",
     "branch_id": s("branch", 1), "origin_branch_id": s("branch", 1),
     "destination_branch_id": s("branch", 1), "origin_city": "Lagos",
     "destination_city": "Lagos", "distance_km": 42.0, "base_fare_passenger": 1000.0,
     "base_fare_cargo_per_kg": 30.0, "estimated_duration_hours": 1.5,
     "intermediate_stops": [], "required_permits": [], "is_active": True,
     "created_at": ts(355), "updated_at": ts(12)},
    {"_id": oid("route", 3), "name": "Abuja → Kaduna Northbound", "type": "interstate",
     "branch_id": s("branch", 2), "origin_branch_id": s("branch", 2),
     "destination_branch_id": s("branch", 1), "origin_city": "Abuja",
     "destination_city": "Kaduna", "distance_km": 135.0, "base_fare_passenger": 3000.0,
     "base_fare_cargo_per_kg": 55.0, "estimated_duration_hours": 2.75,
     "intermediate_stops": [], "required_permits": ["interstate_license"], "is_active": True,
     "created_at": ts(330), "updated_at": ts(15)},
]


def _trip(n, status, route, vehicle, driver, conductor, dep_hours, **kw):
    doc = {
        "_id": oid("trip", n), "route_id": s("route", route), "vehicle_id": s("vehicle", vehicle),
        "driver_id": s("driver", driver), "conductor_id": s("conductor", conductor),
        "branch_id": s("branch", 1),
        "scheduled_departure": NOW + timedelta(hours=dep_hours),
        "scheduled_arrival": NOW + timedelta(hours=dep_hours + 3),
        "origin_terminal": "Lagos Island Terminal",
        "destination_terminal": "Ibadan BRT Park",
        "status": status, "passenger_count": 0, "cargo_weight_kg": 0.0,
        "total_revenue": 0.0, "total_expenses": 0.0, "is_active": True,
        "created_at": ts(1), "updated_at": ts(0),
    }
    doc.update(kw)
    return doc


TRIPS = [
    _trip(1, "planned", 1, 1, 1, 1, 4, passenger_count=18, total_revenue=45000.0,
          cargo_weight_kg=60.0, notes="Booked group — 18 seats plus one parcel"),
    _trip(2, "boarding", 2, 2, 2, 2, 0, passenger_count=22, total_revenue=22000.0,
          actual_departure=NOW - timedelta(minutes=18)),
    _trip(3, "departed", 1, 2, 1, 1, -2, passenger_count=41, total_revenue=102500.0,
          total_expenses=18500.0, cargo_weight_kg=120.0,
          actual_departure=NOW - timedelta(hours=2)),
    _trip(4, "arrived", 2, 1, 2, 2, -26, passenger_count=38, total_revenue=38000.0,
          total_expenses=9200.0, actual_departure=NOW - timedelta(hours=26),
          actual_arrival=NOW - timedelta(hours=23)),
    _trip(5, "closed", 1, 1, 1, 1, -50, passenger_count=46, total_revenue=115000.0,
          total_expenses=21000.0, actual_departure=NOW - timedelta(hours=50),
          actual_arrival=NOW - timedelta(hours=47)),
    _trip(6, "cashed_up", 1, 2, 2, 2, -74, passenger_count=43, total_revenue=107500.0,
          total_expenses=19750.0, actual_departure=NOW - timedelta(hours=74),
          actual_arrival=NOW - timedelta(hours=71)),
    _trip(7, "cancelled", 2, 1, 1, 1, -96, passenger_count=0, total_revenue=0.0,
          total_expenses=0.0,
          cancelled_reason="Vehicle LSR-003-AC moved to maintenance"),
    _trip(8, "planned", 3, 4, 3, 2, 20),
    # A closed trip whose cash-up is still a draft: this is the state a
    # conductor is in when they are declaring the day's takings, and it
    # is the state the manual has to show.
    _trip(9, "closed", 1, 1, 1, 1, -28, passenger_count=20, total_revenue=50000.0,
          total_expenses=12000.0, actual_departure=NOW - timedelta(hours=28),
          actual_arrival=NOW - timedelta(hours=25)),
]

# ── the passenger and cargo manifest ─────────────────────────────────────────
# A trip's `total_revenue` IS the sum of its manifest fares, and a
# cash-up's `expected_total` is the same sum. Seeding one without the
# other produces a demo that contradicts itself on screen — a trip
# showing "Revenue \u20a6102,500" next to an empty manifest.
#
# So the manifests are generated from the same numbers the trips carry,
# and the fares match the route's base fare.
PAX_NAMES = [
    "Ada Bello", "Chidi Okeke", "Fatima Yusuf", "Emeka Obi", "Zainab Lawal",
    "Tunde Bakare", "Amaka Nwosu", "Ibrahim Musa", "Chioma Eze",
    "Segun Adeyemi", "Ngozi Okafor", "Yusuf Abdullahi", "Blessing Etim",
    "Kelechi Nnamdi", "Aisha Sanni", "Femi Akinola", "Halima Danjuma",
    "Obinna Uche", "Rukayat Mohammed", "Tosin Adeola", "Bisi Ajayi",
    "Musa Ibrahim", "Kemi Afolabi", "Olumide Fashola", "Halima Ibrahim",
    "Tunde Alabi", "Nkechi Obi", "Abiola Salami", "Ifeoma Nwankwo",
    "Suleiman Yakubu", "Omolara Akinyemi", "Efe Ibori", "Hauwa Umar",
    "Tobi Akinpelu", "Peace Ojo", "Godwin Eze", "Rita Chukwu",
    "Yahaya Danladi", "Sade Ogunbiyi", "Nnamdi Anyaoku", "Joy Eromosele",
    "Ibrahim Sule", "Mercy Ajibola", "Obinna Nwosu", "Blessing Etim",
    "Sunday Afolabi", "Ngozi Obi",
]


def _manifest_entries():
    """(trip number, passengers, fare) -> a manifest entry per passenger.

    Trips 2 to 6 carry the passenger counts and revenue the demo already
    showed: the fare here is the route's base fare, and count x fare is
    exactly the trip's `total_revenue`.
    """
    entries = []
    n = 0
    for trip, count, fare in (
        (1, 18, 2500.0),    # planned — booked group, still open for edits
        (2, 22, 1000.0),    # boarding — Lagos Island Circular
        (3, 41, 2500.0),    # departed  — Lagos → Ibadan Express
        (4, 38, 1000.0),    # arrived
        (5, 46, 2500.0),    # closed
        (6, 43, 2500.0),    # cashed up
        (9, 20, 2500.0),    # closed, cash-up still a draft
    ):
        for i in range(count):
            n += 1
            name = PAX_NAMES[(n - 1) % len(PAX_NAMES)]
            entries.append({
                "_id": oid("manifest", n),
                "trip_id": s("trip", trip),
                "branch_id": s("branch", 1),
                "type": "passenger",
                "passenger_name": name,
                "passenger_phone": f"+234-80{n % 10}-000-{2000 + n:04d}",
                "passenger_id_number": None,
                "seat_number": f"{1 + (n % 50)}",
                "cargo_description": None,
                "cargo_weight_kg": None,
                "cargo_sender_name": None,
                "cargo_receiver_name": None,
                "cargo_receiver_phone": None,
                "fare": fare,
                # Two in every five paid in advance; the rest pay on board.
                "payment_status": "paid" if n % 5 in (0, 1) else "on_board",
                "payment_method": "cash" if n % 5 in (0, 1) else None,
                "boarded": trip >= 3,
                "is_active": True,
                "created_at": ts(60 - (n % 40)),
                "updated_at": ts(60 - (n % 40)),
            })
    # A parcel on the planned trip and on the trip the manual
    # photographs, so the manifest shows both kinds of booking.
    for trip_no, description, weight, sender in (
        (1, "6 cartons of drinks", 60.0, "Kola Stores Lagos"),
        (3, "12 cartons of drinks", 120.0, "Kola Stores Lagos"),
    ):
        n += 1
        entries.append({
            "_id": oid("manifest", n),
            "trip_id": s("trip", trip_no),
        "branch_id": s("branch", 1),
        "type": "cargo",
        "passenger_name": None,
        "passenger_phone": None,
        "passenger_id_number": None,
        "seat_number": None,
            "cargo_description": description,
            "cargo_weight_kg": weight,
            "cargo_sender_name": sender,
            "cargo_receiver_name": "Adebowale Stores",
            "cargo_receiver_phone": "+234-803-555-0110",
            "fare": 0.0,
            "payment_status": "paid",
            "payment_method": "transfer",
            "boarded": trip_no >= 3,
            "is_active": True,
            "created_at": ts(58),
            "updated_at": ts(58),
        })
    return entries


MANIFEST = _manifest_entries()


EXPENSES = [
    {"_id": oid("expense", 1), "vehicle_id": s("vehicle", 1), "branch_id": s("branch", 1),
     "scope": "on_trip", "trip_id": s("trip", 5), "category": "fuel", "amount": 28500.0,
     "occurred_at": ts(50), "vendor_name": "TotalEnergies Lagos Island",
     "odometer_km": 128100, "is_active": True, "created_at": ts(50), "updated_at": ts(50)},
    {"_id": oid("expense", 2), "vehicle_id": s("vehicle", 2), "branch_id": s("branch", 1),
     "scope": "on_trip", "trip_id": s("trip", 3), "category": "toll", "amount": 4500.0,
     "occurred_at": ts(2), "vendor_name": "Lagos State toll gate", "odometer_km": 96500,
     "is_active": True, "created_at": ts(2), "updated_at": ts(2)},
    {"_id": oid("expense", 3), "variable": None, "vehicle_id": s("vehicle", 3),
     "branch_id": s("branch", 1), "scope": "standalone", "trip_id": None,
     "category": "maintenance", "amount": 62000.0, "occurred_at": ts(9),
     "vendor_name": "Adeola Auto Spares", "notes": "Brake pads and suspension bushes",
     "is_active": True, "created_at": ts(9), "updated_at": ts(9)},
    {"_id": oid("expense", 4), "vehicle_id": s("vehicle", 1), "branch_id": s("branch", 1),
     "scope": "standalone", "trip_id": None, "category": "meal", "amount": 8500.0,
     "occurred_at": ts(3), "vendor_name": "Kuku Foods Lagos", "is_active": True,
     "created_at": ts(3), "updated_at": ts(3)},
    {"_id": oid("expense", 5), "vehicle_id": s("vehicle", 2), "branch_id": s("branch", 1),
     "scope": "on_trip", "trip_id": s("trip", 6), "category": "other", "amount": 2000.0,
     "occurred_at": ts(72), "vendor_name": "Ibadan BRT Park", "is_active": True,
     "created_at": ts(72), "updated_at": ts(72)},
]

FUEL = [
    {"_id": oid("fuel", 1), "vehicle_id": s("vehicle", 1), "branch_id": s("branch", 1),
     "occurred_at": ts(6), "liters": 120.5, "cost_total": 61300.0, "cost_per_liter": 508.71,
     "odometer_km": 128000, "station_name": "TotalEnergies Lagos Island",
     "station_location": "Ozumba Mbadiwe Ave", "is_active": True,
     "created_at": ts(6), "updated_at": ts(6)},
    {"_id": oid("fuel", 2), "vehicle_id": s("vehicle", 2), "branch_id": s("branch", 1),
     "occurred_at": ts(4), "liters": 98.0, "cost_total": 49840.0, "cost_per_liter": 508.57,
     "odometer_km": 96400, "station_name": "NNPC Oando Lekki",
     "station_location": "Lekki Phase 1", "is_active": True,
     "created_at": ts(4), "updated_at": ts(4)},
    {"_id": oid("fuel", 3), "vehicle_id": s("vehicle", 3), "branch_id": s("branch", 1),
     "occurred_at": ts(14), "liters": 64.2, "cost_total": 32600.0, "cost_per_liter": 507.79,
     "odometer_km": 210600, "station_name": "Ardoyi Filling Station",
     "station_location": "Ikeja", "is_active": True,
     "created_at": ts(14), "updated_at": ts(14)},
]

MAINTENANCE = [
    {"_id": oid("maintenance", 1), "vehicle_id": s("vehicle", 3), "branch_id": s("branch", 1),
     "type": "repair", "status": "in_progress", "title": "Brake system overhaul",
     "description": "Front and rear brake pads, discs and air lines.",
     "scheduled_for": ts(10), "started_at": ts(9), "odometer_km": 210700,
     "vendor_name": "Adeola Auto Spares", "cost_parts": 42000.0, "cost_labor": 20000.0,
     "cost_total": 62000.0, "next_due_km": 250000, "next_due_date": ts(-60),
     "is_active": True, "created_at": ts(12), "updated_at": ts(9)},
    {"_id": oid("maintenance", 2), "vehicle_id": s("vehicle", 1), "branch_id": s("branch", 1),
     "type": "routine", "status": "completed", "title": "40,000 km service",
     "description": "Oil, filters, brake check, tyre rotation.",
     "scheduled_for": ts(30), "started_at": ts(30), "completed_at": ts(29),
     "odometer_km": 128000, "vendor_name": "Lagos Fleet Services",
     "cost_parts": 88000.0, "cost_labor": 32000.0, "cost_total": 120000.0,
     "next_due_km": 168000, "next_due_date": ts(-120), "is_active": True,
     "created_at": ts(35), "updated_at": ts(29)},
    {"_id": oid("maintenance", 3), "vehicle_id": s("vehicle", 2), "branch_id": s("branch", 1),
     "type": "inspection", "status": "scheduled", "title": "AC system service",
     "scheduled_for": ts(-5), "odometer_km": 96500, "vendor_name": "Cool Air Lagos",
     "cost_parts": 0.0, "cost_labor": 0.0, "cost_total": 0.0,
     "next_due_km": 120000, "next_due_date": ts(-2), "is_active": True,
     "created_at": ts(15), "updated_at": ts(15)},
]

INCIDENTS = [
    {"_id": oid("incident", 1), "trip_id": s("trip", 3), "vehicle_id": s("vehicle", 2),
     "branch_id": s("branch", 1), "severity": "moderate", "category": "mechanical",
     "description": "Air pressure warning on the rear axle. Trip completed but vehicle "
                    "diverted to the nearest service point.",
     "photos": [], "status": "acknowledged", "reported_by": s("user", 10),
     "notified": [s("user", 3), s("user", 7)], "acknowledged_by": s("user", 7),
     "acknowledged_at": ts(1), "created_at": ts(1.5), "updated_at": ts(1)},
    {"_id": oid("incident", 2), "trip_id": None, "vehicle_id": s("vehicle", 3),
     "branch_id": s("branch", 1), "severity": "severe", "category": "accident",
     "description": "Minor low-speed collision with a kerb while reversing at the depot. "
                    "No injuries reported; vehicle withdrawn for inspection.",
     "photos": [], "status": "open", "reported_by": s("user", 7), "notified": [s("user", 3)],
     "created_at": ts(8), "updated_at": ts(8)},
    {"_id": oid("incident", 3), "trip_id": s("trip", 5), "vehicle_id": s("vehicle", 1),
     "branch_id": s("branch", 1), "severity": "minor", "category": "passenger_dispute",
     "description": "Departure delayed 35 minutes due to a passenger dispute over luggage space.",
     "photos": [], "status": "resolved", "reported_by": s("user", 14), "notified": [],
     "acknowledged_by": s("user", 3), "acknowledged_at": ts(49),
     "resolved_by": s("user", 3), "resolved_at": ts(48),
     "resolution_note": "Passenger compensated with a seat upgrade on the return leg. "
                        "Coach briefing completed with both crews.",
     "created_at": ts(49), "updated_at": ts(48)},
]

NOTIFICATIONS = [
    {"_id": oid("notification", 1), "type": "maintenance", "severity": "warn",
     "title": "Service overdue",
     "body": "LSR-002-AB is 5,000 km past its scheduled AC service.",
     "entity_type": "vehicle", "entity_id": s("vehicle", 2), "branch_id": s("branch", 1),
     "roles": ["super_admin", "owner", "general_manager", "fleet_manager", "branch_manager"],
     "source": "scan", "dedupe_key": "maint-LSR-002-AB", "read_by": [],
     "created_at": ts(0.5), "refreshed_at": ts(0.5)},
    {"_id": oid("notification", 2), "type": "low_fuel", "severity": "danger",
     "title": "Fuel level critical",
     "body": "PHC-021-AE fuel level has fallen to 12%.",
     "entity_type": "vehicle", "entity_id": s("vehicle", 5), "branch_id": s("branch", 3),
     "roles": ["super_admin", "owner", "general_manager", "fleet_manager"],
     "source": "scan", "dedupe_key": "fuel-PHC-021-AE", "read_by": [],
     "created_at": ts(2), "refreshed_at": ts(2)},
    {"_id": oid("notification", 3), "type": "incidents", "severity": "danger",
     "title": "Severe incident reported",
     "body": "Minor low-speed collision reported for LSR-003-AC.",
     "entity_type": "incident", "entity_id": s("incident", 2), "branch_id": s("branch", 1),
     "roles": ["super_admin", "owner", "general_manager", "operations_manager",
               "branch_manager", "fleet_manager"],
     "source": "event", "dedupe_key": "inc-2", "read_by": [s("user", 3)],
     "created_at": ts(7.5), "refreshed_at": ts(7.5)},
    {"_id": oid("notification", 4), "type": "documents", "severity": "warn",
     "title": "Driver licence expiring",
     "body": "Sani Ibrahim's licence LAG-DR-0003 expires in 40 days.",
     "entity_type": "driver", "entity_id": s("driver", 3), "branch_id": s("branch", 2),
     "roles": ["super_admin", "owner", "general_manager", "fleet_manager"],
     "source": "scan", "dedupe_key": "lic-3", "read_by": [],
     "created_at": ts(4), "refreshed_at": ts(4)},
]

CASH_UPS = [
    {"_id": oid("cash_up", 1), "trip_id": s("trip", 6), "conductor_id": s("conductor", 2),
     "branch_id": s("branch", 1), "method": "cash", "amount": 62500.0, "reference": None,
     "breakdown": [{"method": "cash", "amount": 62500.0},
                   {"method": "transfer", "amount": 45000.0}],
     "declared_total": 107500.0, "status": "approved", "expected_total": 107500.0,
     "variance": 0.0, "notes": "", "is_active": True, "created_at": ts(70),
     "updated_at": ts(69)},
    # A cash-up still being counted: the conductor saves it, then submits
    # it for approval. This is the state the manual's cash-up screen shows.
    {"_id": oid("cash_up", 3), "trip_id": s("trip", 9), "conductor_id": s("conductor", 1),
     "branch_id": s("branch", 1), "method": "cash", "amount": 50000.0, "reference": None,
     "breakdown": [{"method": "cash", "amount": 50000.0}],
     "declared_total": 50000.0, "status": "draft", "expected_total": 0.0,
     "variance": 0.0, "notes": "", "is_active": True, "created_at": ts(2),
     "updated_at": ts(2)},
    {"_id": oid("cash_up", 2), "trip_id": s("trip", 5), "conductor_id": s("conductor", 1),
     "branch_id": s("branch", 1), "method": "cash", "amount": 115000.0, "reference": None,
     "breakdown": [{"method": "cash", "amount": 115000.0}],
     "declared_total": 113000.0, "status": "submitted", "expected_total": 115000.0,
     "variance": -2000.0, "notes": "Short by ₦2,000 — conductor notified.",
     "is_active": True, "created_at": ts(48), "updated_at": ts(48)},
]


def _settlement(n, status, branch, lines, **kw):
    gross = sum(l["gross_revenue"] for l in lines)
    texp = sum(l["trip_expenses"] for l in lines)
    s_exp = kw.pop("standalone_expenses", 0.0)
    doc = {
        "_id": oid("settlement", n), "branch_id": s("branch", branch),
        "branch_name": BRANCHES[branch - 1]["name"],
        "period_start": ts(30), "period_end": NOW,
        "driver_rate": 2500.0, "conductor_rate": 1200.0,
        "lines": lines, "status": status,
        "gross_revenue": gross, "trip_expenses": texp,
        "standalone_expenses": s_exp, "total_expenses": texp + s_exp,
        "net_payable": gross - texp - s_exp,
        "total_driver_pay": sum(l.get("driver_pay", 0.0) for l in lines),
        "total_conductor_pay": sum(l.get("conductor_pay", 0.0) for l in lines),
        "notes": "", "is_active": True, "created_at": ts(6), "updated_at": ts(2),
    }
    doc.update(kw)
    return doc


SETTLEMENTS = [
    _settlement(1, "paid", 1, [
        {"trip_id": s("trip", 5), "trip_date": ts(50), "status": "closed",
         "route_name": "Lagos → Ibadan Express", "gross_revenue": 115000.0,
         "trip_expenses": 21000.0, "net": 94000.0, "driver_id": s("driver", 1),
         "driver_name": "Adebayo Ogunlesi", "driver_pay": 2500.0,
         "conductor_id": s("conductor", 1), "conductor_name": "Funke Adebayo",
         "conductor_pay": 1200.0, "cash_up_id": s("cash_up", 2), "cash_up_variance": -2000.0},
        {"trip_id": s("trip", 6), "trip_date": ts(74), "status": "cashed_up",
         "route_name": "Lagos → Ibadan Express", "gross_revenue": 107500.0,
         "trip_expenses": 19750.0, "net": 87750.0, "driver_id": s("driver", 2),
         "driver_name": "Chinedu Nwosu", "driver_pay": 2500.0,
         "conductor_id": s("conductor", 2), "conductor_name": "Blessing Eze",
         "conductor_pay": 1200.0, "cash_up_id": s("cash_up", 1), "cash_up_variance": 0.0},
    ], standalone_expenses=62000.0, approved_by=s("user", 8)),
    _settlement(2, "submitted", 1, [
        {"trip_id": s("trip", 4), "trip_date": ts(26), "status": "arrived",
         "route_name": "Lagos Island Circular", "gross_revenue": 38000.0,
         "trip_expenses": 9200.0, "net": 28800.0, "driver_id": s("driver", 2),
         "driver_name": "Chinedu Nwosu", "driver_pay": 2500.0,
         "conductor_id": s("conductor", 2), "conductor_name": "Blessing Eze",
         "conductor_pay": 1200.0, "cash_up_id": None, "cash_up_variance": None},
    ], standalone_expenses=8500.0),
    _settlement(3, "draft", 2, [
        {"trip_id": s("trip", 8), "trip_date": ts(1), "status": "planned",
         "route_name": "Abuja → Kaduna Northbound", "gross_revenue": 0.0,
         "trip_expenses": 0.0, "net": 0.0, "driver_id": s("driver", 3),
         "driver_name": "Sani Ibrahim", "driver_pay": 2500.0,
         "conductor_id": s("conductor", 1), "conductor_name": "Funke Adebayo",
         "conductor_pay": 1200.0, "cash_up_id": None, "cash_up_variance": None},
    ], standalone_expenses=0.0),
]

AUDIT = [
    {"_id": oid("audit", 1), "action": "login", "entity_type": "user",
     "entity_id": s("user", 3), "actor_id": s("user", 3), "actor_email": "gm@transitos.app",
     "actor_role": "general_manager", "description": "Signed in from iPhone 14 · Lagos, NG",
     "branch_id": s("branch", 1), "ip_address": "102.89.34.12", "created_at": ts(0.2)},
    {"_id": oid("audit", 2), "action": "update", "entity_type": "vehicle",
     "entity_id": s("vehicle", 2), "actor_id": s("user", 7),
     "actor_email": "fm.lagos@transitos.app", "actor_role": "fleet_manager",
     "description": "Updated vehicle status to on_trip", "branch_id": s("branch", 1),
     "ip_address": "102.89.34.87", "created_at": ts(0.4)},
    {"_id": oid("audit", 3), "action": "create", "entity_type": "incident",
     "entity_id": s("incident", 2), "actor_id": s("user", 7),
     "actor_email": "fm.lagos@transitos.app", "actor_role": "fleet_manager",
     "description": "Reported a severe incident for LSR-003-AC",
     "branch_id": s("branch", 1), "ip_address": "102.89.34.87", "created_at": ts(8)},
    {"_id": oid("audit", 4), "action": "update", "entity_type": "settlement",
     "entity_id": s("settlement", 1), "actor_id": s("user", 8),
     "actor_email": "ca@transitos.app", "actor_role": "chief_accountant",
     "description": "Approved settlement for ₦91,750.00", "branch_id": s("branch", 1),
     "ip_address": "105.112.9.44", "created_at": ts(2)},
    {"_id": oid("audit", 5), "action": "login_failed", "entity_type": "user",
     "entity_id": s("user", 10), "actor_id": s("user", 10),
     "actor_email": "driver1@transitos.app", "actor_role": "driver",
     "description": "Failed sign-in — wrong password (attempt 2 of 5)",
     "branch_id": s("branch", 1), "ip_address": "102.91.200.5", "created_at": ts(4)},
    {"_id": oid("audit", 6), "action": "deactivate", "entity_type": "user",
     "entity_id": s("user", 15), "actor_id": s("user", 3),
     "actor_email": "gm@transitos.app", "actor_role": "general_manager",
     "description": "Deactivated user account", "branch_id": s("branch", 1),
     "ip_address": "102.89.34.12", "created_at": ts(26)},
]

INSPECTIONS = [
    {"_id": oid("inspection", 1), "trip_id": s("trip", 3), "vehicle_id": s("vehicle", 2),
     "driver_id": s("driver", 1), "branch_id": s("branch", 1),
     "template_id": "pre_trip_standard", "result": "failed",
     "items": [{"key": "tyres", "label": "Tyres and pressure", "passed": True, "note": None},
               {"key": "lights", "label": "Lights and indicators", "passed": True, "note": None},
               {"key": "brakes", "label": "Brakes and air pressure", "passed": False,
                "note": "Rear pressure low — reported as incident"}],
     "notes": "Brake check failed; vehicle continued under supervision.",
     "inspected_by": s("user", 10), "created_at": ts(2.2), "updated_at": ts(2.2)},
]

PUSH_TOKENS = [
    {"_id": oid("push_token", 1), "user_id": s("user", 1),
     "token": "ExponentPushToken[a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6r7s8t9u0v1w2]",
     "platform": "android", "device_id": "pixel-8a-91f2", "app_version": "1.1.0",
     "is_active": True, "created_at": ts(30), "updated_at": ts(2)},
    {"_id": oid("push_token", 2), "user_id": s("user", 1),
     "token": "ExponentPushToken[z9y8x7w6v5u4t3s2r1q0p9o8n7m6l5k4j3i2h1g0f]",
     "platform": "ios", "device_id": "iphone-15-7c3d", "app_version": "1.1.0",
     "is_active": True, "created_at": ts(20), "updated_at": ts(2)},
    {"_id": oid("push_token", 3), "user_id": s("user", 10),
     "token": "ExponentPushToken[q1w2e3r4t5y6u7i8o9p0a1s2d3f4g5h6j7k8l9z0x1c2v3]",
     "platform": "android", "device_id": "pixel-8a-91f2", "app_version": "1.1.0",
     "is_active": True, "created_at": ts(30), "updated_at": ts(2)},
    {"_id": oid("push_token", 4), "user_id": s("user", 10),
     "token": "ExponentPushToken[m8n9o0p1q2r3s4t5u6v7w8x9y0z1a2b3c4d5e6f7g8h9j0k]",
     "platform": "android", "device_id": "galaxy-s23-44ab", "app_version": "1.1.0",
     "is_active": True, "created_at": ts(20), "updated_at": ts(2)},
    {"_id": oid("push_token", 5), "user_id": s("user", 13),
     "token": "ExponentPushToken[k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2g3h4i5j]",
     "platform": "ios", "device_id": "iphone-13-55ab", "app_version": "1.1.0",
     "is_active": True, "created_at": ts(25), "updated_at": ts(3)},
]

VEHICLE_TRANSFERS = [
    {"_id": oid("vehicle_transfer", 1), "vehicle_id": s("vehicle", 4),
     "from_branch_id": s("branch", 2), "to_branch_id": s("branch", 1),
     "initiated_by": s("user", 6), "confirmed_by": s("user", 3),
     "status": "confirmed", "reason": "Seasonal demand rebalancing",
     "notes": "Moving ABJ-011-AD to Lagos for the December peak.",
     "expected_return_at": ts(-20), "initiated_at": ts(5), "confirmed_at": ts(4),
     "is_active": True, "created_at": ts(5), "updated_at": ts(4)},
    {"_id": oid("vehicle_transfer", 2), "vehicle_id": s("vehicle", 1),
     "from_branch_id": s("branch", 1), "to_branch_id": s("branch", 3),
     "initiated_by": s("user", 4), "status": "initiated",
     "reason": "Workshop capacity at Port Harcourt",
     "notes": "Awaiting confirmation from the receiving branch.",
     "expected_return_at": ts(-10), "initiated_at": ts(1),
     "is_active": True, "created_at": ts(1), "updated_at": ts(1)},
]


async def seed(db):
    for i, (email, name, role, branch, password) in enumerate(USERS):
        await db.users.insert_one({
            "_id": oid("user", i + 1), "email": email, "full_name": name,
            "phone": "+234-800-000-1000", "role": role,
            "branch_id": s("branch", branch) if branch is not None else None,
            "status": "active", "password_hash": hash_password(password),
            "is_active": True, "last_login_at": NOW - timedelta(minutes=5),
            "created_at": ts(200), "updated_at": ts(2),
        })

    await db.branches.insert_many(BRANCHES)
    await db.vehicles.insert_many(VEHICLES)
    await db.drivers.insert_many(DRIVERS)
    await db.conductors.insert_many(CONDUCTORS)
    await db.routes.insert_many(ROUTES)
    await db.trips.insert_many(TRIPS)
    await db.expenses.insert_many(EXPENSES)
    await db.fuel_logs.insert_many(FUEL)
    # The canonical collection name for maintenance is "maintenance" — the
    # router, the alerts engine and the reports all read that one.
    await db.maintenance.insert_many(MAINTENANCE)
    await db.incidents.insert_many(INCIDENTS)
    await db.notifications.insert_many(NOTIFICATIONS)
    await db.manifest.insert_many(MANIFEST)
    await db.cash_ups.insert_many(CASH_UPS)
    await db.settlements.insert_many(SETTLEMENTS)
    # The audit trail lives in "audit_log" (singular).
    await db.audit_log.insert_many(AUDIT)
    await db.inspections.insert_many(INSPECTIONS)
    await db.push_tokens.insert_many(PUSH_TOKENS)
    await db.vehicle_transfers.insert_many(VEHICLE_TRANSFERS)


async def _prepare():
    client = AsyncMongoMockClient(tz_aware=True)
    db = client["transitos_demo"]

    app.dependency_overrides[get_db] = lambda: db
    database_module.db = db

    await seed(db)
    print(f"[demo] seeded {len(USERS)} users, {len(VEHICLES)} vehicles, "
          f"{len(TRIPS)} trips, {len(MANIFEST)} manifest entries, "
          f"{len(SETTLEMENTS)} settlements", flush=True)
    for email, role, _, _, password in USERS:
        print(f"[demo]   {role:<20} {email:<28} {password}", flush=True)


if __name__ == "__main__":
    import asyncio
    asyncio.run(_prepare())
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
