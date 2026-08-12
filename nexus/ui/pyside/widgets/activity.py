from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt

from nexus.ui.pyside.styles import COLORS

class ToolActivityCard(QFrame):
    """A sleek UI component showing the background activity of a tool."""
    
    def __init__(self, name: str, status: str, details=None, parent=None):
        super().__init__(parent)
        self.name = name
        self.setObjectName("ToolActivity")
        self.setStyleSheet(f"""
            #ToolActivity {{
                background-color: {COLORS['bg_main']};
                border: 1px solid #2D2D35;
                border-radius: 8px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header = QHBoxLayout()
        self.icon_label = QLabel("🛠")
        header.addWidget(self.icon_label)
        
        self.title_label = QLabel(self.name.replace("_", " ").title())
        self.title_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: bold;")
        header.addWidget(self.title_label)
        header.addStretch()
        
        layout.addLayout(header)
        
        # Status Details
        self.details_label = QLabel()
        self.details_label.setWordWrap(True)
        self.details_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        layout.addWidget(self.details_label)
        
        self.update_status(status, details)

    def update_status(self, status: str, details=None):
        if status == "started":
            self.icon_label.setText("⚙")
            self.icon_label.setStyleSheet(f"color: {COLORS['accent']};")
            text = "● Executing..."
        elif status == "completed":
            self.icon_label.setText("✓")
            self.icon_label.setStyleSheet(f"color: {COLORS['success']};")
            text = "✓ Completed"
        elif status == "error":
            self.icon_label.setText("✕")
            self.icon_label.setStyleSheet(f"color: {COLORS['error']};")
            text = "✕ Failed"
        else:
            text = status
            
        if details:
            text += f"\n{details}"
            
        self.details_label.setText(text)
