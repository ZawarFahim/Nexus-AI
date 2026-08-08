"""Tests for the streaming tool-call loop.

This is the least forgiving code in Nexus. Tool calls arrive split across stream
chunks exactly as text does -- a name in one chunk, arguments a few characters
at a time in the next -- and the only field present on every piece is an
index. Reassembly bugs here do not crash: they produce a tool call with
truncated arguments, which the model then apologises for in a way that looks
like the model being stupid rather than Nexus being broken.

The provider is driven with a fake client that emits chunks the way a real
stream does, one small piece at a time.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from nexus.core.protocols import (
    LLMConnectionError,
    LLMError,
    Message,
    ToolCall,
    ToolResult,
)
from nexus.llm.openai_compatible import (
    IMAGE_NOTE,
    OpenAICompatibleProvider,
    _message_payload,
)


def text_chunk(text: str) -> SimpleNamespace:
    delta = SimpleNamespace(content=text, tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


def call_chunk(index=0, call_id=None, name=None, arguments=None) -> SimpleNamespace:
    piece = SimpleNamespace(
        index=index,
        id=call_id,
        function=SimpleNamespace(name=name, arguments=arguments),
    )
    delta = SimpleNamespace(content=None, tool_calls=[piece])
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


class FakeCompletions:
    """Replays scripted streams and records every request it received."""

    def __init__(self, scripts: list[list[SimpleNamespace]]) -> None:
        self._scripts = scripts
        self.requests: list[dict] = []

    def create(self, **request):
        self.requests.append(request)
        if not self._scripts:
            raise AssertionError("more requests than scripted responses")
        return iter(self._scripts.pop(0))


def make_provider(scripts, **kwargs) -> tuple[OpenAICompatibleProvider, FakeCompletions]:
    provider = OpenAICompatibleProvider(api_key="k", model="test-model", **kwargs)
    completions = FakeCompletions(scripts)
    provider._client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return provider, completions


class RecordingTools:
    """A toolbox that records calls and returns scripted results."""

    def __init__(self, results=None) -> None:
        self.results = results or {}
        self.calls: list[ToolCall] = []

    def specs(self):
        return [
            {
                "type": "function",
                "function": {"name": "look_at_screen", "description": "Look.",
                             "parameters": {"type": "object", "properties": {}}},
            }
        ]

    def run(self, call: ToolCall) -> ToolResult:
        self.calls.append(call)
        return self.results.get(call.name, ToolResult("done"))


HELLO = [Message("user", "hello")]


# -- plain replies ----------------------------------------------------------


def test_streams_text_without_tools():
    provider, completions = make_provider([[text_chunk("Hi "), text_chunk("there.")]])

    assert list(provider.stream_reply(HELLO)) == ["Hi ", "there."]
    assert "tools" not in completions.requests[0]


def test_declaring_tools_costs_nothing_when_none_are_used():
    """The latency argument for tool calling depends on exactly this."""
    provider, completions = make_provider([[text_chunk("Just talking.")]])

    assert list(provider.stream_reply(HELLO, RecordingTools())) == ["Just talking."]
    # One request, no extra round trip.
    assert len(completions.requests) == 1
    assert completions.requests[0]["tools"]


# -- reassembly -------------------------------------------------------------


def test_a_tool_call_split_across_chunks_is_reassembled():
    tools = RecordingTools()
    provider, _ = make_provider(
        [
            [
                call_chunk(0, "call_abc", "look_at_screen", ""),
                call_chunk(0, None, None, '{"deta'),
                call_chunk(0, None, None, 'il": "hi'),
                call_chunk(0, None, None, 'gh"}'),
            ],
            [text_chunk("I see a code editor.")],
        ]
    )

    assert list(provider.stream_reply(HELLO, tools)) == ["I see a code editor."]
    assert len(tools.calls) == 1
    assert tools.calls[0].id == "call_abc"
    assert tools.calls[0].name == "look_at_screen"
    assert tools.calls[0].arguments == '{"detail": "high"}'


def test_two_parallel_tool_calls_stay_separate():
    tools = RecordingTools()
    provider, _ = make_provider(
        [
            [
                call_chunk(0, "a", "look_at_screen", "{}"),
                call_chunk(1, "b", "other_tool", '{"x":'),
                call_chunk(1, None, None, " 1}"),
            ],
            [text_chunk("Both done.")],
        ]
    )

    list(provider.stream_reply(HELLO, tools))

    assert [call.name for call in tools.calls] == ["look_at_screen", "other_tool"]
    assert tools.calls[1].arguments == '{"x": 1}'


def test_missing_arguments_become_an_empty_object():
    """A no-argument tool often arrives with arguments never set at all."""
    tools = RecordingTools()
    provider, _ = make_provider(
        [[call_chunk(0, "a", "look_at_screen", None)], [text_chunk("ok")]]
    )

    list(provider.stream_reply(HELLO, tools))

    assert tools.calls[0].arguments == "{}"


# -- the loop ---------------------------------------------------------------


def test_tool_results_and_images_reach_the_next_request():
    tools = RecordingTools(
        {"look_at_screen": ToolResult("Screenshot taken.", ("data:image/png;base64,AAA",))}
    )
    provider, completions = make_provider(
        [
            [call_chunk(0, "a", "look_at_screen", "{}")],
            [text_chunk("Looks like VS Code.")],
        ],
        vision_model="a-model-with-eyes",
    )

    list(provider.stream_reply(HELLO, tools))

    second = completions.requests[1]["messages"]
    roles = [m["role"] for m in second]
    assert roles == ["user", "assistant", "tool", "user"]

    # The assistant turn records what was asked for, so the tool answer has
    # something to attach to.
    assert second[1]["tool_calls"][0]["function"]["name"] == "look_at_screen"
    assert second[2]["tool_call_id"] == "a"

    # The image cannot ride in the tool message; it follows as a user turn.
    image_part = second[3]["content"][-1]
    assert image_part["type"] == "image_url"
    assert image_part["image_url"]["url"].startswith("data:image/png;base64,")


def test_images_go_to_the_vision_model_and_text_does_not():
    tools = RecordingTools(
        {"look_at_screen": ToolResult("Taken.", ("data:image/png;base64,AAA",))}
    )
    provider, completions = make_provider(
        [[call_chunk(0, "a", "look_at_screen", "{}")], [text_chunk("A terminal.")]],
        vision_model="eyes",
    )

    list(provider.stream_reply(HELLO, tools))

    assert completions.requests[0]["model"] == "test-model"
    assert completions.requests[1]["model"] == "eyes"


def test_a_blind_service_answers_instead_of_failing():
    """When only a text-only service has allowance left, the turn must finish.

    Sending an image to a model that cannot take one gets the whole request
    rejected, so Nexus would go silent on exactly the question the user asked.
    Explaining the missing picture lets it say "I can't see your screen right
    now" and carry on, which is what a person would do.
    """
    tools = RecordingTools(
        {"look_at_screen": ToolResult("Taken.", ("data:image/png;base64,AAA",))}
    )
    provider, completions = make_provider(
        [
            [call_chunk(0, "a", "look_at_screen", "{}")],
            [text_chunk("I can't see your screen right now.")],
        ],
        vision_model="",  # This service has no eyes.
    )

    replies = list(provider.stream_reply(HELLO, tools))

    assert replies == ["I can't see your screen right now."]
    # The image never went out; an explanation went instead. A tool-calling
    # assistant turn legitimately carries null content, so the thing to assert
    # is that nothing is still in the list form images use.
    second = completions.requests[1]["messages"]
    assert not any(isinstance(message["content"], list) for message in second)
    assert "cannot see images" in second[-1]["content"]
    # And it still used the text model, since there is nothing else to use.
    assert completions.requests[1]["model"] == "test-model"


def test_stripping_images_does_not_damage_the_original_messages():
    """The same turn may still be offered to a service that can see."""
    from nexus.llm.openai_compatible import _describe_missing_images

    original = [
        {"role": "user", "content": [
            {"type": "text", "text": "here"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAA"}},
        ]}
    ]

    _describe_missing_images(original)

    assert original[0]["content"][1]["type"] == "image_url"


def test_tool_results_can_be_reported_as_plain_conversation():
    """Some services reject their own tool call played back to them.

    Gemini answers the follow-up request with "the function call is missing a
    thought_signature" -- a field its native protocol carries and this one
    cannot. The failure lands after the tool has already run, so the browser
    opens and Nexus then says nothing at all. Reporting the result as ordinary
    text sidesteps the formal protocol entirely.
    """
    tools = RecordingTools({"look_at_screen": ToolResult("Opened youtube.com.")})
    provider, completions = make_provider(
        [
            [call_chunk(0, "a", "look_at_screen", "{}")],
            [text_chunk("Done.")],
        ],
        tool_results_as_text=True,
    )

    assert list(provider.stream_reply(HELLO, tools)) == ["Done."]

    second = completions.requests[1]["messages"]
    # No formal tool protocol anywhere in the follow-up.
    assert not any("tool_calls" in message for message in second)
    assert not any(message["role"] == "tool" for message in second)
    # The result still reached the model.
    assert "Opened youtube.com." in second[-1]["content"]


def test_text_form_still_carries_images():
    tools = RecordingTools(
        {"look_at_screen": ToolResult("Taken.", ("data:image/png;base64,AAA",))}
    )
    provider, completions = make_provider(
        [[call_chunk(0, "a", "look_at_screen", "{}")], [text_chunk("A terminal.")]],
        vision_model="eyes",
        tool_results_as_text=True,
    )

    list(provider.stream_reply(HELLO, tools))

    parts = completions.requests[1]["messages"][-1]["content"]
    assert any(part.get("type") == "image_url" for part in parts)


def test_text_spoken_before_a_tool_call_is_kept():
    """It was already streamed to the speaker, so it has to be in the history."""
    tools = RecordingTools()
    provider, completions = make_provider(
        [
            [text_chunk("One sec. "), call_chunk(0, "a", "look_at_screen", "{}")],
            [text_chunk("It's a terminal.")],
        ]
    )

    spoken = list(provider.stream_reply(HELLO, tools))

    assert spoken == ["One sec. ", "It's a terminal."]
    assert completions.requests[1]["messages"][1]["content"] == "One sec. "


def test_the_loop_stops_offering_tools_and_ends():
    """A model that keeps calling tools must still produce an answer."""
    tools = RecordingTools()
    looping = [[call_chunk(0, f"c{i}", "look_at_screen", "{}")] for i in range(3)]
    provider, completions = make_provider([*looping, [text_chunk("Finally, words.")]])

    assert list(provider.stream_reply(HELLO, tools, )) == ["Finally, words."]

    # Three tool rounds, then a fourth request with no tools offered at all.
    assert len(completions.requests) == 4
    assert "tools" not in completions.requests[-1]


def test_tool_rounds_are_configurable():
    tools = RecordingTools()
    provider, completions = make_provider(
        [[call_chunk(0, "a", "look_at_screen", "{}")], [text_chunk("done")]],
        max_tool_rounds=1,
    )

    list(provider.stream_reply(HELLO, tools))

    assert len(completions.requests) == 2
    assert "tools" not in completions.requests[1]


def test_a_rejected_tool_call_retries_without_tools():
    """A tool call the service refuses must not become silence.

    Groq rejects a malformed tool call with a generic error mid-stream. Left
    alone that ends the turn, and because the failure is deterministic for a
    given request, every following question fails the same way -- the user
    presses the key five times and hears nothing at all.
    """
    from openai import APIError

    class RefuseThenAnswer:
        def __init__(self) -> None:
            self.requests: list[dict] = []

        def create(self, **request):
            self.requests.append(request)
            if "tools" in request:
                raise APIError(
                    "Failed to call a function. Please adjust your prompt.",
                    request=None,  # type: ignore[arg-type]
                    body=None,
                )
            return iter([text_chunk("Sure, "), text_chunk("what about it?")])

    provider = OpenAICompatibleProvider(api_key="k", model="m")
    completions = RefuseThenAnswer()
    provider._client = SimpleNamespace(chat=SimpleNamespace(completions=completions))

    assert list(provider.stream_reply(HELLO, RecordingTools())) == [
        "Sure, ",
        "what about it?",
    ]
    # Tried with tools, then again without.
    assert len(completions.requests) == 2
    assert "tools" not in completions.requests[1]


def test_a_rejected_tool_call_is_not_retried_after_speaking():
    """Retrying once text is out would say the first part twice."""
    from openai import APIError

    class SpeakThenRefuse:
        def __init__(self) -> None:
            self.requests: list[dict] = []

        def create(self, **request):
            self.requests.append(request)

            def stream():
                yield text_chunk("Let me see. ")
                raise APIError(
                    "Failed to call a function.",
                    request=None,  # type: ignore[arg-type]
                    body=None,
                )

            return stream()

    provider = OpenAICompatibleProvider(api_key="k", model="m")
    completions = SpeakThenRefuse()
    provider._client = SimpleNamespace(chat=SimpleNamespace(completions=completions))

    with pytest.raises(LLMError):
        list(provider.stream_reply(HELLO, RecordingTools()))

    assert len(completions.requests) == 1


def test_a_broken_stream_is_still_classified():
    provider, _ = make_provider([])
    provider._client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **_k: (_ for _ in ()).throw(OSError("socket died"))
            )
        )
    )

    with pytest.raises(LLMConnectionError):
        list(provider.stream_reply(HELLO))


# -- payload shapes ---------------------------------------------------------


def test_plain_message_payload():
    assert _message_payload(Message("user", "hi")) == {"role": "user", "content": "hi"}


def test_tool_message_carries_its_call_id():
    payload = _message_payload(Message("tool", "result", tool_call_id="call_1"))

    assert payload == {"role": "tool", "tool_call_id": "call_1", "content": "result"}


def test_a_silent_tool_request_sends_null_content():
    """Some endpoints reject an empty string where they accept null."""
    payload = _message_payload(
        Message("assistant", "", tool_calls=(ToolCall("a", "look_at_screen"),))
    )

    assert payload["content"] is None


def test_images_become_content_parts():
    payload = _message_payload(Message("user", IMAGE_NOTE, images=("data:image/png;base64,A",)))

    assert payload["content"][0] == {"type": "text", "text": IMAGE_NOTE}
    assert payload["content"][1]["type"] == "image_url"
