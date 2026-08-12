import sys
from typing import Any
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath

from nexus.ui.pyside.styles import STYLESHEET, COLORS
from nexus.ui.pyside.bridge import NexusBridge
from nexus.ui.pyside.widgets.chat import ChatWidget
from nexus.ui.pyside.widgets.input import InputWidget
from nexus.ui.pyside.widgets.activity import ToolActivityCard
from nexus.core.state import State

class OverlayWindow(QMainWindow):
    """Sleek Frameless window overlay for Nexus."""
    
    def __init__(self, pipeline=None):
        super().__init__()
        self.pipeline = pipeline
        self.bridge = NexusBridge(pipeline) if pipeline else None
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(450, 700)
        self.oldPos = self.pos()

        self._setup_ui()
        self._setup_animations()

    def _setup_ui(self):
        # Central transparent widget to hold the layout
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        
        layout = QVBoxLayout(self.central_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Main background container with rounded corners and shadow
        self.bg_container = QWidget(self.central_widget)
        self.bg_container.setObjectName("BgContainer")
        self.bg_container.setStyleSheet(f"""
            #BgContainer {{
                background-color: {COLORS['bg_main']};
                border-radius: 15px;
                border: 1px solid #1E1E24;
            }}
        """)
        layout.addWidget(self.bg_container)

        # Drop shadow for the futuristic float effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 5)
        self.bg_container.setGraphicsEffect(shadow)

        self.main_layout = QVBoxLayout(self.bg_container)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self._build_header()
        
        # Chat area
        self.chat_widget = ChatWidget(self)
        self.main_layout.addWidget(self.chat_widget, 1)
        
        # Input area
        self.input_widget = InputWidget(self)
        self.main_layout.addWidget(self.input_widget)
        
        if self.bridge:
            self._connect_bridge()
            
        self.chat_widget.show_empty_state(self._on_quick_action)

    def _connect_bridge(self):
        self.bridge.token_received.connect(self.chat_widget.append_nexus_token, Qt.QueuedConnection)
        self.bridge.user_text_received.connect(self.chat_widget.add_user_message, Qt.QueuedConnection)
        self.bridge.state_changed.connect(self.on_state, Qt.QueuedConnection)
        self.bridge.tool_activity.connect(self._on_tool_activity, Qt.QueuedConnection)
        
        self.input_widget.submitted.connect(self.bridge.submit_text)
        self.input_widget.escaped.connect(self._on_escape)
        
    def _on_quick_action(self, cmd: str):
        self.input_widget.set_text(cmd)

    def _on_escape(self):
        if self.pipeline and self.pipeline.state.current in (State.THINKING, State.SPEAKING):
            self.bridge.abort()
        else:
            self.hide_overlay()
            
    def _on_tool_activity(self, name: str, status: str, details: Any = None):
        self.chat_widget.handle_tool_activity(name, status, details)

    def on_state(self, state: State):
        names = {
            State.IDLE: "READY",
            State.LISTENING: "LISTENING",
            State.THINKING: "THINKING",
            State.SPEAKING: "RESPONDING"
        }
        status = names.get(state, "READY")
        color = COLORS["success"] if status == "READY" else COLORS["accent"]
        self.status_label.setText(f"● {status}")
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 12px; letter-spacing: 1px;")

    def _build_header(self):
        self.header = QWidget()
        self.header.setFixedHeight(50)
        self.header.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['bg_secondary']};
                border-top-left-radius: 15px;
                border-top-right-radius: 15px;
                border-bottom: 1px solid #1E1E24;
            }}
        """)
        h_layout = QHBoxLayout(self.header)
        h_layout.setContentsMargins(15, 0, 15, 0)
        
        title = QLabel("◉ NEXUS")
        font = QFont("Segoe UI", 12, QFont.Bold)
        title.setFont(font)
        title.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent; border: none;")
        h_layout.addWidget(title)
        
        h_layout.addStretch()
        
        self.status_label = QLabel("● READY")
        self.status_label.setObjectName("HeaderStatus")
        self.status_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        h_layout.addWidget(self.status_label)
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #94A3B8;
                font-size: 16px;
                font-weight: bold;
                border-radius: 12px;
            }
            QPushButton:hover {
                background: #ef4444;
                color: white;
            }
        """)
        close_btn.clicked.connect(self.hide_overlay)
        h_layout.addWidget(close_btn)
        
        self.main_layout.addWidget(self.header)

    def _setup_animations(self):
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.OutExpo)

    def show_overlay(self):
        # Drop down animation from top of screen or just fade in
        screen_geometry = self.screen().availableGeometry()
        w, h = 450, 700
        x = (screen_geometry.width() - w) // 2
        y = (screen_geometry.height() - h) // 2

        self.setGeometry(x, y - 50, w, h)
        self.setWindowOpacity(0.0)
        self.show()
        
        self.anim.setStartValue(QRect(x, y - 50, w, h))
        self.anim.setEndValue(QRect(x, y, w, h))
        
        self.opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_anim.setDuration(250)
        self.opacity_anim.setStartValue(0.0)
        self.opacity_anim.setEndValue(1.0)
        
        self.anim.start()
        self.opacity_anim.start()
        
        self.input_widget.entry.setFocus()

    def hide_overlay(self):
        self.hide()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.header.geometry().contains(event.pos()):
            self.oldPos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if hasattr(self, 'oldPos') and self.oldPos:
            delta = event.globalPosition().toPoint() - self.oldPos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.oldPos = None
