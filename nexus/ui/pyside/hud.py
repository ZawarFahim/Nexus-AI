import psutil
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont

from nexus.ui.pyside.styles import COLORS
from nexus.core.state import State

class HUDWindow(QWidget):
    """A floating, translucent Heads-Up Display for Nexus system stats."""
    
    toggle_requested = Signal()
    
    def __init__(self, pipeline=None):
        super().__init__()
        self.pipeline = pipeline
        self.toggle_requested.connect(self._on_toggle, Qt.QueuedConnection)
        
        # Transparent, frameless, and click-through
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool | 
            Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(220, 140)
        
        self.is_visible = False
        self._setup_ui()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_stats)
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        self.bg = QWidget(self)
        self.bg.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(10, 10, 12, 180);
                border: 1px solid {COLORS['accent']};
                border-radius: 10px;
            }}
        """)
        bg_layout = QVBoxLayout(self.bg)
        bg_layout.setContentsMargins(15, 15, 15, 15)
        bg_layout.setSpacing(5)
        layout.addWidget(self.bg)
        
        title = QLabel("NEXUS HUD")
        title.setFont(QFont("Consolas", 10, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['accent']}; background: transparent; border: none;")
        bg_layout.addWidget(title)
        
        self.state_label = QLabel("STATUS: READY")
        self.state_label.setFont(QFont("Consolas", 9))
        self.state_label.setStyleSheet(f"color: {COLORS['success']}; background: transparent; border: none;")
        bg_layout.addWidget(self.state_label)
        
        self.cpu_label = QLabel("CPU: --%")
        self.cpu_label.setFont(QFont("Consolas", 9))
        self.cpu_label.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent; border: none;")
        bg_layout.addWidget(self.cpu_label)
        
        self.ram_label = QLabel("RAM: --%")
        self.ram_label.setFont(QFont("Consolas", 9))
        self.ram_label.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent; border: none;")
        bg_layout.addWidget(self.ram_label)
        
        bg_layout.addStretch()

    def _update_stats(self):
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            
            self.cpu_label.setText(f"CPU: {cpu:.1f}%")
            self.ram_label.setText(f"RAM: {ram:.1f}%")
        except Exception:
            pass

    def update_state(self, state: State):
        names = {
            State.IDLE: "READY",
            State.LISTENING: "LISTENING",
            State.THINKING: "THINKING",
            State.SPEAKING: "RESPONDING"
        }
        status = names.get(state, "READY")
        color = COLORS["success"] if status == "READY" else COLORS["accent"]
        self.state_label.setText(f"STATUS: {status}")
        self.state_label.setStyleSheet(f"color: {color}; background: transparent; border: none;")

    def _on_toggle(self):
        if self.is_visible:
            self.hide()
            self.timer.stop()
            self.is_visible = False
        else:
            self._position_window()
            self.show()
            self.timer.start(2000)
            psutil.cpu_percent(interval=None)
            self._update_stats()
            self.is_visible = True

    def _position_window(self):
        screen = self.screen().availableGeometry()
        x = screen.width() - self.width() - 20
        y = screen.height() - self.height() - 20
        self.move(x, y)
