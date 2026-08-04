import datetime
import logging
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional
import tkinter as tk
import customtkinter as ctk

from campus_helpdesk.presentation.theme import ThemeEngine
from campus_helpdesk.presentation.widgets.mascot import MascotAvatar


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"campus_helpdesk.{name}")


logger = get_logger("chat_view")


class ChatView(ctk.CTkFrame):
    """CustomTkinter Touchscreen AI Kiosk Chat View Component."""

    def __init__(
        self,
        master: any,
        theme_engine: ThemeEngine,
        ask_callback: Callable[[str, Optional[str]], Dict[str, Any]],
        ask_stream_callback: Optional[Callable[[str, Optional[str]], Any]] = None,
        stt_callback: Optional[Callable[[], str]] = None,
        tts_service: Optional[Any] = None,
        on_language_changed: Optional[Callable[[str], None]] = None,
        show_sources: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.theme_engine = theme_engine
        self.ask_callback = ask_callback
        self.ask_stream_callback = ask_stream_callback
        self.stt_callback = stt_callback
        self.tts_service = tts_service
        self.on_language_changed = on_language_changed

        self.selected_language = "en"
        self.is_recording = False
        self.show_sources = show_sources
        self._last_sources: List[Dict[str, Any]] = []

        self._cancel_event = threading.Event()
        self._thinking_timer: Optional[str] = None
        self._thinking_dot_count = 1
        self._active_assistant_label: Optional[ctk.CTkLabel] = None
        self._active_assistant_card: Optional[ctk.CTkFrame] = None

        self._build_ui()
        self._start_clock_timer()

    def _build_ui(self) -> None:
        """Construct Premium Kiosk Chat Layout."""
        c = self.theme_engine.colors

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 1. Glassmorphic Header Bar with Mascot Avatar, Online Pill & Clock
        header = ctk.CTkFrame(self, fg_color=c.panel_bg, corner_radius=16, border_width=1, border_color=c.border_color)
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        header.grid_columnconfigure(1, weight=1)

        # Left Branding Group
        brand_frame = ctk.CTkFrame(header, fg_color="transparent")
        brand_frame.grid(row=0, column=0, sticky="w", padx=16, pady=10)

        self.mascot_badge = MascotAvatar(brand_frame, size=42, bg_color=c.panel_bg, accent_color=c.accent_brand)
        self.mascot_badge.pack(side="left", padx=(0, 12))

        title_box = ctk.CTkFrame(brand_frame, fg_color="transparent")
        title_box.pack(side="left")

        ctk.CTkLabel(
            title_box,
            text="Sparky — KLE Tech AI Campus Guide",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=c.text_main,
        ).pack(anchor="w")

        sub_header_frame = ctk.CTkFrame(title_box, fg_color="transparent")
        sub_header_frame.pack(anchor="w")

        ctk.CTkLabel(
            sub_header_frame,
            text="● ONLINE",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=c.accent_success,
        ).pack(side="left")

        # Right Language Switcher & Live Clock Widget
        right_header = ctk.CTkFrame(header, fg_color="transparent")
        right_header.grid(row=0, column=2, sticky="e", padx=16, pady=10)

        self.clock_lbl = ctk.CTkLabel(
            right_header,
            text="12:00 PM",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=c.text_main,
        )
        self.clock_lbl.pack(side="left", padx=(0, 16))

        ctk.CTkLabel(right_header, text="Language:", font=ThemeEngine.font_caption(), text_color=c.text_muted).pack(side="left", padx=(0, 6))
        self.lang_option = ctk.CTkOptionMenu(
            right_header,
            values=["English", "Kannada (ಕನ್ನಡ)", "Hindi (हिंदी)", "Hinglish", "Kanglish"],
            command=self._on_lang_change,
            fg_color=c.accent_primary,
            button_color=c.accent_hover,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            height=32,
            corner_radius=8,
        )
        self.lang_option.pack(side="left")

        # 2. Scrollable Message Stream Container (Bubble Cards)
        self.chat_display = ctk.CTkScrollableFrame(
            self,
            fg_color=c.bg_main,
            corner_radius=16,
            border_width=1,
            border_color=c.border_color,
        )
        self.chat_display.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 6))
        self.chat_display.grid_columnconfigure(0, weight=1)

        # 3. Permanent Assistant Status Bar
        self.status_bar = ctk.CTkFrame(self, fg_color=c.panel_bg, height=36, corner_radius=10)
        self.status_bar.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 6))
        self.status_bar.grid_columnconfigure(0, weight=1)

        self.status_lbl = ctk.CTkLabel(
            self.status_bar,
            text="⚡ READY — Standby for queries",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=c.accent_primary,
            anchor="w",
        )
        self.status_lbl.grid(row=0, column=0, sticky="w", padx=16, pady=6)

        # 4. Touch Input & Voice Control Bar
        input_bar = ctk.CTkFrame(self, fg_color=c.panel_bg, corner_radius=16, border_width=1, border_color=c.border_color)
        input_bar.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 12))
        input_bar.grid_columnconfigure(0, weight=1)

        self.input_entry = ctk.CTkEntry(
            input_bar,
            placeholder_text="Ask Sparky about courses, admissions, hostels, faculty, campus map...",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            height=48,
            corner_radius=24,
            border_width=1,
            border_color=c.border_color,
            fg_color=c.bg_main,
        )
        self.input_entry.grid(row=0, column=0, sticky="ew", padx=(16, 10), pady=10)
        self.input_entry.bind("<Return>", lambda event: self._send_message())

        # Animated Pill Mic Button
        self.mic_btn = ctk.CTkButton(
            input_bar,
            text="🎙️ Tap to Speak",
            width=135,
            height=48,
            corner_radius=24,
            fg_color=c.accent_primary,
            hover_color=c.accent_hover,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self._toggle_voice,
        )
        self.mic_btn.grid(row=0, column=1, padx=(0, 8), pady=10)

        # Touch Send Button
        send_btn = ctk.CTkButton(
            input_bar,
            text="Send 🚀",
            width=110,
            height=48,
            corner_radius=24,
            fg_color=c.accent_brand,
            hover_color="#C2410C",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self._send_message,
        )
        send_btn.grid(row=0, column=2, padx=(0, 16), pady=10)

        # Welcome Assistant Greeting Card
        self._add_assistant_bubble("Welcome! Sparky is ready to assist you with KLE Technological University queries. Ask a question or tap the mic button to start.")

    def _start_clock_timer(self) -> None:
        """Update clock widget every second."""
        now_str = datetime.datetime.now().strftime("%I:%M:%S %p")
        self.clock_lbl.configure(text=now_str)
        self.after(1000, self._start_clock_timer)

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
        self._add_system_badge(f"Switched conversation language to '{choice}'.")
        if self.on_language_changed:
            self.on_language_changed(self.selected_language)

    def trigger_greeting(self, greeting_text: str, language: str) -> None:
        """Receive HRI greeting trigger and speak/display in active UI language."""
        logger.info(f"[ChatUI Greeting Received] Displaying & Speaking: '{greeting_text}'")
        self.after(0, lambda: self._add_assistant_bubble(greeting_text))

        if self.tts_service:
            try:
                self.update_voice_state("speaking", "Speaking greeting...")
                self.tts_service.speak(greeting_text)
                self.after(2500, lambda: self.update_voice_state("ready"))
            except Exception as tts_err:
                logger.warning(f"Greeting TTS error: {tts_err}")

    def _cancel_active_tasks(self) -> None:
        """Cancel any running response generation or TTS playback."""
        self._cancel_event.set()
        self._stop_thinking_animation()
        if self.tts_service and hasattr(self.tts_service, "stop"):
            try:
                self.tts_service.stop()
            except Exception as e:
                logger.warning(f"Error stopping TTS playback: {e}")
        self._cancel_event = threading.Event()

    def start_voice_recording(self, status_msg: str = "Listening for voice input...") -> None:
        """Start voice capture session, updating UI status badge to listening."""
        if not self.stt_callback:
            self._add_system_badge("Voice STT hardware module is offline.")
            return

        if not self.is_recording:
            self._cancel_active_tasks()
            self.is_recording = True
            self.update_voice_state("listening", status_msg)
            logger.info(f"[Voice Recording Started] Message='{status_msg}'")
            threading.Thread(target=self._capture_voice, daemon=True).start()

    def _toggle_voice(self) -> None:
        """Toggle voice input state."""
        if not self.is_recording:
            self.start_voice_recording("Listening for voice input...")
        else:
            self.is_recording = False
            self.update_voice_state("ready")

    def _capture_voice(self) -> None:
        """Capture voice transcript in background thread."""
        try:
            transcript = self.stt_callback()
            self.after(0, lambda: self._on_voice_transcript(transcript))
        except Exception as e:
            self.after(0, lambda: self._on_voice_transcript(f"Voice error: {e}"))

    def _on_voice_transcript(self, transcript: str) -> None:
        """Handle voice transcript result."""
        self.is_recording = False
        self.update_voice_state("ready")
        if transcript and not transcript.startswith("Voice error"):
            logger.info(f"[Speech recognized] '{transcript}'")
            self.input_entry.delete(0, "end")
            self.input_entry.insert(0, transcript)
            self._send_message()
        elif transcript:
            self._add_system_badge(transcript)

    def update_voice_state(self, state_val: str, message: str = "") -> None:
        """Update UI status panel and voice button animation based on AssistantState."""
        c = self.theme_engine.colors
        state_key = state_val.lower()

        state_map = {
            "ready": ("⚡ READY — Standby", "🎙️ Tap to Speak", c.accent_primary, c.accent_primary),
            "idle": ("⚡ READY — Standby", "🎙️ Tap to Speak", c.accent_primary, c.accent_primary),
            "listening": ("🎤 LISTENING — Speak your question...", "🔴 Listening...", c.accent_danger, c.accent_danger),
            "thinking": ("🧠 THINKING — RAG Searching...", "⏳ Thinking...", c.accent_warning, c.accent_warning),
            "speaking": ("🔊 SPEAKING — Synthesizing answer...", "🔊 Speaking...", c.accent_success, c.accent_success),
            "error": ("⚠️ ERROR — Processing fault", "⚠️ Error", c.accent_danger, c.accent_danger),
        }

        status_text, btn_text, btn_color, text_color = state_map.get(
            state_key, (f"STATE: {state_val}", "🎙️ Voice", c.accent_primary, c.text_main)
        )
        display_str = f"{status_text} {message}".strip()
        self.status_lbl.configure(text=display_str, text_color=text_color)
        self.mic_btn.configure(text=btn_text, fg_color=btn_color)

    def update_live_transcript(self, partial_text: str, is_final: bool) -> None:
        """Update live speech transcript."""
        if not is_final:
            self.status_lbl.configure(text=f"🎤 LISTENING: \"{partial_text}\"")
        else:
            self.status_lbl.configure(text="✅ Finalizing transcript...")
            self.input_entry.delete(0, "end")
            self.input_entry.insert(0, partial_text)

    def _send_message(self) -> None:
        """Process user input and start real-time RAG response streaming."""
        query = self.input_entry.get().strip()
        if not query:
            return

        self._cancel_active_tasks()
        cancel_token = self._cancel_event

        self.input_entry.delete(0, "end")
        t_stamp = datetime.datetime.now().strftime("%I:%M %p")

        # 1. Add User Message Bubble Card
        self._add_user_bubble(query, t_stamp)

        # 2. Add Thinking Assistant Bubble Card
        self._add_thinking_bubble(t_stamp)

        # 3. Launch RAG Worker
        self.update_voice_state("thinking", "Searching knowledge base...")
        threading.Thread(
            target=self._run_rag_stream_worker,
            args=(query, cancel_token),
            daemon=True,
        ).start()

    def _add_user_bubble(self, text: str, timestamp: str) -> None:
        """Render modern right-aligned user message card."""
        c = self.theme_engine.colors
        wrapper = ctk.CTkFrame(self.chat_display, fg_color="transparent")
        wrapper.pack(fill="x", padx=12, pady=6, anchor="e")

        card = ctk.CTkFrame(
            wrapper,
            fg_color=c.user_bubble_bg,
            corner_radius=16,
        )
        card.pack(side="right", anchor="e")

        ctk.CTkLabel(
            card,
            text=f"👤 You • {timestamp}",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#93C5FD",
        ).pack(anchor="e", padx=14, pady=(8, 2))

        ctk.CTkLabel(
            card,
            text=text,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=c.user_bubble_fg,
            wraplength=480,
            justify="right",
        ).pack(anchor="e", padx=14, pady=(0, 10))

    def _add_thinking_bubble(self, timestamp: str) -> None:
        """Create assistant response card displaying animated thinking dots."""
        c = self.theme_engine.colors
        wrapper = ctk.CTkFrame(self.chat_display, fg_color="transparent")
        wrapper.pack(fill="x", padx=12, pady=6, anchor="w")

        card = ctk.CTkFrame(
            wrapper,
            fg_color=c.panel_bg,
            border_width=1,
            border_color=c.border_color,
            corner_radius=16,
        )
        card.pack(side="left", anchor="w")

        header_frame = ctk.CTkFrame(card, fg_color="transparent")
        header_frame.pack(anchor="w", padx=14, pady=(8, 4))

        ctk.CTkLabel(
            header_frame,
            text=f"🤖 Sparky • {timestamp}",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=c.accent_brand,
        ).pack(side="left")

        lbl = ctk.CTkLabel(
            card,
            text="🧠 Thinking .",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=c.text_main,
            wraplength=480,
            justify="left",
        )
        lbl.pack(anchor="w", padx=14, pady=(0, 10))

        self._active_assistant_card = card
        self._active_assistant_label = lbl
        self._thinking_dot_count = 1
        self._start_thinking_animation()

    def _start_thinking_animation(self) -> None:
        """Animate thinking dots periodically until tokens arrive."""
        if self._active_assistant_label:
            dots = "." * (self._thinking_dot_count % 4)
            if not dots:
                dots = "."
            self._active_assistant_label.configure(text=f"🧠 Thinking {dots}")
            self._thinking_dot_count += 1
            self._thinking_timer = self.after(400, self._start_thinking_animation)

    def _stop_thinking_animation(self) -> None:
        """Stop periodic dot animation timer."""
        if self._thinking_timer:
            self.after_cancel(self._thinking_timer)
            self._thinking_timer = None

    def _add_assistant_bubble(self, text: str) -> None:
        """Append standalone assistant message card."""
        c = self.theme_engine.colors
        t_stamp = datetime.datetime.now().strftime("%I:%M %p")

        wrapper = ctk.CTkFrame(self.chat_display, fg_color="transparent")
        wrapper.pack(fill="x", padx=12, pady=6, anchor="w")

        card = ctk.CTkFrame(
            wrapper,
            fg_color=c.panel_bg,
            border_width=1,
            border_color=c.border_color,
            corner_radius=16,
        )
        card.pack(side="left", anchor="w")

        ctk.CTkLabel(
            card,
            text=f"🤖 Sparky • {t_stamp}",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=c.accent_brand,
        ).pack(anchor="w", padx=14, pady=(8, 2))

        ctk.CTkLabel(
            card,
            text=text,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=c.text_main,
            wraplength=480,
            justify="left",
        ).pack(anchor="w", padx=14, pady=(0, 10))

    def _add_system_badge(self, text: str) -> None:
        """Render centered system status badge."""
        c = self.theme_engine.colors
        wrapper = ctk.CTkFrame(self.chat_display, fg_color="transparent")
        wrapper.pack(fill="x", padx=12, pady=4)

        badge = ctk.CTkFrame(wrapper, fg_color=c.panel_alt, corner_radius=12)
        badge.pack(anchor="center")

        ctk.CTkLabel(
            badge,
            text=f"ℹ️  {text}",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=c.text_muted,
        ).pack(padx=12, pady=4)

    def _run_rag_stream_worker(self, query: str, cancel_token: threading.Event) -> None:
        """Execute RAG retrieval and stream LLM tokens directly into active assistant card."""
        tokens_received = 0
        try:
            logger.info(f"[Retrieval started] Query='{query}'")

            if cancel_token.is_set():
                return

            if not self.ask_stream_callback:
                if self.ask_callback:
                    res = self.ask_callback(query, self.selected_language)
                    if not cancel_token.is_set():
                        self.after(0, lambda: self._finalize_non_streamed_response(res))
                else:
                    self.after(0, lambda: self._handle_worker_error("No chat service callback configured."))
                return

            stream = self.ask_stream_callback(query, self.selected_language)
            first_token = True
            accumulated_text = ""
            sentence_buffer = ""

            for token in stream:
                if cancel_token.is_set():
                    logger.info("[Task Cancelled] Aborting generation stream.")
                    return

                tokens_received += 1
                if first_token:
                    self._stop_thinking_animation()
                    self.after(0, lambda: self.update_voice_state("speaking", "Streaming response..."))
                    first_token = False

                accumulated_text += token
                sentence_buffer += token

                # Stream token chunk to UI label
                self.after(0, lambda t_txt=accumulated_text: self._update_active_assistant_text(t_txt))

                # Synthesize TTS for completed clauses/sentences simultaneously as text appears
                sentences = re.split(r'(?<=[.!?,;\n।])\s+', sentence_buffer)
                if len(sentences) > 1:
                    complete_sentence = sentences[0].strip()
                    sentence_buffer = " ".join(sentences[1:])
                    if complete_sentence and len(complete_sentence) >= 3 and self.tts_service:
                        try:
                            self.tts_service.speak(complete_sentence, language=self.selected_language)
                        except Exception as tts_err:
                            logger.warning(f"TTS playback exception: {tts_err}")

            # Flush remaining sentence buffer to TTS simultaneously
            if sentence_buffer.strip() and self.tts_service and not cancel_token.is_set():
                final_sentence = sentence_buffer.strip()
                try:
                    self.tts_service.speak(final_sentence, language=self.selected_language)
                except Exception as tts_err:
                    logger.warning(f"TTS final sentence playback exception: {tts_err}")

            # Fallback if stream produced 0 tokens
            if tokens_received == 0 and not cancel_token.is_set() and self.ask_callback:
                logger.warning("Stream yielded 0 tokens. Invoking fallback non-streaming ask_callback...")
                res = self.ask_callback(query, self.selected_language)
                if not cancel_token.is_set():
                    self.after(0, lambda: self._finalize_non_streamed_response(res))
                    return

            logger.info("[Response finished]")
            self.after(0, lambda: self.update_voice_state("ready"))

        except Exception as err:
            logger.error(f"Error in streaming chat worker: {err}", exc_info=True)
            self.after(0, lambda err_msg=str(err): self._handle_worker_error(err_msg))

    def _update_active_assistant_text(self, text: str) -> None:
        """Update active assistant label text safely on main thread."""
        if self._active_assistant_label:
            self._active_assistant_label.configure(text=text)

    def _finalize_non_streamed_response(self, result: Dict[str, Any]) -> None:
        """Display non-streamed result in active assistant bubble and trigger TTS in parallel."""
        self._stop_thinking_animation()
        ans = result.get("answer", "") or "I could not retrieve an answer for your query."
        if self._active_assistant_label:
            self._active_assistant_label.configure(text=ans)

        # Simultaneously start TTS speech playback when answer text displays
        if ans and self.tts_service:
            try:
                self.tts_service.speak(ans, language=self.selected_language)
            except Exception as tts_err:
                logger.warning(f"TTS non-streamed playback exception: {tts_err}")

        sources = result.get("sources", [])
        if self.show_sources and sources and self._active_assistant_card:
            src_box = ctk.CTkFrame(self._active_assistant_card, fg_color="transparent")
            src_box.pack(anchor="w", padx=14, pady=(0, 8))
            ctk.CTkLabel(
                src_box,
                text="📚 Retrieved Context Sources:",
                font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                text_color=self.theme_engine.colors.text_muted,
            ).pack(anchor="w")

            for idx, s in enumerate(sources[:3], start=1):
                doc_name = s.get("source") or "Document"
                score = s.get("score", 0.0)
                chip = ctk.CTkFrame(src_box, fg_color=self.theme_engine.colors.panel_alt, corner_radius=8)
                chip.pack(anchor="w", pady=2)
                ctk.CTkLabel(
                    chip,
                    text=f"[{idx}] {doc_name} (Relevance: {score:.2f})",
                    font=ctk.CTkFont(family="Segoe UI", size=10),
                    text_color=self.theme_engine.colors.text_main,
                ).pack(padx=8, pady=2)

        self.update_voice_state("ready")

    def _handle_worker_error(self, err_msg: str) -> None:
        """Render visible error state."""
        self._stop_thinking_animation()
        if self._active_assistant_label:
            self._active_assistant_label.configure(
                text=f"⚠️ I encountered an issue processing your query: {err_msg}",
                text_color=self.theme_engine.colors.accent_danger,
            )
        self.update_voice_state("error", err_msg)