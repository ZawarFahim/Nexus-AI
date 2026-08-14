import random
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QPen

from nexus.ui.pyside.styles import COLORS

class AudioVisualizerWidget(QWidget):
    """A sleek, simulated audio visualizer waveform."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(30)
        self.setMinimumWidth(100)
        
        self.num_bars = 20
        self.bar_width = 3
        self.spacing = 3
        
        # Current heights and target heights for interpolation
        self.heights = [0.0] * self.num_bars
        self.targets = [0.0] * self.num_bars
        
        self.is_active = False
        self.color = QColor(COLORS["accent"])
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_animation)
        self.timer.start(30)  # ~33 FPS

    def set_active(self, active: bool, color_hex: str = None):
        """Turn the visualizer dancing on or off."""
        self.is_active = active
        if color_hex:
            self.color = QColor(color_hex)
            
        if not active:
            # Flatten to 0 smoothly
            self.targets = [0.0] * self.num_bars

    def _update_animation(self):
        # Update targets if active
        if self.is_active:
            for i in range(self.num_bars):
                # Randomly jump to new targets or smoothly change
                if random.random() < 0.2:
                    self.targets[i] = random.uniform(2.0, self.height() * 0.8)
                    
        # Interpolate current heights towards targets
        needs_update = False
        for i in range(self.num_bars):
            diff = self.targets[i] - self.heights[i]
            if abs(diff) > 0.1:
                # Spring physics / easing
                self.heights[i] += diff * 0.3
                needs_update = True
            else:
                self.heights[i] = self.targets[i]
                
        if needs_update or self.is_active:
            self.update()  # Trigger paintEvent

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate total width to center it
        total_width = (self.num_bars * self.bar_width) + ((self.num_bars - 1) * self.spacing)
        start_x = (self.width() - total_width) / 2
        
        center_y = self.height() / 2
        
        pen = QPen(self.color)
        pen.setWidth(self.bar_width)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        
        for i in range(self.num_bars):
            h = max(2.0, self.heights[i])  # Minimum 2px dot
            x = start_x + i * (self.bar_width + self.spacing)
            
            painter.drawLine(x, center_y - h/2, x, center_y + h/2)
