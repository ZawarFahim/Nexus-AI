"""Tests for assembling the provider chain from configuration.

The rule worth guarding is that a service contributes one entry per model, not
one entry total. Free allowances are metered per model -- Groq's own error
names the model rather than the account -- so a spent quota on the best model
says nothing about the next one. Collapsing them to a single entry means
hitting the same wall and giving up while a perfectly good allowance sits
unused on the same key.
"""

from __future__ import annotations

import pytest

from nexus.core.config import Settings
from nexus.core.protocols import LLMError
from nexus.llm import providers
from nexus.llm.chain import ProviderChain
from nexus.llm.factory import configured, create_provider


@pytest.fixture(autouse=True)
def no_stored_keys(monkeypatch):
    """Ignore whatever is in the real credential store."""
    monkeypatch.setattr("nexus.llm.factory.credentials.load_key", lambda _name: "")


def settings(**keys) -> Settings:
    return Settings(llm_provider="groq", api_keys=keys)


def test_a_service_contributes_one_entry_per_model():
    chain = create_provider(settings(groq="k"))

    assert isinstance(chain, ProviderChain)
    assert len(chain) == len(providers.GROQ.models)
    assert len(chain) > 1, "the fallback models are the point"


def test_the_best_model_is_tried_first():
    chain = create_provider(settings(groq="k"))

    assert providers.GROQ.model in chain.primary.name


def test_every_configured_service_is_included():
    chain = create_provider(settings(groq="k", gemini="g"))

    names = chain.name
    assert providers.GROQ.model in names
    assert providers.GEMINI.model in names


def test_services_come_in_preference_order():
    """Vision-capable first, so "what am I looking at" survives longest."""
    chain = create_provider(settings(groq="k", gemini="g", cerebras="c"))
    order = chain.name

    assert order.index("groq") < order.index("gemini") < order.index("cerebras")


def test_a_model_override_applies_only_to_the_first_entry():
    """Applied to every entry it would name a model the others never heard of."""
    chosen = Settings(llm_provider="groq", api_keys={"groq": "k"}, llm_model="my-model")

    chain = create_provider(chosen)

    assert "my-model" in chain.primary.name
    # The fallbacks keep their own names, or there would be nothing to fall to.
    assert providers.GROQ.fallback_models[0] in chain.name


def test_no_key_anywhere_is_an_error_not_an_empty_chain():
    with pytest.raises(LLMError, match="No API key"):
        create_provider(settings())


def test_configured_lists_only_services_with_keys():
    assert [spec.name for spec in configured(settings(gemini="g"))] == ["gemini"]


def test_the_preferred_service_leads_even_when_it_is_not_the_default():
    chosen = Settings(llm_provider="gemini", api_keys={"groq": "k", "gemini": "g"})

    assert [spec.name for spec in configured(chosen)] == ["gemini", "groq"]


def test_every_provider_names_a_place_to_get_a_key():
    for spec in providers.ALL:
        assert spec.key_url.startswith("https://")
        assert spec.signup_note
        assert spec.env_var.endswith("_API_KEY")
