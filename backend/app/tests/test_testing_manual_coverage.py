"""The testing manual must cover every endpoint and every screen.

A manual that silently omits a route is worse than no manual, because
the client signs off on the illusion of coverage. This test compares the
generated manual against the live OpenAPI schema and the expo-router
route tree, and fails if anything is missing.

If you add an endpoint or a screen, regenerate the manual:

    python docs/build_testing_manual.py
"""

from __future__ import annotations

import pathlib
import re
import sys

import pytest

BACKEND = pathlib.Path(__file__).resolve().parents[2]
REPO = BACKEND.parent
MANUAL = REPO / "docs" / "TESTING_MANUAL.md"
FRONTEND = REPO / "frontend"

sys.path.insert(0, str(REPO / "tools" / "contract"))

from sources import iter_source_files  # noqa: E402


@pytest.fixture(scope="module")
def manual_text() -> str:
    if not MANUAL.exists():
        pytest.fail(
            f"{MANUAL} does not exist — run "
            "`python docs/build_testing_manual.py` to generate it"
        )
    return MANUAL.read_text(encoding="utf-8")


def test_manual_exists_and_is_substantial(manual_text: str):
    assert len(manual_text.splitlines()) > 400, "the manual looks truncated"
    assert "## Part 12 — Client UAT scenarios & sign-off" in manual_text
    assert "Client sign-off" in manual_text


def test_every_endpoint_is_covered(manual_text: str):
    from app.main import app

    spec = app.openapi()
    paths = list(spec["paths"].keys())
    assert paths, "the OpenAPI schema has no paths"

    missing = [p for p in paths if f"`{p}`" not in manual_text]
    assert not missing, (
        "these endpoints are missing from the testing manual — regenerate it with "
        "`python docs/build_testing_manual.py`:\n  " + "\n  ".join(sorted(missing))
    )


def test_every_screen_is_covered(manual_text: str):
    app_dir = FRONTEND / "app"
    routes = []
    for p in iter_source_files(app_dir, ("*.tsx",)):
        if p.name == "_layout.tsx":
            continue
        rel = str(p.relative_to(app_dir))[:-4]
        if rel.startswith("("):
            rel = rel[rel.index(")") + 1:]
        route = "/" + rel.replace("/index", "").strip("/")
        route = re.sub(r"//+", "/", route).rstrip("/") or "/"
        routes.append(route)

    assert routes, "no screens found"
    missing = [r for r in routes if f"`{r}`" not in manual_text]
    assert not missing, (
        "these screens are missing from the testing manual — regenerate it with "
        "`python docs/build_testing_manual.py`:\n  " + "\n  ".join(sorted(missing))
    )


def test_every_state_machine_is_covered(manual_text: str):
    """Each state machine the app enforces must be testable from the manual."""
    machines = {
        "Trip": "planned",
        "Cash-up": "draft",
        "Inspection": "draft",
        "Vehicle transfer": "initiated",
        "Settlement": "draft",
        "Maintenance record": "scheduled",
    }
    for name, first_state in machines.items():
        assert f"### {name}" in manual_text, f"no state-machine section for {name}"
        assert f"`{first_state}`" in manual_text, f"{name} does not list its states"


def test_manual_covers_the_known_regression_areas(manual_text: str):
    """The bugs found during the analysis must have a test item, or they
    will come back unnoticed."""
    for needle, description in [
        ("maintenance_records", "the maintenance collection split"),
        ("receipt", "the PDF receipt export"),
        ("waybill", "the PDF waybill export"),
        ("envelope", "the response envelope"),
        ("index", "the collection index coverage"),
        ("settlement", "the settlements feature"),
        ("live", "the realtime trip board"),
    ]:
        assert needle.lower() in manual_text.lower(), (
            f"the manual does not mention {description}"
        )
