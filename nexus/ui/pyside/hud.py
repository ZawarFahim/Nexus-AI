import psutil
import logging
import time
import ctypes
import math
from datetime import datetime
from collections import deque

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QProgressBar, QGraphicsDropShadowEffect, QListWidget
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen

from nexus.ui.pyside.styles import COLORS
from nexus.core.state import State
from nexus.core.config import Settings

try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    SPOTIPY_AVAILABLE = True
except ImportError:
    SPOTIPY_AVAILABLE = False

logger = logging.getLogger(__name__)


def get_active_window_title():
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
        val = buf.value
        return val if val else "Desktop"
    except Exception:
        return "Unknown Context"


class WaveformWidget(QWidget):
    """A custom widget that draws a live audio waveform."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        self.level = 0.0
        self.phase = 0.0
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(30) # ~30fps
        
    def set_level(self, level: float):
        self.level = level

    def _animate(self):
        self.phase += 0.2
        if self.phase > math.pi * 2:
            self.phase -= math.pi * 2
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        mid_y = height / 2.0
        
        # Draw background line
        pen = QPen(QColor(COLORS['text_secondary']))
        pen.setWidth(1)
        pen.setAlphaF(0.2)
        painter.setPen(pen)
        painter.drawLine(0, int(mid_y), width, int(mid_y))
        
        # Draw waveform
        pen = QPen(QColor(COLORS['success'])) # Ice Blue
        pen.setWidth(2)
        painter.setPen(pen)
        
        amplitude = self.level * (height / 2.0)
        if amplitude < 2:
            amplitude = 2 # minimum wave
            
        freq = 4.0
        
        last_x, last_y = 0, int(mid_y)
        for x in range(0, width, 2):
            normalized_x = x / width
            y_offset = math.sin(self.phase + normalized_x * math.pi * freq) * amplitude
            
            # Taper edges
            taper = math.sin(normalized_x * math.pi)
            y_offset *= taper
            
            y = int(mid_y + y_offset)
            painter.drawLine(last_x, last_y, x, y)
            last_x, last_y = x, y


class GlassPanel(QFrame):
    """A highly polished glassmorphic translucent panel."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_main']};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
            }}
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 8)
        self.setGraphicsEffect(shadow)


class HUDWindow(QWidget):
    """Ultimate Visual J.A.R.V.I.S. Dashboard."""
    
    toggle_requested = Signal()
    audio_level_updated = Signal(float)
    event_logged = Signal(str)
    
    def __init__(self, pipeline=None, settings: Settings = None):
        super().__init__()
        self.pipeline = pipeline
        self.settings = settings
        
        self.toggle_requested.connect(self._on_toggle, Qt.QueuedConnection)
        self.audio_level_updated.connect(self._update_mic_bar, Qt.QueuedConnection)
        self.event_logged.connect(self._add_event, Qt.QueuedConnection)
        
        # Transparent, frameless, and click-through
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool | 
            Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(360, 750)
        
        self.is_visible = False
        self.last_net = None
        self.start_time = time.time()
        self._setup_ui()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_stats)
        
    def _create_metric(self, label_text, parent_layout):
        layout = QVBoxLayout()
        layout.setSpacing(2)
        
        # Micro-typography label
        lbl = QLabel(label_text)
        lbl.setFont(QFont("Inter", 7, QFont.Bold))
        lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; letter-spacing: 1px; background: transparent; border: none;")
        
        # Massive value
        val = QLabel("0%")
        val.setFont(QFont("Inter", 16, QFont.Bold))
        val.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent; border: none;")
        
        # Ultra-thin bar
        bar = QProgressBar()
        bar.setFixedHeight(4)
        bar.setRange(0, 100)
        bar.setValue(0)
        
        layout.addWidget(lbl)
        layout.addWidget(val)
        layout.addWidget(bar)
        parent_layout.addLayout(layout)
        return val, bar
        
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)
        
        # --- System Panel ---
        self.sys_panel = GlassPanel(self)
        sys_layout = QVBoxLayout(self.sys_panel)
        sys_layout.setContentsMargins(20, 20, 20, 20)
        sys_layout.setSpacing(15)
        
        # Massive Clock Header
        self.clock_label = QLabel("00:00:00")
        self.clock_label.setFont(QFont("Inter", 28, QFont.Bold))
        self.clock_label.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent; border: none;")
        self.clock_label.setAlignment(Qt.AlignCenter)
        
        self.date_label = QLabel("MONDAY, JAN 01")
        self.date_label.setFont(QFont("Inter", 9, QFont.Bold))
        self.date_label.setStyleSheet(f"color: {COLORS['text_secondary']}; background: transparent; border: none; letter-spacing: 2px;")
        self.date_label.setAlignment(Qt.AlignCenter)
        
        sys_layout.addWidget(self.clock_label)
        sys_layout.addWidget(self.date_label)
        
        self.state_label = QLabel("SYSTEM: ONLINE")
        self.state_label.setFont(QFont("Inter", 10, QFont.Bold))
        self.state_label.setStyleSheet(f"color: {COLORS['success']}; background: transparent; border: none; letter-spacing: 1px;")
        self.state_label.setAlignment(Qt.AlignCenter)
        sys_layout.addWidget(self.state_label)
        
        # Active Window Tracker
        win_lbl = QLabel("ACTIVE CONTEXT")
        win_lbl.setFont(QFont("Inter", 7, QFont.Bold))
        win_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; letter-spacing: 1px; background: transparent; border: none;")
        sys_layout.addWidget(win_lbl)
        
        self.window_label = QLabel("Desktop")
        self.window_label.setFont(QFont("Inter", 10))
        self.window_label.setStyleSheet(f"color: {COLORS['accent']}; background: transparent; border: none;")
        self.window_label.setWordWrap(True)
        sys_layout.addWidget(self.window_label)

        # CPU/RAM/DISK
        stats_layout = QHBoxLayout()
        self.cpu_val, self.cpu_bar = self._create_metric("CPU USAGE", stats_layout)
        self.ram_val, self.ram_bar = self._create_metric("MEMORY", stats_layout)
        self.disk_val, self.disk_bar = self._create_metric("STORAGE", stats_layout)
        sys_layout.addLayout(stats_layout)
        
        # NET/BATT
        lower_layout = QHBoxLayout()
        self.net_val, _ = self._create_metric("NETWORK DL", lower_layout)
        self.batt_val, self.batt_bar = self._create_metric("BATTERY", lower_layout)
        sys_layout.addLayout(lower_layout)

        main_layout.addWidget(self.sys_panel)

        # --- Audio & Spotify Panel ---
        self.audio_panel = GlassPanel(self)
        audio_layout = QVBoxLayout(self.audio_panel)
        audio_layout.setContentsMargins(20, 15, 20, 15)
        
        sp_title = QLabel("NOW PLAYING")
        sp_title.setFont(QFont("Inter", 7, QFont.Bold))
        sp_title.setStyleSheet(f"color: {COLORS['text_secondary']}; background: transparent; border: none; letter-spacing: 1px;")
        audio_layout.addWidget(sp_title)
        
        self.sp_track_label = QLabel("No media playing")
        self.sp_track_label.setFont(QFont("Inter", 12, QFont.Bold))
        self.sp_track_label.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent; border: none;")
        self.sp_track_label.setWordWrap(True)
        
        self.sp_artist_label = QLabel("--")
        self.sp_artist_label.setFont(QFont("Inter", 9))
        self.sp_artist_label.setStyleSheet(f"color: {COLORS['accent']}; background: transparent; border: none;")
        
        audio_layout.addWidget(self.sp_track_label)
        audio_layout.addWidget(self.sp_artist_label)
        
        # Waveform
        mic_lbl = QLabel("AUDIO INPUT")
        mic_lbl.setFont(QFont("Inter", 7, QFont.Bold))
        mic_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; background: transparent; border: none; letter-spacing: 1px;")
        audio_layout.addWidget(mic_lbl)
        
        self.waveform = WaveformWidget()
        audio_layout.addWidget(self.waveform)
        
        main_layout.addWidget(self.audio_panel)
        
        # --- Matrix Event Feed ---
        self.feed_panel = GlassPanel(self)
        feed_layout = QVBoxLayout(self.feed_panel)
        feed_layout.setContentsMargins(15, 10, 15, 10)
        
        feed_title = QLabel("SYSTEM LOG")
        feed_title.setFont(QFont("Inter", 7, QFont.Bold))
        feed_title.setStyleSheet(f"color: {COLORS['text_secondary']}; background: transparent; border: none; letter-spacing: 1px;")
        feed_layout.addWidget(feed_title)
        
        self.feed_list = QListWidget()
        self.feed_list.setFont(QFont("Consolas", 8))
        self.feed_list.setStyleSheet(f"""
            QListWidget {{
                background-color: transparent;
                border: none;
                color: {COLORS['text_primary']};
            }}
            QListWidget::item {{
                padding: 2px;
            }}
        """)
        self.feed_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.feed_list.setSelectionMode(QListWidget.NoSelection)
        feed_layout.addWidget(self.feed_list)
        
        main_layout.addWidget(self.feed_panel)
        main_layout.addStretch()

    def _add_event(self, event_text: str):
        if not self.is_visible:
            return
        now = datetime.now().strftime("%H:%M:%S")
        self.feed_list.addItem(f"[{now}] {event_text}")
        if self.feed_list.count() > 15:
            self.feed_list.takeItem(0)
        self.feed_list.scrollToBottom()

    def _format_bytes(self, bytes_per_sec):
        if bytes_per_sec < 1024:
            return f"{bytes_per_sec:.0f} B"
        elif bytes_per_sec < 1024 * 1024:
            return f"{bytes_per_sec / 1024:.0f} KB"
        else:
            return f"{bytes_per_sec / (1024*1024):.1f} MB"

    def _update_mic_bar(self, level: float):
        if self.is_visible:
            self.waveform.set_level(level)

    def _update_stats(self):
        try:
            # Clock & Date
            now = datetime.now()
            self.clock_label.setText(now.strftime("%H:%M:%S"))
            self.date_label.setText(now.strftime("%A, %b %d").upper())
            
            # Active Window
            title = get_active_window_title()
            if len(title) > 40:
                title = title[:37] + "..."
            self.window_label.setText(title)
            
            # Basic stats
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage('C:\\').percent
            
            self.cpu_val.setText(f"{cpu:.0f}%")
            self.cpu_bar.setValue(int(cpu))
            self.ram_val.setText(f"{ram:.0f}%")
            self.ram_bar.setValue(int(ram))
            self.disk_val.setText(f"{disk:.0f}%")
            self.disk_bar.setValue(int(disk))
            
            # Battery
            batt = psutil.sensors_battery()
            if batt:
                self.batt_val.setText(f"{batt.percent:.0f}%")
                self.batt_bar.setValue(int(batt.percent))
            else:
                self.batt_val.setText("N/A")
                self.batt_bar.setValue(0)
            
            # Network
            current_net = psutil.net_io_counters()
            if self.last_net:
                dl_bps = (current_net.bytes_recv - self.last_net.bytes_recv) / 2.0
                self.net_val.setText(self._format_bytes(dl_bps))
            self.last_net = current_net
            
        except Exception:
            pass
            
        # Update Spotify
        if SPOTIPY_AVAILABLE and self.settings and self.settings.spotipy_client_id:
            try:
                sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                    client_id=self.settings.spotipy_client_id,
                    client_secret=self.settings.spotipy_client_secret,
                    redirect_uri=self.settings.spotipy_redirect_uri,
                    scope="user-modify-playback-state user-read-playback-state",
                    open_browser=False
                ))
                current = sp.current_playback()
                if current and current.get('is_playing'):
                    song = current['item']['name']
                    artist = current['item']['artists'][0]['name']
                    self.sp_track_label.setText(song)
                    self.sp_artist_label.setText(artist)
                else:
                    self.sp_track_label.setText("Playback paused")
                    self.sp_artist_label.setText("--")
            except Exception as e:
                logger.debug(f"Spotify HUD Error: {e}")

    def update_state(self, state: State):
        names = {
            State.IDLE: "SYSTEM: ONLINE",
            State.LISTENING: "SYSTEM: LISTENING",
            State.THINKING: "SYSTEM: PROCESSING",
            State.SPEAKING: "SYSTEM: RESPONDING"
        }
        status = names.get(state, "SYSTEM: ONLINE")
        color = COLORS["success"] if status == "SYSTEM: ONLINE" else COLORS["accent"]
        self.state_label.setText(f"{status}")
        self.state_label.setStyleSheet(f"color: {color}; background: transparent; border: none; letter-spacing: 1px;")

        # Emit an event to the log
        self.event_logged.emit(f"State transitioned to: {state.name}")

    def _on_toggle(self):
        if self.is_visible:
            self.hide()
            self.timer.stop()
            self.is_visible = False
        else:
            self._position_window()
            self.show()
            self.last_net = psutil.net_io_counters()
            self.timer.start(1000) # Update 1/sec for clock
            psutil.cpu_percent(interval=None)
            self._update_stats()
            self.is_visible = True
            self.event_logged.emit("HUD Activated")

    def _position_window(self):
        screen = self.screen().availableGeometry()
        x = screen.width() - self.width() - 30
        y = screen.height() - self.height() - 30
        self.move(x, y)
