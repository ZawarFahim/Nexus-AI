"""The setup dialogs, driven the way a user drives them.

These are slow and awkward compared with the rest of the suite -- they build
real windows and pump a real event loop -- and they exist because the bug they
cover could not be caught any other way. Validating an API key ran on a worker
thread that then called back into Tk, which tkinter refuses from any thread but
its own unless the main thread is in ``mainloop``. These dialogs block in
``wait_window`` instead, so the call raised, the worker died, and setup sat on
"Checking..." until the user gave up. Every unit around it passed.
"""

from __future__ import annotations

import time

import pytest

tkinter = pytest.importorskip("tkinter")

from nexus.ui.setup import KeyRequest  # noqa: E402

WATCHDOG_SECONDS = 20


@pytest.fixture()
def setup_ui():
    """A real ``WindowSetup``, skipped where no display exists."""
    from nexus.ui.dialogs import WindowSetup

    ui = WindowSetup()
    try:
        ui._ensure_root()
    except tkinter.TclError as exc:  # pragma: no cover -- headless CI
        pytest.skip(f"No display: {exc}")
    yield ui
    ui.close()


def _descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from _descendants(child)


def _find(root, kind):
    """The first widget of ``kind`` under ``root``, or None."""
    return next((w for w in _descendants(root) if isinstance(w, kind)), None)


def _watchdog(root) -> None:
    """Tear the dialog down if it outstays its welcome.

    ``root.quit`` cannot do this: it ends ``mainloop``, and these dialogs block
    in ``wait_window``. Destroying the window is the only thing that returns
    control, and without it a regression hangs the suite instead of failing it
    -- which is the same shape as the bug being tested.
    """

    def fire() -> None:
        toplevel = _find(root, tkinter.Toplevel)
        if toplevel is not None:
            toplevel.destroy()

    root.after(WATCHDOG_SECONDS * 1000, fire)


def _drive(root, typed: str) -> None:
    """Type a key into the dialog and press its button, once both exist.

    Runs on the main thread via ``after``, which is how a real click arrives.
    """
    from tkinter import ttk

    def attempt() -> None:
        entry = _find(root, ttk.Entry)
        button = _find(root, ttk.Button)
        if entry is None or button is None:
            root.after(20, attempt)
            return
        entry.insert(0, typed)
        button.invoke()

    root.after(50, attempt)


def test_ask_key_returns_a_key_the_validator_accepts(setup_ui):
    """The whole point: a good key must end the dialog rather than hang it.

    Fails against the original implementation -- the worker raised
    ``RuntimeError: main thread is not in main loop`` and nothing ever closed
    the window, so the watchdog fires and ``ask_key`` returns None.
    """
    root = setup_ui._ensure_root()
    checked: list[str] = []

    def validate(candidate: str) -> str:
        # Slow enough that the result genuinely lands on the worker thread
        # rather than before the dialog has finished being built.
        time.sleep(0.2)
        checked.append(candidate)
        return ""

    _drive(root, "gsk_good_key")
    _watchdog(root)

    started = time.monotonic()
    result = setup_ui.ask_key(KeyRequest(provider="groq", url="", attempts=3), validate)
    elapsed = time.monotonic() - started

    assert checked == ["gsk_good_key"]
    assert result == "gsk_good_key"
    assert elapsed < WATCHDOG_SECONDS, "dialog hung instead of accepting the key"


def test_ask_key_shows_the_problem_and_stays_open(setup_ui):
    """A rejected key has to say why, not close and not freeze."""
    from tkinter import ttk

    root = setup_ui._ensure_root()
    seen: list[str] = []

    def validate(candidate: str) -> str:
        seen.append(candidate)
        return "That key was rejected."

    def close_once_reported() -> None:
        labels = [w for w in _descendants(root) if isinstance(w, ttk.Label)]
        if any("rejected" in w.cget("text") for w in labels):
            # The message reached the user; now leave the way a user would.
            toplevel = _find(root, tkinter.Toplevel)
            if toplevel is not None:
                toplevel.destroy()
            return
        root.after(20, close_once_reported)

    _drive(root, "gsk_bad_key")
    root.after(300, close_once_reported)
    _watchdog(root)

    started = time.monotonic()
    result = setup_ui.ask_key(KeyRequest(provider="groq", url="", attempts=3), validate)

    assert seen == ["gsk_bad_key"]
    assert result is None
    assert time.monotonic() - started < WATCHDOG_SECONDS


def test_a_validator_that_raises_does_not_strand_the_dialog(setup_ui):
    """An unexpected exception must surface, not kill the worker in silence.

    The original code let anything the validator raised escape into a daemon
    thread, where it was invisible and fatal to setup.
    """
    from tkinter import ttk

    root = setup_ui._ensure_root()

    def validate(_candidate: str) -> str:
        raise ConnectionResetError("connection reset by peer")

    reported: list[str] = []

    def close_once_reported() -> None:
        labels = [w for w in _descendants(root) if isinstance(w, ttk.Label)]
        hit = [w.cget("text") for w in labels if "connection reset" in w.cget("text")]
        if hit:
            reported.extend(hit)
            toplevel = _find(root, tkinter.Toplevel)
            if toplevel is not None:
                toplevel.destroy()
            return
        root.after(20, close_once_reported)

    _drive(root, "gsk_key")
    root.after(200, close_once_reported)
    _watchdog(root)

    setup_ui.ask_key(KeyRequest(provider="groq", url="", attempts=3), validate)

    assert reported, "the dialog never told the user the check had failed"
