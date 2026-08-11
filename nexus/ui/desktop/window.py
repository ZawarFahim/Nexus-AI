"""Main Native UI Window for Nexus."""

import tkinter as tk
from tkinter import ttk
import threading
import logging
from typing import Optional

from nexus.pipeline import Pipeline
from nexus.core.state import State
from nexus.ui.desktop.theme import COLORS, FONTS

logger = logging.getLogger(__name__)

class DesktopWindow:
    def __init__(self, pipeline: Pipeline):
        self.pipeline = pipeline
        self.history: list[str] = []
        self.history_idx: int = -1
        
        self._ready_event = threading.Event()
        self._thread = threading.Thread(target=self._run_tk, daemon=True, name="ev-desktop-ui")
        self._thread.start()
        
        self._ready_event.wait()
        
        # Connect to pipeline
        self.pipeline.subscribe_token(self._on_token)
        self.pipeline.subscribe_user_text(self._on_user_text)
        
    def _run_tk(self):
        self.root = tk.Tk()
        self.root.title("NEXUS")
        self.root.geometry("450x700")
        self.root.configure(bg=COLORS.BG_MAIN)
        self.root.protocol("WM_DELETE_WINDOW", self.hide)
        self.root.attributes("-topmost", True)
        
        # Header
        self.header_frame = tk.Frame(self.root, bg=COLORS.BG_HEADER, height=50)
        self.header_frame.pack(fill=tk.X, side=tk.TOP)
        self.header_frame.pack_propagate(False)
        
        self.title_label = tk.Label(
            self.header_frame, text="◉ NEXUS", bg=COLORS.BG_HEADER, fg=COLORS.FG_PRIMARY,
            font=(FONTS.FAMILY, FONTS.SIZE_TITLE, "bold")
        )
        self.title_label.pack(side=tk.LEFT, padx=15)
        
        self.status_label = tk.Label(
            self.header_frame, text="● READY", bg=COLORS.BG_HEADER, fg=COLORS.FG_SECONDARY,
            font=(FONTS.FAMILY, FONTS.SIZE_SMALL, "bold")
        )
        self.status_label.pack(side=tk.RIGHT, padx=15)
        
        # Border under header
        tk.Frame(self.root, bg=COLORS.BORDER, height=1).pack(fill=tk.X)
        
        # Chat timeline area
        self.chat_frame = tk.Frame(self.root, bg=COLORS.BG_MAIN)
        self.chat_frame.pack(expand=True, fill=tk.BOTH, padx=0, pady=0)
        
        self.chat_text = tk.Text(
            self.chat_frame, bg=COLORS.BG_MAIN, fg=COLORS.FG_PRIMARY, 
            font=(FONTS.FAMILY, FONTS.SIZE_BODY), wrap=tk.WORD, borderwidth=0, highlightthickness=0, state=tk.DISABLED
        )
        self.chat_text.pack(expand=True, fill=tk.BOTH, padx=15, pady=15)
        
        # Tags for styling the chat
        self.chat_text.tag_config("user_header", foreground=COLORS.FG_SECONDARY, font=(FONTS.FAMILY, FONTS.SIZE_SMALL, "bold"), spacing1=10)
        self.chat_text.tag_config("user_msg", foreground=COLORS.FG_PRIMARY, background=COLORS.BG_BUBBLE_USER, lmargin1=10, rmargin=10, spacing1=5, spacing3=5)
        
        self.chat_text.tag_config("nexus_header", foreground=COLORS.FG_ACCENT, font=(FONTS.FAMILY, FONTS.SIZE_SMALL, "bold"), spacing1=10)
        self.chat_text.tag_config("nexus_msg", foreground=COLORS.FG_PRIMARY, lmargin1=10, rmargin=10, spacing1=5, spacing3=5)
        
        self._show_empty_state()
        
        # Border over input
        tk.Frame(self.root, bg=COLORS.BORDER, height=1).pack(fill=tk.X)
        
        # Input area
        self.input_frame = tk.Frame(self.root, bg=COLORS.BG_INPUT, height=60)
        self.input_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.input_frame.pack_propagate(False)
        
        self.entry = tk.Entry(
            self.input_frame, bg=COLORS.BG_INPUT, fg=COLORS.FG_PRIMARY,
            font=(FONTS.FAMILY, FONTS.SIZE_BODY), borderwidth=0, highlightthickness=0, insertbackground=COLORS.FG_PRIMARY
        )
        self.entry.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        self.entry.insert(0, "Type a command...")
        
        self.entry.bind("<FocusIn>", self._clear_placeholder)
        self.entry.bind("<FocusOut>", self._restore_placeholder)
        self.entry.bind("<Escape>", self._on_escape)
        self.entry.bind("<Return>", self._on_enter)
        self.entry.bind("<Up>", self._on_up)
        self.entry.bind("<Down>", self._on_down)
        
        self.root.withdraw()
        self._ready_event.set()
        self.root.mainloop()

    def _clear_placeholder(self, event):
        if self.entry.get() == "Type a command...":
            self.entry.delete(0, tk.END)

    def _restore_placeholder(self, event):
        if not self.entry.get():
            self.entry.insert(0, "Type a command...")

    def show(self):
        if not hasattr(self, 'root'): return
        self.root.after(0, self._show)
        
    def _show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.entry.focus_set()
        
    def hide(self):
        if not hasattr(self, 'root'): return
        self.root.after(0, self.root.withdraw)
        
    def _on_escape(self, event):
        if self.pipeline.state.current in (State.THINKING, State.SPEAKING):
            self.pipeline.abort()
        else:
            self.hide()
        return "break"
        
    def _on_enter(self, event):
        text = self.entry.get().strip()
        if not text or text == "Type a command...":
            return "break"
            
        self.entry.delete(0, tk.END)
        self.history.append(text)
        self.history_idx = len(self.history)
        
        self.pipeline.submit_text(text)
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
        
    def _show_empty_state(self):
        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.delete(1.0, tk.END)
        welcome = "Ready for command\n\nSpeak or type what you want me to do.\n\n────────────────────────\n\nTry:\n\"Open Spotify\"\n\"Find my latest PDF\"\n\"What's wrong with my screen?\"\n"
        self.chat_text.insert(tk.END, welcome, "user_header")
        self.chat_text.tag_add("center", "1.0", "end")
        self.chat_text.tag_config("center", justify="center")
        self.chat_text.config(state=tk.DISABLED)
        self._is_empty = True

    def _on_user_text(self, text: str):
        if hasattr(self, 'root'):
            self.root.after(0, lambda: self._append_user_message(text))
            
    def _on_token(self, fragment: str):
        if hasattr(self, 'root'):
            self.root.after(0, lambda: self._append_nexus_token(fragment))
            
    def _append_user_message(self, text: str):
        if getattr(self, '_is_empty', False):
            self.chat_text.config(state=tk.NORMAL)
            self.chat_text.delete(1.0, tk.END)
            self._is_empty = False
            self._current_nexus_idx = None
            
        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.insert(tk.END, "You\n", "user_header")
        self.chat_text.insert(tk.END, f"{text}\n\n", "user_msg")
        self.chat_text.see(tk.END)
        self.chat_text.config(state=tk.DISABLED)
        self._current_nexus_idx = None # Reset for next nexus response

    def _append_nexus_token(self, fragment: str):
        self.chat_text.config(state=tk.NORMAL)
        if not getattr(self, '_current_nexus_idx', None):
            self.chat_text.insert(tk.END, "Nexus\n", "nexus_header")
            self._current_nexus_idx = self.chat_text.index(tk.INSERT)
            
        self.chat_text.insert(tk.END, fragment, "nexus_msg")
        self.chat_text.see(tk.END)
        self.chat_text.config(state=tk.DISABLED)

    def on_state(self, state: State):
        """Update header based on pipeline state."""
        names = {
            State.IDLE: "READY",
            State.LISTENING: "LISTENING",
            State.THINKING: "THINKING",
            State.SPEAKING: "RESPONDING"
        }
        status = names.get(state, "READY")
        color = COLORS.SUCCESS if status == "READY" else COLORS.FG_ACCENT
        
        if hasattr(self, 'root'):
            self.root.after(0, lambda: self._update_status(status, color))
            
    def _update_status(self, text: str, color: str):
        self.status_label.config(text=f"● {text}", fg=color)
