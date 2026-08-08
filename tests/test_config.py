"""Tests for settings parsing.

A malformed value in a config file must never stop Nexus from starting. Every
parse falls back to a working default, because a user who typed "yes please"
instead of "true" should get a warning, not a crash on launch.
"""

from __future__ import annotations

import pytest

from nexus.core.config import load_settings


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Run each test against a known-empty environment."""
    for name in (
        "NEXUS_LLM_PROVIDER", "NEXUS_LLM_MODEL", "GROQ_API_KEY", "NEXUS_INPUT_DEVICE",
        "NEXUS_OUTPUT_DEVICE", "NEXUS_ALWAYS_ON_MIC", "NEXUS_DEVICE", "NEXUS_VOICE",
        "NEXUS_SPEECH_SPEED", "NEXUS_SILENCE_MS", "NEXUS_VAD_THRESHOLD", "NEXUS_LOG_LEVEL",
    ):
        monkeypatch.delenv(name, raising=False)


def load(tmp_path):
    """Load settings without reading the developer's real .env."""
    return load_settings(env_file=tmp_path / "absent.env")


def test_defaults_are_usable(tmp_path):
    settings = load(tmp_path)
    assert settings.llm_provider == "groq"
    assert settings.always_on_mic is True
    assert settings.device == "auto"
    assert settings.speech_speed == 1.0
    assert settings.silence_ms == 800


def test_values_are_read_from_the_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_VOICE", "en_GB-alba-medium")
    monkeypatch.setenv("NEXUS_SILENCE_MS", "1200")
    settings = load(tmp_path)

    assert settings.voice == "en_GB-alba-medium"
    assert settings.silence_ms == 1200


@pytest.mark.parametrize("value", ["true", "TRUE", "1", "yes", "on"])
def test_truthy_booleans(tmp_path, monkeypatch, value):
    monkeypatch.setenv("NEXUS_ALWAYS_ON_MIC", value)
    assert load(tmp_path).always_on_mic is True


@pytest.mark.parametrize("value", ["false", "FALSE", "0", "no", "off"])
def test_falsy_booleans(tmp_path, monkeypatch, value):
    monkeypatch.setenv("NEXUS_ALWAYS_ON_MIC", value)
    assert load(tmp_path).always_on_mic is False


def test_nonsense_boolean_falls_back(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_ALWAYS_ON_MIC", "yes please")
    assert load(tmp_path).always_on_mic is True


def test_nonsense_number_falls_back(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_SPEECH_SPEED", "quickly")
    assert load(tmp_path).speech_speed == 1.0


def test_blank_device_means_system_default(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_INPUT_DEVICE", "   ")
    assert load(tmp_path).input_device is None


def test_whitespace_is_stripped(tmp_path, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "  gsk_padded  ")
    assert load(tmp_path).api_keys["groq"] == "gsk_padded"


def test_every_provider_has_its_own_key_variable(tmp_path, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_1")
    monkeypatch.setenv("CEREBRAS_API_KEY", "csk_2")

    keys = load(tmp_path).api_keys

    assert keys == {"groq": "gsk_1", "cerebras": "csk_2"}


def test_absent_keys_are_omitted_rather_than_empty(tmp_path, monkeypatch):
    """Presence has to mean usable, or every caller needs a truthiness check."""
    for name in ("GROQ_API_KEY", "CEREBRAS_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(name, raising=False)

    assert load(tmp_path).api_keys == {}


def test_case_is_normalised(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_DEVICE", "CPU")
    monkeypatch.setenv("NEXUS_LOG_LEVEL", "debug")
    settings = load(tmp_path)

    assert settings.device == "cpu"
    assert settings.log_level == "DEBUG"


def test_settings_are_immutable(tmp_path):
    """Settings are passed to every component, so a stray write in one of
    them must not silently reconfigure the rest."""
    settings = load(tmp_path)
    with pytest.raises(AttributeError):
        settings.voice = "something-else"
