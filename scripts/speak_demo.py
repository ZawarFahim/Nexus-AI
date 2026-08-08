"""Manual check for speech synthesis.

Run from the repository root::

    python -m scripts.speak_demo                  # interactive
    python -m scripts.speak_demo --compare        # hear each installed voice

Type text and Nexus speaks it. Blank line to quit.
"""

from __future__ import annotations

import argparse
import time

from nexus.core import logging as nexus_logging
from nexus.core import paths
from nexus.core.config import load_settings
from nexus.tts.piper import PiperVoice, TTSError

SAMPLE = (
    "Hey, I'm Nexus. I'm running entirely on your machine right now, and nothing "
    "you say leaves this computer unless you ask me a question. What would you "
    "like to talk about?"
)


def installed_voices() -> list[str]:
    """Voice names present in the voices directory."""
    return sorted(p.stem for p in paths.voices_dir().glob("*.onnx"))


def compare(settings) -> None:
    """Speak the same line in every installed voice."""
    names = installed_voices()
    if not names:
        print("No voices installed. Run: python -m scripts.setup")
        return

    for name in names:
        print(f"\n--- {name} ---")
        with PiperVoice(voice=name, output_device=settings.output_device) as voice:
            started = time.perf_counter()
            voice.speak(SAMPLE)
            print(f"    spoken in {(time.perf_counter() - started):.1f}s")

    print(f"\nTo choose one, set NEXUS_VOICE in .env. Currently: {settings.voice}")


def interactive(settings) -> None:
    """Speak whatever is typed."""
    with PiperVoice(
        voice=settings.voice,
        output_device=settings.output_device,
        speed=settings.speech_speed,
    ) as voice:
        print("Nexus speech test")
        print(f"  voice   : {voice.name} @ {voice.sample_rate} Hz")
        print(f"  speaker : {voice.output_device}")
        print("  Type something for Nexus to say. Blank line to quit.\n")

        while True:
            try:
                text = input("say> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not text:
                break

            started = time.perf_counter()
            voice.speak(text)
            print(f"     [{(time.perf_counter() - started):.1f}s]\n")

    print("Goodbye.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compare", action="store_true", help="hear every installed voice")
    args = parser.parse_args()

    settings = load_settings()
    nexus_logging.configure(settings.log_level)

    try:
        if args.compare:
            compare(settings)
        else:
            interactive(settings)
    except TTSError as exc:
        print(f"error: {exc}")


if __name__ == "__main__":
    main()
