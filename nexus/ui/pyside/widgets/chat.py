from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QHBoxLayout, QFrame, QPushButton
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QFont

from nexus.ui.pyside.styles import COLORS
from nexus.ui.pyside.widgets.activity import ToolActivityCard
from nexus.ui.pyside.widgets.visualizer import AudioVisualizerWidget

class ChatWidget(QScrollArea):
    """Chat timeline area."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(15, 15, 15, 15)
        self.content_layout.setSpacing(10)
        self.content_layout.addStretch()
        
        self.setWidget(self.content_widget)
        
        self.current_nexus_bubble = None
        self.active_tool_cards = {}
        self.is_empty = True
        
        # Audio Visualizer pinned at bottom of chat area
        self.visualizer = AudioVisualizerWidget(self.content_widget)
        self.content_layout.addWidget(self.visualizer)

    def add_user_message(self, text: str):
        if self.is_empty:
            self.clear()
            
        self.current_nexus_bubble = None
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 5, 0, 5)
        
        header = QLabel("You")
        header.setStyleSheet(f"color: {COLORS['text_secondary']}; font-weight: bold; font-size: 11px;")
        layout.addWidget(header)
        
        bubble = QLabel(text)
        bubble.setWordWrap(True)
        bubble.setStyleSheet(f"""
            QLabel {{
                background-color: {COLORS['bg_secondary']};
                color: {COLORS['text_primary']};
                padding: 10px;
                border-radius: 8px;
            }}
        """)
        layout.addWidget(bubble)
        
        # Insert before visualizer
        self.content_layout.insertWidget(self.content_layout.count() - 2, container)
        self._scroll_to_bottom()

    def append_nexus_token(self, fragment: str):
        if not self.current_nexus_bubble:
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 5, 0, 5)
            
            header = QLabel("Nexus")
            header.setStyleSheet(f"color: {COLORS['accent']}; font-weight: bold; font-size: 11px;")
            layout.addWidget(header)
            
            self.current_nexus_bubble = QLabel(fragment)
            self.current_nexus_bubble.setWordWrap(True)
            self.current_nexus_bubble.setStyleSheet(f"""
                QLabel {{
                    color: {COLORS['text_primary']};
                    padding: 5px 0px;
                }}
            """)
            layout.addWidget(self.current_nexus_bubble)
            self.content_layout.insertWidget(self.content_layout.count() - 2, container)
        else:
            current_text = self.current_nexus_bubble.text()
            self.current_nexus_bubble.setText(current_text + fragment)
            
        self._scroll_to_bottom()
        
    def handle_tool_activity(self, name: str, status: str, details=None):
        if self.is_empty:
            self.clear()
            
        if status == "started":
            # Add new ToolActivityCard
            card = ToolActivityCard(name, status, details)
            self.content_layout.insertWidget(self.content_layout.count() - 2, card)
            self.active_tool_cards[name] = card
        else:
            card = self.active_tool_cards.get(name)
            if card:
                card.update_status(status, details)
                
        self._scroll_to_bottom()

    def clear(self):
        # Remove all widgets except stretch and visualizer
        while self.content_layout.count() > 2:
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.current_nexus_bubble = None
        self.active_tool_cards.clear()
        self.is_empty = False

    def show_empty_state(self, on_quick_action):
        self.clear()
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignCenter)
        
        welcome = QLabel("Ready for command\n\nSpeak or type what you want me to do.")
        welcome.setAlignment(Qt.AlignCenter)
        welcome.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        layout.addWidget(welcome)
        
        # Quick Actions
        actions_layout = QHBoxLayout()
        actions = [
            ("👁 Analyze Screen", "What am I looking at?"),
            ("📁 Find File", "Find my latest PDF"),
            ("🖥 Open App", "Open Spotify")
        ]
        
        for label, cmd in actions:
            # We must use default mutable args for the lambda
            btn = QuickActionButton(label, cmd, on_quick_action)
            actions_layout.addWidget(btn)
            
        layout.addLayout(actions_layout)
        self.content_layout.insertWidget(0, container)
        self.is_empty = True

    def _scroll_to_bottom(self):
        # Need a tiny delay for layout to update before scrolling
        QTimer.singleShot(10, lambda: self.verticalScrollBar().setValue(self.verticalScrollBar().maximum()))

class QuickActionButton(QPushButton):
    def __init__(self, text, cmd, callback):
        super().__init__(text)
        self.cmd = cmd
        self.callback = callback
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {COLORS['accent']};
                color: {COLORS['accent']};
                border-radius: 6px;
                padding: 5px 8px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_glow']};
            }}
        """)
        self.clicked.connect(self._on_click)
        
    def _on_click(self):
        self.callback(self.cmd)
