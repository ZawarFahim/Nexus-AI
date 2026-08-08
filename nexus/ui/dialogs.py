"""First-run setup through windows, for when there is no console to print to.

Satisfies :class:`~nexus.ui.setup.SetupUI`. Tkinter is used deliberately: it is in
the standard library, so it adds no dependency and no unsigned DLL for Windows
code-integrity policies to reject, and it is the toolkit PyInstaller handles
most reliably.

Two rules run through everything here:

**Nothing blocks the event loop.** Validating a key is a network round trip and
downloading is minutes long. Doing either on the UI thread produces a window
Windows paints grey and labels "Not Responding", which reads as a crash. Work
happens on a worker thread.

**Workers hand back data, never Tk calls.** A worker leaves its result in a
plain dict and the main thread polls for it. Calling ``after`` from the worker
is the obvious alternative and it does not work: tkinter refuses calls from
other threads unless the main thread is inside ``mainloop``, and these dialogs
block in ``wait_window``, which pumps events without setting that flag. It
raises ``RuntimeError: main thread is not in main loop`` and kills the worker,
which is how a correct API key came to hang setup forever.

**The key is never displayed.** It is masked as it is typed, kept out of logs,
and handed straight to the encrypted store.
"""

from __future__ import annotations

import logging
import threading
import tkinter as tk
from collections.abc import Sequence
from tkinter import ttk
from typing import Final

from nexus.core import assets
from nexus.core.display import enable_dpi_awareness
from nexus.ui import setup as ui_setup

logger = logging.getLogger(__name__)

APP_TITLE: Final = "Nexus"

# Matches the LISTENING colour of the tray icon, so the two look like one product.
ACCENT: Final = "#3884ff"
MUTED: Final = "#6b7280"

HEADING_FONT: Final = ("Segoe UI", 15)
BODY_FONT: Final = ("Segoe UI", 10)
MONO_FONT: Final = ("Consolas", 10)

PAD: Final = 20
PROGRESS_POLL_MS: Final = 100
CHECK_POLL_MS: Final = 50  # Key validation; low enough to feel immediate.
PROGRESS_SCALE: Final = 1000  # Progressbar wants integers; fractions do not survive.


class WindowSetup:
    """Setup through dialogs. Satisfies :class:`~nexus.ui.setup.SetupUI`.

    One hidden root window is created on demand and reused for every dialog,
    because repeatedly creating and destroying ``Tk`` roots in a single process
    is a known source of crashes. Call :meth:`close` when setup is finished.
    """

    def __init__(self) -> None:
        self._root: tk.Tk | None = None

    # -- plumbing -----------------------------------------------------------

    def _ensure_root(self) -> tk.Tk:
        if self._root is None:
            # Must precede the first window: without it Tk renders at 96 DPI
            # and Windows stretches the result, which on a laptop display looks
            # visibly blurry next to every other program.
            enable_dpi_awareness()
            root = tk.Tk()
            root.withdraw()
            self._root = root
        return self._root

    def _dialog(self, on_close) -> tk.Toplevel:
        """Create a modal, non-resizable dialog wired to ``on_close``."""
        window = tk.Toplevel(self._ensure_root())
        window.title(APP_TITLE)
        window.resizable(False, False)
        window.protocol("WM_DELETE_WINDOW", on_close)
        window.bind("<Escape>", lambda _event: on_close())
        return window

    def _present(self, window: tk.Toplevel) -> None:
        """Centre the dialog, raise it above other windows, and focus it."""
        window.update_idletasks()

        width, height = window.winfo_width(), window.winfo_height()
        x = (window.winfo_screenwidth() - width) // 2
        y = (window.winfo_screenheight() - height) // 3  # Slightly above centre.
        window.geometry(f"+{max(0, x)}+{max(0, y)}")

        # Nexus may be launched from a shortcut while other windows have focus,
        # and a setup prompt hidden behind a browser is a setup prompt nobody
        # completes. Topmost is dropped immediately so it does not hover over
        # everything for the rest of its life.
        window.attributes("-topmost", True)
        window.after(200, lambda: window.attributes("-topmost", False))
        window.focus_force()
        window.grab_set()

    @staticmethod
    def _heading(parent: tk.Misc, text: str) -> ttk.Label:
        return ttk.Label(parent, text=text, font=HEADING_FONT, foreground=ACCENT)

    def close(self) -> None:
        """Destroy the hidden root and every dialog still attached to it."""
        if self._root is not None:
            try:
                self._root.destroy()
            except tk.TclError:
                logger.debug("Root already gone", exc_info=True)
            self._root = None

    # -- questions ----------------------------------------------------------

    def ask_name(self) -> str | None:
        """Ask what Nexus should call them. Returns the name, or None if closed."""
        answer: list[str | None] = [None]

        def cancel() -> None:
            answer[0] = None
            window.destroy()

        def submit(_event: object = None) -> None:
            answer[0] = entry.get()
            window.destroy()

        window = self._dialog(cancel)
        frame = ttk.Frame(window, padding=PAD)
        frame.grid(sticky="nsew")

        self._heading(frame, ui_setup.NAME_TITLE).grid(sticky="w")
        ttk.Label(frame, text=ui_setup.NAME_BODY, font=BODY_FONT).grid(
            sticky="w", pady=(12, 2)
        )

        entry = ttk.Entry(frame, font=BODY_FONT, width=34)
        entry.grid(sticky="ew", pady=(6, 2))
        entry.bind("<Return>", submit)

        ttk.Label(frame, text=ui_setup.NAME_HINT, font=BODY_FONT, foreground=MUTED).grid(
            sticky="w"
        )

        buttons = ttk.Frame(frame)
        buttons.grid(sticky="e", pady=(18, 0))
        ttk.Button(buttons, text="Continue", command=submit).grid(row=0, column=0)

        self._present(window)
        entry.focus_set()
        window.wait_window()
        return answer[0]

    def ask_key(
        self, request: ui_setup.KeyRequest, validate: ui_setup.Validator
    ) -> str | None:
        """Ask for an API key, checking it before accepting.

        Unlike the console flow this does not count attempts. A window can show
        the problem beside the field and let the user fix a typo in place, so
        capping retries would only close a dialog the user is still working in.
        Closing the window is the way out.
        """
        accepted: list[str | None] = [None]
        checking = threading.Event()
        # Written by the worker, read by the poll below. A plain dict rather
        # than a Tk call, because the worker may not touch Tk at all; see the
        # comment on ``poll``.
        outcome: dict[str, tuple[str, str]] = {}

        def cancel() -> None:
            if checking.is_set():
                return  # A validation is in flight; let it land first.
            accepted[0] = None
            window.destroy()

        def finish(key: str, problem: str) -> None:
            checking.clear()
            if not problem:
                accepted[0] = key
                window.destroy()
                return
            status.configure(text=problem, foreground="#c2410c")
            entry.configure(state="normal")
            button.configure(state="normal", text="Continue")
            entry.focus_set()

        def submit(_event: object = None) -> None:
            if checking.is_set():
                return
            key = entry.get().strip()
            if not key:
                status.configure(text="Paste your key here first.", foreground=MUTED)
                return

            checking.set()
            status.configure(text="Checking...", foreground=MUTED)
            entry.configure(state="disabled")
            button.configure(state="disabled", text="Checking")

            def work() -> None:
                try:
                    problem = validate(key)
                except Exception as exc:  # noqa: BLE001 -- must reach the user
                    # A validator that raises anything other than the failure
                    # it documents would otherwise kill this thread silently,
                    # leaving the dialog on "Checking..." with no way forward.
                    logger.exception("Key validation raised")
                    problem = f"Could not check that key: {exc}"
                # Handed over as data. Calling back into Tk from here is what
                # this used to do, and it is not allowed: see ``poll``.
                outcome["result"] = (key, problem)

            threading.Thread(target=work, name="ev-key-check", daemon=True).start()

        def poll() -> None:
            """Deliver a finished validation on the thread Tk belongs to.

            The worker cannot do this itself. Tkinter rejects calls from any
            thread but the one that created the interpreter *unless* the main
            thread is inside ``mainloop``, and this dialog blocks in
            ``wait_window`` instead -- which pumps events but does not set the
            flag tkinter checks. ``window.after`` from the worker therefore
            raised ``RuntimeError: main thread is not in main loop``, killing
            the thread before it could report anything: the user pasted a
            perfectly good key and watched "Checking..." forever.

            Polling from the main thread is how the download dialog below
            already does it, and it is the only arrangement that works here.
            """
            result = outcome.pop("result", None)
            if result is not None:
                finish(*result)
            if window.winfo_exists():
                window.after(CHECK_POLL_MS, poll)

        window = self._dialog(cancel)
        frame = ttk.Frame(window, padding=PAD)
        frame.grid(sticky="nsew")

        self._heading(frame, ui_setup.KEY_TITLE).grid(sticky="w")
        ttk.Label(frame, text=request.body, font=BODY_FONT, justify="left").grid(
            sticky="w", pady=(12, 10)
        )

        # Masked, and never written anywhere but the encrypted store. Pasting
        # with Ctrl+V works as normal.
        entry = ttk.Entry(frame, font=MONO_FONT, width=52, show="•")
        entry.grid(sticky="ew")
        entry.bind("<Return>", submit)

        status = ttk.Label(frame, text="", font=BODY_FONT, foreground=MUTED)
        status.grid(sticky="w", pady=(8, 0))

        buttons = ttk.Frame(frame)
        buttons.grid(sticky="e", pady=(14, 0))
        button = ttk.Button(buttons, text="Continue", command=submit)
        button.grid(row=0, column=0)

        self._present(window)
        entry.focus_set()
        window.after(CHECK_POLL_MS, poll)
        window.wait_window()
        return accepted[0]

    # -- downloading --------------------------------------------------------

    def fetch_assets(self, items: Sequence[assets.Asset]) -> None:
        """Download missing files behind a progress window.

        Raises:
            AssetError: If a download failed or the user cancelled.
        """
        cancelled = threading.Event()
        state: dict[str, object] = {"progress": None, "error": None, "done": False}

        def request_cancel() -> None:
            # Deliberately does not destroy the window. The worker has to notice
            # and unwind first, and tearing down the UI underneath it would
            # leave the poll loop writing to widgets that no longer exist.
            cancelled.set()
            status.configure(text="Stopping...")

        def work() -> None:
            try:
                assets.install(
                    items,
                    on_progress=lambda p: state.__setitem__("progress", p),
                    should_cancel=cancelled.is_set,
                )
            except assets.AssetError as exc:
                state["error"] = exc
            except Exception as exc:  # noqa: BLE001 -- must not kill the thread silently
                logger.exception("Unexpected download failure")
                state["error"] = assets.AssetError(str(exc))
            finally:
                state["done"] = True

        def tick() -> None:
            progress = state["progress"]
            if isinstance(progress, assets.Progress):
                bar.configure(value=progress.fraction * PROGRESS_SCALE)
                if not cancelled.is_set():
                    status.configure(
                        text=f"{progress.done_bytes / 1e6:.0f} of "
                        f"{progress.total_bytes / 1e6:.0f} MB"
                    )
            if state["done"]:
                window.destroy()
                return
            window.after(PROGRESS_POLL_MS, tick)

        window = self._dialog(request_cancel)
        frame = ttk.Frame(window, padding=PAD)
        frame.grid(sticky="nsew")

        self._heading(frame, ui_setup.DOWNLOAD_TITLE).grid(sticky="w")
        ttk.Label(frame, text=ui_setup.DOWNLOAD_BODY, font=BODY_FONT, justify="left").grid(
            sticky="w", pady=(12, 14)
        )

        bar = ttk.Progressbar(frame, maximum=PROGRESS_SCALE, length=420, mode="determinate")
        bar.grid(sticky="ew")

        status = ttk.Label(frame, text="Starting...", font=BODY_FONT, foreground=MUTED)
        status.grid(sticky="w", pady=(8, 0))

        buttons = ttk.Frame(frame)
        buttons.grid(sticky="e", pady=(14, 0))
        ttk.Button(buttons, text="Cancel", command=request_cancel).grid(row=0, column=0)

        threading.Thread(target=work, name="ev-asset-download", daemon=True).start()

        self._present(window)
        window.after(PROGRESS_POLL_MS, tick)
        window.wait_window()

        error = state["error"]
        if isinstance(error, Exception):
            raise error

    # -- telling ------------------------------------------------------------

    def say(self, message: str) -> None:
        """Show a message that needs no answer."""
        from tkinter import messagebox

        self._ensure_root()
        messagebox.showinfo(APP_TITLE, message)
