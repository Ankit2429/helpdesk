"""Centralized CustomTkinter Theme Engine.

Defines HSL color palettes, KLE Tech Amber brand accents, typography scale,
and CustomTkinter appearance mode integration.
"""

from dataclasses import dataclass
import customtkinter as ctk


@dataclass
class ThemeColors:
    """Color palette definition for CustomTkinter UI themes."""

    bg_main: str
    panel_bg: str
    panel_alt: str
    border_color: str
    header_bg: str
    header_fg: str
    text_main: str
    text_muted: str
    accent_primary: str      # Royal Blue (#3B82F6 / #2563EB)
    accent_hover: str
    accent_brand: str        # KLE Tech Warm Amber/Orange (#EA580C / #F59E0B)
    accent_success: str      # Emerald (#10B981)
    accent_warning: str      # Amber (#F59E0B)
    accent_danger: str       # Rose (#EF4444)
    user_bubble_bg: str
    user_bubble_fg: str
    bot_bubble_bg: str
    bot_bubble_fg: str


DARK_THEME = ThemeColors(
    bg_main="#0F172A",          # Slate 900
    panel_bg="#1E293B",         # Slate 800
    panel_alt="#334155",        # Slate 700
    border_color="#334155",     # Slate 700
    header_bg="#020617",        # Slate 950
    header_fg="#F8FAFC",        # Slate 50
    text_main="#F8FAFC",        # Slate 50
    text_muted="#94A3B8",       # Slate 400
    accent_primary="#2563EB",   # Royal Blue 600
    accent_hover="#1D4ED8",     # Royal Blue 700
    accent_brand="#EA580C",     # KLE Warm Amber / Orange 600
    accent_success="#10B981",   # Emerald 500
    accent_warning="#F59E0B",   # Amber 500
    accent_danger="#EF4444",    # Rose 500
    user_bubble_bg="#2563EB",   # Blue 600
    user_bubble_fg="#FFFFFF",   # Pure White
    bot_bubble_bg="#334155",    # Slate 700
    bot_bubble_fg="#F8FAFC",    # Slate 50
)

LIGHT_THEME = ThemeColors(
    bg_main="#F8FAFC",          # Slate 50
    panel_bg="#FFFFFF",         # Pure White
    panel_alt="#E2E8F0",        # Slate 200
    border_color="#E2E8F0",     # Slate 200
    header_bg="#0F172A",        # Slate 900
    header_fg="#F8FAFC",        # Slate 50
    text_main="#0F172A",        # Slate 900
    text_muted="#64748B",       # Slate 500
    accent_primary="#2563EB",   # Royal Blue 600
    accent_hover="#1D4ED8",     # Royal Blue 700
    accent_brand="#D97706",     # KLE Warm Amber 600
    accent_success="#059669",   # Emerald 600
    accent_warning="#D97706",   # Amber 600
    accent_danger="#DC2626",    # Rose 600
    user_bubble_bg="#DBEAFE",   # Blue 100
    user_bubble_fg="#1E3A8A",   # Blue 900
    bot_bubble_bg="#E2E8F0",    # Slate 200
    bot_bubble_fg="#0F172A",    # Slate 900
)


class ThemeEngine:
    """Manages active theme palette and CustomTkinter appearance mode."""

    def __init__(self, mode: str = "dark") -> None:
        self.mode = mode
        self.colors: ThemeColors = DARK_THEME if mode == "dark" else LIGHT_THEME
        ctk.set_appearance_mode("Dark" if mode == "dark" else "Light")
        ctk.set_default_color_theme("blue")

    def toggle_theme(self) -> str:
        """Switch between dark and light themes."""
        if self.mode == "dark":
            self.mode = "light"
            self.colors = LIGHT_THEME
            ctk.set_appearance_mode("Light")
        else:
            self.mode = "dark"
            self.colors = DARK_THEME
            ctk.set_appearance_mode("Dark")
        return self.mode

    # Font Scale Type System
    @staticmethod
    def font_page_title():
        return ctk.CTkFont(family="Segoe UI", size=26, weight="bold")

    @staticmethod
    def font_card_title():
        return ctk.CTkFont(family="Segoe UI", size=16, weight="bold")

    @staticmethod
    def font_body():
        return ctk.CTkFont(family="Segoe UI", size=13, weight="normal")

    @staticmethod
    def font_caption():
        return ctk.CTkFont(family="Segoe UI", size=11, weight="normal")
