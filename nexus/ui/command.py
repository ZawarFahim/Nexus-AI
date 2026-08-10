"""Native Text Command Interface for Nexus."""

import tkinter as tk
from tkinter import scrolledtext
import threading
import logging
from nexus.pipeline import Pipeline
from nexus.core.state import State

logger = logging.getLogger(__name__)

class CommandWindow:
    def __init__(self, pipeline: Pipeline):
        self.pipeline = pipeline
        self.history = []
        self.history_idx = -1
        
        # Build UI on a background thread
        self._ready_event = threading.Event()
        self._thread = threading.Thread(target=self._run_tk, daemon=True, name="ev-command-ui")
        self._thread.start()
        
        # Wait for Tk to initialize before subscribing
        self._ready_event.wait()
        
        # Subscribe to pipeline events
        self.pipeline.subscribe_token(self._on_token)
        self.pipeline.subscribe_user_text(self._on_user_text)

    def _run_tk(self):
        self.root = tk.Tk()
        self.root.title("NEXUS ● READY")
        self.root.geometry("600x450")
        self.root.configure(bg="#1e1e1e")
        self.root.protocol("WM_DELETE_WINDOW", self.hide)
        
        # Make it float above other windows when visible
        self.root.attributes("-topmost", True)
        
        # Conversation history
        self.text_area = scrolledtext.ScrolledText(
            self.root, wrap=tk.WORD, bg="#1e1e1e", fg="#cccccc",
            font=("Segoe UI", 11), state=tk.DISABLED, borderwidth=0, highlightthickness=0
        )
        self.text_area.pack(expand=True, fill=tk.BOTH, padx=15, pady=15)
        
        # Input frame
        self.input_frame = tk.Frame(self.root, bg="#2d2d2d")
        self.input_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=15, pady=15)
        
        self.entry = tk.Entry(
            self.input_frame, bg="#2d2d2d", fg="white", 
            font=("Segoe UI", 12), borderwidth=0, highlightthickness=0, insertbackground="white"
        )
        self.entry.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Key bindings
        self.entry.bind("<Return>", self._on_enter)
        self.entry.bind("<Escape>", self._on_escape)
        self.entry.bind("<Up>", self._on_up)
        self.entry.bind("<Down>", self._on_down)
        
        self.root.withdraw() # Start hidden
        self._ready_event.set()
        
        # Block this thread with the Tk event loop
        self.root.mainloop()

    def show(self):
        """Show and focus the command window. Thread-safe."""
        if not hasattr(self, 'root'): return
        self.root.after(0, self._show)
        
    def _show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.entry.focus_set()
        
    def hide(self):
        """Hide the command window. Thread-safe."""
        if not hasattr(self, 'root'): return
        self.root.after(0, self.root.withdraw)
        
    def _on_enter(self, event):
        text = self.entry.get().strip()
        if not text:
            return "break"
            
        self.entry.delete(0, tk.END)
        self.history.append(text)
        self.history_idx = len(self.history)
        
        # Submit the text. The response and the prompt will be echoed back by the pipeline events.
        self.pipeline.submit_text(text)
        return "break"
        
    def _on_escape(self, event):
        if self.pipeline.state.current in (State.THINKING, State.SPEAKING):
            self.pipeline.abort()
            self._append_to_chat("\n\n[Cancelled]\n")
        else:
            self.hide()
        return "break"
        
    def _on_up(self, event):
        if self.history and self.history_idx > 0:
            self.history_idx -= 1
            self.entry.delete(0, tk.END)
            self.entry.insert(0, self.history[self.history_idx])
        return "break"
            
    def _on_down(self, event):
        if self.history and self.history_idx < len(self.history) - 1:
            self.history_idx += 1
            self.entry.delete(0, tk.END)
            self.entry.insert(0, self.history[self.history_idx])
        elif self.history_idx == len(self.history) - 1:
            self.history_idx += 1
            self.entry.delete(0, tk.END)
        return "break"
        
    def _on_token(self, fragment: str):
        if hasattr(self, 'root'):
            self.root.after(0, lambda: self._append_to_chat(fragment))
        
    def _on_user_text(self, text: str):
        if hasattr(self, 'root'):
            self.root.after(0, lambda: self._append_to_chat(f"\n\nYou:\n{text}\n\nNexus:\n"))
        
    def _append_to_chat(self, text: str):
        self.text_area.config(state=tk.NORMAL)
        self.text_area.insert(tk.END, text)
        self.text_area.see(tk.END)
        self.text_area.config(state=tk.DISABLED)

    def on_state(self, state: State):
        """Handle state transitions from Nexus core. Thread-safe."""
        names = {
            State.IDLE: "READY",
            State.LISTENING: "LISTENING",
            State.THINKING: "THINKING",
            State.SPEAKING: "EXECUTING"
        }
        title = f"NEXUS ● {names.get(state, 'READY')}"
        if hasattr(self, 'root'):
            self.root.after(0, lambda: self.root.title(title))
