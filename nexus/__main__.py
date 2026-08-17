"""Nexus's entry point.

Run with::

    python -m nexus                 # tray application
    python -m nexus --name Mickey   # change what Nexus calls you
    python -m nexus --set-key       # replace the stored API key
    python -m nexus --console       # verbose logging, no tray
    python -m nexus --windowed-setup  # see setup exactly as a packaged user does

This is what the packaged executable will launch, so everything a normal user
depends on -- first-run setup, the single-instance check, the tray, orderly
shutdown -- lives here rather than in a demo script.

Nothing that a user needs to read is printed. A packaged build is a windowed
program with no console attached, so ``print`` there writes to nowhere: the
difference between a printed error and no error at all is invisible to the
person holding the mouse.
"""

from __future__ import annotations

import argparse
import logging
import sys

from nexus import app, onboarding
from nexus.core import logging as nexus_logging
from nexus.core import paths
from nexus.core import profile as profile_store
from nexus.core.config import load_settings
from nexus.core.protocols import LLMError
from nexus.core.single_instance import SingleInstance
from nexus.tools.notify import send_windows_notification
from nexus.ui.setup import ConsoleSetup, SetupUI

logger = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="ev", description="Nexus, a desktop AI companion.")
    parser.add_argument("--name", help="set what Nexus calls you, then start")
    parser.add_argument("--set-key", action="store_true", help="replace the stored API key")
    parser.add_argument(
        "--forget", action="store_true", help="delete the stored name and keys, then exit"
    )
    parser.add_argument(
        "--add-provider",
        metavar="NAME",
        help=(
            "add a second AI service so Nexus keeps working after one runs out of "
            "free usage, then exit. Use --providers to see the choices."
        ),
    )
    parser.add_argument(
        "--providers",
        action="store_true",
        help="list the AI services Nexus can use and which are set up, then exit",
    )
    parser.add_argument(
        "--console",
        action="store_true",
        help="log verbosely to the terminal instead of running quietly",
    )
    parser.add_argument(
        "--no-tray", action="store_true", help="run without a tray icon (for debugging)"
    )
    parser.add_argument(
        "--windowed-setup",
        action="store_true",
        help="use setup dialogs even when a console is attached (for testing)",
    )
    return parser.parse_args(argv)


def choose_setup_ui(args: argparse.Namespace) -> SetupUI:
    """Pick between dialogs and the terminal for first-run questions.

    A packaged build has no console: printing a question there sends it
    nowhere and reads end-of-file immediately, so the user sees an icon that
    flashes and disappears. Running from a checkout keeps the console flow,
    where a terminal is already open and a dialog would be an interruption.
    """
    if args.console and not args.windowed_setup:
        return ConsoleSetup()
    if not (paths.is_frozen() or args.windowed_setup):
        return ConsoleSetup()

    try:
        from nexus.ui.dialogs import WindowSetup

        return WindowSetup()
    except ImportError:
        # Tkinter is standard library but can be absent from a stripped build.
        # Falling back is better than failing setup outright, even if the
        # prompts land somewhere the user cannot see them.
        logger.warning("Setup dialogs unavailable; falling back to the console")
        return ConsoleSetup()


def hide_console() -> None:
    """Hide the terminal a packaged build is attached to.

    Nexus is built as a console application and then hides its window, which
    looks like a workaround because it is one. Windows Smart App Control
    blocks an unsigned *windowed* executable outright -- "an Application
    Control policy has blocked this file" -- while allowing the identical
    console build. Measured both ways on the same machine: same code, same
    bundle, only the bootloader flag different.

    The cost is a console window visible for a fraction of a second at launch.
    That is worth paying to be runnable at all on a clean Windows 11 install,
    where the policy is on by default and cannot be turned off again without
    reinstalling the operating system.
    """
    if not paths.is_frozen():
        return
    try:
        import ctypes

        window = ctypes.windll.kernel32.GetConsoleWindow()
        if window:
            ctypes.windll.user32.ShowWindow(window, 0)  # SW_HIDE
    except Exception:  # noqa: BLE001 -- cosmetic; never worth failing over
        logger.debug("Could not hide the console", exc_info=True)


def main(argv: list[str] | None = None) -> int:
    # Checked before anything else, including argument parsing. A packaged
    # build has no second executable to run the orb from, so Nexus re-runs
    # itself with this flag; that process must become the orb and nothing
    # else, without claiming the microphone or the single-instance lock.
    if argv is None and "--orb" in sys.argv[1:]:
        from nexus.ui.orb.window import run as run_orb

        return run_orb()

    # Kept visible only when explicitly asked for, so a user double-clicking
    # the application does not get a terminal alongside it.
    if "--console" not in (argv if argv is not None else sys.argv[1:]):
        hide_console()

    return _main(argv)


def _main(argv: list[str] | None = None) -> int:
    """Start Nexus.

    Returns:
        A process exit code.
    """
    args = parse_args(argv)

    # Before anything reads a stored name or key: the project used to be called
    # something else, and its settings directory was named after it.
    paths.adopt_legacy_data()

    settings = load_settings()

    nexus_logging.configure(
        level="DEBUG" if args.console else settings.log_level,
        quiet_libraries=not args.console,
        to_file=True,
    )

    if args.forget:
        onboarding.forget()
        onboarding.forget_api_key(settings)
        print(f"Forgot everything stored in {profile_store.data_dir()}")
        return 0

    if args.providers:
        _list_providers(settings)
        return 0

    if args.add_provider:
        ui = choose_setup_ui(args)
        try:
            return 0 if onboarding.add_provider(args.add_provider, settings, ui) else 1
        except onboarding.SetupAbandoned as exc:
            ui.say(str(exc))
            return 1
        finally:
            ui.close()

    # Claimed before any device is opened, so a second copy cannot briefly
    # grab the microphone before discovering it should not have started.
    instance = SingleInstance()
    if not instance.acquire():
        # Said through the UI rather than printed: double-clicking a desktop
        # shortcut twice is the common way to reach this, and from a shortcut
        # there is nowhere for a printed line to appear.
        ui = choose_setup_ui(args)
        try:
            ui.say("Nexus is already running. Look for the icon in your system tray.")
        finally:
            ui.close()
        return 1

    try:
        return _run(args, settings)
    finally:
        instance.release()


def _run(args: argparse.Namespace, settings) -> int:
    ui = choose_setup_ui(args)
    try:
        return _start(args, settings, ui)
    finally:
        # Idempotent, so the normal path closing it early is fine.
        ui.close()


def _start(args: argparse.Namespace, settings, ui: SetupUI) -> int:
    """Complete setup, build Nexus, and hand over to the tray.

    Every failure here is reported through ``ui`` rather than printed. In a
    packaged build there is no console, so a printed message is the same as no
    message -- the user double-clicks Nexus and nothing whatsoever happens.
    """
    from nexus.ui.pyside.app import init_app
    app_instance = init_app()

    if args.set_key:
        onboarding.forget_api_key(settings)

    try:
        profile = (
            onboarding.set_name(args.name)
            if args.name
            else onboarding.ensure_profile(ui)
        )

        api_key = onboarding.ensure_api_key(settings, ui)
        # Last, because it is the slow one: no point spending minutes on a
        # download for someone who was going to abandon setup at the key.
        onboarding.ensure_assets(settings, ui)
    except onboarding.SetupAbandoned as exc:
        ui.say(str(exc))
        return 1

    try:
        components = app.build(settings, profile=profile, api_key=api_key)
    except LLMError as exc:
        ui.say(f"Could not start: {exc}")
        return 1

    print("Starting Nexus...")
    try:
        app.start(components)
    except Exception as exc:  # noqa: BLE001 -- report rather than dump a traceback
        logger.exception("Startup failed")
        ui.say(f"Could not start: {exc}\n\nDetails are in {nexus_logging.log_path()}")
        app.shutdown(components)
        return 1

    _print_ready(components, profile)
    # Setup is over; the tray icon is the interface from here.
    ui.close()

    try:
        if args.no_tray:
            _wait_for_interrupt()
        else:
            _run_tray(args, components)
    finally:
        app.shutdown(components)

    return 0


def _run_tray(args: argparse.Namespace, components: app.Components) -> None:
    """Show the tray icon and block until quit.

    Imported here so that ``--no-tray`` still works if pystray is unavailable.
    """
    from nexus.ui.pyside.tray import PySideTray

    from nexus.llm import providers

    settings = load_settings()
    ready = set(onboarding.configured_providers(settings))
    missing = [(spec.name, spec.label) for spec in providers.ALL if spec.name not in ready]

    tray = PySideTray(
        components,
        on_change_name=lambda: _replace_name(args),
        on_change_key=lambda: _replace_key(args, settings),
        add_provider_options=missing,
        on_add_provider=lambda name: _add_provider(args, settings, name),
        on_open_ui=components.desktop_window.show_requested.emit,
    )
    tray.run()
    
    from PySide6.QtWidgets import QApplication
    app_instance = QApplication.instance()
    if app_instance:
        app_instance.exec()


def _add_provider(args: argparse.Namespace, settings, provider_name: str) -> None:
    ui = choose_setup_ui(args)
    try:
        onboarding.add_provider(provider_name, settings, ui)
    except onboarding.SetupAbandoned as exc:
        ui.say(str(exc))
    finally:
        ui.close()


def _replace_name(args: argparse.Namespace) -> None:
    """Ask for a new name from the tray menu.

    Clearing the stored name first is what makes this work at all: asking is
    conditional on there not being one, so the menu entry previously returned
    immediately without prompting.
    """
    ui = choose_setup_ui(args)
    try:
        onboarding.forget()
        onboarding.ensure_profile(ui)
        ui.say("I'll use that from the next thing you say.")
    finally:
        ui.close()


def _replace_key(args: argparse.Namespace, settings) -> None:
    ui = choose_setup_ui(args)
    try:
        onboarding.forget_api_key(settings)
        onboarding.ensure_api_key(settings, ui)
        ui.say("Key updated. Restart Nexus for it to take effect.")
    except onboarding.SetupAbandoned as exc:
        ui.say(f"Key unchanged: {exc}")
    finally:
        ui.close()


def _list_providers(settings) -> None:
    """Show which AI services Nexus can use and which are set up.

    Each has its own free allowance. Adding a second is what keeps Nexus working
    after the first runs out, rather than going quiet until the next day.
    """
    from nexus.llm import providers

    ready = set(onboarding.configured_providers(settings))
    preferred = (providers.get(settings.llm_provider) or providers.DEFAULT).name

    print("\nAI services Nexus can use, in the order it tries them:\n")
    for spec in providers.ALL:
        if spec.name in ready:
            status = "ready (preferred)" if spec.name == preferred else "ready"
        else:
            status = "not set up"
        sees = "" if spec.can_see else "  [cannot see your screen]"
        print(f"  {spec.label:<14} {status:<18}{sees}")
        print(f"  {'':<14} {spec.signup_note}")
        print(f"  {'':<14} {spec.key_url}\n")

    missing = [spec.name for spec in providers.ALL if spec.name not in ready]
    if missing:
        print(f"Add one with:  python -m nexus --add-provider {missing[0]}\n")


def _wait_for_interrupt() -> None:
    import time

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass


def _print_ready(components: app.Components, profile) -> None:
    name = f", {profile.name}" if profile.name else ""
    print(f"\nNexus is ready{name}.")
    print("  Alt+Space        hold to talk")
    print("  Ctrl+Alt+Space   hands-free mode")
    print("  Alt+Shift+Space  open interface")
    print("  Ctrl+Shift+Space toggle HUD")
    print(
        "  Nexus lives in your system tray. Windows 11 hides new icons, so\n"
        "  click the ^ arrow next to the clock if you cannot see it.\n"
    )
    send_windows_notification("Nexus Online", "System is fully initialized and ready.")


if __name__ == "__main__":
    sys.exit(main())
