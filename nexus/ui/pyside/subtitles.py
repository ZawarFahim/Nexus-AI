import logging
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont

logger = logging.getLogger(__name__)

class SubtitleWindow(QWidget):
    """Cinematic floating subtitles for Nexus and User."""
    
    show_text_requested = Signal(str, str)
    
    def __init__(self, pipeline=None):
        super().__init__()
        self._current_speaker = ""
        self._current_text = ""
        self.pipeline = pipeline
        self.show_text_requested.connect(self._on_show_text, Qt.QueuedConnection)
        
        if self.pipeline:
            self.pipeline.subscribe_user_text(self._on_user_text)
            self.pipeline.subscribe_token(self._on_assistant_token)
            
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool | 
            Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # We will resize dynamically, but start wide
        self.setFixedWidth(800)
        
        self._setup_ui()
        self._position_window()
        self.show()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.label = QLabel("")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFont(QFont("Inter", 24, QFont.Bold))
        self.label.setStyleSheet("color: white; background: transparent;")
        self.label.setWordWrap(True)
        
        # Basic shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(0, 2)
        self.label.setGraphicsEffect(shadow)
        
        layout.addWidget(self.label)
        
    def _position_window(self):
        screen = self.screen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = screen.height() - 150
        self.move(x, y)
        
    def _on_show_text(self, speaker: str, text: str):
        if speaker != self._current_speaker:
            self._current_text = ""
            self._current_speaker = speaker
            
        self._current_text += text
        
        # Dual-color styling using HTML
        speaker_color = "#3498db" if speaker == "User" else "#ffffff"
        formatted = f'<span style="color: {speaker_color}; font-weight: bold;">{speaker}:</span> <span style="color: white;">{self._current_text}</span>'
        
        self.label.setText(formatted)
        self.adjustSize()
        self._position_window()
        self.show()
        
    def _on_user_text(self, text: str):
        # User text comes all at once, so we reset before showing
        self._current_speaker = "" 
        self.show_text_requested.emit("User", text)
        
    def _on_assistant_token(self, text: str):
        self.show_text_requested.emit("Nexus", text)
