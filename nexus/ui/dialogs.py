from __future__ import annotations

import logging
import threading
from collections.abc import Sequence
from typing import Final
import time

from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QProgressBar, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer

from nexus.core import assets
from nexus.ui import setup as ui_setup
from nexus.ui.pyside.styles import STYLESHEET, COLORS

logger = logging.getLogger(__name__)

APP_TITLE: Final = "Nexus Setup"

class WindowSetup:
    """Setup through PySide6 dialogs. Satisfies SetupUI."""

    def __init__(self) -> None:
        self._ensure_app()

    def _ensure_app(self):
        from nexus.ui.pyside.app import init_app
        self.app = init_app()

    def _create_dialog(self):
        dlg = QDialog()
        dlg.setWindowTitle(APP_TITLE)
        dlg.setFixedSize(500, 250)
        dlg.setStyleSheet(STYLESHEET)
        # Apply dark theme background specifically for dialog since it has no parent styles inherited by default sometimes
        dlg.setStyleSheet(f"QDialog {{ background-color: {COLORS['bg_main']}; }}" + STYLESHEET)
        return dlg

    def ask_name(self) -> str | None:
        dlg = self._create_dialog()
        layout = QVBoxLayout(dlg)
        
        layout.addWidget(QLabel(f"<h2>{ui_setup.NAME_TITLE}</h2>", styleSheet=f"color: {COLORS['accent']};"))
        layout.addWidget(QLabel(ui_setup.NAME_BODY))
        
        entry = QLineEdit()
        layout.addWidget(entry)
        
        layout.addWidget(QLabel(ui_setup.NAME_HINT, styleSheet=f"color: {COLORS['text_secondary']};"))
        
        buttons = QHBoxLayout()
        buttons.addStretch()
        btn = QPushButton("Continue")
        btn.clicked.connect(dlg.accept)
        buttons.addWidget(btn)
        
        layout.addLayout(buttons)
        
        if dlg.exec() == QDialog.Accepted:
            return entry.text()
        return None

    def ask_key(self, request: ui_setup.KeyRequest, validate) -> str | None:
        dlg = self._create_dialog()
        dlg.setFixedSize(550, 300)
        layout = QVBoxLayout(dlg)
        
        layout.addWidget(QLabel(f"<h2>{ui_setup.KEY_TITLE}</h2>", styleSheet=f"color: {COLORS['accent']};"))
        
        body_label = QLabel(request.body)
        body_label.setWordWrap(True)
        layout.addWidget(body_label)
        
        entry = QLineEdit()
        entry.setEchoMode(QLineEdit.Password)
        layout.addWidget(entry)
        
        status = QLabel("")
        status.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(status)
        
        buttons = QHBoxLayout()
        buttons.addStretch()
        btn = QPushButton("Continue")
        buttons.addWidget(btn)
        layout.addLayout(buttons)
        
        result_key = [None]
        
        def on_submit():
            key = entry.text().strip()
            if not key:
                status.setText("Paste your key here first.")
                return
                
            entry.setEnabled(False)
            btn.setEnabled(False)
            status.setText("Checking...")
            
            # Simple off-thread validation to not freeze UI
            def work():
                try:
                    problem = validate(key)
                except Exception as e:
                    problem = str(e)
                # Since we don't have a QThread set up for this specific tiny task, we'll use a timer to poll
                dlg.setProperty("problem", problem)
                dlg.setProperty("key", key)
                dlg.setProperty("done", True)
                
            dlg.setProperty("done", False)
            threading.Thread(target=work, daemon=True).start()
            
        def poll():
            if dlg.property("done"):
                problem = dlg.property("problem")
                key = dlg.property("key")
                if not problem:
                    result_key[0] = key
                    dlg.accept()
                else:
                    status.setText(problem)
                    status.setStyleSheet(f"color: {COLORS['error']};")
                    entry.setEnabled(True)
                    btn.setEnabled(True)
                    entry.setFocus()
            else:
                QTimer.singleShot(100, poll)
                
        btn.clicked.connect(on_submit)
        
        if dlg.exec() == QDialog.Accepted:
            return result_key[0]
        return None

    def fetch_assets(self, items: Sequence[assets.Asset]) -> None:
        dlg = self._create_dialog()
        layout = QVBoxLayout(dlg)
        
        layout.addWidget(QLabel(f"<h2>{ui_setup.DOWNLOAD_TITLE}</h2>", styleSheet=f"color: {COLORS['accent']};"))
        body = QLabel(ui_setup.DOWNLOAD_BODY)
        body.setWordWrap(True)
        layout.addWidget(body)
        
        bar = QProgressBar()
        bar.setRange(0, 1000)
        layout.addWidget(bar)
        
        status = QLabel("Starting...")
        layout.addWidget(status)
        
        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel_btn = QPushButton("Cancel")
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        cancelled = threading.Event()
        state = {"progress": None, "error": None, "done": False}
        
        def on_cancel():
            cancelled.set()
            status.setText("Stopping...")
            
        cancel_btn.clicked.connect(on_cancel)
        
        def work():
            try:
                assets.install(
                    items,
                    on_progress=lambda p: state.__setitem__("progress", p),
                    should_cancel=cancelled.is_set,
                )
            except Exception as e:
                state["error"] = e
            finally:
                state["done"] = True
                
        threading.Thread(target=work, daemon=True).start()
        
        def tick():
            progress = state["progress"]
            if isinstance(progress, assets.Progress):
                bar.setValue(int(progress.fraction * 1000))
                if not cancelled.is_set():
                    status.setText(f"{progress.done_bytes / 1e6:.0f} of {progress.total_bytes / 1e6:.0f} MB")
            
            if state["done"]:
                dlg.accept()
            else:
                QTimer.singleShot(100, tick)
                
        QTimer.singleShot(100, tick)
        dlg.exec()
        
        if state["error"]:
            raise Exception(str(state["error"]))

    def say(self, message: str) -> None:
        QMessageBox.information(None, APP_TITLE, message)

    def close(self) -> None:
        pass
