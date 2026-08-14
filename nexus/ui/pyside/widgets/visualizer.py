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
        self.simulated_speech = False
        self.color = QColor(COLORS["accent"])
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_animation)
        self.timer.start(30)  # ~33 FPS

    def set_active(self, active: bool, color_hex: str = None, simulated_speech: bool = False):
        """Turn the visualizer dancing on or off."""
        self.is_active = active
        self.simulated_speech = simulated_speech
        if color_hex:
            self.color = QColor(color_hex)
            
        if not active:
            # Flatten to 0 smoothly
            self.targets = [0.0] * self.num_bars
            
    def pulse(self, intensity: float):
        """Push the waveform up based on volume."""
        if not self.is_active: return
        for i in range(self.num_bars):
            if random.random() < 0.6:
                h = random.uniform(2.0, self.height() * 0.9 * intensity)
                self.targets[i] = max(self.targets[i], h)

    def _update_animation(self):
        # If simulating speech (LLM talking), pulse automatically
        if self.is_active and self.simulated_speech:
            if random.random() < 0.3:
                self.pulse(random.uniform(0.3, 0.8))
                
        needs_update = False
        for i in range(self.num_bars):
            # Falloff / Gravity for targets
            self.targets[i] *= 0.85
            
            diff = self.targets[i] - self.heights[i]
            if abs(diff) > 0.1:
                self.heights[i] += diff * 0.4
                needs_update = True
            else:
                self.heights[i] = self.targets[i]
                if self.heights[i] > 0.1:
                    needs_update = True
                
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
