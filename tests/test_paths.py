"""Tests for path resolution in source and packaged modes.

Packaging bugs are discovered late and diagnosed slowly: the build succeeds,
the executable launches, and something fails minutes later because it wrote to
a directory that no longer exists. These check the rules the packaged build
depends on, without needing a build.
"""

from __future__ import annotations

import sys
from pathlib import Path

from nexus.core import paths


def freeze(monkeypatch, unpacked: Path) -> None:
    """Make ``paths`` believe it is running inside a PyInstaller bundle."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(unpacked), raising=False)


def test_source_mode_uses_the_repository(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)

    assert not paths.is_frozen()
    assert (paths.bundle_dir() / "nexus" / "core" / "paths.py").is_file()
    assert paths.models_dir() == paths.bundle_dir() / "models"


def test_frozen_mode_reads_from_the_unpacked_bundle(monkeypatch, tmp_path):
    freeze(monkeypatch, tmp_path)

    assert paths.is_frozen()
    assert paths.bundle_dir() == tmp_path
    assert paths.piper_binary() == tmp_path / "vendor" / "piper" / "piper.exe"


def test_frozen_mode_never_writes_into_the_bundle(monkeypatch, tmp_path):
    """The bundle is temporary and read-only, so downloads must go elsewhere.

    This is the single most important rule here: getting it wrong produces an
    app that re-downloads 200 MB on every launch.
    """
    freeze(monkeypatch, tmp_path)

    for writable in (paths.models_dir(), paths.voices_dir(), paths.data_dir()):
        assert tmp_path not in writable.parents
        assert writable != tmp_path


def test_downloads_and_settings_share_a_root_when_frozen(monkeypatch, tmp_path):
    freeze(monkeypatch, tmp_path)

    assert paths.models_dir().parent == paths.data_dir()
    assert paths.voices_dir().parent == paths.data_dir()


def test_data_dir_is_stable_across_modes(monkeypatch, tmp_path):
    """A packaged install must find the name and key a source run stored."""
    monkeypatch.delattr(sys, "frozen", raising=False)
    from_source = paths.data_dir()

    freeze(monkeypatch, tmp_path)
    assert paths.data_dir() == from_source


def test_data_dir_follows_localappdata(monkeypatch, tmp_path):
    if sys.platform != "win32":
        return
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert paths.data_dir() == tmp_path / "Nexus"


def test_settings_are_carried_over_from_the_old_name(monkeypatch, tmp_path):
    """Renaming the project must not cost a user their stored key.

    The settings directory is named after the application, so a rename moves
    it. Silently starting fresh would send someone back to a provider console
    to make a new key for no reason they could see.
    """
    if sys.platform != "win32":
        return
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    legacy = tmp_path / paths.LEGACY_APP_DIR_NAME
    legacy.mkdir()
    (legacy / "credentials.json").write_text("{}", encoding="utf-8")

    assert paths.adopt_legacy_data() is True
    assert (paths.data_dir() / "credentials.json").is_file()
    assert not legacy.exists()


def test_carrying_over_never_overwrites_current_settings(monkeypatch, tmp_path):
    if sys.platform != "win32":
        return
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    (tmp_path / paths.LEGACY_APP_DIR_NAME).mkdir()
    current = tmp_path / paths.APP_DIR_NAME
    current.mkdir()
    (current / "credentials.json").write_text("keep me", encoding="utf-8")

    assert paths.adopt_legacy_data() is False
    assert (current / "credentials.json").read_text(encoding="utf-8") == "keep me"


def test_carrying_over_is_harmless_with_nothing_to_carry(monkeypatch, tmp_path):
    if sys.platform != "win32":
        return
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert paths.adopt_legacy_data() is False


def test_describe_names_every_location(monkeypatch, tmp_path):
    freeze(monkeypatch, tmp_path)
    text = paths.describe()

    for label in ("mode", "bundle", "data", "models", "voices", "piper"):
        assert label in text
    assert "packaged" in text
