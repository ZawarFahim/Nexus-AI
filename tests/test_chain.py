"""Tests for falling through to the next provider.

The failure this exists to survive is a cliff: a free allowance lasts an
afternoon and then every request fails identically until tomorrow. The failure
it must not *cause* is worse -- starting a second answer over the top of one
the user is already hearing.
"""

from __future__ import annotations

import pytest

from nexus.core.protocols import (
    LLMConnectionError,
    LLMError,
    LLMProvider,
    LLMQuotaError,
    LLMRateLimitError,
    Message,
)
from nexus.llm.chain import ProviderChain

HELLO = [Message("user", "hello")]


class StubProvider:
    """A provider that says its piece, or fails in a scripted way.

    Args:
        label: Its name.
        reply: Fragments to yield.
        error: Raised instead of, or partway through, the reply.
        fail_after: Fragments to yield before raising. Zero fails immediately.
    """

    def __init__(self, label, reply=("ok",), error=None, fail_after=0) -> None:
        self._label = label
        self._reply = tuple(reply)
        self._error = error
        self._fail_after = fail_after
        self.calls = 0
        self.warmed = 0

    @property
    def name(self) -> str:
        return self._label

    def stream_reply(self, messages, tools=None):
        self.calls += 1
        for index, fragment in enumerate(self._reply):
            if self._error is not None and index >= self._fail_after:
                raise self._error
            yield fragment
        if self._error is not None and self._fail_after >= len(self._reply):
            raise self._error

    def warm_up(self) -> bool:
        self.warmed += 1
        return True


def quota(label="groq") -> LLMQuotaError:
    return LLMQuotaError(f"{label} daily quota exhausted")


def test_a_single_provider_behaves_like_itself():
    chain = ProviderChain([StubProvider("groq", ["hi ", "there"])])

    assert list(chain.stream_reply(HELLO)) == ["hi ", "there"]


def test_an_empty_chain_is_a_wiring_error():
    with pytest.raises(ValueError):
        ProviderChain([])


def test_the_first_working_provider_answers():
    first = StubProvider("groq", ["from groq"])
    second = StubProvider("cerebras", ["from cerebras"])

    assert list(ProviderChain([first, second]).stream_reply(HELLO)) == ["from groq"]
    assert second.calls == 0, "the fallback must not be touched unnecessarily"


def test_an_exhausted_provider_falls_through():
    """The whole point: a spent allowance is not the end of the conversation."""
    first = StubProvider("groq", ["never seen"], error=quota())
    second = StubProvider("cerebras", ["from cerebras"])

    assert list(ProviderChain([first, second]).stream_reply(HELLO)) == ["from cerebras"]


def test_it_keeps_going_down_a_long_chain():
    chain = ProviderChain(
        [
            StubProvider("groq", ["a"], error=quota()),
            StubProvider("cerebras", ["b"], error=LLMConnectionError("down")),
            StubProvider("gemini", ["third time lucky"]),
        ]
    )

    assert list(chain.stream_reply(HELLO)) == ["third time lucky"]


def test_any_failure_falls_through_not_just_quota():
    """A service that cannot see an image is as good a reason as a spent quota.

    Enumerating every way a provider can decline would mean getting that list
    wrong, and a missed case is silence.
    """
    blind = StubProvider("cerebras", ["x"], error=LLMError("no image support"))
    seeing = StubProvider("gemini", ["a code editor"])

    assert list(ProviderChain([blind, seeing]).stream_reply(HELLO)) == ["a code editor"]


def test_a_provider_that_fails_after_speaking_ends_the_turn():
    """Never start a second answer over the top of one being spoken."""
    talkative = StubProvider(
        "groq", ["I think ", "the answer ", "is"], error=quota(), fail_after=2
    )
    spare = StubProvider("cerebras", ["completely different reply"])

    chain = ProviderChain([talkative, spare])
    spoken = []

    with pytest.raises(LLMError):
        for fragment in chain.stream_reply(HELLO):
            spoken.append(fragment)

    assert spoken == ["I think ", "the answer "]
    assert spare.calls == 0, "a second reply would talk over the first"


def test_the_preferred_providers_failure_is_what_surfaces():
    """Nexus speaks this aloud, so it must be the one the user can act on.

    Raising whichever provider happened to fail last meant a user whose Groq
    allowance had run out was told that a third service they had never heard
    of wanted a credit card.
    """
    chain = ProviderChain(
        [
            StubProvider("groq", ["a"], error=quota("groq")),
            StubProvider("cerebras", ["b"], error=LLMError("payment required")),
        ]
    )

    with pytest.raises(LLMQuotaError, match="groq"):
        list(chain.stream_reply(HELLO))


def test_a_rate_limited_provider_is_rested():
    """Retrying an exhausted service every turn costs a round trip each time."""
    spent = StubProvider("groq", ["a"], error=quota())
    spare = StubProvider("gemini", ["from gemini"])
    chain = ProviderChain([spent, spare])

    for _ in range(3):
        assert list(chain.stream_reply(HELLO)) == ["from gemini"]

    assert spent.calls == 1, "the exhausted provider was asked again"
    assert spare.calls == 3


def test_resting_expires():
    spent = StubProvider("groq", ["a"], error=quota())
    chain = ProviderChain([spent, StubProvider("gemini", ["b"])])

    list(chain.stream_reply(HELLO))
    assert spent.calls == 1

    # Pretend the cooldown has passed.
    chain._resting.clear()
    list(chain.stream_reply(HELLO))

    assert spent.calls == 2


def test_a_provider_that_recovers_stops_resting():
    """A working turn clears the mark, so a reset allowance is used again."""
    chain = ProviderChain([StubProvider("groq", ["back again"])])

    chain._resting[0] = (0.0, quota())  # Expired, so it should be retried.
    assert list(chain.stream_reply(HELLO)) == ["back again"]
    assert chain._resting == {}


def test_a_resting_provider_still_owns_the_reported_failure():
    """The reason a service is resting is the reason the user needs to hear.

    Skipping the preferred providers meant the only error left to report came
    from the last one in the chain: a user out of Groq for the day was told
    that a third service they had never heard of wanted a credit card.
    """
    chain = ProviderChain(
        [
            StubProvider("groq", ["a"], error=quota("groq")),
            StubProvider("cerebras", ["b"], error=LLMError("402 payment required")),
        ]
    )

    with pytest.raises(LLMQuotaError, match="groq"):
        list(chain.stream_reply(HELLO))

    # Second turn: both are resting now, and the message must not change.
    with pytest.raises(LLMQuotaError, match="groq"):
        list(chain.stream_reply(HELLO))


def test_a_bill_is_rested_far_longer_than_a_rate_limit():
    """A payment problem is the same in sixty seconds; a rate limit is not."""
    from nexus.llm.chain import COOLDOWN_SECONDS, LONG_COOLDOWN_SECONDS, _cooldown_for
    from nexus.core.protocols import LLMAuthError

    assert _cooldown_for(LLMRateLimitError("slow down")) == COOLDOWN_SECONDS
    assert _cooldown_for(quota()) == LONG_COOLDOWN_SECONDS
    assert _cooldown_for(LLMAuthError("bad key")) == LONG_COOLDOWN_SECONDS
    assert _cooldown_for(LLMError("Error code: 402 payment_required")) == LONG_COOLDOWN_SECONDS


def test_a_transient_failure_is_retried_next_turn():
    """A dropped connection says nothing about the next request."""
    flaky = StubProvider("groq", ["a"], error=LLMConnectionError("blip"))
    chain = ProviderChain([flaky, StubProvider("gemini", ["b"])])

    list(chain.stream_reply(HELLO))
    list(chain.stream_reply(HELLO))

    assert flaky.calls == 2, "a one-off network error should not rest a provider"


def test_tools_reach_every_provider():
    sentinel = object()
    seen = []

    class Recorder(StubProvider):
        def stream_reply(self, messages, tools=None):
            seen.append(tools)
            return super().stream_reply(messages, tools)

    chain = ProviderChain(
        [Recorder("groq", ["a"], error=quota()), Recorder("cerebras", ["b"])]
    )
    list(chain.stream_reply(HELLO, sentinel))

    assert seen == [sentinel, sentinel]


def test_every_provider_is_warmed():
    """The fallback is reached when something has already gone wrong.

    Paying a cold connection's setup at that moment lands the delay on someone
    who has just been kept waiting once already.
    """
    providers = [StubProvider("groq"), StubProvider("cerebras"), StubProvider("gemini")]

    assert ProviderChain(providers).warm_up() is True
    assert all(provider.warmed == 1 for provider in providers)


def test_warming_survives_an_unreachable_provider():
    class Broken(StubProvider):
        def warm_up(self):
            raise RuntimeError("no network")

    chain = ProviderChain([Broken("groq"), StubProvider("cerebras")])

    assert chain.warm_up() is True


def test_the_chain_satisfies_the_provider_protocol():
    assert isinstance(ProviderChain([StubProvider("groq")]), LLMProvider)


def test_the_name_lists_the_order():
    chain = ProviderChain([StubProvider("groq"), StubProvider("cerebras")])

    assert chain.name == "groq then cerebras"
