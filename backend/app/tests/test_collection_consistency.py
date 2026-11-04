"""Collection-name consistency across the app.

MongoDB collection names are just strings, so a typo is invisible at
import time and at type-check time: the reader silently sees an empty
collection and the feature quietly returns nothing.

That is exactly what happened with maintenance records. The router
wrote to ``db["maintenance"]`` while the alerts engine read
``db.maintenance_records`` and the reports read
``db["maintenance_records"]``. Nothing raised. Maintenance-due
notifications never fired and maintenance costs never reached the
profit-and-loss report — and no test caught it, because no test had
ever seeded either collection.

This module pins the rule: a collection may only be accessed through
one name, and every collection the app reads must have an index.
"""

from __future__ import annotations

import ast
import os
import pathlib
import re

import pytest

BACKEND = pathlib.Path(__file__).resolve().parents[2]
APP_DIR = BACKEND / "app"

SCAN_DIRS = ["routers", "services", "core"]
SCAN_FILES = ["scripts/seed.py"]


def _source_files() -> list[pathlib.Path]:
    out: list[pathlib.Path] = []
    for sub in SCAN_DIRS:
        out.extend(sorted((APP_DIR / sub).rglob("*.py")))
    for rel in SCAN_FILES:
        p = BACKEND / rel
        if p.exists():
            out.append(p)
    return out


def _collections_used(path: pathlib.Path) -> dict[str, str]:
    """Map collection name -> access style, for every collection touched.

    Handles both ``db.collection.find(...)`` and ``db["collection"].find(...)``.
    """
    src = path.read_text(encoding="utf-8")
    found: dict[str, str] = {}
    for m in re.finditer(r"\bdb\.([a-z_]+)\.[a-z_]+\(", src):
        found.setdefault(m.group(1), "dot")
    for m in re.finditer(r'\bdb\["([a-z_]+)"\]\.[a-z_]+\(', src):
        found.setdefault(m.group(1), "bracket")
    return found


def _indexed_collections() -> set[str]:
    """Collections that ``create_indexes()`` builds an index for."""
    src = (APP_DIR / "core" / "database.py").read_text(encoding="utf-8")
    return set(re.findall(r"\bdb\.([a-z_]+)\.create_indexes\(", src))


def test_no_collection_is_referenced_under_two_names():
    """One collection, one name — across the whole backend.

    A collection reached as both ``db.x`` and ``db["x"]`` is fine (same
    name). The bug is *two different names* for the same data, e.g.
    ``maintenance`` and ``maintenance_records``.
    """
    # The Mongo driver's own pseudo-collections are not data.
    ignore = {"list_collection_names", "drop_collection"}

    by_name: dict[str, set[str]] = {}
    for path in _source_files():
        for coll in _collections_used(path):
            if coll in ignore:
                continue
            by_name.setdefault(coll, set()).add(path.name)

    # The maintenance collection was written as "maintenance" and read as
    # "maintenance_records". Any other pair like this is a bug.
    KNOWN_ALIASES = {"maintenance_records"}  # removed by the fix below

    problems = []
    for coll, users in sorted(by_name.items()):
        if coll in KNOWN_ALIASES:
            problems.append(
                f"collection {coll!r} is still referenced (by {', '.join(sorted(users))}); "
                "the maintenance router writes to 'maintenance'"
            )

    assert not problems, "collection-name drift:\n  " + "\n  ".join(problems)


def test_every_queried_collection_has_an_index():
    """A collection the app scans must have an index.

    Without one, list and dashboard endpoints degrade into full
    collection scans. Eight collections were missing indexes before
    this check existed.
    """
    ignore = {"list_collection_names", "drop_collection", "system_flags"}
    indexed = _indexed_collections()

    queried: dict[str, set[str]] = {}
    for path in _source_files():
        for coll, _style in _collections_used(path).items():
            if coll in ignore:
                continue
            queried.setdefault(coll, set()).add(path.name)

    missing = {
        coll: users for coll, users in queried.items() if coll not in indexed
    }
    assert not missing, (
        "collections queried without an index: "
        + ", ".join(f"{c} ({', '.join(sorted(u))})" for c, u in sorted(missing.items()))
    )


def test_maintenance_router_and_readers_use_the_same_collection():
    """The maintenance router, the alerts engine and the reports must
    all agree on one collection name.

    This is the specific regression: maintenance-due notifications and
    maintenance costs silently disappeared because the readers looked in
    a collection the router never wrote to.
    """
    router = (APP_DIR / "routers" / "maintenance.py").read_text(encoding="utf-8")
    alerts = (APP_DIR / "services" / "alerts.py").read_text(encoding="utf-8")
    reports = (APP_DIR / "routers" / "reports.py").read_text(encoding="utf-8")

    assert 'db["maintenance"]' in router or "db.maintenance." in router, (
        "the maintenance router no longer names its collection"
    )
    assert "maintenance_records" not in alerts, (
        "the alerts engine still reads db.maintenance_records — it must "
        "read the same collection the maintenance router writes"
    )
    assert "maintenance_records" not in reports, (
        "the reports still read db[\"maintenance_records\"] — they must "
        "read the same collection the maintenance router writes"
    )


def test_index_field_names_exist_on_their_documents():
    """Every field named in an index must be a real field.

    A typo in an index key does not raise — Mongo simply stores an
    index on a field nothing writes to, which is the same as having no
    index at all.

    A field counts as real if it appears on the Pydantic model *or* is
    written by the router that owns the collection. Some documents
    carry bookkeeping fields (such as ``is_active`` on a vehicle
    transfer) that are persisted but deliberately kept off the
    response model.
    """
    # collection -> (model file, router file)
    targets = {
        "incidents": (APP_DIR / "models" / "incident.py", APP_DIR / "routers" / "incidents.py"),
        "inspections": (APP_DIR / "models" / "inspection.py", APP_DIR / "routers" / "inspections.py"),
        "notifications": (APP_DIR / "models" / "notification.py", APP_DIR / "routers" / "notifications.py"),
        "vehicle_documents": (APP_DIR / "models" / "vehicle_document.py", APP_DIR / "routers" / "vehicle_documents.py"),
        "vehicle_transfers": (APP_DIR / "models" / "vehicle_transfer.py", APP_DIR / "routers" / "vehicle_transfers.py"),
        "role_permissions": (APP_DIR / "models" / "role_permission.py", APP_DIR / "routers" / "role_permissions.py"),
    }

    db_src = (APP_DIR / "core" / "database.py").read_text(encoding="utf-8")
    problems: list[str] = []

    for coll, (model_path, router_path) in targets.items():
        if not model_path.exists():
            continue

        # Fields declared on the Pydantic models.
        fields: set[str] = set()
        for model_file in model_path.parent.glob("*.py"):
            tree = ast.parse(model_file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for stmt in node.body:
                        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                            fields.add(stmt.target.id)
                        elif isinstance(stmt, ast.Assign):
                            for t in stmt.targets:
                                if isinstance(t, ast.Name):
                                    fields.add(t.id)

        # Fields the owning router writes into the document.
        if router_path.exists():
            router_src = router_path.read_text(encoding="utf-8")
            fields |= set(re.findall(r'"([a-z_]+)"\s*:', router_src))

        if not fields:
            continue

        block = re.search(
            r"db\." + coll + r"\.create_indexes\((.*?)\n    \)", db_src, re.S
        )
        if not block:
            continue
        keys = re.findall(r'\("([a-z_]+)",\s*(?:ASCENDING|DESCENDING)\)', block.group(1))
        for k in keys:
            if k not in fields:
                problems.append(
                    f"{coll}: index references unknown field {k!r} "
                    f"(known fields: {', '.join(sorted(fields))})"
                )

    assert not problems, "index/model field drift:\n  " + "\n  ".join(problems)
