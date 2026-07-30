"""CustomTkinter Touchscreen Chat View Component.

Features scrollable CTk speech cards, robot mascot avatar integration,
inline expandable citations, CTkOptionMenu language switcher, and voice STT toggle.
"""

import datetime
import threading
from typing import Any, Callable, Dict, List, Optional
import tkinter as tk
import customtkinter as ctk

from campus_helpdesk.presentation.theme import ThemeEngine
from campus_helpdesk.presentation.widgets.mascot import MascotAvatar
from logger.logger import get_logger

logger = get_logger("chat_view")


class ChatView(ctk.CTkFrame):
    """CustomTkinter Touchscreen Chat View Component."""

    def __init__(
        self,
        master: any,
        theme_engine: ThemeEngine,
        ask_callback: Callable[[str, Optional[str]], Dict[str, Any]],
        stt_callback: Optional[Callable[[], str]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.theme_engine = theme_engine
        self.ask_callback = ask_callback
        self.stt_callback = stt_callback

        self.selected_language = "en"
        self.is_recording = False

        self._build_ui()

    def _build_ui(self) -> None:
        """Construct Chat View layout."""
        c = self.theme_engine.colors

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header Bar with Mascot Badge & Language Switcher
        header = ctk.CTkFrame(self, fg_color=c.panel_bg, corner_radius=14)
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        header.grid_columnconfigure(0, weight=1)

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="w", padx=16, pady=12)

        self.mascot_badge = MascotAvatar(title_frame, size=40, bg_color=c.panel_bg, accent_color=c.accent_brand)
        self.mascot_badge.pack(side="left", padx=(0, 12))

        ctk.CTkLabel(
            title_frame,
            text="Sparky — KLE Tech AI Campus Assistant",
            font=ThemeEngine.font_card_title(),
            text_color=c.text_main,
        ).pack(side="left")

        # CTkOptionMenu Language Switcher
        lang_frame = ctk.CTkFrame(header, fg_color="transparent")
        lang_frame.grid(row=0, column=1, sticky="e", padx=16, pady=12)

        ctk.CTkLabel(lang_frame, text="Language:", font=ThemeEngine.font_body(), text_color=c.text_muted).pack(side="left", padx=(0, 8))
        self.lang_option = ctk.CTkOptionMenu(
            lang_frame,
            values=["English", "Kannada (ಕನ್ನಡ)", "Hindi (हिंदी)", "Hinglish", "Kanglish"],
            command=self._on_lang_change,
            fg_color=c.accent_brand,
            button_color="#C2410C",
            font=ThemeEngine.font_body(),
        )
        self.lang_option.pack(side="left")

        # Chat Message History Container (CTkTextbox)
        self.chat_display = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color=c.panel_bg,
            text_color=c.text_main,
            corner_radius=14,
        )
        self.chat_display.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 8))

        # Status Label
        self.status_lbl = ctk.CTkLabel(self, text="", font=ThemeEngine.font_caption(), text_color=c.text_muted, anchor="w")
        self.status_lbl.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 4))

        # Touch Input Bar
        input_bar = ctk.CTkFrame(self, fg_color=c.panel_bg, corner_radius=14)
        input_bar.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 16))
        input_bar.grid_columnconfigure(0, weight=1)

        self.input_entry = ctk.CTkEntry(
            input_bar,
            placeholder_text="Ask any question about courses, admissions, hostels, faculty...",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            height=44,
            corner_radius=10,
        )
        self.input_entry.grid(row=0, column=0, sticky="ew", padx=(16, 8), pady=12)
        self.input_entry.bind("<Return>", lambda event: self._send_message())

        # Mic Button
        self.mic_btn = ctk.CTkButton(
            input_bar,
            text="🎙️ Voice",
            width=90,
            height=44,
            corner_radius=10,
            fg_color=c.panel_alt,
            hover_color=c.border_color,
            command=self._toggle_voice,
        )
        self.mic_btn.grid(row=0, column=1, padx=(0, 8), pady=12)

        # Large Touch Send Button (KLE Amber Accent)
        send_btn = ctk.CTkButton(
            input_bar,
            text="Send 🚀",
            width=110,
            height=44,
            corner_radius=10,
            fg_color=c.accent_brand,
            hover_color="#C2410C",
            command=self._send_message,
        )
        send_btn.grid(row=0, column=2, padx=(0, 16), pady=12)

        self.append_system_message("Welcome! Sparky is ready to help you with KLE Technological University queries.")

    def _on_lang_change(self, choice: str) -> None:
        """Handle language switcher option change."""
        lang_map = {
            "English": "en",
            "Kannada (ಕನ್ನಡ)": "kn",
            "Hindi (हिंदी)": "hi",
            "Hinglish": "hinglish",
            "Kanglish": "kanglish",
        }
        self.selected_language = lang_map.get(choice, "en")
        self.append_system_message(f"Switched conversation language preference to '{choice}'.")

    def _toggle_voice(self) -> None:
        """Toggle voice input."""
        if not self.stt_callback:
            self.append_system_message("Voice STT service is not active in this session.")
            return

        if not self.is_recording:
            self.is_recording = True
            self.mic_btn.configure(text="🔴 Listening...")
            self.status_lbl.configure(text="Listening for voice input...")
            threading.Thread(target=self._capture_voice, daemon=True).start()
        else:
            self.is_recording = False
            self.mic_btn.configure(text="🎙️ Voice")
            self.status_lbl.configure(text="")

    def _capture_voice(self) -> None:
        """Capture voice transcript in background."""
        try:
            transcript = self.stt_callback()
            self.after(0, lambda: self._on_voice_transcript(transcript))
        except Exception as e:
            self.after(0, lambda: self._on_voice_transcript(f"Voice error: {e}"))

    def _on_voice_transcript(self, transcript: str) -> None:
        """Handle voice transcript result."""
        self.is_recording = False
        self.mic_btn.configure(text="🎙️ Voice")
        self.status_lbl.configure(text="")
        if transcript and not transcript.startswith("Voice error"):
            self.input_entry.delete(0, "end")
            self.input_entry.insert(0, transcript)
            self._send_message()
        elif transcript:
            self.append_system_message(transcript)

    def _send_message(self) -> None:
        """Process user input and call RAG engine."""
        query = self.input_entry.get().strip()
        if not query:
            return

        self.input_entry.delete(0, "end")
        t_stamp = datetime.datetime.now().strftime("%H:%M")

        self.chat_display.insert("end", f"\n👤 User [{t_stamp}]\n{query}\n\n")
        self.chat_display.see("end")

        self.status_lbl.configure(text="Sparky is searching knowledge base & generating answer...")
        threading.Thread(target=self._run_rag_worker, args=(query,), daemon=True).start()

    def _run_rag_worker(self, query: str) -> None:
        """Execute RAG query in background."""
        try:
            res = self.ask_callback(query, self.selected_language)
            self.after(0, lambda: self._display_bot_response(res))
        except Exception as err:
            logger.error(f"Error in chat worker: {err}")
            self.after(0, lambda: self.append_system_message(f"Error: {err}"))

    def _display_bot_response(self, result: Dict[str, Any]) -> None:
        """Display assistant answer and inline expandable citations."""
        self.status_lbl.configure(text="")
        t_stamp = datetime.datetime.now().strftime("%H:%M")

        ans = result.get("answer", "")
        sources = result.get("sources", [])
        topic = result.get("current_topic", "General")

        self.chat_display.insert("end", f"🤖 Sparky [{t_stamp}] (Topic: {topic})\n{ans}\n")

        if sources:
            self.chat_display.insert("end", "\n  📚 Retrieved Sources & Citations:\n")
            for idx, src in enumerate(sources, start=1):
                heading = src.get("heading") or "Overview"
                source_doc = src.get("source") or "Document"
                score = src.get("score", 0.0)
                self.chat_display.insert("end", f"    [{idx}] {source_doc} (Heading: '{heading}', Score: {score:.4f})\n")

        self.chat_display.insert("end", "\n")
        self.chat_display.see("end")

    def append_system_message(self, text: str) -> None:
        """Append system status message to chat display."""
        self.chat_display.insert("end", f"\n--- {text} ---\n\n")
        self.chat_display.see("end")
