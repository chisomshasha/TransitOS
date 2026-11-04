#!/usr/bin/env python3
"""Guard — the front end must not use a styling toolchain it has not wired.

Why this exists
---------------
``className="flex-1 bg-white"`` on a React Native ``View`` only does
anything when NativeWind is completely wired:

  1. ``babel.config.js`` must load the ``nativewind/babel`` preset *and*
     pass ``jsxImportSource: "nativewind"`` to ``babel-preset-expo``;
  2. ``metro.config.js`` must wrap the config in ``withNativeWind``;
  3. ``react-native-worklets`` (a native module) must be installed.

If any of those is missing, Babel leaves ``className`` as an unknown
prop on the host component. React Native ignores unknown props, so the
build **succeeds**, the typechecker **passes**, and the screen renders
with **no styles at all** — no flex, no background, no spacing.

That is exactly what happened in this project: ``nativewind`` was
declared in ``frontend/package.json`` but no part of the pipeline was
wired, and ``react-native-worklets`` / ``react-native-reanimated``
(``react-native-css-interop``'s peer requirements) were never installed.
One screen — ``app/(app)/routes/index.tsx`` — was written in Tailwind
classes and shipped unstyled.

This check fails the build on the whole *class* of bug:

  * any ``className=`` in ``frontend/app`` or ``frontend/components``
    while NativeWind is not fully wired; or
  * ``nativewind`` declared in ``frontend/package.json`` without the
    full wiring above — the half-installed state that hides the first
    case.

If the team ever wants Tailwind classes back, wire all three parts and
this check goes green on its own.

Run from the repo root:

    python tools/contract/check_styling.py
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
FRONTEND = REPO / "frontend"

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from sources import iter_source_files  # noqa: E402

SCAN_DIRS = ("app", "components")
SCAN_GLOBS = ("*.tsx", "*.ts")

# `className=` on a JSX element. Deliberately narrow: it must be a JSX
# attribute, so `className:` in an object literal or a TS type does not
# match.
CLASSNAME_RE = re.compile(r"<[A-Za-z][^<>]*?\bclassName\s*=")


def _read(path: pathlib.Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _package_json() -> dict:
    try:
        return json.loads(_read(FRONTEND / "package.json"))
    except json.JSONDecodeError:
        return {}


def _declared(deps: dict, name: str) -> bool:
    return name in deps


def nativewind_wiring() -> tuple[bool, list[str]]:
    """Is NativeWind fully wired? Returns (ok, list of missing parts)."""
    pkg = _package_json()
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

    missing: list[str] = []

    babel = _read(FRONTEND / "babel.config.js")
    if "nativewind/babel" not in babel:
        missing.append("babel.config.js does not load the 'nativewind/babel' preset")
    if "jsxImportSource" not in babel or "nativewind" not in babel:
        missing.append(
            "babel.config.js does not pass jsxImportSource: 'nativewind' to babel-preset-expo"
        )

    metro = _read(FRONTEND / "metro.config.js")
    if "withNativeWind" not in metro:
        missing.append("metro.config.js does not wrap the config in withNativeWind()")

    if not _declared(deps, "react-native-worklets"):
        missing.append(
            "react-native-worklets is not installed (react-native-css-interop needs it)"
        )

    return (not missing), missing


def find_classnames() -> list[tuple[str, int]]:
    """Every `className=` in the scanned source, as (relative path, line)."""
    hits: list[tuple[str, int]] = []
    for sub in SCAN_DIRS:
        base = FRONTEND / sub
        if not base.exists():
            continue
        for path in iter_source_files(base, SCAN_GLOBS):
            src = _read(path)
            for i, line in enumerate(src.splitlines(), start=1):
                if CLASSNAME_RE.search(line):
                    hits.append((str(path.relative_to(REPO)), i))
    return hits


def main() -> int:
    pkg = _package_json()
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    wired, missing = nativewind_wiring()
    uses_nativewind = _declared(deps, "nativewind")

    problems: list[str] = []

    if uses_nativewind and not wired:
        problems.append(
            "nativewind is declared in frontend/package.json but the styling "
            "pipeline is not wired. Either finish the wiring or remove the "
            "dependency. Missing:\n    - " + "\n    - ".join(missing)
        )

    classnames = find_classnames()
    if classnames and not wired:
        listed = "\n    ".join(f"{p}:{ln}" for p, ln in classnames[:40])
        more = (
            f"\n    ...and {len(classnames) - 40} more"
            if len(classnames) > 40
            else ""
        )
        problems.append(
            "className= is used but NativeWind is not wired, so React Native "
            "silently drops it and the screen renders unstyled:\n    "
            + listed
            + more
        )

    print()
    if problems:
        print("  styling  FAIL")
        for p in problems:
            print("    - " + p)
        print()
        return 1

    if uses_nativewind:
        print("  styling  PASS (NativeWind wired; className= allowed)")
    else:
        print("  styling  PASS (no className= usage; styling is inline)")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
