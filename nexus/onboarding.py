"""First-run setup: what Nexus should call you, the key it thinks with, and the
files it needs before it can hear or speak.

The rules live here and the asking lives in :mod:`nexus.ui.setup`, so the same
flow runs through a terminal during development and through dialogs in a
packaged build. Nothing in this module prints.

The three questions are treated differently on purpose:

* A **name** is optional. Refusing to start because someone declined to
  introduce themselves would be absurd, and Nexus works fine without one.
* A **key** is not. Without it Nexus can hear and speak but cannot answer, and a
  companion that silently fails to reply is worse than one that says plainly
  what it needs.
* The **files** are not optional either, but they are also not a question --
  they are a wait. The only meaningful choice is to cancel.
"""

from __future__ import annotations

import logging

from nexus.core import assets, credentials
from nexus.core import profile as profile_store
from nexus.core.config import Settings
from nexus.core.profile import Profile
from nexus.llm import providers
from nexus.llm.factory import validate_key
from nexus.ui.setup import ConsoleSetup, KeyRequest, SetupUI

logger = logging.getLogger(__name__)

MAX_KEY_ATTEMPTS = 3


class SetupAbandoned(RuntimeError):
    """The user declined to complete setup, so Nexus cannot start."""


def _default_ui(ui: SetupUI | None) -> SetupUI:
    return ui if ui is not None else ConsoleSetup()


# -- name -------------------------------------------------------------------


def ensure_profile(ui: SetupUI | None = None, *, ask: bool = True) -> Profile:
    """Load the stored profile, asking for a name on first run.

    Args:
        ui: How to ask. Defaults to the console.
        ask: Whether to prompt when no name is stored. False leaves a missing
            name missing, for non-interactive contexts.

    Returns:
        The profile, which may have no name.
    """
    profile = profile_store.load()
    if profile.is_complete or not ask:
        return profile

    ui = _default_ui(ui)
    answer = ui.ask_name()
    if answer is None:
        return profile

    profile = profile.with_name(answer)
    if not profile.is_complete:
        ui.say("No problem, carrying on without one.")
        return profile

    profile_store.save(profile)
    ui.say(f"Nice to meet you, {profile.name}.")
    return profile


def set_name(name: str) -> Profile:
    """Store a name directly, bypassing the prompt."""
    profile = Profile().with_name(name)
    profile_store.save(profile)
    return profile


def forget() -> None:
    """Delete the stored name."""
    profile_store.clear()


# -- API key ----------------------------------------------------------------


def ensure_api_key(settings: Settings, ui: SetupUI | None = None, *, ask: bool = True) -> str:
    """Resolve the API key, prompting and validating if necessary.

    Resolution order is environment, then encrypted store, then the user. The
    environment comes first so a developer's ``.env`` keeps working and anyone
    can override a stored key without hunting for the file.

    Args:
        settings: Loaded application settings.
        ui: How to ask. Defaults to the console.
        ask: Whether to prompt when no key is available.

    Returns:
        A key that was accepted by the provider.

    Raises:
        SetupAbandoned: If no usable key could be obtained.
    """
    spec = providers.get(settings.llm_provider) or providers.DEFAULT

    if settings.api_keys.get(spec.name):
        logger.debug("Using %s key from the environment", spec.name)
        return settings.api_keys[spec.name]

    stored = credentials.load_key(spec.name)
    if stored:
        logger.debug("Using stored %s key", spec.name)
        return stored

    # Any configured service will do. Someone who added a second provider and
    # then cleared the first should not be made to set up again.
    for other in providers.ALL:
        if other.name == spec.name:
            continue
        spare = settings.api_keys.get(other.name) or credentials.load_key(other.name)
        if spare:
            logger.info("No %s key; using %s instead", spec.name, other.name)
            return spare

    if not ask:
        raise SetupAbandoned(
            f"No {spec.label} API key. Set {spec.env_var} or run Nexus interactively once."
        )

    ui = _default_ui(ui)
    request = KeyRequest(provider=spec.name, url=spec.key_url, attempts=MAX_KEY_ATTEMPTS)

    key = ui.ask_key(request, lambda candidate: validate_key(spec.name, candidate))
    if not key:
        raise SetupAbandoned("Setup cancelled. Nexus needs a key before it can answer.")

    if not credentials.save_key(spec.name, key):
        ui.say("I could not save that key, so I'll ask for it again next time.")
    return key


def add_provider(
    provider_name: str, settings: Settings, ui: SetupUI | None = None
) -> bool:
    """Ask for a key for an additional service and store it.

    Adding one raises how much Nexus can do in a day without changing anything
    about how it behaves: the extra service is only reached once the preferred
    one has nothing left.

    Returns:
        True if a key was stored.
    """
    spec = providers.get(provider_name)
    if spec is None:
        raise SetupAbandoned(f"I do not know a provider called {provider_name!r}.")

    ui = _default_ui(ui)
    request = KeyRequest(provider=spec.name, url=spec.key_url, attempts=MAX_KEY_ATTEMPTS)

    key = ui.ask_key(request, lambda candidate: validate_key(spec.name, candidate))
    if not key:
        return False

    if not credentials.save_key(spec.name, key):
        ui.say(f"I could not save the {spec.label} key.")
        return False

    ui.say(f"{spec.label} added. Restart Nexus to start using it.")
    return True


def configured_providers(settings: Settings) -> list[str]:
    """Names of every service Nexus currently has a key for."""
    return [
        spec.name
        for spec in providers.ALL
        if settings.api_keys.get(spec.name) or credentials.load_key(spec.name)
    ]


def set_api_key(settings: Settings, key: str) -> str:
    """Validate and store a key supplied directly.

    Raises:
        SetupAbandoned: If the key is rejected.
    """
    spec = providers.get(settings.llm_provider) or providers.DEFAULT
    problem = validate_key(spec.name, key)
    if problem:
        raise SetupAbandoned(problem)
    credentials.save_key(spec.name, key)
    return key


def forget_api_key(settings: Settings, provider_name: str = "") -> None:
    """Delete a stored key. Blank clears every provider Nexus knows about."""
    if provider_name:
        credentials.clear_key(provider_name)
        return
    for spec in providers.ALL:
        credentials.clear_key(spec.name)


def add_provider(
    provider_name: str, settings: Settings, ui: SetupUI | None = None
) -> bool:
    """Ask for a key for an additional service and store it.

    Adding one raises how much Nexus can do in a day without changing how it
    behaves: an extra service is reached only once the preferred one has
    nothing left. This is why it is optional -- demanding three signups before
    Nexus says a word would undo the setup flow it took a whole step to get right.

    Returns:
        True if a key was stored.

    Raises:
        SetupAbandoned: If the provider is not one Nexus knows.
    """
    spec = providers.get(provider_name)
    if spec is None:
        known = ", ".join(providers.names())
        raise SetupAbandoned(f"I don't know a provider called {provider_name!r}. Try: {known}")

    ui = _default_ui(ui)
    request = KeyRequest(provider=spec.name, url=spec.key_url, attempts=MAX_KEY_ATTEMPTS)

    key = ui.ask_key(request, lambda candidate: validate_key(spec.name, candidate))
    if not key:
        return False

    if not credentials.save_key(spec.name, key):
        ui.say(f"I could not save the {spec.label} key.")
        return False

    ui.say(f"{spec.label} added. Restart Nexus to start using it.")
    return True


def configured_providers(settings: Settings) -> list[str]:
    """Names of every service Nexus currently has a key for, in preference order."""
    return [
        spec.name
        for spec in providers.ALL
        if settings.api_keys.get(spec.name) or credentials.load_key(spec.name)
    ]


# -- downloaded files -------------------------------------------------------


def ensure_assets(settings: Settings, ui: SetupUI | None = None) -> None:
    """Download the speech model and voice if they are not already present.

    Runs before anything is constructed, because the voice's sample rate is
    read from a file that has to exist first, and because a user who cancels
    should not have a microphone opened on them.

    Raises:
        SetupAbandoned: If the files could not be fetched.
    """
    # Imported here rather than at module scope: this pulls in ctranslate2,
    # which is slow to load and pointless for --forget or --name.
    from nexus.stt.whisper import detect_profile

    model = detect_profile(settings.device).name

    try:
        missing = assets.required(model=model, voice=settings.voice)
    except assets.AssetError as exc:
        raise SetupAbandoned(str(exc)) from exc

    if not missing:
        logger.debug("All assets present")
        return

    total = sum(item.approx_bytes for item in missing) / 1e6
    logger.info("Fetching %d missing file(s), about %.0f MB", len(missing), total)

    try:
        _default_ui(ui).fetch_assets(missing)
    except assets.AssetError as exc:
        raise SetupAbandoned(
            f"{exc}\n\nStart Nexus again to continue from where it stopped."
        ) from exc
