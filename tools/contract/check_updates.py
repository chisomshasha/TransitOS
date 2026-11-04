#!/usr/bin/env python3
"""Guard — the Expo Update configuration has to hang together.

An over-the-air update that never arrives is the worst kind of failure:
there is no error, no crash, the app simply keeps running the old code
while everyone believes a fix has shipped. Every one of the ways that
can happen is static, so they are checked here:

  * ``expo-updates`` must actually be a dependency. Without it the
    native side of the update system is missing and the update URL in
    the app config is inert.
  * The update URL must point at the project's own update server. A
    typo here means every lookup 404s, silently.
  * A runtime version must be declared, and the app version it is
    derived from must be the same in ``app.json`` and ``package.json``.
    The runtime version is what decides which binary an update is
    served to; if the two version numbers disagree, updates get filed
    under a version nobody is running.
  * Every build profile must have a channel, the channels must be
    unique, and they must be the ones the publish scripts target. A
    build with no channel never receives updates; two builds sharing a
    channel means a preview fix reaches production.

Run from the repo root:

    python tools/contract/check_updates.py
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
FRONTEND = REPO / "frontend"

#: The channels this project publishes to. One per build profile.
KNOWN_CHANNELS = {"development", "preview", "production"}

#: The channels the npm publish scripts target.
SCRIPT_CHANNELS = {
    "update:preview": "preview",
    "update:production": "production",
    "update:development": "development",
}


def _load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_config() -> dict:
    """The three files the check reads, as they are on disk."""
    return {
        "app": _load(FRONTEND / "app.json").get("expo", {}),
        "pkg": _load(FRONTEND / "package.json"),
        "eas": _load(FRONTEND / "eas.json"),
    }


def check(config: dict | None = None) -> list[str]:
    """Check the OTA configuration. ``config`` overrides what is on disk."""
    problems: list[str] = []

    if config is None:
        for path in (FRONTEND / "app.json", FRONTEND / "package.json",
                     FRONTEND / "eas.json"):
            if not path.exists():
                return [f"{path} is missing — the OTA configuration cannot be checked"]
        config = load_config()

    app = config["app"]
    pkg = config["pkg"]
    eas = config["eas"]

    # ── the dependency ────────────────────────────────────────────────────
    deps = pkg.get("dependencies", {})
    if "expo-updates" not in deps:
        problems.append(
            "expo-updates is not a dependency — the native update client is missing, so "
            "no update can ever be delivered. Install it with `npx expo install expo-updates`."
        )

    # ── the update server ─────────────────────────────────────────────────
    project_id = ((app.get("extra") or {}).get("eas") or {}).get("projectId")
    if not project_id:
        problems.append(
            "extra.eas.projectId is missing — the app is not linked to an EAS project, so "
            "there is no update server to publish to"
        )
    updates = app.get("updates") or {}
    url = updates.get("url")
    if not url:
        problems.append(
            "app.json has no updates.url — the app will look for updates at the Expo "
            "default instead of this project's update server"
        )
    elif project_id:
        expected = f"https://u.expo.dev/{project_id}"
        if url.rstrip("/") != expected:
            problems.append(
                f"updates.url is {url!r} but this project's update server is {expected!r} — "
                "every update lookup would fail silently"
            )

    # ── the runtime version ───────────────────────────────────────────────
    runtime = app.get("runtimeVersion")
    if not runtime:
        problems.append(
            "app.json has no runtimeVersion — updates cannot be matched to a binary"
        )
    elif isinstance(runtime, dict) and not runtime.get("policy"):
        problems.append("runtimeVersion has a policy but no policy name")
    elif isinstance(runtime, str) and not runtime.strip():
        problems.append("runtimeVersion is empty")

    # The runtime version is derived from the app version. Two different
    # version numbers in the repository mean an update can be published
    # against a version that no binary is running.
    app_version = app.get("version")
    pkg_version = pkg.get("version")
    if app_version and pkg_version and app_version != pkg_version:
        problems.append(
            f"the app version is {app_version!r} in app.json but {pkg_version!r} in "
            "package.json — the runtime version follows app.json, so an update published "
            "against the wrong number would never be delivered"
        )

    # ── the channels ──────────────────────────────────────────────────────
    profiles = (eas.get("build") or {})
    seen: dict[str, str] = {}
    for name, profile in profiles.items():
        if not isinstance(profile, dict):
            continue
        channel = profile.get("channel")
        if not channel:
            problems.append(
                f"the {name!r} build profile has no channel — a build with no channel "
                "never receives updates"
            )
            continue
        if channel not in KNOWN_CHANNELS:
            problems.append(
                f"the {name!r} build profile uses the channel {channel!r}, which is not "
                f"one of {sorted(KNOWN_CHANNELS)}"
            )
        if channel in seen:
            problems.append(
                f"the {name!r} and {seen[channel]!r} profiles share the channel "
                f"{channel!r} — a preview fix would reach production"
            )
        else:
            seen[channel] = name

    # ── the publish scripts ───────────────────────────────────────────────
    scripts = pkg.get("scripts", {})
    for script, channel in SCRIPT_CHANNELS.items():
        if script not in scripts:
            problems.append(f"package.json has no {script!r} script")
            continue
        if f"--channel {channel}" not in scripts[script]:
            problems.append(
                f"the {script!r} script does not target the {channel!r} channel — "
                f"it reads {scripts[script]!r}"
            )
        if channel not in seen:
            problems.append(
                f"the {script!r} script publishes to the {channel!r} channel, but no "
                "build profile uses it"
            )

    # ── the versions EAS will serve ───────────────────────────────────────
    # `eas.json` may resolve the version from the Expo servers rather
    # than from the app config. If it does, the two must still agree,
    # or the runtime version of the build and of the update differ.
    cli = eas.get("cli") or {}
    source = cli.get("appVersionSource")
    if source == "remote" and app_version and pkg_version and app_version != pkg_version:
        problems.append(
            "eas.json resolves the version from the Expo servers while the two version "
            "numbers in the repository disagree — the build and the update would be "
            "filed under different runtime versions"
        )

    return problems


def main() -> int:
    problems = check()
    if problems:
        print("  updates  FAIL")
        for problem in problems:
            print(f"      - {problem}")
        return 1
    print("  updates  PASS (expo-updates configured, channels and runtime version aligned)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
