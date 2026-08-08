"""Tests for in-session conversation history.

If history silently stops accumulating, Nexus answers every question as if it
were the first -- which reads as the model being stupid rather than as a bug.
"""

from __future__ import annotations

from nexus.llm.conversation import Conversation


def test_system_prompt_leads_the_messages():
    conversation = Conversation("BE HELPFUL")
    assert conversation.messages()[0].role == "system"
    assert conversation.messages()[0].content == "BE HELPFUL"


def test_turns_accumulate_in_order():
    conversation = Conversation("S")
    conversation.add("user", "first")
    conversation.add("assistant", "reply")
    conversation.add("user", "second")

    assert [m.content for m in conversation.messages()] == ["S", "first", "reply", "second"]


def test_oldest_turns_are_evicted_first():
    conversation = Conversation("S", max_turns=4)
    for i in range(6):
        conversation.add("user", f"turn {i}")

    contents = [m.content for m in conversation.messages()]
    assert contents == ["S", "turn 2", "turn 3", "turn 4", "turn 5"]


def test_system_prompt_survives_eviction():
    """The system prompt is held separately, so a long conversation cannot
    push Nexus's personality out of its own context."""
    conversation = Conversation("PERSONALITY", max_turns=2)
    for i in range(20):
        conversation.add("user", f"turn {i}")

    assert conversation.messages()[0].content == "PERSONALITY"
    assert len(conversation.messages()) == 3


def test_rollback_removes_an_unanswered_question():
    conversation = Conversation("system")
    conversation.add("user", "what's on my screen")

    assert conversation.rollback() is True
    assert len(conversation) == 0


def test_rollback_leaves_an_answered_turn_alone():
    conversation = Conversation("system")
    conversation.add("user", "hello")
    conversation.add("assistant", "hey")

    assert conversation.rollback() is False
    assert len(conversation) == 2


def test_rollback_on_empty_history_is_harmless():
    assert Conversation("system").rollback() is False


def test_failures_do_not_pile_up_consecutive_questions():
    """The shape that made one bad turn poison every turn after it.

    Without rollback the history becomes a run of user messages with no
    replies, which models handle badly -- so Nexus kept failing long after the
    original cause had passed.
    """
    conversation = Conversation("system")

    for question in ("open chrome", "search for this", "are you there"):
        conversation.add("user", question)
        conversation.rollback()  # Every turn failed.

    assert len(conversation) == 0

    # A turn that works afterwards starts from a clean history.
    conversation.add("user", "hello")
    conversation.add("assistant", "hey")
    roles = [message.role for message in conversation.messages()]
    assert roles == ["system", "user", "assistant"]


def test_clear_keeps_the_system_prompt():
    conversation = Conversation("S")
    conversation.add("user", "something")
    conversation.clear()

    assert len(conversation) == 0
    assert [m.content for m in conversation.messages()] == ["S"]


def test_length_counts_turns_not_the_system_prompt():
    conversation = Conversation("S")
    assert len(conversation) == 0
    conversation.add("user", "one")
    assert len(conversation) == 1
