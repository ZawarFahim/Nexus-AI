"""Stored API credentials.

Kept apart from :mod:`nexus.core.profile` because the two have different rules:
a name is plain text a user may want to read and edit by hand, a credential
is encrypted and should never be printed. Separate files also mean a corrupt
or undecryptable credential cannot cost the user their name.

Environment variables always win. That keeps a developer's ``.env`` working
untouched and gives anyone a way to override a stored key without hunting for
the file.
"""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Final

from nexus.core.profile import data_dir
from nexus.core.secrets import SecretError, protect, unprotect

logger = logging.getLogger(__name__)

CREDENTIALS_FILE: Final = "credentials.json"


def credentials_path() -> Path:
    """Full path to the credentials file."""
    return data_dir() / CREDENTIALS_FILE


def _read_all() -> dict[str, str]:
    path = credentials_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.warning("Could not read %s; ignoring it", path, exc_info=True)
        return {}
    return {k: v for k, v in data.items() if isinstance(v, str)}


def _write_all(entries: dict[str, str]) -> bool:
    path = credentials_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    except OSError:
        logger.warning("Could not write %s", path, exc_info=True)
        return False
    return True


def load_key(provider: str) -> str:
    """Read and decrypt a stored key.

    Args:
        provider: Provider name, such as ``'groq'``.

    Returns:
        The key, or an empty string if absent or undecryptable. A blob written
        by another Windows account cannot be read here, and that is treated as
        "no key stored" rather than an error, so the user is simply asked
        again.
    """
    blob = _read_all().get(provider)
    if not blob:
        return ""

    try:
        return unprotect(base64.b64decode(blob))
    except (SecretError, ValueError):
        logger.info(
            "Stored %s key could not be decrypted; treating it as absent", provider
        )
        return ""


def save_key(provider: str, key: str) -> bool:
    """Encrypt and store a key.

    Returns:
        True on success. Failure is logged rather than raised, since Nexus can
        still run with the key held in memory for this session.
    """
    try:
        blob = base64.b64encode(protect(key)).decode("ascii")
    except SecretError:
        logger.warning("Could not encrypt the %s key", provider, exc_info=True)
        return False

    entries = _read_all()
    entries[provider] = blob
    return _write_all(entries)


def clear_key(provider: str) -> bool:
    """Delete a stored key.

    Returns:
        True if no key for ``provider`` remains.
    """
    entries = _read_all()
    if provider not in entries:
        return True
    del entries[provider]
    return _write_all(entries)
