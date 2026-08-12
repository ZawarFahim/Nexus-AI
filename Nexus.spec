# PyInstaller recipe for Nexus.
#
# Two things here are not obvious and both were found by the build failing.
#
# ctranslate2 and onnxruntime load their DLLs by name at runtime rather than
# importing them, so PyInstaller's scanner cannot see them: the build succeeds
# and the executable dies on launch. They are collected explicitly.
#
# The build produces a folder rather than a single file, deliberately. One-file
# mode unpacks two hundred megabytes to a temporary directory on every launch,
# which is seconds of delay before Nexus starts loading a speech model -- on an
# application whose whole point is answering quickly. The installer hides the
# folder from the user anyway, so single-file buys nothing here.
#
#     python -m PyInstaller Nexus.spec --noconfirm
#
# The executable is a console application that hides its own window. That is
# not a style choice: see CONSOLE below.

import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files

ROOT = Path(SPECPATH)
# Always a console build, and Nexus hides the window itself at startup.
# Smart App Control blocks an unsigned *windowed* executable outright while
# allowing the identical console one -- measured both ways on the same
# machine, same code, same bundle, only this flag different. See
# hide_console in nexus/__main__.py.
CONSOLE = True

# Loaded by filename at runtime; invisible to the import scanner.
binaries = []
for package in ("ctranslate2", "onnxruntime"):
    binaries += collect_dynamic_libs(package)

datas = [
    # The orb's page, and the Piper binary with its own dependencies.
    (str(ROOT / "nexus" / "ui" / "orb" / "index.html"), "nexus/ui/orb"),
    (str(ROOT / "nexus" / "ui" / "orb" / "orb.js"), "nexus/ui/orb"),
    (str(ROOT / "vendor" / "piper"), "vendor/piper"),
]

# faster-whisper ships the Silero voice-activity model as a data file.
datas += collect_data_files("faster_whisper")

hiddenimports = [
    "nexus.ui.orb.window",
    # Selected at runtime by name, so nothing imports them literally.
    "sounddevice",
    "webview.platforms.edgechromium",
    "clr_loader",
    "pythonnet",
]

a = Analysis(
    ["nexus/__main__.py"],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    # PyAV cannot load under Windows code-integrity policies and Nexus never
    # decodes audio files, so it is stubbed at runtime rather than shipped.
    excludes=["av", "tkinter", "test", "unittest"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Nexus",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=CONSOLE,
    icon=str(ROOT / "assets" / "nexus.ico") if (ROOT / "assets" / "nexus.ico").is_file() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Nexus",
)
