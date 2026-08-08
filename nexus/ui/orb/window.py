"""The floating orb window, run as its own process.

Separate from Nexus for two reasons. The tray icon owns the main thread and a
webview wants it too, and a graphics stack failing is not a good reason for a
voice companion to stop answering -- a crash here costs the picture and
nothing else.

State arrives as one JSON object per line on stdin::

    {"state": "listening", "input": 0.4, "output": 0.0}
    {"quit": true}

Two window properties are not cosmetic. It must never take focus: Nexus's
browser control acts on whichever window is in front, so an orb that stole
that would make "scroll down" target the orb instead of the page. And it must
be click-through, or it would swallow clicks on whatever it floats over.
"""

from __future__ import annotations

import ctypes
import json
import logging
import sys
from ctypes import wintypes as wt
from typing import Final

logger = logging.getLogger(__name__)

# Small, because the window is an opaque tile and cannot currently be made
# otherwise -- see _make_click_through. At this size the glow fills most of it
# and it reads as a deliberate widget rather than a stray black rectangle.
WIDTH: Final = 180
HEIGHT: Final = 180

# Bottom-right, above the taskbar and near the tray icon, where a small status
# widget is expected. Bottom-centre put it over whatever the user was reading.
EDGE_MARGIN: Final = 24
BOTTOM_MARGIN: Final = 72

# Extended window styles. LAYERED enables per-pixel alpha, TRANSPARENT makes
# the window ignore the mouse entirely, NOACTIVATE stops it ever becoming the
# foreground window, and TOOLWINDOW keeps it out of Alt-Tab.
WS_EX_LAYERED: Final = 0x00080000
WS_EX_TRANSPARENT: Final = 0x00000020
WS_EX_NOACTIVATE: Final = 0x08000000
WS_EX_TOOLWINDOW: Final = 0x00000080
GWL_EXSTYLE: Final = -20

# Every pixel of exactly this colour is punched out of the window. WebView2
# paints its own opaque background regardless of what the page asks for, so
# asking politely for transparency leaves a white card floating on the desktop.
# A colour key is cruder and works: black suits it, because the orb is a glow
# on black and the parts that should disappear are already black.
LWA_COLORKEY: Final = 0x00000001
TRANSPARENT_KEY: Final = 0x000000  # COLORREF, black


def _make_click_through(title: str) -> None:
    """Apply the styles that keep the orb out of the user's way."""
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, title)
        if not hwnd:
            logger.warning("Could not find the orb window to restyle")
            return

        get_long = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
        set_long = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
        get_long.restype = ctypes.c_ssize_t
        set_long.restype = ctypes.c_ssize_t
        set_long.argtypes = (wt.HWND, ctypes.c_int, ctypes.c_ssize_t)

        style = get_long(hwnd, GWL_EXSTYLE)
        set_long(
            hwnd,
            GWL_EXSTYLE,
            style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW,
        )

        # Clip the window to a circle. A colour key was tried first and does
        # not work: WebView2 composites on the GPU, and hardware-composited
        # pixels ignore a layered window's key, so the orb sat in an opaque
        # card. Clipping happens in the window manager instead, where what the
        # page rendered with is nobody's business -- the corners are simply
        # not part of the window, and what is behind shows through.
        gdi32 = ctypes.windll.gdi32
        gdi32.CreateEllipticRgn.restype = wt.HANDLE
        region = gdi32.CreateEllipticRgn(0, 0, WIDTH, HEIGHT)
        user32.SetWindowRgn(hwnd, region, True)
    except Exception:  # noqa: BLE001 -- the orb is decoration; never fatal
        logger.warning("Could not restyle the orb window", exc_info=True)


def run() -> int:
    """Show the orb and pump state from stdin until told to stop."""
    import os

    # WebView2 composites through the GPU by default, and hardware-composited
    # content ignores a layered window's colour key -- the orb would sit in an
    # opaque card. Rendering to a bitmap instead puts the pixels somewhere the
    # key applies. Must be set before the runtime is created.
    os.environ.setdefault(
        "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS",
        "--disable-gpu-compositing --enable-transparent-visuals",
    )

    import webview

    from nexus.core import paths

    page = paths.bundle_dir() / "nexus" / "ui" / "orb" / "index.html"
    if not page.is_file():
        print(f"orb page missing: {page}", file=sys.stderr)
        return 1

    title = "Nexus Orb"
    window = webview.create_window(
        title,
        str(page),
        width=WIDTH,
        height=HEIGHT,
        frameless=True,
        easy_drag=False,
        on_top=True,
        transparent=True,
        resizable=False,
        focus=False,
        background_color="#000000",
    )

    def pump() -> None:
        """Feed the page from stdin. Ends when Nexus closes the pipe.

        Run by ``webview.start`` once the window exists. Doing this from a
        thread started earlier restyles a window that is not there yet, and
        can tear one down while it is still initialising.
        """
        _make_click_through(title)
        _place(window)
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except ValueError:
                continue
            if message.get("quit"):
                break
            try:
                window.evaluate_js(f"window.nexusUpdate({json.dumps(message)})")
            except Exception:  # noqa: BLE001 -- a closing window races the pipe
                break
        try:
            window.destroy()
        except Exception:  # noqa: BLE001
            pass

    webview.start(pump, private_mode=True)
    return 0


def _place(window) -> None:
    """Put the orb in the bottom-right corner of the primary screen."""
    try:
        user32 = ctypes.windll.user32
        screen_width = user32.GetSystemMetrics(0)
        screen_height = user32.GetSystemMetrics(1)
        window.move(
            screen_width - WIDTH - EDGE_MARGIN,
            screen_height - HEIGHT - BOTTOM_MARGIN,
        )
    except Exception:  # noqa: BLE001
        logger.debug("Could not position the orb", exc_info=True)


if __name__ == "__main__":
    sys.exit(run())
