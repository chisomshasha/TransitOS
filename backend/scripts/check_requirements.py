"""Guard: a Python requirements file must never contain npm/Expo packages.

Why this exists
---------------
The Railway build failed with::

    ERROR: Could not find a version that satisfies the requirement
    expo-linear-gradient==15.0.7 (from versions: none)

`expo-linear-gradient` is an **npm** package (it powers the
`LinearGradient` component in the Expo app). It was mistakenly added to
`backend/requirements.txt`, which the Dockerfile feeds to `pip install`.
It has never existed on PyPI, so pip can never resolve it and the image
build dies before the app ever starts.

The frontend already declares it correctly in `frontend/package.json`::

    "expo-linear-gradient": "~15.0.7"

so the only correct action is to keep it out of the Python requirements.

Usage
-----
    python -m scripts.check_requirements            # check backend/requirements.txt
    python -m scripts.check_requirements path.txt   # check a specific file

Exit code 0 = clean, 1 = a JavaScript-only package was found.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Packages that exist on npm but never on PyPI. These are the ones that
# have actually caused build failures in this project, plus the rest of
# the Expo/React Native surface so the guard catches the next one.
JS_ONLY_PACKAGES: set[str] = {
    "expo",
    "expo-linear-gradient",
    "expo-notifications",
    "expo-camera",
    "expo-constants",
    "expo-router",
    "expo-secure-store",
    "expo-file-system",
    "expo-image-picker",
    "expo-print",
    "expo-sharing",
    "expo-splash-screen",
    "expo-status-bar",
    "expo-system-ui",
    "expo-build-properties",
    "expo-dev-client",
    "expo-linking",
    "react",
    "react-dom",
    "react-native",
    "react-native-gesture-handler",
    "react-native-safe-area-context",
    "react-native-screens",
    "react-native-svg",
    "react-native-web",
    "react-native-webview",
    "react-native-toast-message",
    "react-native-qrcode-svg",
    "lucide-react-native",
    "nativewind",
    "tailwindcss",
    "postcss",
    "autoprefixer",
    "babel-preset-expo",
    "next",
    "typescript",
    "zod",
    "zustand",
    "axios",
    "clsx",
    "tailwind-merge",
    "@hookform/resolvers",
    "@react-native-community/netinfo",
    "@tanstack/react-query",
    "@types/react",
}

# `name==1.2.3`, `name>=1.2.3`, `name[extra]==1.2.3`, bare `name`
_REQUIREMENT_RE = re.compile(
    r"^\s*(?P<name>[A-Za-z0-9._\-]+)\s*(?:\[[^\]]*\])?\s*(?P<spec>[<>=!~]=?.*)?$"
)


def _normalize(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def check_requirements_file(path: Path) -> list[str]:
    """Return a list of human-readable problems found in ``path``."""
    problems: list[str] = []
    if not path.exists():
        return [f"{path}: file not found"]

    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # Strip inline comments and environment markers.
        line = line.split(" #", 1)[0].split(";", 1)[0].strip()
        if not line:
            continue

        match = _REQUIREMENT_RE.match(line)
        if not match:
            continue

        name = _normalize(match.group("name"))
        if name in JS_ONLY_PACKAGES:
            problems.append(
                f"{path}:{lineno}: `{match.group('name')}` is an npm/Expo package, "
                f"not a Python package — pip can never install it.\n"
                f"           Move it to `frontend/package.json` and run "
                f"`npm install` there. Removing it fixes the Docker/Railway build."
            )
    return problems


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        targets = [Path(p) for p in argv[1:]]
    else:
        repo_root = Path(__file__).resolve().parents[2]
        targets = [repo_root / "backend" / "requirements.txt"]

    all_problems: list[str] = []
    for target in targets:
        all_problems.extend(check_requirements_file(target))

    if all_problems:
        print("=" * 72, file=sys.stderr)
        print("INVALID PYTHON REQUIREMENTS — JavaScript packages detected", file=sys.stderr)
        print("=" * 72, file=sys.stderr)
        for problem in all_problems:
            print(f"  ✗ {problem}", file=sys.stderr)
        print("", file=sys.stderr)
        print(
            "Frontend dependencies belong in frontend/package.json.\n"
            "This will fail the Railway/Docker build with:\n"
            "  ERROR: Could not find a version that satisfies the requirement ...",
            file=sys.stderr,
        )
        return 1

    print(f"✓ requirements OK — no JavaScript packages found ({len(targets)} file(s) checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
