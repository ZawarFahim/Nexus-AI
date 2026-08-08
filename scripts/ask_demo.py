"""Ask Nexus something by typing, with every tool available, but no speech.

Run from the repository root::

    python -m scripts.ask_demo "what am I looking at"
    python -m scripts.ask_demo "open youtube"
    python -m scripts.ask_demo "scroll down twice"
    python -m scripts.ask_demo --save shot.png    # see what Nexus sees
    python -m scripts.ask_demo --no-tools         # prove it declines instead

Exists to separate failures that look identical through a microphone: a
question misheard, a tool the model declined to use, and a tool that ran and
failed. Everything except speech runs here, and the log line for each tool
call says which of the three happened.
"""

from __future__ import annotations

import argparse
import base64
import sys
import time
from pathlib import Path

from nexus import app, onboarding
from nexus.core import logging as nexus_logging
from nexus.core.config import load_settings
from nexus.core.protocols import LLMError
from nexus.llm.conversation import Conversation
from nexus.llm.factory import create_provider
from nexus.llm.prompt import build_system_prompt
from nexus.tools import screen

DEFAULT_QUESTION = "What am I looking at right now?"


def save_capture(path: Path) -> None:
    """Write the screenshot Nexus would send, so it can be inspected."""
    data_uri, width, height = screen.capture()
    payload = base64.b64decode(data_uri.split(",", 1)[1])
    path.write_bytes(payload)
    print(f"Saved {width}x{height}, {len(payload) / 1024:.0f} KB to {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?", default=DEFAULT_QUESTION)
    parser.add_argument("--save", type=Path, help="write the screenshot here and exit")
    parser.add_argument(
        "--no-tools", action="store_true", help="ask without offering the screen tool"
    )
    parser.add_argument(
        "--poisoned",
        action="store_true",
        help="seed the history with Nexus having denied it can see, which is how "
        "a single missed question used to break every question after it",
    )
    parser.add_argument("--verbose", action="store_true", help="show library logging")
    args = parser.parse_args()

    nexus_logging.configure(
        level="DEBUG" if args.verbose else "INFO",
        quiet_libraries=not args.verbose,
        to_file=False,
    )

    if args.save:
        save_capture(args.save)
        return 0

    settings = load_settings()
    try:
        api_key = onboarding.ensure_api_key(settings)
    except onboarding.SetupAbandoned as exc:
        print(exc)
        return 1

    # Built the same way the real application builds them, so the demo cannot
    # quietly test a different set of capabilities than Nexus actually has.
    tools = None if args.no_tools else app.build_tools(settings)
    provider = create_provider(settings, api_key)
    conversation = Conversation(
        build_system_prompt(
            can_see_screen=tools is not None and "look_at_screen" in tools.names,
            can_use_browser=tools is not None and "open_in_browser" in tools.names,
        )
    )
    if args.poisoned:
        conversation.add("user", "hey whats on my screen")
        conversation.add("assistant", "I can't see your screen, so I don't know.")
    conversation.add("user", args.question)

    print(f"model:    {provider.name}")
    print(f"tools:    {tools.names if tools else 'none'}")
    print(f"question: {args.question}\n")

    started = time.perf_counter()
    first_token = 0.0
    reply: list[str] = []

    try:
        for fragment in provider.stream_reply(conversation.messages(), tools):
            if not first_token:
                first_token = time.perf_counter() - started
            reply.append(fragment)
            print(fragment, end="", flush=True)
    except LLMError as exc:
        print(f"\n\nFailed: {exc}")
        return 1

    total = time.perf_counter() - started
    words = len("".join(reply).split())
    print(f"\n\nfirst token {first_token * 1000:.0f} ms, total {total:.1f} s, {words} words")
    return 0


if __name__ == "__main__":
    sys.exit(main())
