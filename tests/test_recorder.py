"""Tests for capture buffering, driven without a microphone.

Covers the tap guard, which was wrong once: it measured the clip including
pre-roll, so a 90 ms brush of the hotkey cleared a 200 ms threshold and would
later have fired a needless transcription and API call.
"""

from __future__ import annotations

import numpy as np

from nexus.audio.recorder import BLOCK_FRAMES, SAMPLE_RATE, AudioClip, AudioRecorder


def block(value: float = 0.1) -> np.ndarray:
    return np.full(BLOCK_FRAMES, value, dtype=np.float32)


def feed(recorder: AudioRecorder, count: int, value: float = 0.1) -> None:
    """Push blocks in as the audio callback would."""
    for _ in range(count):
        recorder._on_audio(  # noqa: SLF001
            block(value).reshape(-1, 1), BLOCK_FRAMES, None, _NoStatus()
        )


class _NoStatus:
    output_underflow = False

    def __bool__(self) -> bool:
        return False


def test_clip_reports_duration_and_peak():
    clip = AudioClip(np.array([0.0, 0.5, -0.75], dtype=np.float32))
    assert clip.peak == 0.75
    assert clip.sample_rate == SAMPLE_RATE
    assert not clip.is_silent


def test_silence_is_flagged():
    assert AudioClip(np.zeros(100, dtype=np.float32)).is_silent


def test_capture_returns_audio():
    recorder = AudioRecorder(always_on=False, min_duration_ms=0)
    recorder.begin_capture()
    feed(recorder, 10)
    clip = recorder.end_capture()

    assert clip is not None
    assert len(clip.samples) == 10 * BLOCK_FRAMES


def test_tap_shorter_than_the_minimum_is_discarded():
    recorder = AudioRecorder(always_on=False, min_duration_ms=200)
    recorder.begin_capture()
    feed(recorder, 3)  # 90 ms
    assert recorder.end_capture() is None


def test_preroll_does_not_count_toward_the_tap_guard():
    """The guard must measure only what the user held for. Counting the
    pre-roll let a 90 ms tap clear a 200 ms threshold."""
    recorder = AudioRecorder(always_on=True, preroll_ms=300, min_duration_ms=200)

    feed(recorder, 10)  # fills the pre-roll while idle
    recorder.begin_capture()
    feed(recorder, 3)  # 90 ms held

    assert recorder.end_capture() is None


def test_preroll_is_prepended_to_a_real_capture():
    recorder = AudioRecorder(always_on=True, preroll_ms=300, min_duration_ms=100)

    feed(recorder, 20, value=0.2)  # pre-roll fills and rolls over
    recorder.begin_capture()
    feed(recorder, 10, value=0.4)
    clip = recorder.end_capture()

    assert clip is not None
    # 300 ms of pre-roll at 30 ms per block, plus the 10 held blocks.
    assert len(clip.samples) == 20 * BLOCK_FRAMES


def test_preroll_can_be_skipped():
    """An interrupting press must not include the pre-roll: on speakers it
    holds Nexus's own voice."""
    recorder = AudioRecorder(always_on=True, preroll_ms=300, min_duration_ms=0)

    feed(recorder, 20)
    recorder.begin_capture(use_preroll=False)
    feed(recorder, 5)
    clip = recorder.end_capture()

    assert clip is not None
    assert len(clip.samples) == 5 * BLOCK_FRAMES


def test_capture_length_is_capped():
    """A stuck key must not record without limit."""
    recorder = AudioRecorder(always_on=False, min_duration_ms=0, max_duration_ms=300)
    recorder.begin_capture()
    feed(recorder, 100)  # 3 seconds offered, 300 ms allowed
    clip = recorder.end_capture()

    assert clip is not None
    assert len(clip.samples) <= int(SAMPLE_RATE * 0.3) + BLOCK_FRAMES


def test_end_capture_without_begin_returns_none():
    recorder = AudioRecorder(always_on=False)
    assert recorder.end_capture() is None


def test_begin_capture_twice_is_ignored():
    """Duplicate key events must not reset a capture in progress."""
    recorder = AudioRecorder(always_on=False, min_duration_ms=0)
    recorder.begin_capture()
    feed(recorder, 5)
    recorder.begin_capture()
    feed(recorder, 5)
    clip = recorder.end_capture()

    assert clip is not None
    assert len(clip.samples) == 10 * BLOCK_FRAMES


def test_listeners_receive_every_block():
    recorder = AudioRecorder(always_on=True, min_duration_ms=0)
    seen: list[int] = []
    recorder.subscribe(lambda b: seen.append(len(b)))

    feed(recorder, 4)
    assert seen == [BLOCK_FRAMES] * 4


def test_a_failing_listener_does_not_stop_capture():
    recorder = AudioRecorder(always_on=True, min_duration_ms=0)
    recorder.subscribe(lambda _b: 1 / 0)

    recorder.begin_capture()
    feed(recorder, 5)
    clip = recorder.end_capture()

    assert clip is not None
