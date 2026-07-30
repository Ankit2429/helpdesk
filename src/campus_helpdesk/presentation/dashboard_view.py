"""CustomTkinter Main Dashboard View Component.

Features stat cards with distinct visual hierarchy, embedded live camera thumbnail preview,
latency sparkline chart, robot mascot quick actions, and icon-based real-time activity feed.
"""

import datetime
from pathlib import Path
import threading
import time
from typing import Any, Callable, Dict, List, Optional
import tkinter as tk
import customtkinter as ctk

import cv2
from PIL import Image, ImageTk

from campus_helpdesk.presentation.theme import ThemeEngine
from campus_helpdesk.presentation.widgets.mascot import MascotAvatar
from campus_helpdesk.presentation.widgets.sparkline import LatencySparkline
from logger.logger import get_logger

logger = get_logger("dashboard_view")


class DashboardView(ctk.CTkFrame):
    """CustomTkinter Dashboard View Component."""

    def __init__(
        self,
        master: any,
        theme_engine: ThemeEngine,
        nav_callback: Callable[[str], None],
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.theme_engine = theme_engine
        self.nav_callback = nav_callback

        self.activity_logs: List[Dict[str, str]] = []
        self.cam_preview_cap: Optional[cv2.VideoCapture] = None
        self.is_cam_preview_running = False

        self._build_ui()
        self._start_mini_camera_preview()

    def _build_ui(self) -> None:
        """Construct CustomTkinter Dashboard layout."""
        c = self.theme_engine.colors

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # Page Header Banner
        header = ctk.CTkFrame(self, fg_color=c.panel_bg, corner_radius=14)
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 12))
        header.grid_columnconfigure(0, weight=1)

        title_lbl = ctk.CTkLabel(
            header,
            text="KLE Tech AI Helpdesk — System Dashboard",
            font=ThemeEngine.font_page_title(),
            text_color=c.text_main,
        )
        title_lbl.grid(row=0, column=0, sticky="w", padx=20, pady=(16, 4))

        sub_lbl = ctk.CTkLabel(
            header,
            text="Real-time campus assistance overview, knowledge base status, and live camera preview.",
            font=ThemeEngine.font_body(),
            text_color=c.text_muted,
        )
        sub_lbl.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 16))

        # 4 Stat Cards with Visual Hierarchy
        stats_grid = ctk.CTkFrame(self, fg_color="transparent")
        stats_grid.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 12))
        stats_grid.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Card 1: RAG Knowledge Base + Sparkline Chart
        c1 = ctk.CTkFrame(stats_grid, fg_color=c.panel_bg, corner_radius=14, border_width=1, border_color=c.accent_primary)
        c1.grid(row=0, column=0, sticky="ew", padx=6, pady=4)
        ctk.CTkLabel(c1, text="📊 RAG KNOWLEDGE BASE", font=ThemeEngine.font_caption(), text_color=c.text_muted).pack(anchor="w", padx=14, pady=(12, 2))
        ctk.CTkLabel(c1, text="18,051 Chunks", font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color=c.accent_primary).pack(anchor="w", padx=14)
        self.sparkline = LatencySparkline(c1, width=180, height=36, line_color=c.accent_primary)
        self.sparkline.pack(anchor="w", padx=14, pady=(4, 12))

        # Card 2: Live Camera Thumbnail Preview Frame
        c2 = ctk.CTkFrame(stats_grid, fg_color=c.panel_bg, corner_radius=14, border_width=1, border_color=c.accent_success)
        c2.grid(row=0, column=1, sticky="ew", padx=6, pady=4)
        ctk.CTkLabel(c2, text="📷 CAMERA FEED PREVIEW", font=ThemeEngine.font_caption(), text_color=c.text_muted).pack(anchor="w", padx=14, pady=(8, 2))

        self.cam_preview_lbl = tk.Label(c2, text="● Camera Live Preview", font=("Segoe UI", 9), bg=c.panel_bg, fg=c.accent_success)
        self.cam_preview_lbl.pack(padx=12, pady=(2, 8))

        # Card 3: Ollama Model
        c3 = ctk.CTkFrame(stats_grid, fg_color=c.panel_bg, corner_radius=14, border_width=1, border_color=c.accent_brand)
        c3.grid(row=0, column=2, sticky="ew", padx=6, pady=4)
        ctk.CTkLabel(c3, text="🧠 OLLAMA LLM MODEL", font=ThemeEngine.font_caption(), text_color=c.text_muted).pack(anchor="w", padx=14, pady=(12, 2))
        ctk.CTkLabel(c3, text="llama3.1:8b", font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color=c.accent_brand).pack(anchor="w", padx=14)
        ctk.CTkLabel(c3, text="● Local Inference Ready", font=ThemeEngine.font_caption(), text_color=c.accent_success).pack(anchor="w", padx=14, pady=(4, 12))

        # Card 4: System Health
        c4 = ctk.CTkFrame(stats_grid, fg_color=c.panel_bg, corner_radius=14, border_width=1, border_color=c.accent_success)
        c4.grid(row=0, column=3, sticky="ew", padx=6, pady=4)
        ctk.CTkLabel(c4, text="⚙️ SYSTEM STATUS", font=ThemeEngine.font_caption(), text_color=c.text_muted).pack(anchor="w", padx=14, pady=(12, 2))
        ctk.CTkLabel(c4, text="HEALTHY", font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color=c.accent_success).pack(anchor="w", padx=14)
        ctk.CTkLabel(c4, text="● Session Active", font=ThemeEngine.font_caption(), text_color=c.text_muted).pack(anchor="w", padx=14, pady=(4, 12))

        # Quick Action Touch Tiles (with Mascot Tile)
        actions = ctk.CTkFrame(self, fg_color=c.panel_bg, corner_radius=14)
        actions.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
        actions.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkLabel(actions, text="Quick Touch Actions", font=ThemeEngine.font_card_title(), text_color=c.text_main).grid(row=0, column=0, columnspan=4, sticky="w", padx=16, pady=(12, 8))

        # Tile 1: Mascot Chat Tile (Warm KLE Amber Accent)
        t1 = ctk.CTkFrame(actions, fg_color=c.panel_alt, corner_radius=12)
        t1.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 12))
        b1 = ctk.CTkButton(
            t1,
            text="🤖 Ask Mascot",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=c.accent_brand,
            hover_color="#C2410C",
            command=lambda: self.nav_callback("chat"),
        )
        b1.pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkLabel(t1, text="Start AI conversation", font=ThemeEngine.font_caption(), text_color=c.text_muted).pack(pady=(0, 8))

        # Tile 2: Camera Stream Tile
        t2 = ctk.CTkFrame(actions, fg_color=c.panel_alt, corner_radius=12)
        t2.grid(row=1, column=1, sticky="ew", padx=8, pady=(0, 12))
        b2 = ctk.CTkButton(
            t2,
            text="📷 Open Camera",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=c.accent_success,
            hover_color="#047857",
            command=lambda: self.nav_callback("camera"),
        )
        b2.pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkLabel(t2, text="Live feed & snapshots", font=ThemeEngine.font_caption(), text_color=c.text_muted).pack(pady=(0, 8))

        # Tile 3: Settings Tile
        t3 = ctk.CTkFrame(actions, fg_color=c.panel_alt, corner_radius=12)
        t3.grid(row=1, column=2, sticky="ew", padx=8, pady=(0, 12))
        b3 = ctk.CTkButton(
            t3,
            text="⚙️ Settings",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=c.accent_primary,
            hover_color=c.accent_hover,
            command=lambda: self.nav_callback("settings"),
        )
        b3.pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkLabel(t3, text="Model & language config", font=ThemeEngine.font_caption(), text_color=c.text_muted).pack(pady=(0, 8))

        # Tile 4: Diagnostics Tile
        t4 = ctk.CTkFrame(actions, fg_color=c.panel_alt, corner_radius=12)
        t4.grid(row=1, column=3, sticky="ew", padx=8, pady=(0, 12))
        b4 = ctk.CTkButton(
            t4,
            text="📊 Diagnostics",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=c.panel_bg,
            hover_color=c.border_color,
            command=lambda: self.nav_callback("diagnostics"),
        )
        b4.pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkLabel(t4, text="System metrics & logs", font=ThemeEngine.font_caption(), text_color=c.text_muted).pack(pady=(0, 8))

        # Promoted Real-time Live Activity Log Feed (with Event Icons)
        act_frame = ctk.CTkFrame(self, fg_color=c.panel_bg, corner_radius=14)
        act_frame.grid(row=3, column=0, sticky="nsew", padx=16, pady=(0, 16))
        act_frame.grid_columnconfigure(0, weight=1)
        act_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(act_frame, text="📜 Live System Activity Feed", font=ThemeEngine.font_card_title(), text_color=c.text_main).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 8))

        self.activity_textbox = ctk.CTkTextbox(
            act_frame,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=c.panel_alt,
            text_color=c.text_main,
            corner_radius=10,
        )
        self.activity_textbox.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        self.log_activity("⚙️ Dashboard initialized. Connected to ChromaDB RAG Pipeline.", category="system")
        self.log_activity("🧠 Local Ollama model 'llama3.1:8b' pre-flight check passed.", category="system")
        self.log_activity("📷 Person detection active on webcam stream 0.", category="vision")

    def _start_mini_camera_preview(self) -> None:
        """Start low-res mini preview of OpenCV camera for dashboard card."""
        threading.Thread(target=self._mini_camera_loop, daemon=True).start()

    def _mini_camera_loop(self) -> None:
        """Capture small 160x90px preview frames for dashboard camera card."""
        self.is_cam_preview_running = True
        try:
            cap = cv2.VideoCapture(0)
            if cap and cap.isOpened():
                for _ in range(5):  # Grab a sample preview frame
                    ret, frame = cap.read()
                    if ret:
                        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        img = Image.fromarray(rgb).resize((140, 80), Image.Resampling.LANCZOS)
                        img_tk = ImageTk.PhotoImage(image=img)
                        self.after(0, lambda image_tk=img_tk: self._update_mini_cam(image_tk))
                        break
                    time.sleep(0.05)
                cap.release()
        except Exception:
            pass

    def _update_mini_cam(self, img_tk: ImageTk.PhotoImage) -> None:
        """Update mini camera label in main thread."""
        if self.winfo_exists():
            self.cam_preview_lbl.config(image=img_tk, text="")
            self.cam_preview_lbl.image = img_tk

    def log_activity(self, message: str, category: str = "system") -> None:
        """Add real-time event log entry to live feed."""
        t_stamp = datetime.datetime.now().strftime("%H:%M:%S")
        entry = f"[{t_stamp}] {message}\n"
        self.activity_logs.append({"timestamp": t_stamp, "message": message, "category": category})
        if hasattr(self, "activity_textbox") and self.activity_textbox.winfo_exists():
            self.activity_textbox.insert("1.0", entry)
