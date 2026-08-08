"""Tests for browser control.

Two things here can do real damage if they are wrong, and neither announces
itself. Sending navigation keys to a window that is not a browser types into
whatever is: an editor, a terminal, a chat box. And deciding what counts as a
browser by window class classifies every Electron application -- Visual Studio
Code included -- as one, which is how Nexus would end up paging through source
code instead of a web page.

So the focus check is tested harder than the keystrokes are.
"""

from __future__ import annotations

import pytest

from nexus.tools import browser


class FakeWindows:
    """Stands in for the Win32 layer, recording what was sent."""

    def __init__(self, *, title="", executable="", hwnd=1234, accept=True) -> None:
        self._title = title
        self._executable = executable
        self._hwnd = hwnd
        self._accept = accept
        self.sent: list[tuple[int, ...]] = []

    # -- the parts browser.py uses --
    def foreground_window(self) -> int:
        return self._hwnd

    def window_title(self, _hwnd) -> str:
        return self._title

    def window_process_id(self, _hwnd) -> int:
        return 99

    def process_name(self, _pid) -> str:
        return self._executable

    def send_keys(self, *keys) -> bool:
        self.sent.append(keys)
        return self._accept

    def __getattr__(self, name):
        # Virtual key constants and anything else pass through to the real
        # module, so the fake only has to model behaviour, not data.
        from nexus.input import win32

        return getattr(win32, name)


@pytest.fixture
def windows(monkeypatch):
    def install(**kwargs) -> FakeWindows:
        fake = FakeWindows(**kwargs)
        monkeypatch.setattr(browser, "win32", fake)
        return fake

    return install


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    """Strip the settle and repeat delays so tests are not paced by sleeps."""
    monkeypatch.setattr(browser.time, "sleep", lambda _seconds: None)


CHROME = {"title": "Wikipedia - Google Chrome", "executable": "chrome.exe"}
VSCODE = {"title": "app.py - Visual Studio Code", "executable": "code.exe"}


# -- what counts as a browser -----------------------------------------------


@pytest.mark.parametrize(
    "executable",
    ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "vivaldi.exe"],
)
def test_real_browsers_are_recognised(windows, executable):
    windows(title="A page", executable=executable)

    focused, _what = browser.is_browser_focused()

    assert focused


def test_vs_code_is_not_a_browser(windows):
    """It reports Chrome's window class, which is why the check uses the exe."""
    windows(**VSCODE)

    focused, what = browser.is_browser_focused()

    assert not focused
    assert "Visual Studio Code" in what


@pytest.mark.parametrize("executable", ["code.exe", "slack.exe", "discord.exe", "explorer.exe"])
def test_other_electron_apps_are_not_browsers(windows, executable):
    windows(title="Something", executable=executable)

    assert browser.is_browser_focused()[0] is False


def test_no_foreground_window_is_not_a_browser(windows):
    windows(hwnd=0)

    focused, what = browser.is_browser_focused()

    assert not focused
    assert what == "nothing"


# -- navigating --------------------------------------------------------------


def test_scrolling_sends_page_down(windows):
    fake = windows(**CHROME)

    result = browser._run_control({"action": "scroll_down"})

    assert fake.sent == [(browser.win32.VK_NEXT,)]
    assert "scroll down" in result.content


def test_repeating_sends_the_key_that_many_times(windows):
    fake = windows(**CHROME)

    browser._run_control({"action": "scroll_down", "times": 3})

    assert len(fake.sent) == 3


def test_repeats_are_capped(windows):
    """A model asking for a thousand scrolls must not lock up the machine."""
    fake = windows(**CHROME)

    browser._run_control({"action": "scroll_down", "times": 10_000})

    assert len(fake.sent) == browser.MAX_REPEATS


def test_a_nonsense_repeat_count_falls_back_to_one(windows):
    fake = windows(**CHROME)

    browser._run_control({"action": "scroll_down", "times": "lots"})

    assert len(fake.sent) == 1


def test_going_back_is_alt_left(windows):
    fake = windows(**CHROME)

    browser._run_control({"action": "back"})

    assert fake.sent == [(browser.win32.VK_MENU, browser.win32.VK_LEFT)]


def test_nothing_is_sent_when_a_browser_is_not_in_front(windows):
    """The whole point of the check: no keystrokes into an editor."""
    fake = windows(**VSCODE)

    result = browser._run_control({"action": "scroll_down"})

    assert fake.sent == []
    assert "not the window in front" in result.content
    assert "Visual Studio Code" in result.content


def test_an_unknown_action_is_reported_not_sent(windows):
    fake = windows(**CHROME)

    result = browser._run_control({"action": "do_a_barrel_roll"})

    assert fake.sent == []
    assert "not something I can do" in result.content


def test_refused_input_becomes_a_message(windows):
    """An elevated window silently swallows synthetic input."""
    windows(**CHROME, accept=False)

    result = browser._run_control({"action": "scroll_down"})

    assert "would not let me" in result.content


def test_every_action_maps_to_real_keys():
    for name, keys in browser.ACTIONS.items():
        assert keys, f"{name} has no keystroke"
        assert all(isinstance(key, int) for key in keys)


# -- opening -----------------------------------------------------------------


@pytest.fixture
def opened(monkeypatch):
    urls: list[str] = []
    monkeypatch.setattr(browser, "open_url", urls.append)
    return urls


def test_an_address_is_opened_directly(opened):
    result = browser._run_open({"target": "youtube.com"})

    assert opened == ["youtube.com"]
    assert "Opened youtube.com" in result.content


def test_words_become_a_web_search(opened):
    browser._run_open({"target": "piper text to speech"})

    assert opened == ["https://www.google.com/search?q=piper+text+to+speech"]


@pytest.mark.parametrize("field", ["target", "url", "query"])
def test_older_argument_names_still_work(opened, field):
    """Models reach for names they were shown in a previous version."""
    browser._run_open({field: "best python tutorial"})

    assert opened[0].startswith("https://www.google.com/search?q=")


def test_the_open_tool_requires_its_one_argument():
    """A schema where everything is optional decodes badly.

    Groq was seen emitting the tool name and its arguments fused into one
    string against the two-optional-parameter version, and rejecting it with
    its own validator -- after which Nexus said nothing at all.
    """
    schema = browser.open_tool().parameters

    assert schema["required"] == ["target"]
    assert list(schema["properties"]) == ["target"]


def test_nothing_to_open_is_reported(opened):
    result = browser._run_open({})

    assert opened == []
    assert "need a website" in result.content


def test_open_url_supplies_a_scheme(monkeypatch):
    seen: list[str] = []
    monkeypatch.setattr(browser.webbrowser, "open", lambda url, new=0: seen.append(url) or True)

    browser.open_url("example.com")

    assert seen == ["https://example.com"]


def test_open_url_leaves_an_existing_scheme_alone(monkeypatch):
    seen: list[str] = []
    monkeypatch.setattr(browser.webbrowser, "open", lambda url, new=0: seen.append(url) or True)

    browser.open_url("http://example.com/x")

    assert seen == ["http://example.com/x"]


# -- tool definitions --------------------------------------------------------


def test_the_control_tool_offers_every_action_exactly_once():
    """The enum is the whole menu the model chooses from.

    The description used to repeat this list with a gloss on each entry, which
    cost around two hundred and fifty tokens per request to restate what the
    enum already said. If a name is ever added here, the enum must carry it --
    the description no longer will.
    """
    schema = browser.control_tool().parameters
    description = browser.control_tool().description

    assert schema["properties"]["action"]["enum"] == sorted(browser.ACTIONS)
    assert schema["required"] == ["action"]

    # Names are self-explanatory precisely so the description need not list
    # them. If one stops being so, that is a naming problem, not a prompt one.
    assert not any(name in description for name in browser.ACTIONS)


def test_tool_definitions_stay_small():
    """Every token here is spent on every request, whether a tool is used or not.

    A free API tier is measured in tokens per day, so verbose descriptions are
    not a style question: they are turns the user does not get.
    """
    import json

    for tool in (browser.control_tool(), browser.open_tool()):
        approximate_tokens = len(json.dumps(tool.spec())) // 4
        assert approximate_tokens < 180, f"{tool.name} costs ~{approximate_tokens} tokens"
