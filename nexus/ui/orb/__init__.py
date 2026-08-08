"""The floating orb, and the handle Nexus drives it with.

The window runs as a separate process; :class:`OrbController` starts it, feeds
it, and makes sure it dies with Nexus. Everything here is best-effort: the orb
is decoration, and no failure in it should ever stop Nexus answering.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import threading
from typing import Final

from nexus.core.paths import is_frozen
from nexus.core.state import State

logger = logging.getLogger(__name__)

# How the state machine's names reach the page.
_STATE_NAMES: Final = {
    State.IDLE: "idle",
    State.LISTENING: "listening",
    State.THINKING: "thinking",
    State.SPEAKING: "speaking",
}

# Levels are sent at most this often. The page eases between what it is given,
# so pushing every audio block would be a hundred writes a second to say
# something two would have said.
MIN_INTERVAL_SECONDS: Final = 0.05

STOP_TIMEOUT_SECONDS: Final = 3.0


class OrbController:
    """Runs the orb window and keeps it in step with Nexus.

    Args:
        enabled: False makes every method a no-op, so callers need no
            conditionals and the orb can be turned off without special cases.
    """

    def __init__(self, *, enabled: bool = True) -> None:
        self._enabled = enabled
        self._process: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()
        self._last_sent = 0.0
        self._state = "idle"

    # -- lifecycle ----------------------------------------------------------

    def start(self) -> bool:
        """Launch the orb process.

        Returns:
            True if it started. Failure is logged and swallowed: Nexus without
            a picture is still Nexus.
        """
        if not self._enabled or self._process is not None:
            return False

        # Frozen builds re-run the executable with a flag rather than shipping
        # a second one; from source it is the module.
        command = (
            [sys.executable, "--orb"]
            if is_frozen()
            else [sys.executable, "-m", "nexus.ui.orb.window"]
        )

        try:
            self._process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError:
            logger.warning("Could not start the orb", exc_info=True)
            self._process = None
            return False

        logger.info("Orb started")
        return True

    def stop(self) -> None:
        """Close the orb, politely then otherwise."""
        process, self._process = self._process, None
        if process is None:
            return

        self._write(process, {"quit": True})
        try:
            process.wait(timeout=STOP_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()

    # -- updates ------------------------------------------------------------

    def on_state(self, state: State) -> None:
        """Follow Nexus's state. Safe to call from any thread."""
        self._state = _STATE_NAMES.get(state, "idle")
        self._send({"state": self._state})

    def on_levels(self, *, input_level: float = 0.0, output_level: float = 0.0) -> None:
        """Report how loud the microphone and the speaker are, in 0.0-1.0."""
        import time

        now = time.monotonic()
        if now - self._last_sent < MIN_INTERVAL_SECONDS:
            return
        self._last_sent = now
        self._send({"input": input_level, "output": output_level})

    def _send(self, message: dict) -> None:
        process = self._process
        if process is None:
            return
        self._write(process, message)

    def _write(self, process: subprocess.Popen[str], message: dict) -> None:
        with self._lock:
            try:
                if process.stdin is None or process.stdin.closed:
                    return
                process.stdin.write(json.dumps(message) + "\n")
                process.stdin.flush()
            except (OSError, ValueError):
                # The orb died. Stop trying, and let Nexus carry on.
                logger.debug("Orb pipe closed", exc_info=True)
                self._process = None


__all__ = ["OrbController"]
