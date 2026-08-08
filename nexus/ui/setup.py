"""The questions first-run setup has to ask, independent of how they are asked.

A packaged ``Nexus.exe`` is a windowed program with no console attached. Printing
a question there is not merely ugly -- the text goes nowhere, ``input`` reads
end-of-file immediately, and the user sees an icon that flashes and vanishes.
So the same flow has to work through dialogs.

Rather than duplicating the rules in a console version and a window version,
setup depends on this protocol and the caller supplies an implementation. The
console one below stays useful: it is what ``--console`` and development use,
and it keeps the flow testable without a display.

The wording lives here too, so both front ends say the same thing.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from nexus.core import assets

logger = logging.getLogger(__name__)

NAME_TITLE = "Hi, I'm Nexus."
NAME_BODY = "What should I call you?"
NAME_HINT = "You can leave this blank."

KEY_TITLE = "One more thing"
KEY_BODY = """\
I need a free key to think with.

  1.  Open {url}
  2.  Sign in with Google or GitHub. It takes about thirty seconds,
      and no card is required.
  3.  Click "Create API Key" and give it any name you like.
  4.  Copy the key and paste it below.

Your key is encrypted with your Windows account and stored on this
computer only. It is never sent anywhere except {provider}."""

DOWNLOAD_TITLE = "Getting ready"
DOWNLOAD_BODY = """\
I'm downloading the voice and speech files I need. This happens once.

If it stops partway, just start me again -- I'll continue from where
I left off rather than starting over."""


@dataclass(frozen=True, slots=True)
class KeyRequest:
    """Everything needed to ask for an API key.

    Attributes:
        provider: Provider name, for display.
        url: Where the user gets a key.
        attempts: How many tries before giving up.
    """

    provider: str
    url: str
    attempts: int = 3

    @property
    def body(self) -> str:
        """The explanation shown above the input."""
        return KEY_BODY.format(url=self.url, provider=self.provider.title())


# Returns an empty string when the key works, or a sentence explaining what is
# wrong with it. Passed into the UI so that a window can validate in place and
# let the user correct a typo, rather than closing and reopening.
Validator = Callable[[str], str]


@runtime_checkable
class SetupUI(Protocol):
    """How setup talks to the user."""

    def ask_name(self) -> str | None:
        """Ask what Nexus should call them.

        Returns:
            The typed name, an empty string to go without one, or ``None`` if
            the user closed the prompt. Both blank answers are fine: Nexus works
            without a name.
        """
        ...

    def ask_key(self, request: KeyRequest, validate: Validator) -> str | None:
        """Ask for an API key, retrying until one validates.

        The implementation calls ``validate`` on each attempt and shows what
        it returns. Keys must never be echoed, logged, or written anywhere but
        the encrypted store.

        Returns:
            A validated key, or ``None`` if the user gave up.
        """
        ...

    def fetch_assets(self, items: Sequence[assets.Asset]) -> None:
        """Download missing files, showing progress.

        Raises:
            AssetError: If a download failed or was cancelled.
        """
        ...

    def say(self, message: str) -> None:
        """Report something that needs no answer."""
        ...

    def close(self) -> None:
        """Release anything the front end is holding."""
        ...


class ConsoleSetup:
    """Setup through a terminal. Satisfies :class:`SetupUI`.

    Used by ``--console`` and by anyone running from a checkout, where a
    terminal is already open and a dialog would be an interruption.
    """

    def ask_name(self) -> str | None:
        print(f"\n{NAME_TITLE}\n\n{NAME_BODY}\n({NAME_HINT})\n")
        try:
            return input("  Your name: ")
        except (EOFError, KeyboardInterrupt):
            print()
            return None

    def ask_key(self, request: KeyRequest, validate: Validator) -> str | None:
        # Imported lazily: getpass touches the terminal at import time on some
        # platforms, and a windowed run has no terminal to touch.
        import getpass

        print(f"\n{KEY_TITLE}\n\n{request.body}\n")

        for attempt in range(1, request.attempts + 1):
            try:
                # Hidden as it is typed. Pasting still works.
                key = getpass.getpass("  Paste your key (hidden): ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return None

            if not key:
                print("  I need a key to answer questions. Ctrl+C to quit.\n")
                continue

            print("  Checking...", end="", flush=True)
            problem = validate(key)
            if not problem:
                print(" that works.")
                return key

            print(f"\r  {problem}          ")
            if attempt < request.attempts:
                print()

        return None

    def fetch_assets(self, items: Sequence[assets.Asset]) -> None:
        approx = sum(item.approx_bytes for item in items) / 1e6
        print(f"\n{DOWNLOAD_TITLE}\n\n{DOWNLOAD_BODY}\n")
        print(f"  About {approx:.0f} MB to fetch.")
        assets.install(items, on_progress=_ConsoleProgress())

    def say(self, message: str) -> None:
        print(f"\n  {message}")

    def close(self) -> None:
        return None


class _ConsoleProgress:
    """Prints one self-overwriting progress line, throttled to stay readable."""

    def __init__(self, interval: float = 0.2) -> None:
        self._interval = interval
        self._last = 0.0

    def __call__(self, progress: assets.Progress) -> None:
        import time

        now = time.monotonic()
        finished = progress.label == "done"
        if not finished and now - self._last < self._interval:
            return
        self._last = now

        filled = int(progress.fraction * 24)
        bar = "#" * filled + "." * (24 - filled)
        print(
            f"\r  [{bar}] {progress.fraction:>4.0%}  "
            f"{progress.done_bytes / 1e6:.0f} / {progress.total_bytes / 1e6:.0f} MB  "
            f"{progress.label:<14}",
            end="",
            flush=True,
        )
        if finished:
            print()
