"""Orchestrates one turn of conversation: hear, understand, answer, speak.

Everything here is wiring. The pipeline depends only on the protocols in
:mod:`nexus.core.protocols`, so the speech engine, language model, and voice can
each be replaced without touching this file.

Threading
---------
Three threads matter, and the split is not optional::

    hotkey dispatcher ──► worker thread          realtime audio threads
    begin/end capture     transcribe             microphone callback
    interrupt             generate               playback callback
                          speak

The hotkey handler must return in well under 300 ms or Windows silently
uninstalls the keyboard hook, and transcription alone takes roughly 800 ms.
So a press only queues work. This is also what makes barge-in possible: the
dispatcher stays free to react while the worker is busy speaking.

Latency
-------
The reply is spoken sentence by sentence as it is generated, rather than after
it is complete. Time to Nexus's first word is therefore fixed at roughly
transcription plus first token plus first sentence, and does not grow with the
length of the answer.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from collections.abc import Iterator, Callable
from dataclasses import dataclass, field
from typing import Final, Any

from nexus.audio.recorder import AudioClip, AudioRecorder
from nexus.core.protocols import LLMError, LLMProvider, STTEngine, Toolbox, TTSEngine
from nexus.core.state import State, StateMachine
from nexus.llm.conversation import Conversation

logger = logging.getLogger(__name__)

_SHUTDOWN: Final = None

# One pending request. A second press while a turn is queued replaces it:
# the user has moved on, and answering a superseded question is worse than
# dropping it.
_QUEUE_SIZE: Final = 1


@dataclass(slots=True)
class TurnTiming:
    """Where the time went in one exchange, for the latency budget."""

    transcribe_ms: float = 0.0
    first_token_ms: float = 0.0
    first_sentence_ms: float = 0.0
    total_to_speech_ms: float = 0.0
    words: int = 0
    heard: str = ""
    reply: str = ""
    history_turns: int = 0
    sentences: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TurnRequest:
    """A request to process a conversation turn."""
    audio: AudioClip | None = None
    text: str | None = None
    speak: bool = True


class Pipeline:
    """Runs conversation turns in response to hotkey presses.

    Args:
        recorder: Microphone capture.
        transcriber: Speech recognition.
        provider: Language model.
        voice: Speech synthesis.
        conversation: In-session history.
        state: Shared state machine, so a UI can follow along.
        tools: Capabilities the model may use, such as looking at the screen.
            ``None`` leaves Nexus a pure conversationalist.
    """

    def __init__(
        self,
        *,
        recorder: AudioRecorder,
        transcriber: STTEngine,
        provider: LLMProvider,
        voice: TTSEngine,
        conversation: Conversation,
        state: StateMachine | None = None,
        tools: Toolbox | None = None,
    ) -> None:
        self._recorder = recorder
        self._transcriber = transcriber
        self._provider = provider
        self._voice = voice
        self._conversation = conversation
        self._tools = tools
        self.state = state or StateMachine()

        self._work: queue.Queue[TurnRequest | None] = queue.Queue(maxsize=_QUEUE_SIZE)
        self._worker: threading.Thread | None = None
        self._cancel = threading.Event()
        self._busy = threading.Event()
        self._released_at = 0.0
        self._last_error_kind: str | None = None
        self.last_timing: TurnTiming | None = None
        
        self._token_listeners: list[Callable[[str], None]] = []
        self._user_text_listeners: list[Callable[[str], None]] = []

    def subscribe_token(self, listener: Callable[[str], None]) -> None:
        self._token_listeners.append(listener)
        
    def subscribe_user_text(self, listener: Callable[[str], None]) -> None:
        self._user_text_listeners.append(listener)

    # -- lifecycle ----------------------------------------------------------

    def start(self) -> None:
        """Begin processing turns."""
        if self._worker is not None:
            return
        self._worker = threading.Thread(target=self._run, name="ev-pipeline", daemon=True)
        self._worker.start()

    def stop(self) -> None:
        """Stop the worker and silence any reply in progress."""
        self._cancel.set()
        self._voice.interrupt()
        if self._worker is not None:
            self._work.put(_SHUTDOWN)
            self._worker.join(timeout=5.0)
            self._worker = None
        self.state.transition(State.IDLE)

    # -- hotkey handlers ----------------------------------------------------

    def abort(self) -> None:
        """Silence any reply in progress and stop generating it."""
        self._cancel.set()
        self._voice.interrupt()
        self.state.transition(State.IDLE)

    def on_press(self) -> None:
        """Start listening. Must return promptly; see module docstring."""
        interrupting = self._busy.is_set()
        if interrupting:
            # Barge-in. Cancel before capturing so the reply stops immediately
            # rather than after the current sentence.
            self._cancel.set()
            self._voice.interrupt()
            logger.debug("Interrupted by user")

        # On speakers the pre-roll holds Nexus's own voice, which would be
        # transcribed as if the user had said it.
        self._recorder.begin_capture(use_preroll=not interrupting)
        self.state.transition(State.LISTENING)

    def on_release(self) -> None:
        """Stop listening and queue the recording for processing."""
        clip = self._recorder.end_capture()
        if clip is None:
            self.state.transition(State.IDLE)
            return
        self.submit(clip)

    def submit(self, clip: AudioClip) -> None:
        """Queue a recording for processing.

        Used by both push-to-talk and hands-free mode, which differ only in
        how they decide an utterance is over.
        """
        self._submit_request(TurnRequest(audio=clip, speak=True))

    def submit_text(self, text: str) -> None:
        """Queue a typed text command for processing."""
        self._submit_request(TurnRequest(text=text, speak=False))
        
    def _submit_request(self, request: TurnRequest) -> None:
        self._released_at = time.perf_counter()

        try:
            self._work.put_nowait(request)
        except queue.Full:
            # Replace the superseded request rather than queueing behind it.
            try:
                self._work.get_nowait()
            except queue.Empty:
                pass
            try:
                self._work.put_nowait(request)
            except queue.Full:
                logger.warning("Dropped a recording; pipeline is not keeping up")

        self.state.transition(State.THINKING)

    # -- worker -------------------------------------------------------------

    def _run(self) -> None:
        while True:
            request = self._work.get()
            if request is _SHUTDOWN:
                return
            try:
                self._handle(request)
            except Exception:  # noqa: BLE001 -- one bad turn must not end the loop
                logger.exception("Turn failed")
                self.state.transition(State.IDLE)
            finally:
                self._busy.clear()

    def _handle(self, request: TurnRequest) -> None:
        """Run one complete turn."""
        self._busy.set()
        self._cancel.clear()
        timing = TurnTiming()
        released = self._released_at

        # --- hear ---
        if request.text is not None:
            timing.heard = request.text
            timing.transcribe_ms = 0.0
            transcript_text = request.text
        else:
            try:
                transcript = self._transcriber.transcribe(request.audio)
            except Exception:  # noqa: BLE001 -- a failed model must not end the loop
                logger.exception("Transcription failed")
                self._speak_error(LLMError("Transcription failed"))
                self.state.transition(State.IDLE)
                self.last_timing = timing
                return

            timing.transcribe_ms = transcript.latency * 1000

            if transcript.is_empty:
                logger.info("No speech recognised")
                self.state.transition(State.IDLE)
                self.last_timing = timing
                return
            transcript_text = transcript.text

        logger.info("Heard: %s", transcript_text)
        
        for listener in self._user_text_listeners:
            try:
                listener(transcript_text)
            except Exception:
                pass
                
        self._conversation.add("user", transcript_text)

        if self._cancel.is_set():
            self.state.transition(State.IDLE)
            return

        # --- think and speak, overlapped ---
        self.state.transition(State.SPEAKING)
        collected: list[str] = []

        try:
            fragments = self._observe(
                self._provider.stream_reply(self._conversation.messages(), self._tools),
                collected,
                timing,
                released,
            )
            if request.speak:
                for sentence in self._voice.stream_sentences(fragments):
                    if not timing.first_sentence_ms:
                        timing.first_sentence_ms = (time.perf_counter() - released) * 1000
                    timing.sentences.append(sentence)
            else:
                for fragment in fragments:
                    pass # Handled entirely by the token listeners in _observe

        except LLMError as exc:
            logger.error("Reply failed: %s", exc)
            # Take the unanswered question back out of the history. Left in, it
            # accumulates: several failures in a row leave a run of consecutive
            # user messages, and a conversation shaped like that keeps failing
            # long after whatever caused the first problem has passed.
            self._conversation.rollback()
            self._speak_error(exc)
            self.state.transition(State.IDLE)
            self.last_timing = timing
            return

        # A turn that got this far worked, so the next failure is news again.
        self._last_error_kind = None

        reply = "".join(collected).strip()
        if reply and not self._cancel.is_set():
            self._conversation.add("assistant", reply)
        timing.reply = reply
        timing.words = len(reply.split())
        timing.history_turns = len(self._conversation)

        if request.speak:
            self._voice.wait_until_spoken()
            
        timing.total_to_speech_ms = (time.perf_counter() - released) * 1000
        self.last_timing = timing
        self.state.transition(State.IDLE)

    def _observe(
        self,
        fragments: Iterator[str],
        collected: list[str],
        timing: TurnTiming,
        released: float,
    ) -> Iterator[str]:
        """Pass fragments through, recording them and honouring cancellation.

        Cancellation is checked here rather than inside the synthesiser so that
        generation stops too. Continuing to stream tokens for a reply nobody
        will hear wastes both time and quota.
        """
        for fragment in fragments:
            if self._cancel.is_set():
                return
            if not timing.first_token_ms:
                timing.first_token_ms = (time.perf_counter() - released) * 1000
            collected.append(fragment)
            
            for listener in self._token_listeners:
                try:
                    listener(fragment)
                except Exception:
                    pass
                    
            yield fragment

    def _speak_error(self, error: LLMError) -> None:
        """Explain a failure out loud rather than going quiet.

        Silence after a press is indistinguishable from Nexus being broken, so
        the user presses the key again with no idea why.

        Repeats are suppressed. A dropped connection fails on every attempt,
        and hearing the same sentence five times in a row is worse than
        hearing it once -- so the same problem is announced only when it is
        not the one announced last time.
        """
        message = getattr(error, "spoken", LLMError.spoken)
        kind = type(error).__name__

        if kind == self._last_error_kind:
            logger.debug("Suppressing a repeat of %s", kind)
            return
        self._last_error_kind = kind

        try:
            self._voice.speak_stream([message])
            self._voice.wait_until_spoken()
        except Exception:  # noqa: BLE001 -- already handling a failure
            logger.exception("Could not speak the error message")
