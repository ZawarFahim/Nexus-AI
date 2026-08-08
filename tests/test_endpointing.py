"""Tests for the hands-free speech endpointer.

Drives the state machine with synthetic probabilities rather than audio, so
these test the decision logic -- how long a pause ends a turn, how much noise
is ignored -- without depending on a model or a microphone.
"""

from __future__ import annotations

import numpy as np
import pytest

from nexus.audio.endpointing import FRAME_MS, SpeechEndpointer, SpeechEvent


class FakeVAD:
    """Returns a scripted probability per frame."""

    def __init__(self, probabilities: list[float]) -> None:
        self._probabilities = list(probabilities)

    def __call__(self, chunk: np.ndarray, *_args, **_kwargs):
        frames = len(chunk) // 512
        out = [self._probabilities.pop(0) if self._probabilities else 0.0 for _ in range(frames)]
        return np.array(out, dtype=np.float32)


def endpointer_with(probabilities, **kwargs) -> SpeechEndpointer:
    endpointer = SpeechEndpointer(**kwargs)
    endpointer._model = FakeVAD(probabilities)  # noqa: SLF001
    return endpointer


def feed_frames(endpointer: SpeechEndpointer, count: int) -> list[SpeechEvent]:
    """Push ``count`` frames' worth of audio through, one frame at a time."""
    events = []
    for _ in range(count):
        events.extend(endpointer.feed(np.zeros(512, dtype=np.float32)))
    return events


def test_speech_starts_after_enough_voiced_frames():
    endpointer = endpointer_with([0.9] * 10, min_speech_ms=160)
    events = feed_frames(endpointer, 10)

    assert events.count(SpeechEvent.STARTED) == 1
    assert endpointer.in_speech


def test_brief_noise_does_not_start_speech():
    """A cough or a keystroke is voiced for a frame or two. Requiring a run
    is what stops Nexus answering a door slam."""
    endpointer = endpointer_with([0.9, 0.9, 0.0, 0.0, 0.0, 0.0], min_speech_ms=160)
    events = feed_frames(endpointer, 6)

    assert SpeechEvent.STARTED not in events
    assert not endpointer.in_speech


def test_silence_ends_the_turn():
    silence_frames = 800 // FRAME_MS
    endpointer = endpointer_with(
        [0.9] * 10 + [0.0] * (silence_frames + 2), min_speech_ms=160, silence_ms=800
    )
    events = feed_frames(endpointer, 12 + silence_frames)

    assert events.count(SpeechEvent.STARTED) == 1
    assert events.count(SpeechEvent.ENDED) == 1
    assert not endpointer.in_speech


def test_short_pause_does_not_end_the_turn():
    """People pause mid-thought. Ending a turn on a brief gap cuts them off."""
    gap = (800 // FRAME_MS) - 3
    endpointer = endpointer_with(
        [0.9] * 10 + [0.0] * gap + [0.9] * 10, min_speech_ms=160, silence_ms=800
    )
    events = feed_frames(endpointer, 20 + gap)

    assert SpeechEvent.ENDED not in events
    assert endpointer.in_speech


def test_utterance_length_is_capped():
    """A noisy room must not record forever."""
    endpointer = endpointer_with([0.9] * 500, min_speech_ms=64, max_utterance_ms=320)
    events = feed_frames(endpointer, 40)

    assert SpeechEvent.ENDED in events
    assert not endpointer.in_speech


def test_reset_clears_state():
    endpointer = endpointer_with([0.9] * 10, min_speech_ms=160)
    feed_frames(endpointer, 10)
    assert endpointer.in_speech

    endpointer.reset()
    assert not endpointer.in_speech


def test_partial_frames_are_buffered_across_calls():
    """The recorder emits 480-sample blocks and the model needs 512, so
    frames must be assembled across calls rather than dropped."""
    endpointer = endpointer_with([0.9] * 20, min_speech_ms=160)
    events = []
    for _ in range(20):
        events.extend(endpointer.feed(np.zeros(480, dtype=np.float32)))

    assert SpeechEvent.STARTED in events


@pytest.mark.parametrize("threshold", [0.3, 0.5, 0.8])
def test_threshold_is_respected(threshold):
    below = threshold - 0.05
    endpointer = endpointer_with([below] * 20, threshold=threshold, min_speech_ms=64)
    assert feed_frames(endpointer, 20) == []
