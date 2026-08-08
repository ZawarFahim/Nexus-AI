"""Tray icons, drawn at runtime rather than loaded from files.

Generating them in code means nothing to ship, nothing for PyInstaller to
miss, and no chance of a missing asset leaving Nexus with a blank tray slot. At
this size an icon is a coloured shape, and a colour communicates state faster
than any glyph that fits in sixteen pixels.

Colours are chosen for meaning rather than decoration: grey is dormant, blue
is receiving, amber is working, green is producing output. Each is also
distinguishable in the common forms of colour blindness by differing in
lightness as well as hue.
"""

from __future__ import annotations

import functools
from typing import Final

from PIL import Image, ImageDraw

from nexus.core.state import State

# Windows scales the tray icon down; drawing large and letting it shrink is
# far cleaner than drawing at the final size.
CANVAS: Final = 64

_COLOURS: Final[dict[State, tuple[int, int, int]]] = {
    State.IDLE: (128, 132, 138),
    State.LISTENING: (56, 132, 255),
    State.THINKING: (232, 160, 40),
    State.SPEAKING: (48, 176, 96),
}

_RING: Final = (255, 255, 255, 40)


@functools.lru_cache(maxsize=len(State))
def for_state(state: State) -> Image.Image:
    """Return the tray image for a state.

    Cached because pystray asks for the icon on every update, and redrawing
    four fixed images repeatedly would be wasted work.
    """
    image = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    colour = _COLOURS[state]
    margin = 6
    draw.ellipse((margin, margin, CANVAS - margin, CANVAS - margin), fill=(*colour, 255))

    # A faint inner ring keeps the shape readable against both light and dark
    # taskbars, where a flat disc can otherwise disappear.
    inset = margin + 7
    draw.ellipse((inset, inset, CANVAS - inset, CANVAS - inset), outline=_RING, width=3)

    if state is State.LISTENING:
        # A dot in the centre reads as "receiving" and, more importantly,
        # distinguishes this state without relying on colour alone.
        centre = CANVAS // 2
        radius = 7
        draw.ellipse(
            (centre - radius, centre - radius, centre + radius, centre + radius),
            fill=(255, 255, 255, 230),
        )

    return image


def tooltip(state: State, *, hands_free: bool) -> str:
    """Text shown when hovering over the tray icon."""
    labels = {
        State.IDLE: "Nexus - ready",
        State.LISTENING: "Nexus - listening",
        State.THINKING: "Nexus - thinking",
        State.SPEAKING: "Nexus - speaking",
    }
    suffix = " (hands-free)" if hands_free else ""
    return labels[state] + suffix
