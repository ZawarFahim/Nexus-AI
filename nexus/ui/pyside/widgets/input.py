from PySide6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton
from PySide6.QtCore import Qt, Signal

from nexus.ui.pyside.styles import COLORS

class InputWidget(QWidget):
    """Text input area for Nexus."""
    
    submitted = Signal(str)
    escaped = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.history = []
        self.history_idx = -1
        
        self.setFixedHeight(70)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 15)
        
        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Type a command...")
        
        # We need to capture Up/Down/Escape/Enter
        self.entry.installEventFilter(self)
        
        layout.addWidget(self.entry)

    def eventFilter(self, obj, event):
        if obj is self.entry and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                text = self.entry.text().strip()
                if text:
                    self.history.append(text)
                    self.history_idx = len(self.history)
                    self.entry.clear()
                    self.submitted.emit(text)
                return True
            elif event.key() == Qt.Key_Escape:
                self.escaped.emit()
                return True
            elif event.key() == Qt.Key_Up:
                if self.history and self.history_idx > 0:
                    self.history_idx -= 1
                    self.entry.setText(self.history[self.history_idx])
                return True
            elif event.key() == Qt.Key_Down:
                if self.history and self.history_idx < len(self.history) - 1:
                    self.history_idx += 1
                    self.entry.setText(self.history[self.history_idx])
                elif self.history_idx == len(self.history) - 1:
                    self.history_idx += 1
                    self.entry.clear()
                return True
        return super().eventFilter(obj, event)

    def set_text(self, text: str):
        self.entry.setText(text)
        self.entry.setFocus()
