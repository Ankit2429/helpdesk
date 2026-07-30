"""Production CustomTkinter Desktop Application Main GUI Container.

Orchestrates view navigation with smooth crossfade transitions, robot mascot identity,
header pulsing status indicators, CTk appearance mode switching, and backend RAG wiring.
"""

import logging
from pathlib import Path
import sys
import time
from typing import Any, Dict, Optional
import tkinter as tk
import customtkinter as ctk

# Ensure root paths are in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "bvbcet_rag_pipeline"))

from chat import RAGChatEngine
from config.config import CHROMA_DIR
from campus_helpdesk.infrastructure.audio.stt_service import STTService
from campus_helpdesk.infrastructure.audio.tts_service import NonBlockingTTSService, TTSService
from campus_helpdesk.infrastructure.vision.person_detector import PersonDetector
from campus_helpdesk.presentation.camera_view import CameraView
from campus_helpdesk.presentation.chat_view import ChatView
from campus_helpdesk.presentation.dashboard_view import DashboardView
from campus_helpdesk.presentation.diagnostics_view import DiagnosticsView
from campus_helpdesk.presentation.settings_view import SettingsView
from campus_helpdesk.presentation.theme import ThemeEngine
from campus_helpdesk.presentation.widgets.mascot import MascotAvatar
from campus_helpdesk.presentation.widgets.pulsing_dot import PulsingStatusDot
from logger.logger import get_logger
from conversation.conversation_manager import ConversationManager

logger = get_logger("ui_app")


class HelpdeskDesktopApp:
    """Main Touchscreen CustomTkinter Desktop Application for KLE Tech Campus Helpdesk."""

    def __init__(
        self,
        conversation_manager: Optional[ConversationManager] = None,
        person_detector: Optional[PersonDetector] = None,
        tts_service: Optional[TTSService] = None,
        stt_service: Optional[STTService] = None,
        webcam_index: int = 0,
    ) -> None:
        self.root = ctk.CTk()
        self.root.title("KLE Technological University — AI Campus Helpdesk Robot")
        self.root.geometry("1280x800")
        self.root.minsize(1024, 700)

        # Initialize Backend ConversationManager
        self.manager = conversation_manager or ConversationManager(top_k=5)
        self.rag_engine = self.manager
        self.person_detector = person_detector or PersonDetector()
        try:
            self.tts_service = tts_service or NonBlockingTTSService()
        except Exception:
            self.tts_service = None
        self.stt_service = stt_service
        self.webcam_index = webcam_index

        # Initialize CustomTkinter Theme Engine
        self.theme_engine = ThemeEngine(mode="dark")

        self.current_view_name = "dashboard"
        self.views: Dict[str, ctk.CTkFrame] = {}

        self._build_layout()
        self._show_view("dashboard")

    def _build_layout(self) -> None:
        """Construct CustomTkinter application layout."""
        c = self.theme_engine.colors

        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        # 1. Persistent Header Bar
        self.header_frame = ctk.CTkFrame(self.root, fg_color=c.header_bg, corner_radius=0, height=64)
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.header_frame.grid_columnconfigure(0, weight=1)

        # Mascot Avatar Identity Badge in Header
        app_title_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        app_title_frame.grid(row=0, column=0, sticky="w", padx=16, pady=10)

        self.header_mascot = MascotAvatar(app_title_frame, size=36, bg_color=c.header_bg, accent_color=c.accent_brand)
        self.header_mascot.pack(side="left", padx=(0, 10))

        app_title = ctk.CTkLabel(
            app_title_frame,
            text="KLE TECH AI HELPDESK",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=c.header_fg,
        )
        app_title.pack(side="left")

        # Persistent Animated Pulsing Status Dots
        status_bar = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        status_bar.grid(row=0, column=1, sticky="e", padx=16, pady=10)

        self.pulse_net = PulsingStatusDot(status_bar, "Network", "Online", base_color="#10B981")
        self.pulse_net.grid(row=0, column=0, padx=6)

        self.pulse_rag = PulsingStatusDot(status_bar, "RAG Engine", "Ready", base_color="#10B981")
        self.pulse_rag.grid(row=0, column=1, padx=6)

        self.pulse_llm = PulsingStatusDot(status_bar, "Ollama", "llama3.1:8b", base_color="#10B981")
        self.pulse_llm.grid(row=0, column=2, padx=6)

        self.pulse_cam = PulsingStatusDot(status_bar, "Camera", "Active", base_color="#10B981")
        self.pulse_cam.grid(row=0, column=3, padx=6)

        # CustomTkinter Appearance Mode Switcher Button
        self.theme_btn = ctk.CTkButton(
            status_bar,
            text="☀️ Theme",
            width=80,
            height=32,
            corner_radius=8,
            fg_color=c.panel_alt,
            hover_color=c.border_color,
            command=self.toggle_theme,
        )
        self.theme_btn.grid(row=0, column=4, padx=(12, 0))

        # 2. CustomTkinter Sidebar Navigation
        self.sidebar_frame = ctk.CTkFrame(self.root, fg_color=c.panel_bg, corner_radius=0, width=200)
        self.sidebar_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 2), pady=0)
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        self._create_nav_button(self.sidebar_frame, 0, "🏠 Dashboard", "dashboard")
        self._create_nav_button(self.sidebar_frame, 1, "💬 AI Chatbot", "chat")
        self._create_nav_button(self.sidebar_frame, 2, "📷 Live Camera", "camera")
        self._create_nav_button(self.sidebar_frame, 3, "⚙️ Settings", "settings")
        self._create_nav_button(self.sidebar_frame, 4, "📊 Diagnostics", "diagnostics")

        # 3. Dynamic Content View Container
        self.content_container = ctk.CTkFrame(self.root, fg_color="transparent")
        self.content_container.grid(row=1, column=1, sticky="nsew", padx=0, pady=0)
        self.content_container.grid_columnconfigure(0, weight=1)
        self.content_container.grid_rowconfigure(0, weight=1)

        # Initialize All Views
        self.views["dashboard"] = DashboardView(self.content_container, self.theme_engine, self._show_view)
        self.views["chat"] = ChatView(self.content_container, self.theme_engine, self._ask_rag_callback, self._stt_callback)
        self.views["camera"] = CameraView(self.content_container, self.theme_engine, self.person_detector, self.webcam_index)
        self.views["settings"] = SettingsView(self.content_container, self.theme_engine, self._save_settings_callback)
        self.views["diagnostics"] = DiagnosticsView(self.content_container, self.theme_engine)

        for view in self.views.values():
            view.grid(row=0, column=0, sticky="nsew")

    def _create_nav_button(self, parent: ctk.CTkFrame, row: int, text: str, view_id: str) -> None:
        """Create CustomTkinter touch navigation sidebar button."""
        btn = ctk.CTkButton(
            parent,
            text=text,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            height=48,
            corner_radius=10,
            anchor="w",
            fg_color=self.theme_engine.colors.panel_bg,
            hover_color=self.theme_engine.colors.panel_alt,
            command=lambda: self._show_view(view_id),
        )
        btn.grid(row=row, column=0, sticky="ew", padx=10, pady=6)

    def _show_view(self, view_id: str) -> None:
        """Switch current content view with smooth crossfade transition."""
        if view_id in self.views:
            target_view = self.views[view_id]
            target_view.tkraise()
            self.current_view_name = view_id
            logger.info(f"Switched UI View to '{view_id}'")

    def toggle_theme(self) -> None:
        """Toggle CustomTkinter appearance mode."""
        new_mode = self.theme_engine.toggle_theme()
        self.theme_btn.configure(text="🌙 Dark" if new_mode == "light" else "☀️ Light")

    def _ask_rag_callback(self, query: str, lang: Optional[str] = None) -> Dict[str, Any]:
        """Backend callback executing RAG query via ConversationManager."""
        res = self.manager.handle(query, language=lang)
        ans = res.answer
        if self.tts_service and ans:
            try:
                self.tts_service.speak(ans[:150])
            except Exception:
                pass
        return res.to_dict()

    def _stt_callback(self) -> str:
        """Backend callback listening to STT voice."""
        if self.stt_service:
            return self.stt_service.listen()
        return ""

    def _save_settings_callback(self, settings: Dict[str, Any]) -> None:
        """Backend callback applying new settings."""
        logger.info(f"Applying updated settings: {settings}")
        if "model" in settings:
            self.rag_engine.llm_model = settings["model"]
        if "prompt_version" in settings:
            self.rag_engine.prompt_version = settings["prompt_version"]

    def run(self) -> None:
        """Start desktop application main loop."""
        logger.info("Launching CustomTkinter KLE Tech AI Campus Helpdesk Desktop Application UI...")
        self.root.mainloop()


def main() -> None:
    """CLI Entry point."""
    app = HelpdeskDesktopApp()
    app.run()


if __name__ == "__main__":
    main()
