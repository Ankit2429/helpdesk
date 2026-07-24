"""Tkinter Desktop Interface for Campus Helpdesk Robot Demo."""

import logging
import threading
import tkinter as tk
from tkinter import scrolledtext

import cv2

from campus_helpdesk.application.chat_service import ChatService
from campus_helpdesk.application.session_controller import RobotStatus, SessionController
from campus_helpdesk.infrastructure.audio.stt_service import STTService
from campus_helpdesk.infrastructure.audio.tts_service import TTSService
from campus_helpdesk.infrastructure.vision.person_detector import PersonDetector

logger = logging.getLogger(__name__)

# --- Modern Color Palette ---
BG_MAIN = "#F8FAFC"        # Slate 50 window background
PANEL_BG = "#FFFFFF"       # Pure white panel
BORDER_COLOR = "#E2E8F0"   # Slate 200 border
HEADER_BG = "#0F172A"      # Slate 900 dark navy header
HEADER_FG = "#F8FAFC"      # White header text
TEXT_MAIN = "#0F172A"      # Dark slate primary text
TEXT_MUTED = "#64748B"     # Slate 500 muted text

# Accent & Button Colors
ACCENT_PRIMARY = "#2563EB"   # Royal Blue 600
ACCENT_HOVER = "#1D4ED8"     # Royal Blue 700
MIC_BG_NORMAL = "#E0F2FE"    # Sky 100
MIC_FG_NORMAL = "#0284C7"    # Sky 700
MIC_BG_HOVER = "#BAE6FD"     # Sky 200
MIC_BG_ACTIVE = "#FEE2E2"    # Red 100
MIC_FG_ACTIVE = "#DC2626"    # Red 600

# Chat Message Colors
USER_NAME_FG = "#1D4ED8"     # Blue 700
USER_TEXT_FG = "#1E3A8A"     # Blue 900
BOT_NAME_FG = "#15803D"      # Green 700
BOT_TEXT_FG = "#14532D"      # Green 900
SYS_TEXT_FG = "#64748B"      # Slate 500


class ModernChatWindow:
    """Visually polished Tkinter desktop interface for Campus Helpdesk Robot Demo."""

    def __init__(
        self,
        chat_service: ChatService,
        person_detector: PersonDetector,
        tts_service: TTSService,
        stt_service: STTService | None = None,
        webcam_index: int = 0,
    ) -> None:
        self._chat_service = chat_service
        self._detector = person_detector
        self._tts_service = tts_service
        self._stt_service = stt_service
        self._webcam_index = webcam_index

        self._controller = SessionController(
            on_status_change=self._update_status_ui,
            on_message_received=self._append_chat_message,
        )
        self._detector._on_person_entered = self._handle_person_entered
        self._detector._on_person_left = self._handle_person_left

        self._root = tk.Tk()
        self._root.title("Campus Helpdesk Robot — Demo")
        self._root.geometry("880x680")
        self._root.configure(bg=BG_MAIN)
        self._root.resizable(True, True)

        self._is_recording = False
        self._cap: cv2.VideoCapture | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct polished Tkinter layout with modern header, chat bubbles, and input bar."""
        # ── 1. Top Header Bar ────────────────────────────────────
        header = tk.Frame(self._root, bg=HEADER_BG, height=64)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        title_frame = tk.Frame(header, bg=HEADER_BG)
        title_frame.pack(side=tk.LEFT, padx=24, pady=12)

        tk.Label(
            title_frame,
            text="🤖  Campus Helpdesk Robot",
            font=("Segoe UI", 16, "bold"),
            fg=HEADER_FG,
            bg=HEADER_BG,
        ).pack(anchor="w")

        # Dynamic Status Badge (Pill with colored background)
        self._status_badge = tk.Label(
            header,
            text="● IDLE",
            font=("Segoe UI", 10, "bold"),
            fg="#15803D",
            bg="#DCFCE7",
            padx=14,
            pady=5,
            bd=0,
            relief="flat",
        )
        self._status_badge.pack(side=tk.RIGHT, padx=24, pady=14)

        # ── 2. Main Content Card (Conversation Area) ─────────────
        content_card = tk.Frame(
            self._root,
            bg=PANEL_BG,
            bd=1,
            relief="solid",
            highlightthickness=1,
            highlightbackground=BORDER_COLOR,
        )
        content_card.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        # Section Header
        tk.Label(
            content_card,
            text="💬  Conversation",
            font=("Segoe UI", 12, "bold"),
            fg=TEXT_MAIN,
            bg=PANEL_BG,
        ).pack(anchor="w", padx=16, pady=(14, 8))

        # Chat Transcript Text Widget
        self._chat_area = scrolledtext.ScrolledText(
            content_card,
            wrap=tk.WORD,
            bg="#F8FAFC",
            fg=TEXT_MAIN,
            font=("Segoe UI", 11),
            state=tk.DISABLED,
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDER_COLOR,
            padx=14,
            pady=14,
        )
        self._chat_area.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))

        # Configure Tag Styles for Chat Bubbles & Alignment
        self._chat_area.tag_config(
            "user_name", foreground=USER_NAME_FG, font=("Segoe UI", 10, "bold"), justify="right"
        )
        self._chat_area.tag_config(
            "user_text", foreground=USER_TEXT_FG, font=("Segoe UI", 11), justify="right"
        )
        self._chat_area.tag_config(
            "robot_name", foreground=BOT_NAME_FG, font=("Segoe UI", 10, "bold"), justify="left"
        )
        self._chat_area.tag_config(
            "robot_text", foreground=BOT_TEXT_FG, font=("Segoe UI", 11), justify="left"
        )
        self._chat_area.tag_config(
            "system_text", foreground=SYS_TEXT_FG, font=("Segoe UI", 10, "italic"), justify="center"
        )

        # ── 3. Bottom Input Row ──────────────────────────────────
        input_row = tk.Frame(content_card, bg=PANEL_BG)
        input_row.pack(fill=tk.X, padx=16, pady=(0, 16))

        # Mic Button with hover effect
        self._mic_btn = tk.Button(
            input_row,
            text="🎙  Mic",
            font=("Segoe UI", 10, "bold"),
            bg=MIC_BG_NORMAL,
            fg=MIC_FG_NORMAL,
            activebackground=MIC_BG_HOVER,
            activeforeground=MIC_FG_NORMAL,
            bd=0,
            relief="flat",
            padx=16,
            pady=8,
            cursor="hand2",
            command=self._toggle_voice_input,
        )
        self._mic_btn.pack(side=tk.LEFT, padx=(0, 10))
        self._bind_hover(self._mic_btn, MIC_BG_NORMAL, MIC_BG_HOVER)

        # Text Input Field
        self._entry = tk.Entry(
            input_row,
            font=("Segoe UI", 11),
            bg="#FFFFFF",
            fg=TEXT_MAIN,
            insertbackground=TEXT_MAIN,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDER_COLOR,
            highlightcolor=ACCENT_PRIMARY,
        )
        self._entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), ipady=7)
        self._entry.bind("<Return>", lambda e: self._send_user_message())
        self._entry.focus()

        # Send Button with hover effect
        self._send_btn = tk.Button(
            input_row,
            text="Send  ➔",
            font=("Segoe UI", 10, "bold"),
            bg=ACCENT_PRIMARY,
            fg="#FFFFFF",
            activebackground=ACCENT_HOVER,
            activeforeground="#FFFFFF",
            bd=0,
            relief="flat",
            padx=18,
            pady=8,
            cursor="hand2",
            command=self._send_user_message,
        )
        self._send_btn.pack(side=tk.RIGHT)
        self._bind_hover(self._send_btn, ACCENT_PRIMARY, ACCENT_HOVER)

    def _bind_hover(self, widget: tk.Button, normal_bg: str, hover_bg: str) -> None:
        """Attach smooth hover background color transition to a button."""

        def _on_enter(e):
            if not getattr(self, "_is_recording", False) or widget != self._mic_btn:
                widget.config(bg=hover_bg)

        def _on_leave(e):
            if not getattr(self, "_is_recording", False) or widget != self._mic_btn:
                widget.config(bg=normal_bg)

        widget.bind("<Enter>", _on_enter)
        widget.bind("<Leave>", _on_leave)

    def _update_status_ui(self, status: RobotStatus) -> None:
        """Thread-safe update of UI status badge colors and text per state."""

        def _update():
            # Pill styling per state: (Text, Background, Foreground)
            badge_map = {
                RobotStatus.IDLE: ("● IDLE", "#DCFCE7", "#15803D"),           # Soft green
                RobotStatus.LISTENING: ("🎙 LISTENING...", "#FEF3C7", "#B45309"), # Soft yellow/amber
                RobotStatus.THINKING: ("🤔 THINKING...", "#F3E8FF", "#6B21A8"),  # Soft purple
                RobotStatus.SPEAKING: ("🔊 SPEAKING", "#E0F2FE", "#0369A1"),     # Soft blue/sky
            }
            text, bg, fg = badge_map.get(status, ("● UNKNOWN", "#E2E8F0", "#475569"))
            self._status_badge.config(text=text, bg=bg, fg=fg)

        self._root.after(0, _update)

    def _append_chat_message(self, sender: str, text: str) -> None:
        """Thread-safe append formatted message to chat transcript."""

        def _append():
            self._chat_area.config(state=tk.NORMAL)
            if sender == "User":
                self._chat_area.insert(tk.END, "You:\n", "user_name")
                self._chat_area.insert(tk.END, f"{text}\n\n", "user_text")
            elif sender == "Robot":
                self._chat_area.insert(tk.END, "Robot:\n", "robot_name")
                self._chat_area.insert(tk.END, f"{text}\n\n", "robot_text")
            else:
                self._chat_area.insert(tk.END, f"[{text}]\n\n", "system_text")
            self._chat_area.see(tk.END)
            self._chat_area.config(state=tk.DISABLED)

        self._root.after(0, _append)

    def _handle_person_entered(self) -> None:
        """Triggered when frontal face / eye contact is detected by background vision service."""
        greeting = self._controller.trigger_greeting()
        if greeting:
            self._tts_service.speak(greeting)
            self._root.after(2500, lambda: self._controller.set_status(RobotStatus.LISTENING))

    def _handle_person_left(self) -> None:
        """Triggered when person leaves camera frame."""
        self._controller.user_left()
        self._append_chat_message("System", "Person left — returned to IDLE.")

    def _send_user_message(self) -> None:
        text = self._entry.get().strip()
        if not text:
            return
        self._entry.delete(0, tk.END)
        self._append_chat_message("User", text)
        self._process_question_async(text)

    def _toggle_voice_input(self) -> None:
        if self._is_recording:
            self._is_recording = False
            self._mic_btn.config(bg=MIC_BG_NORMAL, fg=MIC_FG_NORMAL, text="🎙  Mic")
        else:
            self._is_recording = True
            self._mic_btn.config(bg=MIC_BG_ACTIVE, fg=MIC_FG_ACTIVE, text="🛑  Listening...")
            self._controller.set_status(RobotStatus.LISTENING)
            threading.Thread(target=self._capture_live_voice, daemon=True).start()

    def _capture_live_voice(self) -> None:
        transcript = ""
        if self._stt_service is not None and hasattr(self._stt_service, "listen_and_transcribe"):
            try:
                transcript = self._stt_service.listen_and_transcribe(
                    timeout=8,
                    phrase_time_limit=15,
                    tts_service=self._tts_service,
                )
            except Exception as err:
                logger.warning(f"Live voice capture error: {err}")

        self._is_recording = False
        self._root.after(0, lambda: self._mic_btn.config(bg=MIC_BG_NORMAL, fg=MIC_FG_NORMAL, text="🎙  Mic"))

        if transcript:
            self._append_chat_message("User", f"[Voice] {transcript}")
            self._process_question_async(transcript)
        else:
            self._append_chat_message("System", "Could not hear speech — please try again.")
            self._controller.set_status(RobotStatus.IDLE)

    def _process_question_async(self, question: str) -> None:
        def _worker():
            self._controller.set_status(RobotStatus.THINKING)
            try:
                result = self._chat_service.respond(question)
                reply = result.reply
            except Exception as err:
                logger.error(f"Chat error: {err}")
                reply = "Sorry, I had trouble processing that. Please try again."
            self._append_chat_message("Robot", reply)
            self._controller.set_status(RobotStatus.SPEAKING)
            self._tts_service.speak(reply)
            self._root.after(4000, lambda: self._controller.set_status(RobotStatus.LISTENING))

        threading.Thread(target=_worker, daemon=True).start()

    # ── Background Camera Loop (Headless) ──────────────────────────

    def _init_camera(self) -> None:
        import os

        os.environ["OPENCV_LOG_LEVEL"] = "OFF"
        os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"

        backends = [("DSHOW", cv2.CAP_DSHOW), ("ANY", cv2.CAP_ANY), ("MSMF", cv2.CAP_MSMF)]
        unique_indices = list(dict.fromkeys([self._webcam_index, 0, 1, 2]))

        for idx in unique_indices:
            for backend_name, backend_api in backends:
                try:
                    cap = cv2.VideoCapture(idx, backend_api)
                    if cap.isOpened():
                        ret, frame = cap.read()
                        if ret and frame is not None and frame.size > 0:
                            self._cap = cap
                            logger.info(f"Background camera initialized: index {idx} ({backend_name})")
                            return
                        cap.release()
                except Exception as err:
                    logger.debug(f"Camera index {idx} / {backend_name} failed: {err}")

        logger.warning("No camera found for background person detection.")

    def _update_camera_feed(self) -> None:
        """Background video capture loop feeding frames to person detector."""
        if self._cap is not None and self._cap.isOpened():
            ret, frame = self._cap.read()
            if ret and frame is not None and frame.size > 0:
                self._camera_read_failures = 0
                # Process frame headlessly in person detector
                self._detector.detect_in_frame(frame)
            else:
                self._camera_read_failures = getattr(self, "_camera_read_failures", 0) + 1
                if self._camera_read_failures >= 10:
                    logger.warning("Camera connection lost. Releasing camera capture.")
                    self._cap.release()
                    self._cap = None
                    return

        self._root.after(40, self._update_camera_feed)

    def start(self) -> None:
        """Start GUI event loop and headless background camera capture."""
        self._camera_read_failures = 0
        self._init_camera()
        self._update_camera_feed()
        self._root.mainloop()
        if self._cap is not None:
            self._cap.release()
