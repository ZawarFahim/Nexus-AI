"""Tests for turn orchestration, using stubs instead of models.

Covers the wiring rather than the components: that history accumulates across
turns, that a failure is spoken rather than swallowed, and that a broken
component does not take the worker thread down with it.
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from nexus.audio.recorder import SAMPLE_RATE, AudioClip
from nexus.core.protocols import LLMConnectionError, LLMError, Transcript
from nexus.core.state import State
from nexus.llm.conversation import Conversation
from nexus.pipeline import Pipeline


class StubRecorder:
    def __init__(self) -> None:
        self.preroll_used: list[bool] = []

    def begin_capture(self, *, use_preroll: bool = True) -> None:
        self.preroll_used.append(use_preroll)

    def end_capture(self):
        return AudioClip(np.zeros(SAMPLE_RATE, dtype=np.float32))


class StubSTT:
    def __init__(self, texts=None, error=None) -> None:
        self.texts = list(texts or ["hello"])
        self.error = error

    def load(self) -> None:
        pass

    def transcribe(self, clip):
        if self.error:
            raise self.error
        text = self.texts.pop(0) if self.texts else ""
        return Transcript(text=text, language="en", latency=0.01)


class StubProvider:
    name = "stub"

    def __init__(self, error=None) -> None:
        self.error = error
        self.seen: list[list[tuple[str, str]]] = []
        self.tools_offered: list[object] = []

    def stream_reply(self, messages, tools=None):
        self.seen.append([(m.role, m.content) for m in messages])
        self.tools_offered.append(tools)
        if self.error:
            raise self.error
        yield from ["Sure. ", "Here you go."]


class StubVoice:
    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.interrupts = 0

    def stream_sentences(self, fragments):
        text = "".join(fragments)
        for sentence in filter(None, (s.strip() for s in text.split(". "))):
            self.spoken.append(sentence)
            yield sentence

    def speak_stream(self, fragments):
        self.spoken.extend(fragments)

    def wait_until_spoken(self):
        return True

    def interrupt(self):
        self.interrupts += 1


def build(stt=None, provider=None, voice=None, conversation=None):
    pipeline = Pipeline(
        recorder=StubRecorder(),
        transcriber=stt or StubSTT(),
        provider=provider or StubProvider(),
        voice=voice or StubVoice(),
        conversation=conversation or Conversation("SYSTEM"),
    )
    pipeline.start()
    return pipeline


def run_turn(pipeline, timeout=3.0):
    pipeline.on_press()
    pipeline.on_release()
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        if pipeline.state.current is State.IDLE and pipeline.last_timing is not None:
            return
        time.sleep(0.01)
    raise AssertionError("turn did not complete")


def test_history_accumulates_across_turns():
    """Without this, every question is answered as if it were the first,
    which reads as the model being stupid rather than as a bug."""
    provider = StubProvider()
    pipeline = build(stt=StubSTT(["first question", "second question"]), provider=provider)

    run_turn(pipeline)
    run_turn(pipeline)
    pipeline.stop()

    assert len(provider.seen[0]) == 2  # system + first
    assert len(provider.seen[1]) == 4  # system + first + reply + second
    assert provider.seen[1][2][0] == "assistant"


def test_reply_is_spoken():
    voice = StubVoice()
    pipeline = build(voice=voice)
    run_turn(pipeline)
    pipeline.stop()

    assert voice.spoken


def test_empty_transcript_produces_no_request():
    provider = StubProvider()
    pipeline = build(stt=StubSTT([""]), provider=provider)
    run_turn(pipeline)
    pipeline.stop()

    assert provider.seen == []


def test_connection_failure_is_spoken_not_swallowed():
    """Silence after a press is indistinguishable from Nexus being broken."""
    voice = StubVoice()
    pipeline = build(provider=StubProvider(error=LLMConnectionError("no net")), voice=voice)
    run_turn(pipeline)
    pipeline.stop()

    assert any("internet" in line.lower() for line in voice.spoken)


def test_repeated_failures_are_announced_once():
    """A dropped connection fails every attempt; hearing the same sentence
    five times is worse than hearing it once."""
    voice = StubVoice()
    pipeline = build(
        stt=StubSTT(["one", "two", "three"]),
        provider=StubProvider(error=LLMConnectionError("no net")),
        voice=voice,
    )
    for _ in range(3):
        run_turn(pipeline)
    pipeline.stop()

    assert len(voice.spoken) == 1


def test_transcription_failure_does_not_kill_the_worker():
    """A crash in the worker would leave Nexus silently deaf until restarted."""
    voice = StubVoice()
    pipeline = build(stt=StubSTT(error=RuntimeError("model exploded")), voice=voice)
    run_turn(pipeline)

    assert voice.spoken
    assert pipeline.state.current is State.IDLE

    pipeline.stop()


def test_interrupting_press_skips_the_preroll():
    """On speakers the pre-roll holds Nexus's own voice, which would otherwise
    be transcribed as if the user had said it."""
    pipeline = build()
    recorder = pipeline._recorder  # noqa: SLF001

    pipeline.on_press()
    assert recorder.preroll_used == [True]

    pipeline._busy.set()  # noqa: SLF001 -- simulate Nexus mid-reply
    pipeline.on_press()
    assert recorder.preroll_used[-1] is False

    pipeline.stop()


def test_abort_silences_the_voice():
    voice = StubVoice()
    pipeline = build(voice=voice)
    pipeline.abort()

    assert voice.interrupts == 1
    assert pipeline.state.current is State.IDLE

    pipeline.stop()


def test_recovery_after_a_failure_resets_the_error_notice():
    """Once a turn succeeds, the next failure is news again."""
    voice = StubVoice()
    provider = StubProvider(error=LLMConnectionError("no net"))
    pipeline = build(stt=StubSTT(["a", "b", "c"]), provider=provider, voice=voice)

    run_turn(pipeline)
    assert len(voice.spoken) == 1

    provider.error = None
    run_turn(pipeline)

    provider.error = LLMConnectionError("no net again")
    run_turn(pipeline)
    pipeline.stop()

    spoken_errors = [line for line in voice.spoken if "internet" in line.lower()]
    assert len(spoken_errors) == 2
