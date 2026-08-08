"""Manual check for the language model, typed rather than spoken.

Run from the repository root::

    python -m scripts.chat_demo

Type a message and watch the reply stream in. The timing that matters is
"first token", because that is how long Nexus would stay silent before starting
to speak. Blank line or Ctrl+C to exit.
"""

from __future__ import annotations

import time

from nexus.core import logging as nexus_logging
from nexus.core.config import load_settings
from nexus.core.protocols import LLMError
from nexus.llm.conversation import Conversation
from nexus.llm.factory import create_provider
from nexus.llm.prompt import SYSTEM_PROMPT


def main() -> None:
    settings = load_settings()
    nexus_logging.configure(settings.log_level)

    try:
        provider = create_provider(settings)
    except LLMError as exc:
        print(f"error: {exc}")
        return

    conversation = Conversation(SYSTEM_PROMPT)
    provider.warm_up()

    print("Nexus chat test")
    print(f"  provider: {provider.name}")
    print("  Type a message. Blank line to quit.")
    print("  Try a follow-up like 'why?' to check it remembers the last turn.\n")

    while True:
        try:
            prompt = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not prompt:
            break

        conversation.add("user", prompt)
        started = time.perf_counter()
        first_token_at: float | None = None
        reply: list[str] = []

        print("Nexus > ", end="", flush=True)
        try:
            for fragment in provider.stream_reply(conversation.messages()):
                if first_token_at is None:
                    first_token_at = time.perf_counter()
                reply.append(fragment)
                print(fragment, end="", flush=True)
        except LLMError as exc:
            print(f"\nerror: {exc}")
            continue

        total = time.perf_counter() - started
        text = "".join(reply)
        conversation.add("assistant", text)

        first_ms = (first_token_at - started) * 1000 if first_token_at else 0.0
        print(
            f"\n      [first token {first_ms:.0f} ms | complete {total * 1000:.0f} ms "
            f"| {len(text.split())} words | history {len(conversation)} turns]\n"
        )

    print("Goodbye.")


if __name__ == "__main__":
    main()
