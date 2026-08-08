"""Tests for the first-run flow.

Onboarding is the code with the worst failure characteristics in Nexus: it runs
once, on someone else's machine, before anything else works, and when it goes
wrong the user has no output to report and no reason to try again. It is also
the code a developer stops exercising the moment their own name and key are
stored.

These drive the flow through a fake front end, so the rules are checked
without a display and without touching the real profile or credential store.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import pytest

from nexus import onboarding
from nexus.core import assets
from nexus.core.config import Settings
from nexus.ui.setup import KeyRequest, SetupUI


@dataclass
class FakeUI:
    """A scripted stand-in for a console or a window.

    Attributes:
        name: What ``ask_name`` returns. ``None`` models a closed dialog.
        keys: Keys to offer in order, as if typed one after another.
    """

    name: str | None = ""
    keys: list[str] = field(default_factory=list)
    fetch_error: Exception | None = None

    asked_name: bool = False
    asked_key: bool = False
    fetched: list[assets.Asset] = field(default_factory=list)
    said: list[str] = field(default_factory=list)
    closed: bool = False

    def ask_name(self) -> str | None:
        self.asked_name = True
        return self.name

    def ask_key(self, request: KeyRequest, validate) -> str | None:
        self.asked_key = True
        for candidate in self.keys:
            if not validate(candidate):
                return candidate
        return None

    def fetch_assets(self, items: Sequence[assets.Asset]) -> None:
        self.fetched = list(items)
        if self.fetch_error is not None:
            raise self.fetch_error

    def say(self, message: str) -> None:
        self.said.append(message)

    def close(self) -> None:
        self.closed = True


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    """Point the profile and credential files at a temporary directory."""
    monkeypatch.setattr(onboarding.profile_store, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(onboarding.credentials, "data_dir", lambda: tmp_path)
    return tmp_path


def test_fake_ui_matches_the_protocol():
    """A drifting fake is a test suite that stops testing the real thing."""
    assert isinstance(FakeUI(), SetupUI)


# -- name -------------------------------------------------------------------


def test_asks_for_a_name_on_first_run():
    ui = FakeUI(name="Mickey")

    profile = onboarding.ensure_profile(ui)

    assert ui.asked_name
    assert profile.name == "Mickey"
    # Stored, or the question comes back on every launch.
    assert onboarding.profile_store.load().name == "Mickey"


def test_does_not_ask_again_once_a_name_is_stored():
    onboarding.set_name("Mickey")
    ui = FakeUI(name="Someone Else")

    profile = onboarding.ensure_profile(ui)

    assert not ui.asked_name
    assert profile.name == "Mickey"


def test_a_closed_name_dialog_is_not_an_error():
    """Declining to give a name must not stop Nexus starting."""
    ui = FakeUI(name=None)

    profile = onboarding.ensure_profile(ui)

    assert profile.name == ""
    assert not profile.is_complete


def test_a_blank_name_carries_on_without_one():
    ui = FakeUI(name="   ")

    profile = onboarding.ensure_profile(ui)

    assert profile.name == ""
    assert ui.said, "the user should be told their answer was accepted"


# -- key --------------------------------------------------------------------


def settings(**keys) -> Settings:
    """Settings with the given provider keys present in the environment."""
    return Settings(llm_provider="groq", api_keys=keys)


def accept_all(monkeypatch) -> None:
    monkeypatch.setattr(onboarding, "validate_key", lambda _provider, _key: "")


def reject_all(monkeypatch, problem: str = "That key was rejected.") -> None:
    monkeypatch.setattr(onboarding, "validate_key", lambda _provider, _key: problem)


def test_the_environment_wins_over_everything(monkeypatch):
    ui = FakeUI(keys=["gsk_typed"])
    accept_all(monkeypatch)

    key = onboarding.ensure_api_key(settings(groq="gsk_env"), ui)

    assert key == "gsk_env"
    assert not ui.asked_key


def test_another_provider_is_used_before_asking_again(monkeypatch):
    """Someone who added a second service should not be re-onboarded.

    Clearing the preferred provider's key must not throw away a working setup
    that happens to run on a different one.
    """
    accept_all(monkeypatch)
    ui = FakeUI(keys=["gsk_typed"])

    key = onboarding.ensure_api_key(settings(cerebras="csk_stored"), ui)

    assert key == "csk_stored"
    assert not ui.asked_key


def test_a_stored_key_is_reused(monkeypatch):
    accept_all(monkeypatch)
    onboarding.credentials.save_key("groq", "gsk_stored")
    ui = FakeUI(keys=["gsk_typed"])

    assert onboarding.ensure_api_key(settings(), ui) == "gsk_stored"
    assert not ui.asked_key


def test_asks_for_a_key_and_stores_it(monkeypatch):
    accept_all(monkeypatch)
    ui = FakeUI(keys=["gsk_typed"])

    key = onboarding.ensure_api_key(settings(), ui)

    assert key == "gsk_typed"
    assert ui.asked_key
    # Stored encrypted, so the next launch does not ask again.
    assert onboarding.credentials.load_key("groq") == "gsk_typed"


def test_a_rejected_key_is_retried_then_abandoned(monkeypatch):
    reject_all(monkeypatch)
    ui = FakeUI(keys=["bad1", "bad2", "bad3"])

    with pytest.raises(onboarding.SetupAbandoned):
        onboarding.ensure_api_key(settings(), ui)

    assert onboarding.credentials.load_key("groq") == ""


def test_the_first_working_key_is_taken(monkeypatch):
    monkeypatch.setattr(
        onboarding, "validate_key", lambda _p, key: "" if key == "good" else "no"
    )
    ui = FakeUI(keys=["bad", "good", "unused"])

    assert onboarding.ensure_api_key(settings(), ui) == "good"


def test_giving_up_on_the_key_stops_startup(monkeypatch):
    accept_all(monkeypatch)
    ui = FakeUI(keys=[])  # Closed the dialog without typing anything.

    with pytest.raises(onboarding.SetupAbandoned, match="needs a key"):
        onboarding.ensure_api_key(settings(), ui)


def test_a_key_is_never_repeated_back(monkeypatch):
    """Nothing shown to the user may contain the credential itself."""
    accept_all(monkeypatch)
    ui = FakeUI(keys=["gsk_supersecret"])

    onboarding.ensure_api_key(settings(), ui)

    assert all("gsk_supersecret" not in message for message in ui.said)


def test_non_interactive_mode_refuses_rather_than_hangs():
    with pytest.raises(onboarding.SetupAbandoned, match="GROQ_API_KEY"):
        onboarding.ensure_api_key(settings(), FakeUI(), ask=False)


# -- downloaded files -------------------------------------------------------


@pytest.fixture
def offline(monkeypatch, tmp_path):
    """Pretend the speech model is missing, without touching the network."""
    missing = [
        assets.Asset("speech model", "https://example.invalid/m", tmp_path / "model.bin"),
    ]
    monkeypatch.setattr(assets, "required", lambda **_kwargs: missing)
    return missing


def test_downloads_what_is_missing(offline):
    ui = FakeUI()

    onboarding.ensure_assets(settings(), ui)

    assert ui.fetched == offline


def test_skips_downloading_when_everything_is_present(monkeypatch):
    monkeypatch.setattr(assets, "required", lambda **_kwargs: [])
    ui = FakeUI()

    onboarding.ensure_assets(settings(), ui)

    assert ui.fetched == []


def test_a_failed_download_says_how_to_recover(offline):
    ui = FakeUI(fetch_error=assets.AssetError("Connection lost"))

    with pytest.raises(onboarding.SetupAbandoned, match="continue from where it stopped"):
        onboarding.ensure_assets(settings(), ui)
