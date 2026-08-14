import logging
from typing import Any
from PySide6.QtCore import QObject, Signal
from nexus.pipeline import Pipeline
from nexus.core.state import State

logger = logging.getLogger(__name__)

class NexusBridge(QObject):
    """Bridge between Nexus core background threads and Qt UI thread.
    
    Qt UI updates MUST happen on the main thread. This class exposes thread-safe
    Qt signals that the Nexus core can trigger from background workers.
    """
    
    # Signals
    token_received = Signal(str)
    user_text_received = Signal(str)
    state_changed = Signal(object)
    tool_activity = Signal(str, str, object)  # name, status, details

    def __init__(self, pipeline: Pipeline, parent=None):
        super().__init__(parent)
        self.pipeline = pipeline
        self._connect_to_pipeline()

    def _connect_to_pipeline(self):
        """Subscribe to pipeline events and emit them as Qt Signals."""
        self.pipeline.subscribe_token(self._on_token)
        self.pipeline.subscribe_user_text(self._on_user_text)
        
        # Assume StateMachine exposes a subscribe mechanism. If not, we hook it manually or polling.
        # Actually, in the Tkinter window it used `on_state` but let's check pipeline state hooks.
        if hasattr(self.pipeline.state, "subscribe"):
            self.pipeline.state.subscribe(self._on_state)
            
        if getattr(self.pipeline, "_tools", None) and hasattr(self.pipeline._tools, "subscribe"):
            self.pipeline._tools.subscribe(self._on_tool_activity)

    def _on_token(self, token: str):
        self.token_received.emit(token)

    def _on_user_text(self, text: str):
        self.user_text_received.emit(text)
        
    def _on_state(self, state: State):
        self.state_changed.emit(state)

    def _on_tool_activity(self, name: str, status: str, details: Any):
        self.tool_activity.emit(name, status, details)

    def submit_text(self, text: str):
        """Called from UI to send text to Nexus."""
        if text.strip():
            # Run in pipeline thread
            import threading
            threading.Thread(target=self.pipeline.submit_text, args=(text,), daemon=True).start()

    def abort(self):
        self.pipeline.abort()
