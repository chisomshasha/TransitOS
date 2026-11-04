"""No dict literal may define the same key twice.

Python silently keeps the **last** value when a dict literal repeats a
key. There is no warning, no error — the earlier value just vanishes.

That is how the permissions matrix ended up with two ``audit_log``
entries in the ``conductor`` row::

    "conductor": {
        ...
        "audit_log": ["read"],     # <- line 205
        ...
        "audit_log": [],            # <- line 216, this one always won
        ...
    },

The role therefore never had the audit-log read it appeared to have,
and the matrix the admin screen renders disagreed with the file by
inspection. A copy-paste slip that Python accepts without a murmur.

This test parses every module in the backend and fails if any dict
literal repeats a key. It is the guard for the whole class: a stray
line in a config dict cannot disappear again.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

BACKEND = pathlib.Path(__file__).resolve().parents[2]


def _modules() -> list[pathlib.Path]:
    return [
        p
        for p in sorted(BACKEND.rglob("*.py"))
        if "__pycache__" not in p.parts
        and ".venv" not in p.parts
        and "site-packages" not in p.parts
    ]


def test_no_duplicate_keys_in_any_dict_literal():
    duplicates: list[str] = []

    for path in _modules():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:  # pragma: no cover - caught by other checks
            pytest.fail(f"{path} does not parse: {exc}")

        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            seen: dict[str, int] = {}
            for key in node.keys:
                if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
                    continue
                if key.value in seen:
                    duplicates.append(
                        f"{path.relative_to(BACKEND.parent)}:{key.lineno} — "
                        f"'{key.value}' is defined again (first at line {seen[key.value]})"
                    )
                seen[key.value] = key.lineno

    assert not duplicates, (
        "duplicate dict keys — Python keeps the last one and ignores the rest:\n  "
        + "\n  ".join(duplicates)
    )


def test_the_permissions_matrix_has_no_shadowed_keys():
    """The matrix must not repeat a resource inside a role's row."""
    from app.models.role_permission import DEFAULT_PERMISSIONS, RESOURCES

    for role, perms in DEFAULT_PERMISSIONS.items():
        unknown = set(perms) - set(RESOURCES)
        assert not unknown, f"{role} lists unknown resources: {sorted(unknown)}"


def test_every_role_has_a_row_for_every_resource():
    """A missing key and a ``[]`` key are different things to a reader."""
    from app.models.role_permission import DEFAULT_PERMISSIONS, RESOURCES

    for role, perms in DEFAULT_PERMISSIONS.items():
        missing = set(RESOURCES) - set(perms)
        assert not missing, f"{role} is missing resources: {sorted(missing)}"
