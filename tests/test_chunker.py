"""Tests for splitting a token stream into speakable sentences.

The chunker decides when Nexus opens its mouth, so a bug here is heard rather
than seen: speech in fragments, or a long silence before the first word.
"""

from __future__ import annotations

import pytest

from nexus.tts.chunker import split_stream


def as_fragments(text: str, size: int = 5) -> list[str]:
    """Chop text the way a language model streams it: mid-word, arbitrarily."""
    return [text[i : i + size] for i in range(0, len(text), size)]


def test_splits_on_sentence_boundaries():
    text = "One thing happened here. Then another thing happened. And a third."
    assert split_stream(as_fragments(text)).__iter__()
    chunks = list(split_stream(as_fragments(text)))
    assert chunks == [
        "One thing happened here.",
        "Then another thing happened.",
        "And a third.",
    ]


def test_emits_nothing_until_a_boundary_arrives():
    """A partial sentence must not be spoken; intonation needs the whole clause."""
    assert list(split_stream(["This is not finished yet"])) == [
        "This is not finished yet"
    ]
    assert list(split_stream(["Finished. ", "Not finished"])) == [
        "Finished.",
        "Not finished",
    ]


def test_first_chunk_may_break_at_a_clause():
    """The opening chunk breaks early so Nexus starts talking sooner."""
    text = "Recursion is when a function calls itself, which sounds odd but works."
    chunks = list(split_stream(as_fragments(text)))
    assert chunks[0] == "Recursion is when a function calls itself,"


def test_later_chunks_do_not_break_at_clauses():
    """Only the first chunk breaks on a comma; doing it throughout would
    chop the reply into fragments and destroy its rhythm."""
    text = "Short one here. Now a much longer sentence, with a comma in it, that keeps going."
    chunks = list(split_stream(as_fragments(text)))
    assert chunks[0] == "Short one here."
    assert chunks[1] == (
        "Now a much longer sentence, with a comma in it, that keeps going."
    )


@pytest.mark.parametrize("text", ["3.14 is pi.", "Costs 1.50 today."])
def test_decimals_do_not_split(text):
    """A period between digits is not a sentence end."""
    assert list(split_stream(as_fragments(text, 3))) == [text.strip()]


def test_long_text_without_punctuation_is_still_emitted():
    """A reply written without punctuation must still get spoken."""
    text = "word " * 200
    chunks = list(split_stream([text]))
    assert chunks
    assert all(len(chunk) <= 320 for chunk in chunks)
    assert "".join(chunks).replace(" ", "") == text.replace(" ", "")


def test_no_empty_chunks():
    chunks = list(split_stream(["Hi.", "  ", "  ", "There.  ", "   "]))
    assert all(chunk.strip() for chunk in chunks)


def test_empty_input_yields_nothing():
    assert list(split_stream([])) == []
    assert list(split_stream(["", "   ", ""])) == []


def test_question_and_exclamation_end_sentences():
    chunks = list(split_stream(as_fragments("Really? Yes! Okay then.")))
    assert chunks == ["Really?", "Yes!", "Okay then."]


def test_fragment_size_does_not_change_the_result():
    """Chunking must depend on the text, not on how the model happened to
    split it -- otherwise output varies run to run."""
    text = "First sentence here. Second one follows. Third arrives last."
    results = {tuple(split_stream(as_fragments(text, n))) for n in (1, 2, 3, 7, 40)}
    assert len(results) == 1
