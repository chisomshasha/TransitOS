"""
Capture real screens of the TransitOS web build for the User Manual.

Drives the *actual* shipped front end (the Expo web export) in headless
Chromium against the seeded demo backend, signs in as each role, and writes
one PNG per screen. The images in the manual are therefore genuine renders,
not hand-drawn mock-ups.

Usage:
    python3 docs/mockup/capture.py
"""

from __future__ import annotations

import os
import sys
import time

from playwright.sync_api import sync_playwright

BASE = os.environ.get("MOCKUP_BASE_URL", "http://127.0.0.1:8080")
OUT = os.path.abspath(os.environ.get("MOCKUP_OUT", "docs/mockup/shots"))
API = os.environ.get("MOCKUP_API_URL", "http://127.0.0.1:8000")

VIEWPORT = {"width": 390, "height": 844}
DEVICE_SCALE = 2

ROLE_PASSWORDS = {
    "super_admin": "Admin#Transit2026!",
    "owner": "Owner#Transit2026!",
    "general_manager": "Gm#Transit2026!",
    "branch_manager": "Bm#Transit2026!",
    "operations_manager": "Om#Transit2026!",
    "fleet_manager": "Fm#Transit2026!",
    "chief_accountant": "Ca#Transit2026!",
    "branch_accountant": "Ba#Transit2026!",
    "driver": "Driver#Transit2026!",
    "conductor": "Conductor#Transit2026!",
}

ROLE_EMAILS = {
    "super_admin": "admin@transitos.app",
    "owner": "owner@transitos.app",
    "general_manager": "gm@transitos.app",
    "branch_manager": "bm.lagos@transitos.app",
    "operations_manager": "om@transitos.app",
    "fleet_manager": "fm.lagos@transitos.app",
    "chief_accountant": "ca@transitos.app",
    "branch_accountant": "ba.lagos@transitos.app",
    "driver": "driver1@transitos.app",
    "conductor": "conductor1@transitos.app",
}

# Deterministic ids — must match docs/mockup/demo_server.py exactly.
_ID = "652f3a1b9c4d2e0011aa"
BRANCH = f"{_ID}b001"
VEHICLE = f"{_ID}b101"
VEHICLE2 = f"{_ID}b102"
TRIP_ACTIVE = f"{_ID}b503"
TRIP_CLOSED = f"{_ID}b505"
# A trip still planned — its manifest is still open, so the capture can
# show the buttons that add a passenger or a parcel. It belongs to
# conductor 1, so the conductor can open it (a crew member sees only
# their own trips).
TRIP_PLANNED = f"{_ID}b501"
# A closed trip whose cash-up is still a draft — the state a conductor
# is in while declaring the day's takings.
TRIP_DRAFT = f"{_ID}b509"
INCIDENT = f"{_ID}b902"
SETTLEMENT_PAID = f"{_ID}bc01"
SETTLEMENT_SUBMITTED = f"{_ID}bc02"
DRIVER = f"{_ID}b201"
CONDUCTOR = f"{_ID}b301"
ROUTE = f"{_ID}b401"
USER = f"{_ID}bf01"

# Which screens to capture for which role.
# (capture-name, route)  — the name is prefixed with the role automatically.
PLAN = {
    "general": [
        ("login", "/login"),
        ("forgot-password", "/forgot-password"),
        ("forgot-username", "/forgot-username"),
    ],
    "super_admin": [
        ("home", "/"),
        ("more", "/more"),
        ("profile", "/profile"),
        ("notifications", "/notifications"),
        ("trips", "/trips"),
        ("trip-detail", f"/trips/{TRIP_ACTIVE}"),
        ("trip-manifest", f"/trips/{TRIP_ACTIVE}", "manifest-editor"),
        ("trip-cash-up", f"/trips/{TRIP_CLOSED}", "cash-up-section"),
        ("trip-closed", f"/trips/{TRIP_CLOSED}"),
        ("trip-draft-cash-up", f"/trips/{TRIP_DRAFT}", "cash-up-section"),
        ("live-board", "/trips/live"),
        ("vehicles", "/vehicles"),
        ("vehicle-detail", f"/vehicles/{VEHICLE}"),
        ("drivers", "/drivers"),
        ("driver-detail", f"/drivers/{DRIVER}"),
        ("conductors", "/conductors"),
        ("conductor-detail", f"/conductors/{CONDUCTOR}"),
        ("routes", "/routes"),
        ("route-detail", f"/routes/{ROUTE}"),
        ("branches", "/branches"),
        ("branch-detail", f"/branches/{BRANCH}"),
        ("users", "/users"),
        ("user-detail", f"/users/{USER}"),
        ("incidents", "/incidents"),
        ("incident-detail", f"/incidents/{INCIDENT}"),
        ("report-incident", "/report-incident"),
        ("fuel", "/fuel"),
        ("maintenance", "/maintenance"),
        ("expenses", "/expenses"),
        ("cash-ups", "/cash-ups"),
        ("settlements", "/settlements"),
        ("settlement-detail", f"/settlements/{SETTLEMENT_PAID}"),
        ("reports", "/reports"),
        ("audit-log", "/audit-log"),
        ("role-permissions", "/role-permissions"),
        ("transfers", "/transfers"),
        ("map", "/map"),
        ("devices", "/devices"),
    ],
    "general_manager": [
        ("home", "/"),
        ("more", "/more"),
        ("profile", "/profile"),
        ("trips", "/trips"),
        ("trip-detail", f"/trips/{TRIP_ACTIVE}"),
        ("trip-manifest", f"/trips/{TRIP_ACTIVE}", "manifest-editor"),
        ("trip-cash-up", f"/trips/{TRIP_CLOSED}", "cash-up-section"),
        ("live-board", "/trips/live"),
        ("vehicles", "/vehicles"),
        ("branches", "/branches"),
        ("users", "/users"),
        ("incidents", "/incidents"),
        ("incident-detail", f"/incidents/{INCIDENT}"),
        ("report-incident", "/report-incident"),
        ("map", "/map"),
        ("reports", "/reports"),
        ("settlements", "/settlements"),
    ],
    "driver": [
        ("home", "/"),
        ("trips", "/trips"),
        ("trip-detail", f"/trips/{TRIP_ACTIVE}"),
        ("trip-status", f"/trips/{TRIP_ACTIVE}", "trip-status-panel"),
        ("live-board", "/trips/live"),
        ("checklist", f"/pre-trip-checklist?tripId={TRIP_ACTIVE}"),
        ("report-incident", "/report-incident"),
        ("more", "/more"),
        ("profile", "/profile"),
    ],
    "conductor": [
        ("home", "/"),
        ("trips", "/trips"),
        ("trip-detail", f"/trips/{TRIP_ACTIVE}"),
        ("trip-manifest", f"/trips/{TRIP_PLANNED}", "manifest-editor"),
        ("trip-cash-up", f"/trips/{TRIP_DRAFT}", "cash-up-section"),
        ("cash-ups", "/cash-ups"),
        ("more", "/more"),
        ("profile", "/profile"),
    ],
    "chief_accountant": [
        ("home", "/"),
        ("expenses", "/expenses"),
        ("settlements", "/settlements"),
        ("settlement-detail", f"/settlements/{SETTLEMENT_SUBMITTED}"),
        ("reports", "/reports"),
        ("more", "/more"),
    ],
    "branch_manager": [
        ("home", "/"),
        ("trips", "/trips"),
        ("trip-status", f"/trips/{TRIP_ACTIVE}", "trip-status-panel"),
        ("trip-cash-up", f"/trips/{TRIP_DRAFT}", "cash-up-section"),
        ("branches", "/branches"),
        ("branch-detail", f"/branches/{BRANCH}"),
        ("settlements", "/settlements"),
        ("users", "/users"),
        ("more", "/more"),
    ],
    "fleet_manager": [
        ("home", "/"),
        ("vehicles", "/vehicles"),
        ("vehicle-detail", f"/vehicles/{VEHICLE2}"),
        ("fuel", "/fuel"),
        ("maintenance", "/maintenance"),
        ("incidents", "/incidents"),
        ("map", "/map"),
        ("more", "/more"),
    ],
    "operations_manager": [
        ("home", "/"),
        ("trips", "/trips"),
        ("live-board", "/trips/live"),
        ("incidents", "/incidents"),
        ("map", "/map"),
        ("more", "/more"),
    ],
    "branch_accountant": [
        ("home", "/"),
        ("expenses", "/expenses"),
        ("cash-ups", "/cash-ups"),
        ("reports", "/reports"),
        ("more", "/more"),
    ],
    "owner": [
        ("home", "/"),
        ("reports", "/reports"),
        ("settlements", "/settlements"),
        ("more", "/more"),
    ],
}


def login(page, email: str, password: str) -> None:
    """Sign in through the real login form and wait for the app shell."""
    page.goto(f"{BASE}/login", wait_until="networkidle", timeout=45000)
    page.wait_for_selector("[data-testid='login-email']", timeout=30000)
    page.fill("[data-testid='login-email']", email)
    page.fill("[data-testid='login-password']", password)
    page.click("[data-testid='login-submit']")
    # Wait for the app shell to take over from the auth layout.
    page.wait_for_function(
        "() => !location.pathname.startsWith('/login') "
        "&& !location.pathname.startsWith('/forgot')",
        timeout=30000,
    )
    page.wait_for_timeout(1200)


def inject_real_logo(page) -> bool:
    """Replace the login screen's generic bus glyph with the app's REAL logo.

    The shipped login screen draws a Lucide ``Bus`` icon in the brand
    header. The product's actual logo lives in the codebase at
    ``frontend/assets/transitos-logo.png`` (byte-identical to the app
    icon and the adaptive icon). This swaps the placeholder glyph for
    that real asset so the manual shows the genuine logo.

    Nothing else on the page is touched.
    """
    return page.evaluate(
        """() => {
            const img = new Image();
            img.src = '/logo.png';
            img.id = 'real-logo';
            img.style.width = '64px';
            img.style.height = '64px';
            img.style.borderRadius = '16px';
            img.style.display = 'block';
            img.style.boxShadow = '0 6px 18px rgba(0,0,0,0.28)';

            // Locate the brand header: the element whose text is exactly
            // 'TransitOS', then its parent's first <svg> (the bus glyph).
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            let label = null;
            while (walker.nextNode()) {
                const t = walker.currentNode.textContent.trim();
                if (t === 'TransitOS') { label = walker.currentNode.parentElement; break; }
            }
            if (!label) return false;
            const header = label.parentElement;
            const svg = header.querySelector('svg');
            if (!svg) return false;
            svg.replaceWith(img);
            return true;
        }"""
    )


def scroll_to(page, test_id: str) -> bool:
    """Bring a section into view before the shot.

    A phone viewport shows one screenful. The trip screen is longer than
    that, so the money-loop sections — the manifest, the cash-up — need
    to be scrolled to before they are photographed, or the manual would
    only ever show the top of the screen.
    """
    try:
        page.wait_for_selector(f"[data-testid='{test_id}']", timeout=8000)
    except Exception:
        print(f"    ! no element with testID '{test_id}'")
        return False
    page.evaluate(
        """(id) => {
            const el = document.querySelector(`[data-testid='${id}']`);
            if (el) el.scrollIntoView({ block: 'start' });
        }""",
        test_id,
    )
    page.wait_for_timeout(900)
    return True


def shoot(page, name: str, route: str, logo: bool = False, scroll: str | None = None) -> str:
    target = f"{BASE}{route}"
    try:
        page.goto(target, wait_until="networkidle", timeout=45000)
    except Exception as exc:  # noqa: BLE001
        print(f"    ! {name}: navigation warning ({str(exc)[:80]})")
        page.wait_for_timeout(2500)
    # Let data-driven content settle (queries, layout animation, skeletons).
    page.wait_for_timeout(2600)
    try:
        page.wait_for_function(
            "() => !document.body.innerText.includes('Loading…')", timeout=8000)
    except Exception:
        pass
    page.wait_for_timeout(700)
    if scroll:
        scroll_to(page, scroll)
    if logo:
        ok = inject_real_logo(page)
        page.wait_for_timeout(500)
        if not ok:
            print(f"    ! {name}: could not place the real logo")
    path = os.path.join(OUT, f"{name}.png")
    page.screenshot(path=path)
    title = page.title()
    body = page.inner_text("body")[:180].replace("\n", " | ")
    print(f"  ✓ {name:<26} {route:<34} {title[:28]:<28} {body[:90]}")
    return path


def main():
    os.makedirs(OUT, exist_ok=True)
    only = sys.argv[1:] or None

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb"])

        # ---- unauthenticated screens -------------------------------------
        if not only or "general" in only:
            print("[capture] general (signed out)")
            ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=DEVICE_SCALE,
                                      is_mobile=True, has_touch=True)
            page = ctx.new_page()
            for entry in PLAN["general"]:
                name, route = entry[0], entry[1]
                shoot(page, name, route, logo=(name == "login"))
            ctx.close()

        # ---- per-role screens --------------------------------------------
        for role, screens in PLAN.items():
            if role == "general":
                continue
            if only and role not in only:
                continue
            print(f"[capture] {role}")
            ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=DEVICE_SCALE,
                                      is_mobile=True, has_touch=True)
            page = ctx.new_page()
            try:
                login(page, ROLE_EMAILS[role], ROLE_PASSWORDS[role])
            except Exception as exc:  # noqa: BLE001
                print(f"    ! login failed: {str(exc)[:140]}")
                ctx.close()
                continue
            for entry in screens:
                name, route = entry[0], entry[1]
                scroll = entry[2] if len(entry) > 2 else None
                shoot(page, f"{role}-{name}", route, scroll=scroll)
            ctx.close()

        browser.close()
    print(f"[capture] done -> {OUT}")


if __name__ == "__main__":
    main()
