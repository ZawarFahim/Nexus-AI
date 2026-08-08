"""Manual check for the push-to-talk hotkey.

Run from the repository root::

    python -m scripts.hotkey_demo

Hold Alt+Space and watch the timings. Press Ctrl+C to exit.
"""

from __future__ import annotations

import logging
import time

from nexus.input.hotkey import PushToTalkHotkey

_pressed_at: float | None = None


def on_press() -> None:
    global _pressed_at
    _pressed_at = time.perf_counter()
    print("\n[HELD]     listening...", flush=True)


def on_release() -> None:
    held = time.perf_counter() - (_pressed_at or time.perf_counter())
    print(f"[RELEASED] held for {held:.2f}s", flush=True)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)-8s %(name)s: %(message)s"
    )

    print("Nexus hotkey test")
    print("  1. Hold Alt+Space  -> [HELD] appears, no grey system menu")
    print("  2. Release         -> [RELEASED] with a duration")
    print("  3. Hold for 3s     -> exactly one [HELD], not a repeat storm")
    print("  4. Type normally   -> other keys are unaffected")
    print("  Ctrl+C to quit.\n")

    with PushToTalkHotkey(on_press=on_press, on_release=on_release):
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\nShutting down.")


if __name__ == "__main__":
    main()
