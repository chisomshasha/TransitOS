"""The over-the-air publish path must stay usable.

An update that cannot be published is an update that never reaches the
field, and the two things that stop it are quiet:

* **no Node.** A Codespace created before ``.devcontainer/`` existed
  has neither Node nor the EAS CLI, so ``npm run update:production``
  answers *npm: command not found* and ``eas update`` answers *eas:
  command not found*.
* **the wrong account.** The project belongs to one Expo account.
  Publishing as another fails with a "project not found" that looks
  like a broken project rather than a wrong login.

``backend/scripts/publish_update.sh`` exists for both: it installs what
is missing and checks the login before it publishes. This file makes
sure it stays there, stays runnable, and stays the path the documents
point at — because a script that drifts away from the documentation is
the same failure in a different costume.
"""

from __future__ import annotations

import os
import pathlib
import re
import subprocess

BACKEND = pathlib.Path(__file__).resolve().parents[2]
REPO = BACKEND.parent
SCRIPT = BACKEND / "scripts" / "publish_update.sh"
BOOTSTRAP = BACKEND / "scripts" / "setup_codespace.sh"


def test_the_publish_script_exists_and_is_executable():
    assert SCRIPT.exists(), "backend/scripts/publish_update.sh is missing"
    assert os.access(SCRIPT, os.X_OK), (
        "publish_update.sh is not executable — run: chmod +x backend/scripts/publish_update.sh"
    )


def test_the_publish_script_is_valid_shell():
    """A syntax error in the publish path is found at the worst moment."""
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT)], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_the_bootstrap_script_is_valid_shell():
    result = subprocess.run(
        ["bash", "-n", str(BOOTSTRAP)], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_the_publish_script_installs_what_the_codespace_is_missing():
    """It has to cope with no Node and no EAS CLI."""
    src = SCRIPT.read_text(encoding="utf-8")
    assert "deb.nodesource.com" in src, (
        "the publish script must install Node when it is missing"
    )
    assert "npm install -g eas-cli" in src, (
        "the publish script must install the EAS CLI when it is missing"
    )
    assert "eas whoami" in src, (
        "the publish script must check who is signed in before publishing"
    )
    assert "--rollout-percentage" in src, (
        "the publish script must print how to widen a staged rollout"
    )


def test_the_bootstrap_installs_node_too():
    """A Codespace without Node cannot run the app or publish an update."""
    src = BOOTSTRAP.read_text(encoding="utf-8")
    assert "deb.nodesource.com" in src, (
        "setup_codespace.sh must install Node — 'npm: command not found'"
    )
    assert "eas-cli" in src, (
        "setup_codespace.sh must install the EAS CLI"
    )


def test_the_documents_point_at_the_publish_script():
    """A script nobody is told about does not get used."""
    for doc in (
        "docs/OTA_UPDATES.md",
        "docs/PRE-BUILD-CHECKLIST.md",
        "README.md",
    ):
        path = REPO / doc
        assert path.exists(), f"{doc} is missing"
        text = path.read_text(encoding="utf-8")
        assert "publish_update.sh" in text, (
            f"{doc} does not mention backend/scripts/publish_update.sh — "
            "people will try 'eas update' and hit 'command not found'"
        )


def test_the_ota_document_explains_the_first_build_requirement():
    """The one APK that has to happen first, stated plainly."""
    text = (REPO / "docs" / "OTA_UPDATES.md").read_text(encoding="utf-8")
    # Strip the markdown emphasis so the wording is matched, not the
    # formatting around it.
    flat = re.sub(r"\s+", " ", text.replace("*", "").replace("`", ""))
    assert re.search(r"expo-updates.{0,40}native library", flat, re.I), (
        "the OTA guide must say that the update client lives in the APK"
    )
    assert "npm: command not found" in flat, (
        "the OTA guide must cover the 'no Node in this Codespace' case"
    )
