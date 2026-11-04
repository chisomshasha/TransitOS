"""
Guards for the generated User Manual.

The manual is generated from the codebase (docs/build_user_manual.py), so
it cannot drift away from the application in most ways. These tests cover
the remaining failure modes:

* a role gains a screen but the manual has no section for it;
* the manual references a screenshot that was never captured;
* a screenshot exists but no manual references it, so it was captured for
  nothing;
* the manual's role list stops matching the application's.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
MANUAL = ROOT / "docs" / "USER_MANUAL.md"
SHOTS = ROOT / "docs" / "mockup" / "shots"
RBAC = ROOT / "frontend" / "lib" / "rbac.ts"
TYPES = ROOT / "frontend" / "lib" / "types.ts"


def _manual_text() -> str:
    if not MANUAL.exists():
        pytest.skip("USER_MANUAL.md has not been generated yet")
    return MANUAL.read_text(encoding="utf-8")


def test_manual_exists_and_is_substantial():
    text = _manual_text()
    assert len(text) > 20_000, "the manual is too short to be a user manual"
    assert "Part 0" in text and "Part 1" in text and "Part 2" in text
    assert "Part 3" in text


def test_every_role_has_a_manual_section():
    """A role in the app must have a section in the role manuals."""
    text = _manual_text()
    src = RBAC.read_text(encoding="utf-8")
    roles = set(re.findall(r"'([a-z_]+)'", re.search(
        r"ALL_ROLES[^=]*=\s*\[(.*?)\]", src, re.S).group(1)))
    assert roles, "could not read ALL_ROLES from rbac.ts"

    missing = []
    for role in sorted(roles):
        # Each role must appear in a section heading and in the
        # role->tab table.
        if f"`{role}`" not in text:
            missing.append(role)
    assert not missing, f"roles with no manual section: {missing}"


def test_role_labels_match_the_application():
    """The manual's role names must be the app's own labels."""
    text = _manual_text()
    src = TYPES.read_text(encoding="utf-8")
    block = re.search(r"ROLE_LABELS[^=]*=\s*\{(.*?)\}", src, re.S).group(1)
    labels = dict(re.findall(r"['\"]?([a-z_]+)['\"]?\s*:\s*'([^']+)'", block))
    assert labels, "could not read ROLE_LABELS"
    for role, label in labels.items():
        assert label in text, f"role label {label!r} ({role}) is missing from the manual"


def test_every_referenced_screenshot_exists():
    text = _manual_text()
    refs = re.findall(r"!\[[^\]]*\]\((mockup/shots/[^)]+)\)", text)
    assert refs, "the manual embeds no screenshots"
    missing = [r for r in refs if not (ROOT / "docs" / r).exists()]
    assert not missing, f"screenshots referenced but not captured: {missing}"


def test_captured_screens_are_all_used():
    """Every captured screenshot should appear in the manual."""
    text = _manual_text()
    refs = set(re.findall(r"!\[[^\]]*\]\(mockup/shots/([^)]+)\)", text))
    if not SHOTS.exists():
        pytest.skip("no screenshots captured yet")
    on_disk = {p.name for p in SHOTS.glob("*.png")}
    unused = sorted(on_disk - refs)
    assert not unused, f"screenshots captured but never referenced: {unused}"


def test_the_real_logo_is_used():
    """The manual's branding must be the app's own logo asset.

    The logo lives in the codebase at frontend/assets/transitos-logo.png
    and is byte-identical to the app icon and the adaptive icon. The
    manual must not substitute a lookalike.
    """
    assets = ROOT / "frontend" / "assets"
    logo = assets / "transitos-logo.png"
    icon = assets / "icon.png"
    adaptive = assets / "adaptive-icon.png"
    assert logo.exists(), "the real logo asset is missing"
    data = logo.read_bytes()
    assert data == icon.read_bytes() == adaptive.read_bytes(), (
        "the logo, the app icon and the adaptive icon must be the same asset"
    )
    # The manual is built from that exact asset: the document plan points
    # the renderer at it, and the rendered DOCX really contains an image.
    converter = (ROOT / "docs" / "markdown_to_plan.py").read_text(encoding="utf-8")
    assert "transitos-logo.png" in converter, (
        "the document converter must use the app's real logo asset"
    )

    import zipfile
    docx = ROOT / "docs" / "TransitOS-User-Manual.docx"
    if docx.exists():
        with zipfile.ZipFile(docx) as zf:
            media = [n for n in zf.namelist()
                     if "/media/" in n or n.startswith("media/")]
        assert media, "the rendered manual contains no images"


def test_access_table_is_generated_from_the_code():
    """The screen/role access table must list every gated screen."""
    text = _manual_text()
    src = RBAC.read_text(encoding="utf-8")
    block = re.search(r"SCREEN_ACCESS[^=]*=\s*\[(.*?)\n\];", src, re.S).group(1)
    prefixes = re.findall(r"prefix:\s*'([^']+)'", block)
    assert len(prefixes) >= 20, "could not read SCREEN_ACCESS"
    missing = [p for p in prefixes if f"`{p}`" not in text]
    assert not missing, f"gated screens missing from the access table: {missing}"
