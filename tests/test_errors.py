"""Tests for failure handling.

This is the code that only runs when something is already broken, which is
exactly when nobody is watching. A wrong branch here turns a dropped Wi-Fi
connection into silence, and silence is indistinguishable from Nexus crashing.
"""

from __future__ import annotations

import httpx
import pytest
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    InternalServerError,
    OpenAIError,
    RateLimitError,
)

from nexus.core.protocols import (
    LLMAuthError,
    LLMConnectionError,
    LLMError,
    LLMQuotaError,
    LLMRateLimitError,
    LLMToolCallError,
    Transcript,
)
from nexus.llm.openai_compatible import _classify


def response(status: int) -> httpx.Response:
    return httpx.Response(status, request=httpx.Request("POST", "https://example.test"))


@pytest.mark.parametrize(
    ("exception", "expected"),
    [
        (AuthenticationError("bad key", response=response(401), body=None), LLMAuthError),
        (RateLimitError("slow down", response=response(429), body=None), LLMRateLimitError),
        (APIConnectionError(request=httpx.Request("POST", "https://x.test")), LLMConnectionError),
        (APITimeoutError(request=httpx.Request("POST", "https://x.test")), LLMConnectionError),
        (InternalServerError("boom", response=response(500), body=None), LLMConnectionError),
    ],
)
def test_sdk_errors_are_classified(exception, expected):
    assert isinstance(_classify(exception, "groq/test"), expected)


def test_a_daily_quota_is_not_reported_as_a_moment_to_wait():
    """"Give me a moment" is right for a per-minute cap and wrong for a daily one.

    The two arrive as the same exception type and differ only in the message,
    so telling a user to try again shortly when the allowance is gone until
    tomorrow sends them pressing the key for hours.
    """
    exhausted = RateLimitError(
        "Rate limit reached for model `llama-3.3-70b-versatile` on tokens per "
        "day (TPD): Limit 100000, Used 99212",
        response=response(429),
        body=None,
    )

    error = _classify(exhausted, "groq/test")

    assert isinstance(error, LLMQuotaError)
    assert "moment" not in error.spoken
    assert "tomorrow" in error.spoken


def test_a_per_minute_limit_still_says_to_wait_briefly():
    brief = RateLimitError(
        "Rate limit reached on tokens per minute (TPM): Limit 8000",
        response=response(429),
        body=None,
    )

    error = _classify(brief, "groq/test")

    assert isinstance(error, LLMRateLimitError)
    assert not isinstance(error, LLMQuotaError)


def test_a_rejected_tool_call_is_its_own_kind():
    """It is recoverable, so it must be distinguishable from a real failure."""
    refused = OpenAIError("Failed to call a function. Please adjust your prompt.")

    assert isinstance(_classify(refused, "groq/test"), LLMToolCallError)


def test_every_error_has_something_to_say():
    """Nexus speaks these aloud, so an error with no message would be silence."""
    for cls in (LLMError, LLMConnectionError, LLMAuthError, LLMRateLimitError):
        assert cls.spoken
        assert not cls.spoken.endswith(("Error", "Exception"))


def test_error_messages_are_distinct():
    """'I lost my connection' and 'my key stopped working' call for different
    responses from the user, so they must not collapse into one sentence."""
    spoken = {
        cls.spoken
        for cls in (LLMError, LLMConnectionError, LLMAuthError, LLMRateLimitError)
    }
    assert len(spoken) == 4


def test_subclasses_are_catchable_as_llm_error():
    """Callers catch LLMError broadly; a subclass escaping that would kill
    the worker thread."""
    for cls in (LLMConnectionError, LLMAuthError, LLMRateLimitError):
        assert issubclass(cls, LLMError)


def test_empty_transcript_is_detected():
    assert Transcript(text="", language="en", latency=0.1).is_empty
    assert not Transcript(text="hello", language="en", latency=0.1).is_empty
