"""Tkinter-backed Modern Desktop Interface for Offline Helpdesk Robot Demo."""

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


class ModernChatWindow:
    """Tkinter GUI Window providing live camera feed, chat bubbles, and status indicator."""

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
        self._root.title("Campus Helpdesk Robot - Offline MVP Demo")
        self._root.geometry("900x650")
        self._root.configure(bg="#1E1E2E")

        self._is_recording = False
        self._cap: cv2.VideoCapture | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct responsive dark-theme desktop UI layout."""
        # Top Header Bar with Status
        header_frame = tk.Frame(self._root, bg="#181825", height=60)
        header_frame.pack(fill=tk.X, side=tk.TOP)

        title_label = tk.Label(
            header_frame,
            text="🤖 Campus Helpdesk Robot",
            font=("Segoe UI", 16, "bold"),
            fg="#CDD6F4",
            bg="#181825",
        )
        title_label.pack(side=tk.LEFT, padx=20, pady=10)

        self._status_label = tk.Label(
            header_frame,
            text="STATUS: IDLE",
            font=("Segoe UI", 11, "bold"),
            fg="#A6ADC8",
            bg="#313244",
            padx=12,
            pady=4,
        )
        self._status_label.pack(side=tk.RIGHT, padx=20, pady=10)

        # Main Split Frame (Left: Webcam & Info, Right: Chat Interface)
        main_frame = tk.Frame(self._root, bg="#1E1E2E")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        left_frame = tk.Frame(main_frame, bg="#1E1E2E", width=320)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        # Camera Feed Preview Label
        cam_title = tk.Label(left_frame, text="Vision Detection", font=("Segoe UI", 10, "bold"), fg="#BAC2DE", bg="#1E1E2E")
        cam_title.pack(anchor="w", pady=(0, 5))

        self._cam_label = tk.Label(left_frame, bg="#11111B", text="Initializing camera...", fg="#6C7086")
        self._cam_label.pack(fill=tk.BOTH, expand=True)

        # Right Frame: Chat
        right_frame = tk.Frame(main_frame, bg="#1E1E2E")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._chat_area = scrolledtext.ScrolledText(
            right_frame,
            wrap=tk.WORD,
            bg="#181825",
            fg="#CDD6F4",
            font=("Segoe UI", 10),
            state=tk.DISABLED,
            bd=0,
            highlightthickness=1,
            highlightbackground="#313244",
        )
        self._chat_area.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Configure Tag Styles for Chat Bubbles
        self._chat_area.tag_config("user", foreground="#89B4FA", justify="right")
        self._chat_area.tag_config("robot", foreground="#A6E3A1", justify="left")
        self._chat_area.tag_config("system", foreground="#F9E2AF", justify="center")

        # Bottom Input Control Bar
        input_frame = tk.Frame(right_frame, bg="#1E1E2E")
        input_frame.pack(fill=tk.X)

        self._mic_btn = tk.Button(
            input_frame,
            text="🎙️ Mic",
            font=("Segoe UI", 10, "bold"),
            bg="#313244",
            fg="#CDD6F4",
            activebackground="#45475A",
            activeforeground="#CDD6F4",
            bd=0,
            padx=12,
            pady=6,
            command=self._toggle_voice_input,
        )
        self._mic_btn.pack(side=tk.LEFT, padx=(0, 5))

        self._entry = tk.Entry(
            input_frame,
            font=("Segoe UI", 11),
            bg="#313244",
            fg="#CDD6F4",
            insertbackground="#CDD6F4",
            bd=0,
            highlightthickness=1,
            highlightbackground="#45475A",
        )
        self._entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self._entry.bind("<Return>", lambda e: self._send_user_message())

        self._send_btn = tk.Button(
            input_frame,
            text="Send ➔",
            font=("Segoe UI", 10, "bold"),
            bg="#89B4FA",
            fg="#11111B",
            activebackground="#B4BEFE",
            bd=0,
            padx=15,
            pady=6,
            command=self._send_user_message,
        )
        self._send_btn.pack(side=tk.RIGHT, padx=(5, 0))

    def _update_status_ui(self, status: RobotStatus) -> None:
        """Thread-safe update of UI status badge colors and text."""

        def _update():
            color_map = {
                RobotStatus.IDLE: ("STATUS: IDLE", "#313244", "#A6ADC8"),
                RobotStatus.LISTENING: ("STATUS: LISTENING 🎙️", "#89B4FA", "#11111B"),
                RobotStatus.RECORDING: ("STATUS: RECORDING 🔴", "#F38BA8", "#11111B"),
                RobotStatus.TRANSCRIBING: ("STATUS: TRANSCRIBING ⚙️", "#FAB387", "#11111B"),
                RobotStatus.THINKING: ("STATUS: THINKING 🤔", "#F9E2AF", "#11111B"),
                RobotStatus.SPEAKING: ("STATUS: SPEAKING 🔊", "#A6E3A1", "#11111B"),
            }
            text, bg, fg = color_map.get(status, ("STATUS: UNKNOWN", "#313244", "#CDD6F4"))
            self._status_label.config(text=text, bg=bg, fg=fg)

        self._root.after(0, _update)

    def _append_chat_message(self, sender: str, text: str) -> None:
        """Thread-safe append to chat transcript."""

        def _append():
            self._chat_area.config(state=tk.NORMAL)
            if sender == "User":
                self._chat_area.insert(tk.END, f"\nUser:\n{text}\n", "user")
            elif sender == "Robot":
                self._chat_area.insert(tk.END, f"\nRobot:\n{text}\n", "robot")
            else:
                self._chat_area.insert(tk.END, f"\n--- {text} ---\n", "system")
            self._chat_area.see(tk.END)
            self._chat_area.config(state=tk.DISABLED)

        self._root.after(0, _append)

    def _handle_person_entered(self) -> None:
        """Callback when person is detected in webcam feed."""
        greeting = self._controller.trigger_greeting()
        if greeting:
            self._tts_service.speak(greeting)
            self._root.after(2000, lambda: self._controller.set_status(RobotStatus.LISTENING))

    def _handle_person_left(self) -> None:
        """Callback when person leaves webcam feed."""
        self._controller.user_left()
        self._append_chat_message("System", "Person left area. Returned to IDLE.")

    def _send_user_message(self) -> None:
        """Handler for text input send action."""
        text = self._entry.get().strip()
        if not text:
            return

        self._entry.delete(0, tk.END)
        self._append_chat_message("User", text)
        self._process_question_async(text)

    def _toggle_voice_input(self) -> None:
        """Toggle microphone capture and trigger real-time Speech-to-Text transcription."""
        if self._is_recording:
            self._is_recording = False
            self._mic_btn.config(bg="#313244", text="🎙️ Mic")
        else:
            self._is_recording = True
            self._mic_btn.config(bg="#F38BA8", text="🛑 Stop")
            self._controller.set_status(RobotStatus.LISTENING)
            threading.Thread(target=self._capture_live_voice, daemon=True).start()

    def _capture_live_voice(self) -> None:
        """Capture live microphone audio and transcribe to user question."""
        transcript = ""
        if self._stt_service is not None and hasattr(self._stt_service, "listen_and_transcribe"):
            try:
                self._controller.set_status(RobotStatus.RECORDING)
                self._append_chat_message("System", "Recording audio from microphone...")
                
                transcript = self._stt_service.listen_and_transcribe(
                    timeout=8,
                    phrase_time_limit=15,
                    tts_service=self._tts_service,
                )
                self._controller.set_status(RobotStatus.TRANSCRIBING)
            except Exception as err:
                logger.error(f"Live voice capture error: {err}")

        self._is_recording = False
        self._root.after(0, lambda: self._mic_btn.config(bg="#313244", text="🎙️ Mic"))

        if transcript:
            logger.info(f"Live microphone recognized speech: '{transcript}'")
            self._append_chat_message("User", transcript)
            self._process_question_async(transcript)
        else:
            self._append_chat_message("System", "Could not hear any speech. Please try again.")
            self._controller.set_status(RobotStatus.IDLE)

    def _process_question_async(self, question: str) -> None:
        """Execute RAG + Ollama inference asynchronously to avoid freezing Tkinter GUI."""

        def _worker():
            self._controller.set_status(RobotStatus.THINKING)
            try:
                chat_result = self._chat_service.respond(question)
                reply = chat_result.reply
            except Exception as err:
                logger.error(f"Chat processing error: {err}")
                reply = "I apologize, I encountered an issue processing your request."

            self._append_chat_message("Robot", reply)
            self._controller.set_status(RobotStatus.SPEAKING)
            self._tts_service.speak(reply)

            # Return to listening/idle state after speaking
            self._root.after(4000, lambda: self._controller.set_status(RobotStatus.LISTENING))

        threading.Thread(target=_worker, daemon=True).start()

    def _init_camera(self) -> None:
        """Attempt to open an available camera using preferred backends and index scanning."""
        import os

        # Quiet OpenCV verbose C++ warnings in terminal
        os.environ["OPENCV_LOG_LEVEL"] = "OFF"
        os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"

        # Backends to try: DirectShow (CAP_DSHOW) first on Windows, then CAP_ANY, then MSMF (CAP_MSMF)
        backends = [
            ("DSHOW", cv2.CAP_DSHOW),
            ("ANY", cv2.CAP_ANY),
            ("MSMF", cv2.CAP_MSMF),
        ]
        indices_to_try = [self._webcam_index, 0, 1, 2]
        # Deduplicate while preserving order
        unique_indices = list(dict.fromkeys(indices_to_try))

        for idx in unique_indices:
            for backend_name, backend_api in backends:
                try:
                    cap = cv2.VideoCapture(idx, backend_api)
                    if cap.isOpened():
                        ret, frame = cap.read()
                        if ret and frame is not None and frame.size > 0:
                            self._cap = cap
                            logger.info(f"Successfully initialized camera index {idx} using backend {backend_name}")
                            return
                        cap.release()
                except Exception as err:
                    logger.debug(f"Camera open attempt failed for index {idx} with backend {backend_name}: {err}")

        logger.warning("No functional camera device could be opened across indices 0, 1, 2 and backends DSHOW/ANY/MSMF.")
        self._cam_label.configure(
            text="⚠️ Camera Unavailable\n\n(No working webcam detected)",
            fg="#F38BA8",
            font=("Segoe UI", 10, "bold"),
        )

    def _update_camera_feed(self) -> None:
        """Webcam loop fetching frames, running person detector, updating GUI preview label."""
        if self._cap is not None and self._cap.isOpened():
            ret, frame = self._cap.read()
            if ret and frame is not None and frame.size > 0:
                self._camera_read_failures = 0
                # Run detector on frame
                detection_result = self._detector.detect_in_frame(frame)
                annotated_frame = detection_result.annotated_frame

                # Draw attention-tracking crosshair at face center if detected
                if detection_result.face_center is not None:
                    norm_x, norm_y = detection_result.face_center
                    h, w = annotated_frame.shape[:2]
                    cx = int(norm_x * w)
                    cy = int(norm_y * h)

                    # Yellow center dot and crosshair target
                    cv2.circle(annotated_frame, (cx, cy), 5, (0, 255, 255), -1)
                    cv2.drawMarker(
                        annotated_frame,
                        (cx, cy),
                        (0, 255, 255),
                        markerType=cv2.MARKER_CROSS,
                        markerSize=18,
                        thickness=2,
                    )

                # Convert OpenCV BGR to Tkinter PhotoImage
                rgb_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb_frame)
                img = img.resize((300, 225))
                imgtk = ImageTk.PhotoImage(image=img)
                self._cam_label.imgtk = imgtk
                self._cam_label.configure(image=imgtk)
            else:
                self._camera_read_failures = getattr(self, "_camera_read_failures", 0) + 1
                if self._camera_read_failures >= 10:
                    logger.warning("Camera stream failed continuously. Disabling video capture loop.")
                    self._cap.release()
                    self._cap = None
                    self._cam_label.configure(
                        text="⚠️ Camera Stream Error\n\n(Connection Lost)",
                        fg="#F38BA8",
                        font=("Segoe UI", 10, "bold"),
                    )
                    return

        self._root.after(50, self._update_camera_feed)

    def start(self) -> None:
        """Start GUI loop and open camera device."""
        self._camera_read_failures = 0
        self._init_camera()
        self._update_camera_feed()
        self._root.mainloop()

        if self._cap is not None:
            self._cap.release()

