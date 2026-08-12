import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase, QFont

from nexus.ui.pyside.styles import STYLESHEET

def init_app():
    """Initialize the PySide6 Application instance."""
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    
    # Apply global stylesheet
    app.setStyleSheet(STYLESHEET)
    app.setQuitOnLastWindowClosed(False)  # We run in tray primarily
    
    # Load fonts if necessary (we use standard Segoe UI/Inter for sleek look)
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    return app
