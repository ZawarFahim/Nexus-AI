"""The small amount of information Nexus keeps about its user.

Deliberately narrow. This is a name, not a memory: nothing said during a
conversation is written here, and the file is trivially readable and
deletable by hand. Long-term memory remains a separate future feature with a
separate consent question.

The file lives in the per-user application data directory rather than beside
the code, because an installed program cannot write to Program Files, and
because a user's name should survive reinstalling Nexus.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Final

from nexus.core.paths import data_dir

logger = logging.getLogger(__name__)

__all__ = [
    "MAX_NAME_LENGTH",
    "PROFILE_FILE",
    "Profile",
    "clean_name",
    "clear",
    "data_dir",
    "load",
    "profile_path",
    "save",
]

PROFILE_FILE: Final = "profile.json"

# Spoken aloud and injected into a prompt, so keep it to something name-shaped.
MAX_NAME_LENGTH: Final = 40
_UNSAFE = re.compile(r"[\r\n\t]")


def profile_path() -> Path:
    """Full path to the profile file."""
    return data_dir() / PROFILE_FILE


@dataclass(frozen=True, slots=True)
class Profile:
    """What Nexus knows about the person it is talking to.

    Attributes:
        name: What they asked to be called. Empty means never answered, which
            is a valid state -- Nexus simply does not use a name.
    """

    name: str = ""

    @property
    def is_complete(self) -> bool:
        """Whether first-run setup has been answered."""
        return bool(self.name)

    def with_name(self, name: str) -> Profile:
        """Return a copy carrying a cleaned version of ``name``."""
        return replace(self, name=clean_name(name))


def clean_name(raw: str) -> str:
    """Normalise a typed name.

    Strips control characters that would corrupt the prompt, and truncates
    rather than rejecting so that an odd answer still produces something
    usable instead of an error on first run.
    """
    return _UNSAFE.sub(" ", raw).strip()[:MAX_NAME_LENGTH]


def load() -> Profile:
    """Read the stored profile.

    Returns:
        The saved profile, or an empty one if absent or unreadable. A corrupt
        file is treated as missing: losing a name is not worth a crash on
        startup.
    """
    path = profile_path()
    if not path.is_file():
        return Profile()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Profile(name=clean_name(str(data.get("name", ""))))
    except (OSError, ValueError):
        logger.warning("Could not read %s; treating as a new profile", path, exc_info=True)
        return Profile()


def save(profile: Profile) -> bool:
    """Write the profile.

    Returns:
        True on success. Failure is logged rather than raised -- Nexus works
        fine without a stored name, and an unwritable disk should not stop it
        starting.
    """
    path = profile_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"name": profile.name}, indent=2) + "\n", encoding="utf-8"
        )
    except OSError:
        logger.warning("Could not save profile to %s", path, exc_info=True)
        return False

    logger.debug("Saved profile to %s", path)
    return True


def clear() -> bool:
    """Delete the stored profile.

    Returns:
        True if no profile remains.
    """
    try:
        profile_path().unlink(missing_ok=True)
    except OSError:
        logger.warning("Could not delete %s", profile_path(), exc_info=True)
        return False
    return True
