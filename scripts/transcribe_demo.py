"""Manual check for speech-to-text.

Run from the repository root::

    python -m scripts.transcribe_demo

The model is downloaded on first run, which takes a few minutes. Hold
Alt+Space, speak, release, and your words appear. Ctrl+C to exit.
"""

from __future__ import annotations

import time

from nexus.audio.recorder import AudioRecorder
from nexus.core import logging as nexus_logging
from nexus.core.config import load_settings
from nexus.input.hotkey import PushToTalkHotkey
from nexus.stt.whisper import WhisperTranscriber


def main() -> None:
    settings = load_settings()
    nexus_logging.configure(settings.log_level)

    transcriber = WhisperTranscriber(device_preference=settings.device)
    recorder = AudioRecorder(
        device_name=settings.input_device,
        always_on=settings.always_on_mic,
    )

    print("Nexus transcription test")
    print(f"  profile: {transcriber.profile}")
    print("  loading model (first run downloads weights; be patient)...", flush=True)

    transcriber.load()
    print("  ready.\n")

    def on_press() -> None:
        recorder.begin_capture()
        print("\n[REC]  listening...", flush=True)

    def on_release() -> None:
        clip = recorder.end_capture()
        if clip is None:
            print("[SKIP] too short to be intentional", flush=True)
            return

        if clip.is_silent:
            print(f"[QUIET] peak {clip.peak:.2f} -- check the mic is unmuted", flush=True)

        transcript = transcriber.transcribe(clip)
        if transcript.is_empty:
            print("[EMPTY] no speech recognised", flush=True)
            return

        realtime = clip.duration / transcript.latency if transcript.latency else 0.0
        print(f'[HEARD] "{transcript.text}"', flush=True)
        print(
            f"        {clip.duration:.2f}s audio -> {transcript.latency * 1000:.0f} ms "
            f"({realtime:.1f}x realtime, lang={transcript.language})",
            flush=True,
        )

    with recorder, PushToTalkHotkey(on_press=on_press, on_release=on_release):
        print("  Hold Alt+Space, speak, release. Ctrl+C to quit.\n")
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\nShutting down.")


if __name__ == "__main__":
    main()
