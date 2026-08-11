"""Builds and runs Nexus.

The composition root: the one place that names concrete classes and wires them
together. Everything else depends on protocols, which is what keeps swapping a
component to a single edit here.

Startup order is deliberate. Every model and connection is warmed before the
hotkey is registered, so the first press is as fast as the hundredth rather
than paying for a cold Whisper model, a TLS handshake, and a Piper model load
all at once.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

from nexus.audio.endpointing import SpeechEndpointer
from nexus.audio.recorder import AudioRecorder
from nexus.core.config import Settings
from nexus.core.profile import Profile
from nexus.core.state import State, StateMachine
from nexus.hands_free import HandsFreeMode
from nexus.input.hotkey import ALT_SPACE, CTRL_ALT_SPACE, ALT_SHIFT_SPACE, HotkeyListener
from nexus.llm.conversation import Conversation
from nexus.llm.factory import create_provider
from nexus.llm.prompt import build_system_prompt
from nexus.pipeline import Pipeline
from nexus.stt.whisper import WhisperTranscriber
from nexus.tools import browser
from nexus.tools.registry import ToolRegistry
from nexus.tools.screen import screen_tool
from nexus.tools.desktop import desktop_tool
from nexus.tools.files import files_tool
from nexus.tts.piper import PiperVoice
from nexus.ui.orb import OrbController
from nexus.ui.command import CommandWindow

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Components:
    """Everything Nexus is made of, already wired together."""

    recorder: AudioRecorder
    transcriber: WhisperTranscriber
    voice: PiperVoice
    pipeline: Pipeline
    hands_free: HandsFreeMode
    hotkeys: HotkeyListener
    orb: OrbController
    command_window: CommandWindow
    state: StateMachine


def _has(tools: ToolRegistry | None, name: str) -> bool:
    """Whether a named capability is actually registered."""
    return tools is not None and name in tools.names


def build_tools(settings: Settings) -> ToolRegistry | None:
    """Assemble the capabilities Nexus is allowed to use.

    A disabled capability is left out of the registry rather than registered
    and refused. The model is then never told it exists, so there is no chance
    of it promising something it cannot do.

    Returns:
        The registry, or ``None`` if nothing is enabled -- which keeps tool
        declarations off requests entirely rather than sending an empty list.
    """
    registry = ToolRegistry()
    if settings.allow_screen:
        registry.add(screen_tool())
    if settings.allow_browser:
        registry.add(browser.open_tool())
        registry.add(browser.control_tool())
    # Desktop automation is always added if enabled, but for now we'll just add it.
    registry.add(desktop_tool())
    registry.add(files_tool())

    if not len(registry):
        logger.info("No tools enabled; Nexus can only talk")
        return None

    logger.info("Tools available: %s", ", ".join(registry.names))
    return registry


def build(
    settings: Settings,
    *,
    profile: Profile | None = None,
    api_key: str = "",
    state: StateMachine | None = None,
) -> Components:
    """Construct Nexus from configuration, without starting anything.

    Args:
        settings: Loaded application settings.
        profile: What Nexus knows about the user. ``None`` means no name is
            known, which is a supported state rather than an error.
        api_key: Credential resolved by onboarding. Empty falls back to the
            environment, which is how tests and developers bypass setup.
        state: Shared state machine, so a UI can subscribe before startup.

    Returns:
        The assembled components.

    Raises:
        LLMError: If the configured provider cannot be created.
    """
    state = state or StateMachine()
    profile = profile or Profile()

    recorder = AudioRecorder(
        device_name=settings.input_device,
        always_on=settings.always_on_mic,
    )
    transcriber = WhisperTranscriber(device_preference=settings.device)
    provider = create_provider(settings, api_key)
    voice = PiperVoice(
        voice=settings.voice,
        output_device=settings.output_device,
        speed=settings.speech_speed,
    )

    tools = build_tools(settings)
    pipeline = Pipeline(
        recorder=recorder,
        transcriber=transcriber,
        provider=provider,
        voice=voice,
        conversation=Conversation(
            # Derived from the registry rather than from settings, deliberately.
            # Telling the model it can see a screen it has no tool for produces
            # a confident description of something it never looked at.
            build_system_prompt(
                profile.name,
                can_see_screen=_has(tools, "look_at_screen"),
                can_use_browser=_has(tools, "open_in_browser"),
            )
        ),
        state=state,
        tools=tools,
    )
    hands_free = HandsFreeMode(
        recorder=recorder,
        pipeline=pipeline,
        state=state,
        endpointer=SpeechEndpointer(
            threshold=settings.vad_threshold,
            silence_ms=settings.silence_ms,
        ),
    )

    def toggle_hands_free() -> None:
        # Toggling off must also silence a reply in progress, or the mode
        # appears not to have turned off until Nexus finishes its sentence.
        if hands_free.enabled:
            pipeline.abort()
        hands_free.toggle()

    hotkeys = HotkeyListener()
    hotkeys.register(ALT_SPACE, pipeline.on_press, pipeline.on_release)
    hotkeys.register(CTRL_ALT_SPACE, toggle_hands_free)
    
    command_window = CommandWindow(pipeline)
    hotkeys.register(ALT_SHIFT_SPACE, command_window.show)

    orb = OrbController(enabled=settings.show_orb)
    state.subscribe(orb.on_state)
    state.subscribe(command_window.on_state)

    def show_microphone_level(block) -> None:
        """Feed the orb from the audio thread.

        Runs on the realtime callback, so it must only measure and hand off;
        the controller drops updates that arrive too close together, and
        blocking here would cause dropouts.
        """
        import numpy as np

        # Root mean square, scaled: speech sits low in a 0-1 range and the orb
        # would barely move if the raw value were used.
        level = float(np.sqrt(np.mean(np.square(block)))) * 6.0
        orb.on_levels(input_level=min(1.0, level))

    recorder.subscribe(show_microphone_level)

    # Warming the connection is pure latency work and needs no result.
    threading.Thread(
        target=provider.warm_up, name="ev-llm-warm", daemon=True
    ).start()

    return Components(
        recorder=recorder,
        transcriber=transcriber,
        voice=voice,
        pipeline=pipeline,
        hands_free=hands_free,
        hotkeys=hotkeys,
        orb=orb,
        command_window=command_window,
        state=state,
    )


def start(components: Components) -> None:
    """Load models and register the hotkey.

    The hotkey is registered last, deliberately. Registering it first would
    let the user press it while Whisper was still loading, which looks
    identical to Nexus being broken.
    """
    components.transcriber.load()
    components.voice.start()
    components.recorder.start()
    components.pipeline.start()
    components.hands_free.prepare()
    components.orb.start()
    components.hotkeys.start()
    components.state.transition(State.IDLE)


def shutdown(components: Components) -> None:
    """Release everything, in the reverse order of startup."""
    components.hotkeys.stop()
    components.orb.stop()
    components.hands_free.close()
    components.pipeline.stop()
    components.recorder.stop()
    components.voice.stop()
