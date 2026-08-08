"""Nexus, end to end. Hold Alt+Space and talk.

Run from the repository root::

    python -m scripts.talk_demo
    python -m scripts.talk_demo --name Mickey    # change what Nexus calls you
    python -m scripts.talk_demo --set-key        # replace the stored API key
    python -m scripts.talk_demo --forget         # delete the stored name and key

Ctrl+C to exit.
"""

from __future__ import annotations

import argparse
import time

from nexus import app, onboarding
from nexus.core import logging as nexus_logging
from nexus.core import profile as profile_store
from nexus.core.config import load_settings
from nexus.core.protocols import LLMError
from nexus.core.state import State
from nexus.tts.piper import TTSError

_BANNER = {
    State.IDLE: "",
    State.LISTENING: "  [listening]",
    State.THINKING: "  [thinking]",
    State.SPEAKING: "  [speaking]",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Talk to Nexus.")
    parser.add_argument("--name", help="set what Nexus calls you and continue")
    parser.add_argument(
        "--set-key", action="store_true", help="replace the stored API key"
    )
    parser.add_argument(
        "--forget", action="store_true", help="delete the stored name and key"
    )
    args = parser.parse_args()

    settings = load_settings()
    nexus_logging.configure(settings.log_level)

    if args.forget:
        onboarding.forget()
        onboarding.forget_api_key(settings)
        print(f"Forgot everything stored in {profile_store.data_dir()}")
        return

    if args.set_key:
        onboarding.forget_api_key(settings)

    profile = onboarding.set_name(args.name) if args.name else onboarding.ensure_profile()

    try:
        api_key = onboarding.ensure_api_key(settings)
    except onboarding.SetupAbandoned as exc:
        print(f"\n{exc}")
        return

    try:
        components = app.build(settings, profile=profile, api_key=api_key)
    except LLMError as exc:
        print(f"error: {exc}")
        return

    def on_state(state: State) -> None:
        if state is not State.IDLE:
            suffix = "  (hands-free)" if components.hands_free.enabled else ""
            print(_BANNER[state] + suffix, flush=True)

    components.state.subscribe(on_state)

    print("Nexus")
    print("  loading models, this takes a few seconds...", flush=True)

    try:
        app.start(components)
    except (TTSError, RuntimeError) as exc:
        print(f"error: {exc}")
        return

    print(f"  calling you: {profile.name or '(no name set)'}")
    print(f"  hearing  : {components.transcriber.profile}")
    print(f"  voice    : {components.voice.name}")
    print(f"  mic      : {components.recorder.device}")
    print(f"  speaker  : {components.voice.output_device}")
    print("\n  Alt+Space        hold to talk")
    print("  Ctrl+Alt+Space   toggle hands-free mode (just talk)")
    print("  Ctrl+C           quit\n")

    try:
        while True:
            time.sleep(0.3)
            timing = components.pipeline.last_timing
            if timing is not None and timing.total_to_speech_ms:
                components.pipeline.last_timing = None
                print(f'  you > "{timing.heard}"', flush=True)
                print(f'  Nexus  > "{timing.reply}"', flush=True)
                print(
                    f"      [heard in {timing.transcribe_ms:.0f} ms"
                    f" | first token {timing.first_token_ms:.0f} ms"
                    f" | SPOKE AT {timing.first_sentence_ms:.0f} ms"
                    f" | {timing.words} words"
                    f" | history {timing.history_turns} turns]\n",
                    flush=True,
                )
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        app.shutdown(components)


if __name__ == "__main__":
    main()
