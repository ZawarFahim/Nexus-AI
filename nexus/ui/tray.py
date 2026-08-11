"""System tray presence.

Nexus has no window, so the tray icon is the entire user interface: the only
indication that it is running, the only feedback that it heard you, and the
only way to quit it. That makes state visibility the point rather than a
nicety -- without it, a missed hotkey and a broken microphone look identical.

pystray requires its event loop on the main thread on Windows, so the tray
owns the main thread and everything else runs on the background threads set
up by :mod:`nexus.app`.
"""

from __future__ import annotations

import logging
import threading
import webbrowser
from collections.abc import Callable, Sequence
from typing import Final

import pystray

from nexus.app import Components
from nexus.core.state import State
from nexus.ui import icons

logger = logging.getLogger(__name__)

PROJECT_URL: Final = "https://github.com/abdullah61305/Nexus"


class TrayApp:
    """Runs Nexus with a system tray icon.

    Args:
        components: An already-started Nexus.
        on_quit: Called on the way out, before the icon disappears.
        on_change_name: Opens whatever flow changes the stored name. Omit to
            hide the menu entry.
        on_change_key: Opens whatever flow replaces the API key.
        add_provider_options: Services that can still be added, as
            ``(name, label)`` pairs, paired with ``on_add_provider``. Empty
            hides the entry, which is what happens once all are configured.
        on_add_provider: Called with a provider name to set one up.
        announce_on_start: Show a notification saying where the icon is.
    """

    def __init__(
        self,
        components: Components,
        *,
        on_quit: Callable[[], None] | None = None,
        on_change_name: Callable[[], None] | None = None,
        on_change_key: Callable[[], None] | None = None,
        add_provider_options: Sequence[tuple[str, str]] = (),
        on_add_provider: Callable[[str], None] | None = None,
        on_open_ui: Callable[[], None] | None = None,
        announce_on_start: bool = True,
    ) -> None:
        self._components = components
        self._on_quit = on_quit
        self._on_change_name = on_change_name
        self._on_change_key = on_change_key
        self._add_provider_options = tuple(add_provider_options)
        self._on_add_provider = on_add_provider
        self._on_open_ui = on_open_ui
        self._announce_on_start = announce_on_start

        self._icon = pystray.Icon(
            "ev",
            icon=icons.for_state(State.IDLE),
            title=icons.tooltip(State.IDLE, hands_free=False),
            menu=self._build_menu(),
        )
        components.state.subscribe(self._on_state_change)

    # -- menu ---------------------------------------------------------------

    def _build_menu(self) -> pystray.Menu:
        items: list[pystray.MenuItem] = []
        
        if self._on_open_ui is not None:
            items.append(pystray.MenuItem("Open Interface", self._open_ui))
            items.append(pystray.Menu.SEPARATOR)
            
        items.extend([
            pystray.MenuItem(
                "Hands-free mode",
                self._toggle_hands_free,
                checked=lambda _item: self._components.hands_free.enabled,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(self._status_text, None, enabled=False),
            pystray.Menu.SEPARATOR,
        ])

        if self._on_change_name is not None:
            items.append(pystray.MenuItem("Change my name...", self._change_name))
        if self._on_change_key is not None:
            items.append(pystray.MenuItem("Change API key...", self._change_key))

        # Each service has its own free allowance, so adding one is how a user
        # who has run out for the day keeps going instead of waiting.
        if self._on_add_provider is not None and self._add_provider_options:
            items.append(
                pystray.MenuItem(
                    "Add more free usage",
                    pystray.Menu(
                        *(
                            pystray.MenuItem(label, self._adder(name))
                            for name, label in self._add_provider_options
                        )
                    ),
                )
            )

        items += [
            pystray.MenuItem("Open project page", self._open_project),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit Nexus", self._quit),
        ]
        return pystray.Menu(*items)

    def _status_text(self, _item: object) -> str:
        """A disabled menu entry showing what Nexus is doing and how to talk."""
        state = self._components.state.current
        readable = {
            State.IDLE: "Ready",
            State.LISTENING: "Listening...",
            State.THINKING: "Thinking...",
            State.SPEAKING: "Speaking...",
        }[state]
        return f"{readable}   (hold Alt+Space)"

    # -- actions ------------------------------------------------------------

    def _toggle_hands_free(self, _icon: object = None, _item: object = None) -> None:
        if self._components.hands_free.enabled:
            self._components.pipeline.abort()
        self._components.hands_free.toggle()
        self._refresh()

    def _open_ui(self, _icon: object = None, _item: object = None) -> None:
        if self._on_open_ui is not None:
            self._on_open_ui()

    def _change_name(self, _icon: object = None, _item: object = None) -> None:
        self._run_detached(self._on_change_name)

    def _change_key(self, _icon: object = None, _item: object = None) -> None:
        self._run_detached(self._on_change_key)

    def _adder(self, provider_name: str) -> Callable[[object, object], None]:
        """Build a menu callback that sets up one named provider."""

        def action(_icon: object = None, _item: object = None) -> None:
            handler = self._on_add_provider
            if handler is not None:
                self._run_detached(lambda: handler(provider_name))

        return action

    def _open_project(self, _icon: object = None, _item: object = None) -> None:
        webbrowser.open(PROJECT_URL)

    def _quit(self, _icon: object = None, _item: object = None) -> None:
        logger.info("Quit requested from the tray")
        if self._on_quit is not None:
            self._on_quit()
        self._icon.stop()

    @staticmethod
    def _run_detached(action: Callable[[], None] | None) -> None:
        """Run a menu action off the tray thread.

        Menu callbacks run on the thread pumping tray messages. Anything that
        blocks there freezes the icon, and settings flows may wait on the user.
        """
        if action is None:
            return
        threading.Thread(target=action, name="ev-tray-action", daemon=True).start()

    # -- state --------------------------------------------------------------

    def _on_state_change(self, state: State) -> None:
        """Reflect Nexus's state in the icon. Called from whichever thread moved it."""
        try:
            self._icon.icon = icons.for_state(state)
            self._icon.title = icons.tooltip(
                state, hands_free=self._components.hands_free.enabled
            )
        except Exception:  # noqa: BLE001 -- a cosmetic update must never break Nexus
            logger.debug("Could not update the tray icon", exc_info=True)

    def _refresh(self) -> None:
        self._on_state_change(self._components.state.current)
        self._icon.update_menu()

    # -- lifecycle ----------------------------------------------------------

    def run(self) -> None:
        """Show the icon and block until Nexus is quit."""
        self._icon.run(setup=self._announce)

    def _announce(self, icon: pystray.Icon) -> None:
        """Point the user at the tray icon once it exists.

        Windows 11 hides newly registered tray icons behind the overflow
        chevron and no longer lets an application pin itself. Without this,
        a first-time user sees nothing happen and concludes Nexus failed to
        start. The notification is the only remaining way to say where it
        went.
        """
        icon.visible = True
        if not self._announce_on_start:
            return
        try:
            icon.notify(
                "Nexus is running in your system tray. If you cannot see the "
                "icon, click the arrow next to the clock.",
                "Nexus is ready",
            )
        except Exception:  # noqa: BLE001 -- notifications are not essential
            logger.debug("Could not show the startup notification", exc_info=True)
