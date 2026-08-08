"""Tests for the keyboard hook's classification rules.

The hook itself needs Windows to install it, but the classification it does can
be driven directly, which is where the behaviour that matters lives.

The injected-event rule is the one worth guarding. Nexus synthesises keystrokes to
drive the browser, and its own low-level hook sees them exactly as if they had
been typed: pressing Alt+Left to go back registers Alt as held, so the next
Space fires push-to-talk. Nexus interrupting itself with a key it pressed is the
kind of bug that only appears once two features are used together.
"""

from __future__ import annotations

import ctypes

import pytest

from nexus.input import win32
from nexus.input.hotkey import ALT_SPACE, Chord, HotkeyListener, Modifier


def event(vk_code: int, *, injected: bool = False) -> int:
    """Build a KBDLLHOOKSTRUCT and return its address, as Windows passes it."""
    payload = win32.KBDLLHOOKSTRUCT(
        vkCode=vk_code,
        scanCode=0,
        flags=win32.LLKHF_INJECTED if injected else 0,
        time=0,
        dwExtraInfo=None,
    )
    # Kept alive on the function object: ctypes frees the buffer as soon as the
    # last reference goes, and the address would then point at nothing.
    event.keepalive.append(payload)
    return ctypes.addressof(payload)


event.keepalive = []  # type: ignore[attr-defined]


@pytest.fixture
def listener():
    fired: list[str] = []
    hotkeys = HotkeyListener()
    hotkeys.register(
        ALT_SPACE, lambda: fired.append("press"), lambda: fired.append("release")
    )
    return hotkeys, fired


def send(hotkeys: HotkeyListener, vk_code: int, message: int, *, injected=False) -> int:
    """Push one key event through the hook procedure. Returns its verdict."""
    return hotkeys._hook_procedure(win32.HC_ACTION, message, event(vk_code, injected=injected))


SUPPRESSED = 1


def test_a_real_chord_is_claimed(listener):
    hotkeys, _fired = listener

    send(hotkeys, win32.VK_LMENU, win32.WM_KEYDOWN)
    verdict = send(hotkeys, win32.VK_SPACE, win32.WM_SYSKEYDOWN)

    assert verdict == SUPPRESSED


def test_injected_keys_are_ignored(listener):
    """Nexus's own browser keystrokes must not drive Nexus's own hotkeys."""
    hotkeys, _fired = listener

    send(hotkeys, win32.VK_LMENU, win32.WM_KEYDOWN, injected=True)
    verdict = send(hotkeys, win32.VK_SPACE, win32.WM_SYSKEYDOWN, injected=True)

    assert verdict != SUPPRESSED


def test_an_injected_alt_does_not_leave_alt_held(listener):
    """The specific failure: Alt+Left to go back, then Space starts recording.

    The injected Alt must not be recorded as held, or the user's very next
    Space -- typed while writing a sentence -- looks like Alt+Space.
    """
    hotkeys, _fired = listener

    # Nexus presses Alt+Left to navigate back.
    send(hotkeys, win32.VK_MENU, win32.WM_KEYDOWN, injected=True)
    send(hotkeys, win32.VK_LEFT, win32.WM_KEYDOWN, injected=True)
    send(hotkeys, win32.VK_LEFT, win32.WM_KEYUP, injected=True)
    send(hotkeys, win32.VK_MENU, win32.WM_KEYUP, injected=True)

    # The user then types a space, with no modifier held.
    verdict = send(hotkeys, win32.VK_SPACE, win32.WM_KEYDOWN)

    assert verdict != SUPPRESSED, "a typed space was swallowed as a hotkey"


def test_a_real_space_alone_is_not_claimed(listener):
    hotkeys, _fired = listener

    assert send(hotkeys, win32.VK_SPACE, win32.WM_KEYDOWN) != SUPPRESSED


def test_modifiers_are_never_suppressed(listener):
    """Suppressing Alt would break every other shortcut on the system."""
    hotkeys, _fired = listener

    assert send(hotkeys, win32.VK_LMENU, win32.WM_KEYDOWN) != SUPPRESSED


def test_the_wrong_modifier_set_does_not_match(listener):
    """Chords match exactly, so Ctrl+Alt+Space stays distinct from Alt+Space."""
    hotkeys, _fired = listener

    send(hotkeys, win32.VK_LCONTROL, win32.WM_KEYDOWN)
    send(hotkeys, win32.VK_LMENU, win32.WM_KEYDOWN)
    verdict = send(hotkeys, win32.VK_SPACE, win32.WM_SYSKEYDOWN)

    assert verdict != SUPPRESSED


def test_chords_compare_by_value():
    assert Chord(win32.VK_SPACE, frozenset({Modifier.ALT})) == ALT_SPACE
