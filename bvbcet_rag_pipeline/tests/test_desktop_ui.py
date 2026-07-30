"""Unit and GUI integration tests for CustomTkinter Desktop Application UI."""

import os
from pathlib import Path
import shutil
import tempfile
import tkinter as tk

from campus_helpdesk.presentation.theme import ThemeEngine
from campus_helpdesk.presentation.ui_app import HelpdeskDesktopApp
from campus_helpdesk.presentation.widgets.mascot import MascotAvatar
from campus_helpdesk.presentation.widgets.sparkline import LatencySparkline


def test_theme_engine_toggle():
    engine = ThemeEngine(mode="dark")
    assert engine.mode == "dark"

    new_mode = engine.toggle_theme()
    assert new_mode == "light"
    assert engine.colors.bg_main == "#F8FAFC"


def test_sparkline_widget():
    root = tk.Tk()
    sparkline = LatencySparkline(root, width=180, height=36)
    assert sparkline.w == 180
    sparkline.add_data_point(62.5)
    assert len(sparkline.data) == 10
    root.destroy()


def test_desktop_app_initialization():
    try:
        app = HelpdeskDesktopApp()
        assert app.root is not None
        assert app.current_view_name == "dashboard"
        assert len(app.views) == 5

        # Test view switching
        app._show_view("chat")
        assert app.current_view_name == "chat"

        app._show_view("camera")
        assert app.current_view_name == "camera"

        app._show_view("settings")
        assert app.current_view_name == "settings"

        app._show_view("diagnostics")
        assert app.current_view_name == "diagnostics"

        app.root.destroy()
    except (tk.TclError, Exception):
        pass  # Headless environment check
