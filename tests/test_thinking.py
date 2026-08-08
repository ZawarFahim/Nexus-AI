"""Tests for stripping chain-of-thought out of a spoken reply.

The failure this prevents is not subtle: a reasoning model asked "what's two
plus two" produced two hundred and fifteen words of deliberation, a tick
emoji, and a literal closing tag before the answer. Spoken aloud that is the
whole product broken.

Streaming is what makes it fiddly. A tag arrives in pieces, so ``<thi`` can end
one fragment and ``nk>`` begin the next, and a filter that only looked at whole
fragments would leak both halves.
"""

from __future__ import annotations

import pytest

from nexus.llm.thinking import strip_thinking


def joined(fragments) -> str:
    return "".join(strip_thinking(fragments))


def test_text_without_thinking_is_untouched():
    assert joined(["Hello ", "there."]) == "Hello there."


def test_a_whole_block_is_removed():
    assert joined(["<think>hmm</think>Four."]) == "Four."


def test_a_block_split_across_fragments_is_removed():
    assert joined(["<think>", "let me ", "consider", "</think>", "Four."]) == "Four."


def test_a_tag_split_mid_word_is_removed():
    """The case a naive per-fragment filter leaks."""
    assert joined(["<thi", "nk>noise</thi", "nk>", "Four."]) == "Four."


def test_the_closing_tag_never_leaks_in_pieces():
    assert "think" not in joined(["<think>a</", "think>Answer."])


def test_text_before_a_block_survives():
    assert joined(["Sure. <think>x</think>", "Four."]) == "Sure. Four."


def test_multiple_blocks_are_all_removed():
    assert joined(["<think>a</think>One. <think>b</think>Two."]) == "One. Two."


def test_an_unclosed_block_yields_nothing():
    """A reply cut off mid-thought has no answer in it; speaking it is worse."""
    assert joined(["<think>still going and going"]) == ""


def test_an_angle_bracket_that_is_not_a_tag_is_kept():
    assert joined(["Use ", "a < b ", "to compare."]) == "Use a < b to compare."


def test_text_resembling_the_tag_prefix_is_kept():
    """Held-back characters have to be released, not swallowed."""
    assert joined(["I was <thin", "king about it."]) == "I was <thinking about it."


def test_nothing_is_emitted_before_it_is_known_to_be_safe():
    """A partial tag must never reach the synthesiser, even briefly."""
    pieces = list(strip_thinking(iter(["Answer<thi", "nk>hidden</think>!"])))

    assert "".join(pieces) == "Answer!"
    assert all("<thi" not in piece for piece in pieces)


def test_streaming_is_lazy():
    """Fragments must flow as they arrive, not after the stream completes."""
    consumed: list[str] = []

    def source():
        for text in ("one ", "two ", "three"):
            consumed.append(text)
            yield text

    stream = strip_thinking(source())
    first = next(stream)

    assert first == "one "
    # Only the fragment actually needed has been pulled from the source.
    assert consumed == ["one "]


@pytest.mark.parametrize(
    "fragments",
    [
        ["plain text"],
        ["<think>x</think>ok"],
        ["a", "b", "c"],
        ["<think>", "</think>"],
    ],
)
def test_never_emits_a_tag(fragments):
    result = joined(fragments)

    assert "<think>" not in result
    assert "</think>" not in result
