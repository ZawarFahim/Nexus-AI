"""Tests for the tool registry and the screen capture tool.

The registry's contract is that it never raises. Everything crossing into it
was chosen by a language model -- the tool name, the arguments, whether the
arguments are even JSON -- so every one of those is an input a real model
produces sooner or later, not a hypothetical.
"""

from __future__ import annotations

import base64

import pytest

from nexus.core.protocols import ToolCall, ToolResult, Toolbox
from nexus.tools import screen
from nexus.tools.registry import Tool, ToolRegistry


def echo_tool(name: str = "echo") -> Tool:
    return Tool(
        name=name,
        description="Repeat the argument back.",
        run=lambda args: ToolResult(f"got {args.get('text', '')}"),
        parameters={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    )


def test_registry_satisfies_the_toolbox_protocol():
    assert isinstance(ToolRegistry(), Toolbox)


def test_specs_are_shaped_for_the_chat_api():
    registry = ToolRegistry([echo_tool()])

    spec = registry.specs()[0]

    assert spec["type"] == "function"
    assert spec["function"]["name"] == "echo"
    assert spec["function"]["description"]
    assert spec["function"]["parameters"]["properties"]["text"]["type"] == "string"


def test_runs_a_tool_with_parsed_arguments():
    registry = ToolRegistry([echo_tool()])

    result = registry.run(ToolCall("call_1", "echo", '{"text": "hello"}'))

    assert result.content == "got hello"


def test_an_unknown_tool_is_reported_not_raised():
    """Models invent plausible-sounding tools. That must not end the turn."""
    registry = ToolRegistry([echo_tool()])

    result = registry.run(ToolCall("call_1", "read_my_mind", "{}"))

    assert "no tool called" in result.content
    # Naming what does exist lets the model recover in the next round.
    assert "echo" in result.content


def test_malformed_arguments_are_reported_not_raised():
    registry = ToolRegistry([echo_tool()])

    result = registry.run(ToolCall("call_1", "echo", '{"text": '))

    assert "not valid JSON" in result.content


def test_non_object_arguments_are_rejected():
    registry = ToolRegistry([echo_tool()])

    result = registry.run(ToolCall("call_1", "echo", '"just a string"'))

    assert "expected an object" in result.content


@pytest.mark.parametrize("arguments", ["", "  ", "{}", "null", " null "])
def test_a_tool_with_no_parameters_accepts_every_way_of_saying_so(arguments):
    """Models call a no-argument tool with null as readily as with {}.

    Rejecting null meant the tool never ran. The model retried, was rejected
    again, and finally answered without having looked -- indistinguishable,
    from the outside, from Nexus ignoring the question.
    """
    registry = ToolRegistry([Tool("ping", "Ping.", lambda args: ToolResult(str(args)))])

    assert registry.run(ToolCall("c", "ping", arguments)).content == "{}"


def test_a_raising_tool_becomes_a_message():
    """A crash inside a tool would otherwise kill the streaming loop."""

    def explode(_args):
        raise RuntimeError("disk on fire")

    registry = ToolRegistry([Tool("boom", "Explode.", explode)])

    result = registry.run(ToolCall("call_1", "boom", "{}"))

    assert "did not work" in result.content
    assert "disk on fire" in result.content


def test_re_registering_replaces():
    registry = ToolRegistry([echo_tool()])
    registry.add(Tool("echo", "Different.", lambda _a: ToolResult("new")))

    assert len(registry) == 1
    assert registry.run(ToolCall("c", "echo", "{}")).content == "new"


# -- screen capture ---------------------------------------------------------


class FakeImage:
    """Stands in for a Pillow image, recording what was asked of it.

    Args:
        size: Starting dimensions.
        payload_size: Bytes each ``save`` writes, so a test can make PNG
            output cross the size limit that triggers the JPEG fallback.
    """

    def __init__(self, size=(1920, 1080), payload_size=64) -> None:
        self.size = size
        self.payload_size = payload_size
        self.thumbnailed_to = None
        self.converted_to = None
        self.formats: list[str] = []

    def thumbnail(self, box, _resample=None):
        self.thumbnailed_to = box
        # Pillow shrinks in place, preserving aspect ratio.
        scale = min(box[0] / self.size[0], box[1] / self.size[1], 1.0)
        self.size = (int(self.size[0] * scale), int(self.size[1] * scale))

    def convert(self, mode):
        self.converted_to = mode
        return self

    def save(self, buffer, format=None, **_kwargs):  # noqa: A002 -- Pillow's name
        self.formats.append(format)
        buffer.write(b"\x89" + format.encode() + b"x" * self.payload_size)


@pytest.fixture
def fake_grab(monkeypatch):
    """Replace the screenshot with a controllable stand-in."""
    captured = {}

    def install(size=(1920, 1080), payload_size=64):
        image = FakeImage(size, payload_size)
        captured["image"] = image
        monkeypatch.setattr(
            screen, "enable_dpi_awareness", lambda: True, raising=False
        )

        class FakeGrab:
            @staticmethod
            def grab(all_screens=False):
                captured["all_screens"] = all_screens
                return image

        class FakeImageModule:
            LANCZOS = "lanczos"

        monkeypatch.setitem(
            __import__("sys").modules,
            "PIL",
            type("PIL", (), {"Image": FakeImageModule, "ImageGrab": FakeGrab}),
        )
        return captured

    return install


def test_capture_returns_a_png_data_uri(fake_grab):
    fake_grab()

    data_uri, width, height = screen.capture()

    assert data_uri.startswith("data:image/png;base64,")
    assert (width, height) == (1920, 1080)
    # Decodes cleanly, or the API rejects the whole request.
    base64.b64decode(data_uri.split(",", 1)[1], validate=True)


def test_capture_spans_every_monitor(fake_grab):
    captured = fake_grab()

    screen.capture()

    assert captured["all_screens"] is True


def test_a_single_screen_is_not_resized(fake_grab):
    """Resizing costs fidelity and, for screenshots, actually costs size too."""
    captured = fake_grab(size=(1920, 1080))

    screen.capture()

    assert captured["image"].thumbnailed_to is None


def test_an_oversized_desktop_is_shrunk(fake_grab):
    """Three 4K monitors would otherwise be a very slow upload."""
    captured = fake_grab(size=(11520, 2160))

    _uri, width, height = screen.capture()

    assert captured["image"].thumbnailed_to == (screen.MAX_DIMENSION, screen.MAX_DIMENSION)
    assert max(width, height) <= screen.MAX_DIMENSION


def test_a_small_capture_stays_png(fake_grab):
    captured = fake_grab()

    data_uri, _w, _h = screen.capture()

    assert captured["image"].formats == ["PNG"]
    assert data_uri.startswith("data:image/png;")


def test_a_large_capture_falls_back_to_jpeg(fake_grab):
    """A screen playing video compresses badly as PNG and uploads slowly."""
    captured = fake_grab(payload_size=screen.PNG_SIZE_LIMIT_BYTES + 1)

    data_uri, _w, _h = screen.capture()

    assert captured["image"].formats == ["PNG", "JPEG"]
    # The declared media type has to follow the format, or the endpoint
    # decodes it as the wrong thing.
    assert data_uri.startswith("data:image/jpeg;")


def test_alpha_is_dropped(fake_grab):
    """No display has transparency, and some endpoints reject RGBA."""
    captured = fake_grab()

    screen.capture()

    assert captured["image"].converted_to == "RGB"


def test_a_failed_capture_becomes_a_message_not_an_exception(monkeypatch):
    def refuse(_args=None):
        raise screen.ScreenCaptureError("no display")

    monkeypatch.setattr(screen, "capture", refuse)

    result = screen.screen_tool().run({})

    assert "could not see the screen" in result.content
    assert result.images == ()


def test_the_screen_tool_takes_no_arguments():
    """Nothing for the model to get wrong is the most reliable tool there is."""
    tool = screen.screen_tool()

    assert tool.parameters["properties"] == {}
