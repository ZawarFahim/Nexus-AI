"""Build Nexus into a folder of files that runs without Python installed.

Run from the repository root::

    python -m scripts.build              # the real, windowed build
    python -m scripts.build --console    # same, but crashes are visible
    python -m scripts.build --icon       # regenerate the icon and exit

Use ``--console`` while anything is broken. A windowed executable that fails
during startup has nowhere to print why: it simply does not appear, which is
indistinguishable from double-clicking nothing at all.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from nexus.core import paths

ROOT = paths.bundle_dir()
DIST = ROOT / "dist" / "Nexus"
ICON = ROOT / "assets" / "nexus.ico"


def make_icon() -> Path:
    """Draw the application icon at the sizes Windows asks for.

    Generated rather than committed as a binary, from the same drawing the
    tray icon uses, so the two can never drift apart.
    """
    from nexus.core.state import State
    from nexus.ui import icons

    ICON.parent.mkdir(parents=True, exist_ok=True)
    image = icons.for_state(State.IDLE)
    sizes = [(size, size) for size in (16, 24, 32, 48, 64, 128, 256)]
    image.save(ICON, format="ICO", sizes=sizes)
    print(f"icon: {ICON} ({ICON.stat().st_size / 1024:.0f} KB)")
    return ICON


def build(console: bool) -> int:
    """Run PyInstaller and report what came out."""
    if DIST.exists():
        shutil.rmtree(DIST, ignore_errors=True)

    environment = dict(os.environ, NEXUS_BUILD_CONSOLE="1" if console else "0")
    started = time.perf_counter()

    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(ROOT / "Nexus.spec"), "--noconfirm",
         "--distpath", str(ROOT / "dist"), "--workpath", str(ROOT / "build")],
        env=environment,
        cwd=ROOT,
    )
    elapsed = time.perf_counter() - started

    if result.returncode != 0:
        print(f"\nBuild failed after {elapsed:.0f}s")
        return result.returncode

    executable = DIST / "Nexus.exe"
    if not executable.is_file():
        print(f"\nBuild reported success but {executable} is missing")
        return 1

    total = sum(f.stat().st_size for f in DIST.rglob("*") if f.is_file())
    print(f"\nBuilt in {elapsed:.0f}s")
    print(f"  {executable}")
    print(f"  {total / 1e6:.0f} MB across {sum(1 for _ in DIST.rglob('*'))} files")
    print(f"  {'console' if console else 'windowed'} build")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--console", action="store_true",
                        help="keep a terminal attached so startup errors are visible")
    parser.add_argument("--icon", action="store_true", help="regenerate the icon and exit")
    args = parser.parse_args()

    make_icon()
    if args.icon:
        return 0
    return build(args.console)


if __name__ == "__main__":
    sys.exit(main())
