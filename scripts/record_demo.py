"""Manual check for microphone capture driven by the push-to-talk hotkey.

Run from the repository root::

    python -m scripts.record_demo

Hold Alt+Space, speak, release. Each capture is written to ``recordings/``
so you can play it back and judge the quality yourself. Ctrl+C to exit.
"""

from __future__ import annotations

import time
import wave
from datetime import datetime
from pathlib import Path

import numpy as np

from nexus.audio.recorder import AudioClip, AudioRecorder
from nexus.core import logging as nexus_logging
from nexus.core import paths
from nexus.core.config import load_settings
from nexus.input.hotkey import PushToTalkHotkey

OUTPUT_DIR = paths.downloads_dir() / "recordings"


def write_wav(clip: AudioClip, path: Path) -> None:
    """Save a clip as a 16-bit PCM wav.

    Nexus keeps audio as float32 because that is what Whisper consumes, but wav
    players expect integer PCM, so this narrows it for listening only.
    """
    pcm = np.clip(clip.samples, -1.0, 1.0)
    pcm = (pcm * np.iinfo(np.int16).max).astype(np.int16)

    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(clip.sample_rate)
        handle.writeframes(pcm.tobytes())


def level_meter(peak: float, width: int = 24) -> str:
    """Render a peak level as a text bar, so a dead mic is obvious."""
    filled = min(width, int(peak * width))
    return f"[{'#' * filled}{'-' * (width - filled)}]"


def main() -> None:
    settings = load_settings()
    nexus_logging.configure(settings.log_level)

    recorder = AudioRecorder(
        device_name=settings.input_device,
        always_on=settings.always_on_mic,
    )
    started_at = 0.0

    def on_press() -> None:
        nonlocal started_at
        started_at = time.perf_counter()
        recorder.begin_capture()
        print("\n[REC]  listening...", flush=True)

    def on_release() -> None:
        clip = recorder.end_capture()
        elapsed = (time.perf_counter() - started_at) * 1000

        if clip is None:
            print("[SKIP] too short to be intentional", flush=True)
            return

        # Millisecond precision: two captures inside the same second would
        # otherwise silently overwrite each other.
        stamp = f"{datetime.now():%Y%m%d-%H%M%S-%f}"[:-3]
        path = OUTPUT_DIR / f"{stamp}.wav"
        write_wav(clip, path)

        print(
            f"[SAVE] {clip.duration:5.2f}s  "
            f"peak {clip.peak:4.2f} {level_meter(clip.peak)}  "
            f"({elapsed:.0f} ms held)",
            flush=True,
        )
        print(f"       {path}", flush=True)

        if clip.is_silent:
            print(
                "       WARNING: almost no signal. Check the mic is unmuted "
                "and set NEXUS_INPUT_DEVICE in .env if the wrong device is in use.",
                flush=True,
            )

    with recorder, PushToTalkHotkey(on_press=on_press, on_release=on_release):
        print("Nexus recording test")
        print(f"  device : {recorder.device}")
        print(f"  mode   : {'always-on + pre-roll' if settings.always_on_mic else 'open on demand'}")
        print(f"  output : {OUTPUT_DIR}")
        print("\n  Hold Alt+Space, speak, release. Ctrl+C to quit.\n")
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\nShutting down.")


if __name__ == "__main__":
    main()
