"""Design system and colors for the Nexus Desktop UI."""

from dataclasses import dataclass
from typing import Final

@dataclass(frozen=True)
class Colors:
    BG_MAIN: str = "#18181A"
    BG_HEADER: str = "#101012"
    BG_INPUT: str = "#222225"
    BG_BUBBLE_USER: str = "#2E2E32"
    BG_BUBBLE_NEXUS: str = "#1E1E22"
    
    FG_PRIMARY: str = "#F0F0F0"
    FG_SECONDARY: str = "#9E9E9E"
    FG_ACCENT: str = "#3B82F6" # Subtle blue
    
    BORDER: str = "#2A2A2E"
    SUCCESS: str = "#10B981"
    ERROR: str = "#EF4444"

@dataclass(frozen=True)
class Fonts:
    FAMILY: str = "Segoe UI"
    FAMILY_MONO: str = "Consolas"
    
    SIZE_TITLE: int = 14
    SIZE_BODY: int = 11
    SIZE_SMALL: int = 9

COLORS: Final = Colors()
FONTS: Final = Fonts()
