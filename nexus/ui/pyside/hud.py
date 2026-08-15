import psutil
import logging
from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QBrush, QPen
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
                border: 1px solid {COLORS['accent']};
                border-radius: 12px;
            }}
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(COLORS['accent_glow']))
        shadow.setOffset(0, 0)
        self.setGraphicsEffect(shadow)


class HUDWindow(QWidget):
    """Tony Stark's Cyberpunk Glassmorphic HUD."""
    
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
        self.setFixedSize(300, 400)
        
        self.is_visible = False
        self._setup_ui()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_stats)
        
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # --- System Panel ---
        self.sys_panel = GlassPanel(self)
        sys_layout = QVBoxLayout(self.sys_panel)
        sys_layout.setContentsMargins(15, 15, 15, 15)
        
        title = QLabel("NEXUS CORE // HUD")
        title.setFont(QFont("Consolas", 11, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['accent']}; background: transparent; border: none;")
        sys_layout.addWidget(title)
        
        self.state_label = QLabel("SYSTEM: ONLINE")
        self.state_label.setFont(QFont("Consolas", 10))
        self.state_label.setStyleSheet(f"color: {COLORS['success']}; background: transparent; border: none;")
        sys_layout.addWidget(self.state_label)
        
        # Stats layout
        stats_layout = QHBoxLayout()
        self.cpu_label = QLabel("CPU: 0%")
        self.cpu_label.setFont(QFont("Consolas", 9))
        self.cpu_label.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent; border: none;")
        
        self.ram_label = QLabel("MEM: 0%")
        self.ram_label.setFont(QFont("Consolas", 9))
        self.ram_label.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent; border: none;")
        
        stats_layout.addWidget(self.cpu_label)
        stats_layout.addWidget(self.ram_label)
        sys_layout.addLayout(stats_layout)
        main_layout.addWidget(self.sys_panel)

        # --- Spotify Panel ---
        self.spotify_panel = GlassPanel(self)
        spotify_layout = QVBoxLayout(self.spotify_panel)
        spotify_layout.setContentsMargins(15, 10, 15, 10)
        
        sp_title = QLabel("🎵 AUDIO LINK")
        sp_title.setFont(QFont("Consolas", 9, QFont.Bold))
        sp_title.setStyleSheet(f"color: {COLORS['accent']}; background: transparent; border: none;")
        spotify_layout.addWidget(sp_title)
        
        self.sp_track_label = QLabel("NO MEDIA DETECTED")
        self.sp_track_label.setFont(QFont("Consolas", 9))
        self.sp_track_label.setStyleSheet(f"color: {COLORS['text_secondary']}; background: transparent; border: none;")
        self.sp_track_label.setWordWrap(True)
        spotify_layout.addWidget(self.sp_track_label)
        
        main_layout.addWidget(self.spotify_panel)

        # --- To-Do Panel ---
        self.todo_panel = GlassPanel(self)
        todo_layout = QVBoxLayout(self.todo_panel)
        todo_layout.setContentsMargins(15, 10, 15, 10)
        
        todo_title = QLabel("📝 ACTIVE DIRECTIVES")
        todo_title.setFont(QFont("Consolas", 9, QFont.Bold))
        todo_title.setStyleSheet(f"color: {COLORS['accent']}; background: transparent; border: none;")
        todo_layout.addWidget(todo_title)
        
        todo_list = QLabel("- [ ] Build UI\\n- [ ] Expand Vision\\n- [ ] Dominate World")
        todo_list.setFont(QFont("Consolas", 9))
        todo_list.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent; border: none;")
        todo_layout.addWidget(todo_list)
        
        main_layout.addWidget(self.todo_panel)
        main_layout.addStretch()

    def _update_stats(self):
        # Update CPU/RAM
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            
            self.cpu_label.setText(f"CPU: {cpu:.1f}%")
            self.ram_label.setText(f"MEM: {ram:.1f}%")
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
                    self.sp_track_label.setStyleSheet(f"color: {COLORS['success']}; background: transparent; border: none;")
                else:
                    self.sp_track_label.setText("PLAYBACK PAUSED")
                    self.sp_track_label.setStyleSheet(f"color: {COLORS['text_secondary']}; background: transparent; border: none;")
            except Exception as e:
                logger.debug(f"Spotify HUD Error: {e}")
                self.sp_track_label.setText("AUDIO LINK FAILED")

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
        self.state_label.setStyleSheet(f"color: {color}; background: transparent; border: none;")

    def _on_toggle(self):
        if self.is_visible:
            self.hide()
            self.timer.stop()
            self.is_visible = False
        else:
            self._position_window()
            self.show()
            self.timer.start(2000)
            psutil.cpu_percent(interval=None)
            self._update_stats()
            self.is_visible = True

    def _position_window(self):
        screen = self.screen().availableGeometry()
        x = screen.width() - self.width() - 30
        y = screen.height() - self.height() - 30
        self.move(x, y)
