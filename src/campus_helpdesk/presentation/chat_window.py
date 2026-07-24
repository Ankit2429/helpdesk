"""Tkinter Desktop Interface for Campus Helpdesk Robot Demo."""

import logging
import threading
import tkinter as tk
from tkinter import scrolledtext

import cv2
from PIL import Image, ImageTk

from campus_helpdesk.application.chat_service import ChatService
from campus_helpdesk.application.session_controller import RobotStatus, SessionController
from campus_helpdesk.infrastructure.audio.stt_service import STTService
from campus_helpdesk.infrastructure.audio.tts_service import TTSService
from campus_helpdesk.infrastructure.vision.person_detector import PersonDetector

logger = logging.getLogger(__name__)

# --- Colour palette (clean light theme) ---
BG = "#F5F5F5"
PANEL = "#FFFFFF"
BORDER = "#CCCCCC"
ACCENT = "#1565C0"
GREEN = "#2E7D32"
RED = "#C62828"
TEXT = "#212121"
SUBTEXT = "#616161"
SYS_MSG_FG = "#757575"


class ModernChatWindow:
    """Clean Tkinter demo window — camera on left, chat on right."""

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
        self._root.geometry("1000x680")
        self._root.configure(bg=BG)
        self._root.resizable(True, True)

        self._is_recording = False
        self._cap: cv2.VideoCapture | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        # ── Header bar ──────────────────────────────────────────
        header = tk.Frame(self._root, bg=ACCENT, height=56)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        tk.Label(
            header,
            text="🤖  Campus Helpdesk Robot",
            font=("Arial", 17, "bold"),
            fg="white",
            bg=ACCENT,
        ).pack(side=tk.LEFT, padx=20, pady=12)

        self._status_label = tk.Label(
            header,
            text="● IDLE",
            font=("Arial", 12, "bold"),
            fg="white",
            bg=ACCENT,
        )
        self._status_label.pack(side=tk.RIGHT, padx=24, pady=12)

        # ── Main content area ───────────────────────────────────
        content = tk.Frame(self._root, bg=BG)
        content.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)

        # Left panel — camera
        left = tk.Frame(content, bg=PANEL, bd=1, relief="solid")
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        tk.Label(
            left,
            text="📷  Live Camera — Person Detection",
            font=("Arial", 11, "bold"),
            fg=TEXT,
            bg=PANEL,
        ).pack(anchor="w", padx=10, pady=(8, 4))

        self._cam_label = tk.Label(
            left,
            bg="#222222",
            text="Starting camera...",
            fg="#AAAAAA",
            font=("Arial", 10),
            width=42,
        )
        self._cam_label.pack(padx=8, pady=(0, 8))

        self._detection_badge = tk.Label(
            left,
            text="No person detected",
            font=("Arial", 10),
            fg=SUBTEXT,
            bg=PANEL,
        )
        self._detection_badge.pack(pady=(0, 10))

        # Right panel — chat
        right = tk.Frame(content, bg=PANEL, bd=1, relief="solid")
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        tk.Label(
            right,
            text="💬  Conversation",
            font=("Arial", 11, "bold"),
            fg=TEXT,
            bg=PANEL,
        ).pack(anchor="w", padx=10, pady=(8, 4))

        self._chat_area = scrolledtext.ScrolledText(
            right,
            wrap=tk.WORD,
            bg="#FAFAFA",
            fg=TEXT,
            font=("Arial", 11),
            state=tk.DISABLED,
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            padx=8,
            pady=8,
        )
        self._chat_area.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        self._chat_area.tag_config("user_name",   foreground=ACCENT, font=("Arial", 10, "bold"))
        self._chat_area.tag_config("user_text",   foreground="#1A237E", font=("Arial", 11))
        self._chat_area.tag_config("robot_name",  foreground=GREEN,  font=("Arial", 10, "bold"))
        self._chat_area.tag_config("robot_text",  foreground=GREEN,  font=("Arial", 11))
        self._chat_area.tag_config("system_text", foreground=SYS_MSG_FG, font=("Arial", 10, "italic"))

        input_row = tk.Frame(right, bg=PANEL)
        input_row.pack(fill=tk.X, padx=8, pady=(0, 10))

        self._mic_btn = tk.Button(
            input_row,
            text="🎙 Mic",
            font=("Arial", 11, "bold"),
            bg="#E3F2FD",
            fg=ACCENT,
            activebackground="#BBDEFB",
            relief="groove",
            padx=10,
            pady=6,
            command=self._toggle_voice_input,
        )
        self._mic_btn.pack(side=tk.LEFT, padx=(0, 6))

        self._entry = tk.Entry(
            input_row,
            font=("Arial", 12),
            bg="white",
            fg=TEXT,
            insertbackground=TEXT,
            relief="groove",
            bd=2,
        )
        self._entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self._entry.bind("<Return>", lambda e: self._send_user_message())
        self._entry.focus()

        self._send_btn = tk.Button(
            input_row,
            text="Send  ➤",
            font=("Arial", 11, "bold"),
            bg=ACCENT,
            fg="white",
            activebackground="#0D47A1",
            relief="flat",
            padx=14,
            pady=6,
            command=self._send_user_message,
        )
        self._send_btn.pack(side=tk.RIGHT)

    def _update_status_ui(self, status: RobotStatus) -> None:
        def _update():
            label_map = {
                RobotStatus.IDLE:      ("● IDLE",          "white"),
                RobotStatus.LISTENING: ("🎙 LISTENING...", "#FFEB3B"),
                RobotStatus.THINKING:  ("🤔 THINKING...",  "#FFCC02"),
                RobotStatus.SPEAKING:  ("🔊 SPEAKING",     "#A5D6A7"),
            }
            text, fg = label_map.get(status, ("● IDLE", "white"))
            self._status_label.config(text=text, fg=fg)
        self._root.after(0, _update)

    def _append_chat_message(self, sender: str, text: str) -> None:
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
        def _badge():
            self._detection_badge.config(text="✅ Person detected!", fg=GREEN)
        self._root.after(0, _badge)
        greeting = self._controller.trigger_greeting()
        if greeting:
            self._tts_service.speak(greeting)
            self._root.after(2500, lambda: self._controller.set_status(RobotStatus.LISTENING))

    def _handle_person_left(self) -> None:
        def _badge():
            self._detection_badge.config(text="No person detected", fg=SUBTEXT)
        self._root.after(0, _badge)
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
            self._mic_btn.config(bg="#E3F2FD", fg=ACCENT, text="🎙 Mic")
        else:
            self._is_recording = True
            self._mic_btn.config(bg=RED, fg="white", text="🛑 Listening...")
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
        self._root.after(0, lambda: self._mic_btn.config(bg="#E3F2FD", fg=ACCENT, text="🎙 Mic"))

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
                            logger.info(f"Camera opened: index {idx} ({backend_name})")
                            return
                        cap.release()
                except Exception as err:
                    logger.debug(f"Camera index {idx} / {backend_name} failed: {err}")

        logger.warning("No camera found.")
        self._cam_label.configure(
            text="⚠️ No Camera\n\nPlease connect a webcam",
            fg="#FF5252",
            font=("Arial", 11, "bold"),
        )

    def _update_camera_feed(self) -> None:
        if self._cap is not None and self._cap.isOpened():
            ret, frame = self._cap.read()
            if ret and frame is not None and frame.size > 0:
                self._camera_read_failures = 0
                detection_result = self._detector.detect_in_frame(frame)
                annotated_frame = detection_result.annotated_frame

                if detection_result.face_center is not None:
                    norm_x, norm_y = detection_result.face_center
                    h, w = annotated_frame.shape[:2]
                    cx, cy = int(norm_x * w), int(norm_y * h)
                    cv2.circle(annotated_frame, (cx, cy), 6, (0, 220, 0), -1)
                    cv2.drawMarker(annotated_frame, (cx, cy), (0, 220, 0),
                                   markerType=cv2.MARKER_CROSS, markerSize=22, thickness=2)

                rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb)
                img = img.resize((380, 285))
                imgtk = ImageTk.PhotoImage(image=img)
                self._cam_label.imgtk = imgtk
                self._cam_label.configure(image=imgtk, text="")
            else:
                self._camera_read_failures = getattr(self, "_camera_read_failures", 0) + 1
                if self._camera_read_failures >= 10:
                    self._cap.release()
                    self._cap = None
                    self._cam_label.configure(text="⚠️ Camera lost", fg="#FF5252")
                    return

        self._root.after(40, self._update_camera_feed)

    def start(self) -> None:
        """Start GUI event loop and camera capture."""
        self._camera_read_failures = 0
        self._init_camera()
        self._update_camera_feed()
        self._root.mainloop()
        if self._cap is not None:
            self._cap.release()
