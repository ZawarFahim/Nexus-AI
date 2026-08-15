import psutil
import logging
from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QGraphicsDropShadowEffect

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


class GlassPanel(QFrame):
    """A glassmorphic translucent panel."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_main']};
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px;
            }}
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)


class HUDWindow(QWidget):
    """Sleek, minimalist dashboard."""
    
    toggle_requested = Signal()
    
    def __init__(self, pipeline=None, settings: Settings = None):
        super().__init__()
        self.pipeline = pipeline
        self.settings = settings
        self.toggle_requested.connect(self._on_toggle, Qt.QueuedConnection)
        
        # Transparent, frameless, and click-through
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool | 
            Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(300, 360)
        
        self.is_visible = False
        self.last_net = None
        self._setup_ui()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_stats)
        
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)
        
        # --- System Panel ---
        self.sys_panel = GlassPanel(self)
        sys_layout = QVBoxLayout(self.sys_panel)
        sys_layout.setContentsMargins(15, 15, 15, 15)
        sys_layout.setSpacing(8)
        
        title = QLabel("SYSTEM METRICS")
        title.setFont(QFont("Inter", 10, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text_secondary']}; background: transparent; border: none; letter-spacing: 1px;")
        sys_layout.addWidget(title)
        
        self.state_label = QLabel("STATUS: ONLINE")
        self.state_label.setFont(QFont("Inter", 11, QFont.Bold))
        self.state_label.setStyleSheet(f"color: {COLORS['success']}; background: transparent; border: none;")
        sys_layout.addWidget(self.state_label)
        
        # CPU/RAM/DISK
        stats_layout = QHBoxLayout()
        self.cpu_label = QLabel("CPU: 0%")
        self.cpu_label.setFont(QFont("Consolas", 10))
        self.cpu_label.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent; border: none;")
        
        self.ram_label = QLabel("MEM: 0%")
        self.ram_label.setFont(QFont("Consolas", 10))
        self.ram_label.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent; border: none;")
        
        stats_layout.addWidget(self.cpu_label)
        stats_layout.addWidget(self.ram_label)
        sys_layout.addLayout(stats_layout)
        
        # NET/DISK
        net_layout = QHBoxLayout()
        self.disk_label = QLabel("DSK: 0%")
        self.disk_label.setFont(QFont("Consolas", 10))
        self.disk_label.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent; border: none;")
        
        self.net_label = QLabel("NET: 0 KB/s")
        self.net_label.setFont(QFont("Consolas", 10))
        self.net_label.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent; border: none;")
        
        net_layout.addWidget(self.disk_label)
        net_layout.addWidget(self.net_label)
        sys_layout.addLayout(net_layout)

        main_layout.addWidget(self.sys_panel)

        # --- Spotify Panel ---
        self.spotify_panel = GlassPanel(self)
        spotify_layout = QVBoxLayout(self.spotify_panel)
        spotify_layout.setContentsMargins(15, 15, 15, 15)
        
        sp_title = QLabel("NOW PLAYING")
        sp_title.setFont(QFont("Inter", 10, QFont.Bold))
        sp_title.setStyleSheet(f"color: {COLORS['text_secondary']}; background: transparent; border: none; letter-spacing: 1px;")
        spotify_layout.addWidget(sp_title)
        
        self.sp_track_label = QLabel("No media playing")
        self.sp_track_label.setFont(QFont("Inter", 10))
        self.sp_track_label.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent; border: none;")
        self.sp_track_label.setWordWrap(True)
        spotify_layout.addWidget(self.sp_track_label)
        
        main_layout.addWidget(self.spotify_panel)
        main_layout.addStretch()

    def _format_bytes(self, bytes_per_sec):
        if bytes_per_sec < 1024:
            return f"{bytes_per_sec:.0f} B/s"
        elif bytes_per_sec < 1024 * 1024:
            return f"{bytes_per_sec / 1024:.0f} KB/s"
        else:
            return f"{bytes_per_sec / (1024*1024):.1f} MB/s"

    def _update_stats(self):
        try:
            # Basic stats
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage('C:\\').percent
            self.cpu_label.setText(f"CPU: {cpu:.1f}%")
            self.ram_label.setText(f"MEM: {ram:.1f}%")
            self.disk_label.setText(f"DSK: {disk:.1f}%")
            
            # Network
            current_net = psutil.net_io_counters()
            if self.last_net:
                dl_bps = (current_net.bytes_recv - self.last_net.bytes_recv) / 2.0
                ul_bps = (current_net.bytes_sent - self.last_net.bytes_sent) / 2.0
                self.net_label.setText(f"DL: {self._format_bytes(dl_bps)}")
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
                    scope="user-read-playback-state",
                    open_browser=False
                ))
                current = sp.current_playback()
                if current and current.get('is_playing'):
                    song = current['item']['name']
                    artist = current['item']['artists'][0]['name']
                    self.sp_track_label.setText(f"{artist} - {song}")
                    self.sp_track_label.setStyleSheet(f"color: {COLORS['accent']}; background: transparent; border: none;")
                else:
                    self.sp_track_label.setText("Playback paused")
                    self.sp_track_label.setStyleSheet(f"color: {COLORS['text_secondary']}; background: transparent; border: none;")
            except Exception as e:
                logger.debug(f"Spotify HUD Error: {e}")

    def update_state(self, state: State):
        names = {
            State.IDLE: "STATUS: ONLINE",
            State.LISTENING: "STATUS: LISTENING",
            State.THINKING: "STATUS: PROCESSING",
            State.SPEAKING: "STATUS: RESPONDING"
        }
        status = names.get(state, "STATUS: ONLINE")
        color = COLORS["success"] if status == "STATUS: ONLINE" else COLORS["accent"]
        self.state_label.setText(f"{status}")
        self.state_label.setStyleSheet(f"color: {color}; background: transparent; border: none;")

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
