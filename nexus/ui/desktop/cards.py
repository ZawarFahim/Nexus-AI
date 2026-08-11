"""Tool activity UI components."""

import tkinter as tk
from typing import Any
from nexus.ui.desktop.theme import COLORS, FONTS

class ToolActivityCard(tk.Frame):
    def __init__(self, parent: tk.Widget, name: str, status: str, details: Any = None):
        super().__init__(parent, bg=COLORS.BG_BUBBLE_NEXUS, highlightbackground=COLORS.BORDER, highlightthickness=1)
        self.name = name
        
        # Mapping tool names to icons and friendly names
        icons = {
            "look_at_screen": "👁 Screen Analysis",
            "manage_files": "📁 File Assistant",
            "control_desktop": "🖥 Desktop Action",
            "open_in_browser": "🌐 Browser Action",
            "control_browser": "🌐 Browser Action",
        }
        
        title_text = icons.get(name, f"🛠 {name.replace('_', ' ').title()}")
        
        self.title_lbl = tk.Label(
            self, text=title_text, bg=COLORS.BG_BUBBLE_NEXUS, fg=COLORS.FG_ACCENT, 
            font=(FONTS.FAMILY, FONTS.SIZE_SMALL, "bold")
        )
        self.title_lbl.pack(anchor=tk.W, padx=10, pady=(8,2))
        
        self.status_lbl = tk.Label(
            self, text=self._format_status(status, details), 
            bg=COLORS.BG_BUBBLE_NEXUS, fg=COLORS.FG_PRIMARY, font=(FONTS.FAMILY, FONTS.SIZE_BODY)
        )
        self.status_lbl.pack(anchor=tk.W, padx=10, pady=(2,8))

    def _format_status(self, status: str, details: Any) -> str:
        if status == "started":
            return "● Executing..."
        elif status == "completed":
            return "✓ Completed"
        elif status == "error":
            err = details.get("error", "Unknown error") if isinstance(details, dict) else ""
            return f"✗ Failed: {err}"
        return f"● {status}"
        
    def update_status(self, status: str, details: Any = None):
        self.status_lbl.config(text=self._format_status(status, details))
        if status == "completed":
            self.title_lbl.config(fg=COLORS.SUCCESS)
        elif status == "error":
            self.title_lbl.config(fg=COLORS.ERROR)
            self.status_lbl.config(fg=COLORS.ERROR)
