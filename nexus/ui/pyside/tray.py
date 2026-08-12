import logging
from typing import Callable, Sequence
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication, QStyle
from PySide6.QtGui import QIcon, QAction, QPixmap
from PySide6.QtCore import Qt, QObject

from nexus import app
from nexus.core import paths

logger = logging.getLogger(__name__)

class PySideTray(QObject):
    def __init__(
        self,
        components: app.Components,
        on_change_name: Callable[[], None] | None = None,
        on_change_key: Callable[[], None] | None = None,
        add_provider_options: Sequence[tuple[str, str]] = (),
        on_add_provider: Callable[[str], None] | None = None,
        on_open_ui: Callable[[], None] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.components = components
        self.on_change_name = on_change_name
        self.on_change_key = on_change_key
        self.on_open_ui = on_open_ui
        self.add_provider_options = add_provider_options
        self.on_add_provider = on_add_provider
        
        self.tray_icon = QSystemTrayIcon(self)
        icon_path = paths.bundle_dir() / "assets" / "nexus.ico"
        if icon_path.exists():
            self.tray_icon.setIcon(QIcon(str(icon_path)))
        else:
            # Fallback if nexus.ico is missing
            fallback = QPixmap(16, 16)
            fallback.fill(Qt.GlobalColor.gray)
            self.tray_icon.setIcon(QIcon(fallback))
        self.tray_icon.setToolTip("Nexus")
        
        self.menu = QMenu(parent=self.tray_icon.parentWidget() if hasattr(self.tray_icon, "parentWidget") else None)
        self._build_menu()
        self.tray_icon.setContextMenu(self.menu)
        
        self.tray_icon.activated.connect(self._on_tray_activated)
        
        # Connect to pipeline state to change tray icon
        # In a real app we would bridge this via a QThread safe signal
        # For now, it will rely on the pipeline updates.

    def _build_menu(self):
        self.menu.clear()
        
        if self.on_open_ui:
            open_action = QAction("Open Interface", self)
            open_action.triggered.connect(self.on_open_ui)
            self.menu.addAction(open_action)
            self.menu.addSeparator()
            
        hands_free = QAction("Hands-free mode", self)
        hands_free.setCheckable(True)
        hands_free.setChecked(self.components.hands_free.enabled)
        hands_free.triggered.connect(self._toggle_hands_free)
        self.menu.addAction(hands_free)
        
        self.menu.addSeparator()
        
        if self.on_change_name:
            change_name = QAction("Change my name...", self)
            change_name.triggered.connect(self.on_change_name)
            self.menu.addAction(change_name)
            
        if self.on_change_key:
            change_key = QAction("Change API key...", self)
            change_key.triggered.connect(self.on_change_key)
            self.menu.addAction(change_key)
            
        if self.add_provider_options:
            provider_menu = self.menu.addMenu("Add AI service...")
            for name, label in self.add_provider_options:
                action = QAction(label, self)
                # Need to capture name in lambda
                action.triggered.connect(lambda checked=False, n=name: self._add_provider(n))
                provider_menu.addAction(action)
                
        self.menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.exit_app)
        self.menu.addAction(exit_action)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.on_open_ui:
                self.on_open_ui()

    def _toggle_hands_free(self, checked):
        if self.components.hands_free.enabled:
            self.components.pipeline.abort()
        self.components.hands_free.toggle()
        
    def _add_provider(self, name):
        if self.on_add_provider:
            self.on_add_provider(name)

    def run(self):
        self.tray_icon.show()
        
    def exit_app(self):
        # We don't call QApplication.quit() immediately if we want graceful shutdown
        import sys
        from PySide6.QtWidgets import QApplication
        QApplication.instance().quit()
