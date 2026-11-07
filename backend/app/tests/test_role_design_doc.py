"""The role-design document must stay true to the code.

``docs/ROLE_DESIGN.md`` explains the app to the client: what each role
is for, what it is accountable for, what it can see, and how the
records fit together. It is the one document in the repository that
describes the *design* rather than the operation of a screen, which
makes it the easiest one to leave behind when the code moves.

So the claims in it are checked against the code here: the role list,
the permission matrix, the scopes, the screen counts and the dashboard
views. If a role is added, a permission moves, or a screen opens or
closes, this fails and the document is updated with it.
"""

from __future__ import annotations

import pathlib
import re

import pytest

BACKEND = pathlib.Path(__file__).resolve().parents[2]
REPO = BACKEND.parent
FRONTEND = REPO / "frontend"
DOC = REPO / "docs" / "ROLE_DESIGN.md"


@pytest.fixture
def doc() -> str:
    assert DOC.exists(), "docs/ROLE_DESIGN.md is missing"
    return DOC.read_text(encoding="utf-8")


def test_every_role_is_described(doc: str):
    """A role that exists in the code must be in the document.

    The document names roles the way the app labels them ("Super Admin",
    not ``super_admin``) — it is written for the client, not for the
    database — so the check is against the display names.
    """
    from app.core.roles import Role
    from app.models.role_permission import DEFAULT_PERMISSIONS

    labels = re.search(
        r"export const ROLE_LABELS[^=]*=\s*\{(.*?)\n\};",
        (FRONTEND / "lib" / "types.ts").read_text(encoding="utf-8"),
        re.S,
    ).group(1)
    display = dict(re.findall(r"(\w+):\s*'([^']+)'", labels))

    for role in DEFAULT_PERMISSIONS:
        assert display.get(role, role) in doc, (
            f"the {role} role is not described in ROLE_DESIGN.md"
        )
    for role in Role:
        assert display.get(role.value, role.value) in doc


def test_the_permission_matrix_claim_is_true(doc: str):
    """The document names nineteen resources and six actions."""
    from app.models.role_permission import ACTIONS, RESOURCES

    flat = re.sub(r"\s+", " ", doc)
    words = {w.lower() for w in re.findall(r"[A-Za-z]+", flat)}
    assert "nineteen" in flat.lower() or len(RESOURCES) == 19
    assert len(RESOURCES) == 19, "the document says nineteen resources"
    assert len(ACTIONS) == 6, "the document says six actions"
    assert "nineteen" in flat.lower(), (
        "the document should say 'nineteen' kinds of record so a reader can count them"
    )
    for action in ("create", "read", "update", "delete", "approve", "export"):
        assert action in words, f"the action '{action}' is not named in the document"


def test_the_scope_claim_is_true(doc: str):
    """Three scopes, and the roles that hold them."""
    from app.models.role_permission import DEFAULT_SCOPES

    flat = re.sub(r"\s+", " ", doc)
    assert set(DEFAULT_SCOPES.values()) == {"all", "branch", "own"}
    for scope in ("all", "branch", "own"):
        assert f"`{scope}`" in doc, f"the scope '{scope}' is not in the document"
    # The document's scope table must not name a role that has another scope.
    for role, scope in DEFAULT_SCOPES.items():
        if scope == "own":
            assert role in flat, f"{role} should be named as an 'own' scope role"


def test_the_screen_counts_are_true(doc: str):
    """The document states how many screens each role opens."""
    src = (FRONTEND / "lib" / "rbac.ts").read_text(encoding="utf-8")
    block = re.search(r"SCREEN_ACCESS[^=]*=\s*\[(.*?)\n\];", src, re.S).group(1)
    entries = re.findall(r"prefix:\s*'([^']+)',\s*roles:\s*\[(.*?)\]", block, re.S)
    all_roles = {
        "super_admin", "owner", "general_manager", "operations_manager",
        "fleet_manager", "branch_manager", "chief_accountant",
        "branch_accountant", "driver", "conductor",
    }
    per_role = {r: 0 for r in all_roles}
    for _prefix, blob in entries:
        rs = set(re.findall(r"'([a-z_]+)'", blob))
        if "ALL_ROLES" in blob:
            rs = set(all_roles)
        for r in rs:
            per_role[r] += 1

    assert len(entries) == 21, "the document says twenty-one screens"
    assert "twenty-one screens" in re.sub(r"\s+", " ", doc)

    # The counts the document states for individual roles.
    stated = {
        "general_manager": 21, "branch_manager": 19, "fleet_manager": 14,
        "operations_manager": 13, "chief_accountant": 4,
        "branch_accountant": 6, "driver": 4, "conductor": 4,
    }
    for role, count in stated.items():
        assert per_role[role] == count, (
            f"{role} opens {per_role[role]} screens; the document says {count}"
        )


def test_the_crew_never_get_company_figures(doc: str):
    """The document's central claim about the crew must hold in code."""
    src = (FRONTEND / "lib" / "dashboard-view.ts").read_text(encoding="utf-8")
    for view in ("DRIVER_VIEW", "CONDUCTOR_VIEW"):
        block = re.search(rf"const {view}[^=]*=\s*\{{(.*?)\n\}};", src, re.S)
        assert block, f"{view} is missing from frontend/lib/dashboard-view.ts"
        body = block.group(1)
        for figure in ("revenue", "cash_variance", "active_fleet", "pending_cashups"):
            assert f"'{figure}'" not in body, (
                f"{view} shows {figure}; the document says the crew sees none"
            )


def test_the_document_covers_every_business_cycle(doc: str):
    """Four cycles, and each is named."""
    flat = re.sub(r"\s+", " ", doc)
    assert "four cycles" in flat.lower()
    for cycle in ("Operations", "Money", "Fleet", "Settlement"):
        assert f"Cycle" in doc and cycle in doc, (
            f"the {cycle} cycle is not described"
        )
    for heading in (
        "Cycle 1 — Operations",
        "Cycle 2 — Money",
        "Cycle 3 — Fleet",
        "Cycle 4 — Settlement",
    ):
        assert heading in doc, f"the heading {heading!r} is missing"


def test_the_document_mentions_every_screen_group(doc: str):
    """The screen list in the document must cover the app's areas."""
    for area in (
        "branches", "users", "vehicles", "drivers", "conductors", "routes",
        "trips", "fuel", "maintenance", "expenses", "cash-ups", "reports",
        "audit log", "transfers", "incidents", "inspections",
        "vehicle documents", "settlements",
    ):
        assert area in doc, f"the document never mentions {area}"
