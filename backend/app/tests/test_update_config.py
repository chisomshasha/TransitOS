"""The Expo Update configuration has to hang together.

An over-the-air update that never arrives is the worst kind of failure:
there is no error and no crash — the app simply keeps running the old
code while everyone believes a fix has shipped. Every way that can
happen is static, so `tools/contract/check_updates.py` checks it.

This file proves two things: the configuration in the repository is
correct, and the guard actually catches each way it could be broken.
A guard that cannot fail is worse than no guard, because it is trusted.
"""

from __future__ import annotations

import copy
import pathlib
import sys

import pytest

BACKEND = pathlib.Path(__file__).resolve().parents[2]
REPO = BACKEND.parent
sys.path.insert(0, str(REPO / "tools" / "contract"))

import check_updates  # noqa: E402


@pytest.fixture
def config() -> dict:
    """The real configuration, as a deep copy so a test can break it."""
    return copy.deepcopy(check_updates.load_config())


def test_the_shipped_configuration_is_correct():
    """The repository as it stands passes the guard."""
    assert check_updates.check() == []


def test_expo_updates_is_installed():
    """The native update client has to be a dependency.

    Without the package the update URL in the app config is inert: the
    binary has no update client, so nothing is ever fetched.
    """
    config = check_updates.load_config()
    assert "expo-updates" in config["pkg"]["dependencies"]


def test_the_update_url_points_at_this_projects_server():
    """A wrong update URL means every lookup fails, silently."""
    config = check_updates.load_config()
    project_id = config["app"]["extra"]["eas"]["projectId"]
    assert config["app"]["updates"]["url"] == f"https://u.expo.dev/{project_id}"


def test_a_wrong_update_url_is_caught(config):
    config["app"]["updates"]["url"] = "https://u.expo.dev/00000000-0000-0000-0000-000000000000"
    problems = check_updates.check(config)
    assert problems, "a mismatched update URL was accepted"
    assert any("update server" in p for p in problems)


def test_a_missing_update_url_is_caught(config):
    del config["app"]["updates"]["url"]
    problems = check_updates.check(config)
    assert any("updates.url" in p for p in problems)


def test_a_missing_dependency_is_caught(config):
    del config["pkg"]["dependencies"]["expo-updates"]
    problems = check_updates.check(config)
    assert any("expo-updates is not a dependency" in p for p in problems)


def test_a_missing_runtime_version_is_caught(config):
    del config["app"]["runtimeVersion"]
    problems = check_updates.check(config)
    assert any("runtimeVersion" in p for p in problems)


def test_disagreeing_version_numbers_are_caught(config):
    """The runtime version follows the app version in app.json.

    If package.json says something else, an update can be published
    against a version no binary is running.
    """
    config["pkg"]["version"] = "9.9.9"
    problems = check_updates.check(config)
    assert any("runtime version follows app.json" in p for p in problems)


def test_a_profile_without_a_channel_is_caught(config):
    """A build with no channel never receives updates."""
    del config["eas"]["build"]["production"]["channel"]
    problems = check_updates.check(config)
    assert any("has no channel" in p for p in problems)


def test_two_profiles_sharing_a_channel_are_caught(config):
    """A preview fix must never reach production."""
    config["eas"]["build"]["preview"]["channel"] = "production"
    problems = check_updates.check(config)
    assert any("share the channel" in p for p in problems)


def test_an_unknown_channel_is_caught(config):
    config["eas"]["build"]["preview"]["channel"] = "staging"
    problems = check_updates.check(config)
    assert any("not one of" in p for p in problems)


def test_a_publish_script_pointing_at_the_wrong_channel_is_caught(config):
    config["pkg"]["scripts"]["update:production"] = (
        "npx eas-cli update --channel preview"
    )
    problems = check_updates.check(config)
    assert any("update:production" in p for p in problems)


def test_a_publish_script_without_a_channel_is_caught(config):
    config["pkg"]["scripts"]["update:preview"] = "npx eas-cli update"
    problems = check_updates.check(config)
    assert any("update:preview" in p for p in problems)


def test_every_publish_script_has_a_channel_to_publish_to(config):
    """A script that publishes to a channel no build listens to is dead."""
    config["eas"]["build"]["preview"]["channel"] = "internal"
    problems = check_updates.check(config)
    assert any("no build profile uses it" in p for p in problems)
