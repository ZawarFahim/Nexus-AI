"""Ensures only one Nexus runs at a time.

Two copies would fight over one microphone and both install the same keyboard
hook, so a single keypress would start two recordings and produce two replies
talking over each other. The failure looks like a bug in Nexus rather than what
it is, so the second launch is stopped before it can start.

A named Windows mutex is used rather than a lock file. The kernel releases it
when the process ends, including on a crash or a kill from Task Manager,
whereas a stale lock file would leave Nexus refusing to start until deleted by
hand.
"""

from __future__ import annotations

import ctypes
import logging
import sys
from ctypes import wintypes as wt
from typing import Final

logger = logging.getLogger(__name__)

# "Global\" would cover every user on the machine. Nexus is per-user: two people
# logged into the same PC should each get their own.
MUTEX_NAME: Final = "Local\\Nexus.DesktopCompanion.SingleInstance"

ERROR_ALREADY_EXISTS: Final = 183


class SingleInstance:
    """Holds a system-wide claim to being the only running Nexus.

    The claim lasts as long as the object, so it must be kept alive for the
    life of the process rather than created and discarded.
    """

    def __init__(self, name: str = MUTEX_NAME) -> None:
        self._name = name
        self._handle: int | None = None

    def acquire(self) -> bool:
        """Try to become the only instance.

        Returns:
            True if this process now owns the claim. False means another Nexus is
            already running. Always True on platforms without the API, since
            refusing to start is worse than allowing a duplicate.
        """
        if sys.platform != "win32":
            return True

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = (wt.LPVOID, wt.BOOL, wt.LPCWSTR)
        kernel32.CreateMutexW.restype = wt.HANDLE

        handle = kernel32.CreateMutexW(None, True, self._name)
        error = ctypes.get_last_error()

        if not handle:
            logger.warning("Could not create the single-instance mutex; continuing")
            return True

        if error == ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(handle)
            return False

        self._handle = handle
        return True

    def release(self) -> None:
        """Give up the claim."""
        if self._handle is None:
            return
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.ReleaseMutex(self._handle)
        kernel32.CloseHandle(self._handle)
        self._handle = None

    def __enter__(self) -> SingleInstance:
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.release()
