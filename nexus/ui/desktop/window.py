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
        
        self._ready_event = threading.Event()
        self._thread = threading.Thread(target=self._run_tk, daemon=True, name="ev-desktop-ui")
        self._thread.start()
        
        self._ready_event.wait()
        
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
        
        # Chat timeline area (will be populated in Commit 2)
        self.chat_frame = tk.Frame(self.root, bg=COLORS.BG_MAIN)
        self.chat_frame.pack(expand=True, fill=tk.BOTH, padx=0, pady=0)
        
        self.empty_state = tk.Label(
            self.chat_frame, 
            text="Ready for command\n\nSpeak or type what you want me to do.\n\n────────────────────────\n\nTry:\n\"Open Spotify\"\n\"Find my latest PDF\"\n\"What's wrong with my screen?\"", 
            bg=COLORS.BG_MAIN, fg=COLORS.FG_SECONDARY, font=(FONTS.FAMILY, FONTS.SIZE_BODY),
            justify=tk.CENTER
        )
        self.empty_state.pack(expand=True)
        
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
        self.hide()
        return "break"
