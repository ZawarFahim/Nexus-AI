import psutil
import logging
import time
import ctypes
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QProgressBar, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont

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
    """Ultra-Sleek, minimalist dashboard."""
    
    toggle_requested = Signal()
    audio_level_updated = Signal(float)
    
    def __init__(self, pipeline=None, settings: Settings = None):
        super().__init__()
        self.pipeline = pipeline
        self.settings = settings
        self.toggle_requested.connect(self._on_toggle, Qt.QueuedConnection)
        self.audio_level_updated.connect(self._update_mic_bar, Qt.QueuedConnection)
        
        # Transparent, frameless, and click-through
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool | 
            Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(320, 600)
        
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
        
        # Header
        header_layout = QHBoxLayout()
        self.state_label = QLabel("SYSTEM: ONLINE")
        self.state_label.setFont(QFont("Inter", 9, QFont.Bold))
        self.state_label.setStyleSheet(f"color: {COLORS['success']}; background: transparent; border: none; letter-spacing: 1px;")
        
        self.uptime_label = QLabel("UP: 00:00")
        self.uptime_label.setFont(QFont("Consolas", 8))
        self.uptime_label.setStyleSheet(f"color: {COLORS['text_secondary']}; background: transparent; border: none;")
        self.uptime_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        header_layout.addWidget(self.state_label)
        header_layout.addWidget(self.uptime_label)
        sys_layout.addLayout(header_layout)
        
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
        
        # NET/BATT/MIC
        lower_layout = QHBoxLayout()
        self.net_val, _ = self._create_metric("NETWORK DL", lower_layout)
        self.batt_val, self.batt_bar = self._create_metric("BATTERY", lower_layout)
        self.mic_val, self.mic_bar = self._create_metric("MICROPHONE", lower_layout)
        self.mic_val.setText("LIVE")
        self.mic_bar.setStyleSheet("""
            QProgressBar::chunk { background-color: #F87171; border-radius: 2px; }
        """)
        sys_layout.addLayout(lower_layout)

        main_layout.addWidget(self.sys_panel)

        # --- Spotify Panel ---
        self.spotify_panel = GlassPanel(self)
        spotify_layout = QVBoxLayout(self.spotify_panel)
        spotify_layout.setContentsMargins(20, 15, 20, 15)
        
        sp_title = QLabel("NOW PLAYING")
        sp_title.setFont(QFont("Inter", 7, QFont.Bold))
        sp_title.setStyleSheet(f"color: {COLORS['text_secondary']}; background: transparent; border: none; letter-spacing: 1px;")
        spotify_layout.addWidget(sp_title)
        
        self.sp_track_label = QLabel("No media playing")
        self.sp_track_label.setFont(QFont("Inter", 12, QFont.Bold))
        self.sp_track_label.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent; border: none;")
        self.sp_track_label.setWordWrap(True)
        
        self.sp_artist_label = QLabel("--")
        self.sp_artist_label.setFont(QFont("Inter", 9))
        self.sp_artist_label.setStyleSheet(f"color: {COLORS['accent']}; background: transparent; border: none;")
        
        spotify_layout.addWidget(self.sp_track_label)
        spotify_layout.addWidget(self.sp_artist_label)
        
        main_layout.addWidget(self.spotify_panel)
        main_layout.addStretch()

    def _format_bytes(self, bytes_per_sec):
        if bytes_per_sec < 1024:
            return f"{bytes_per_sec:.0f} B"
        elif bytes_per_sec < 1024 * 1024:
            return f"{bytes_per_sec / 1024:.0f} KB"
        else:
            return f"{bytes_per_sec / (1024*1024):.1f} MB"

    def _update_mic_bar(self, level: float):
        # Level comes in 0.0 to 1.0
        if self.is_visible:
            self.mic_bar.setValue(int(level * 100))

    def _update_stats(self):
        try:
            # Uptime
            elapsed = int(time.time() - self.start_time)
            mins, secs = divmod(elapsed, 60)
            hours, mins = divmod(mins, 60)
            if hours > 0:
                self.uptime_label.setText(f"UP: {hours:02d}:{mins:02d}:{secs:02d}")
            else:
                self.uptime_label.setText(f"UP: {mins:02d}:{secs:02d}")
                
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

    def _on_toggle(self):
        if self.is_visible:
            self.hide()
            self.timer.stop()
            self.is_visible = False
        else:
            self._position_window()
            self.show()
            self.last_net = psutil.net_io_counters()
            self.timer.start(2000)
            psutil.cpu_percent(interval=None)
            self._update_stats()
            self.is_visible = True

    def _position_window(self):
        screen = self.screen().availableGeometry()
        x = screen.width() - self.width() - 30
        y = screen.height() - self.height() - 30
        self.move(x, y)
