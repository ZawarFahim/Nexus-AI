"""Styles and animations for PySide6 UI."""

STYLESHEET = """
QWidget {
    background-color: #0A0A0C;
    color: #E2E8F0;
    font-family: 'Segoe UI', 'Inter', sans-serif;
    font-size: 14px;
}

QMainWindow {
    background-color: transparent;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollBar:vertical {
    background: #111115;
    width: 8px;
    margin: 0px 0px 0px 0px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #3884ff;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QLineEdit, QTextEdit {
    background-color: #16161A;
    border: 1px solid #2D2D35;
    border-radius: 12px;
    padding: 12px;
    color: #FFFFFF;
    selection-background-color: #3884ff;
}

QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #3884ff;
}

QPushButton {
    background-color: #3884ff;
    color: white;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: bold;
    border: none;
}

QPushButton:hover {
    background-color: #5599ff;
}

QPushButton:pressed {
    background-color: #1e5eb8;
}

/* Status specific */
#HeaderStatus {
    color: #10b981;
    font-weight: bold;
    font-size: 12px;
    letter-spacing: 1px;
}
"""

COLORS = {
    "bg_main": "rgba(20, 20, 22, 220)", # Minimalist charcoal, frosted
    "bg_secondary": "rgba(30, 30, 34, 180)",
    "accent": "#F8FAFC", # Clean frosty white
    "accent_glow": "rgba(255, 255, 255, 0.15)",
    "text_primary": "#F1F5F9",
    "text_secondary": "#94A3B8",
    "success": "#38BDF8", # Soft ice blue
    "error": "#F87171", # Soft coral
    "info": "#818CF8", # Soft indigo
    "warning": "#FBBF24", # Soft amber
}
