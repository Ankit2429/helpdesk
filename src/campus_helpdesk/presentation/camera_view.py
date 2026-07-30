"""CustomTkinter Live Camera & Vision Panel Component.

Displays live OpenCV camera feed with person detection overlays, start/stop controls,
snapshot capture button, status overlay, and recent capture thumbnail gallery.
"""

import datetime
from pathlib import Path
import threading
import time
from typing import Any, List, Optional
import tkinter as tk
import customtkinter as ctk

import cv2
from PIL import Image, ImageTk

from campus_helpdesk.infrastructure.vision.person_detector import PersonDetector
from campus_helpdesk.presentation.theme import ThemeEngine
from logger.logger import get_logger

logger = get_logger("camera_view")

SNAPSHOTS_DIR: Path = Path("storage/snapshots")


class CameraView(ctk.CTkFrame):
    """CustomTkinter Live Camera View Component."""

    def __init__(
        self,
        master: any,
        theme_engine: ThemeEngine,
        person_detector: Optional[PersonDetector] = None,
        webcam_index: int = 0,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.theme_engine = theme_engine
        self.detector = person_detector or PersonDetector()
        self.webcam_index = webcam_index

        self.cap: Optional[cv2.VideoCapture] = None
        self.is_streaming = False
        self.recent_snapshots: List[Path] = []
        self.snapshots_dir = SNAPSHOTS_DIR
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

        self._build_ui()
        self._load_existing_snapshots()

    def _build_ui(self) -> None:
        """Construct Camera View layout."""
        c = self.theme_engine.colors

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header Block
        header = ctk.CTkFrame(self, fg_color=c.panel_bg, corner_radius=14)
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header, text="📷 Live Vision Camera Stream & Person Detector", font=ThemeEngine.font_card_title(), text_color=c.text_main).grid(row=0, column=0, sticky="w", padx=16, pady=12)

        # Video Canvas Preview Container
        self.video_frame = ctk.CTkFrame(self, fg_color=c.panel_bg, corner_radius=14)
        self.video_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 8))
        self.video_frame.grid_columnconfigure(0, weight=1)
        self.video_frame.grid_rowconfigure(0, weight=1)

        self.video_label = tk.Label(
            self.video_frame,
            text="Camera Stream Stopped\nTap 'Start Stream' below to launch live webcam feed",
            font=("Segoe UI", 13),
            bg=c.panel_bg,
            fg=c.text_muted,
        )
        self.video_label.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)

        # Control Bar Buttons
        ctrl_bar = ctk.CTkFrame(self, fg_color=c.panel_bg, corner_radius=14)
        ctrl_bar.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 8))
        ctrl_bar.grid_columnconfigure((0, 1), weight=1)

        self.stream_btn = ctk.CTkButton(
            ctrl_bar,
            text="▶ Start Stream",
            height=44,
            corner_radius=10,
            fg_color=c.accent_success,
            hover_color="#047857",
            command=self.toggle_stream,
        )
        self.stream_btn.grid(row=0, column=0, sticky="ew", padx=(16, 8), pady=12)

        self.snap_btn = ctk.CTkButton(
            ctrl_bar,
            text="📸 Capture Snapshot",
            height=44,
            corner_radius=10,
            fg_color=c.accent_brand,
            hover_color="#C2410C",
            command=self.take_snapshot,
        )
        self.snap_btn.grid(row=0, column=1, sticky="ew", padx=(8, 16), pady=12)

        # Snapshot Gallery Strip
        gallery_frame = ctk.CTkFrame(self, fg_color=c.panel_bg, corner_radius=14)
        gallery_frame.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 16))
        gallery_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(gallery_frame, text="Recent Capture Snapshots", font=ThemeEngine.font_card_title(), text_color=c.text_main).grid(row=0, column=0, sticky="w", padx=16, pady=(8, 4))

        self.gallery_strip = ctk.CTkFrame(gallery_frame, fg_color="transparent")
        self.gallery_strip.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))

    def toggle_stream(self) -> None:
        """Toggle live video stream."""
        if not self.is_streaming:
            self.start_stream()
        else:
            self.stop_stream()

    def start_stream(self) -> None:
        """Initialize webcam stream."""
        self.cap = cv2.VideoCapture(self.webcam_index)
        if not self.cap or not self.cap.isOpened():
            self.video_label.config(text="⚠️ Failed opening camera webcam device.\nCheck camera connection or index.")
            return

        self.is_streaming = True
        self.stream_btn.configure(text="⏹ Stop Stream", fg_color=self.theme_engine.colors.accent_danger, hover_color="#B91C1C")
        logger.info(f"Started camera video stream (index {self.webcam_index}).")
        threading.Thread(target=self._stream_loop, daemon=True).start()

    def stop_stream(self) -> None:
        """Stop video stream."""
        self.is_streaming = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self.stream_btn.configure(text="▶ Start Stream", fg_color=self.theme_engine.colors.accent_success, hover_color="#047857")
        self.video_label.config(text="Camera Stream Stopped\nTap 'Start Stream' to launch camera feed")
        logger.info("Stopped camera video stream.")

    def _stream_loop(self) -> None:
        """Continuously capture frames and run person detector."""
        prev_time = time.time()
        fps = 0.0

        while self.is_streaming and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.05)
                continue

            curr_time = time.time()
            fps = round(1.0 / max(0.001, curr_time - prev_time), 1)
            prev_time = curr_time

            detected_boxes = self.detector.detect_persons(frame) if self.detector else []

            status_str = f"Status: ACTIVE | Persons: {len(detected_boxes)} | FPS: {fps:.1f}"
            cv2.putText(frame, status_str, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb_frame).resize((640, 360), Image.Resampling.LANCZOS)
            img_tk = ImageTk.PhotoImage(image=img)

            self.after(0, lambda image_tk=img_tk: self._update_video_frame(image_tk))
            time.sleep(0.03)

    def _update_video_frame(self, img_tk: ImageTk.PhotoImage) -> None:
        """Update video label image."""
        if self.is_streaming:
            self.video_label.config(image=img_tk, text="")
            self.video_label.image = img_tk

    def take_snapshot(self) -> None:
        """Capture current snapshot image."""
        if not self.cap or not self.is_streaming:
            return

        ret, frame = self.cap.read()
        if ret:
            t_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            snap_path = self.snapshots_dir / f"snapshot_{t_str}.jpg"
            cv2.imwrite(str(snap_path), frame)
            logger.info(f"Saved snapshot to {snap_path}")
            self.recent_snapshots.append(snap_path)
            self._update_gallery()

    def _load_existing_snapshots(self) -> None:
        """Load existing snapshots."""
        if self.snapshots_dir.exists():
            snaps = sorted(list(self.snapshots_dir.glob("*.jpg")), reverse=True)[:5]
            self.recent_snapshots = snaps
            self._update_gallery()

    def _update_gallery(self) -> None:
        """Redraw snapshot gallery strip."""
        for child in self.gallery_strip.winfo_children():
            child.destroy()

        if not self.recent_snapshots:
            ctk.CTkLabel(self.gallery_strip, text="No snapshots captured yet.", font=ThemeEngine.font_caption(), text_color=self.theme_engine.colors.text_muted).grid(row=0, column=0, padx=8, pady=8)
            return

        for idx, snap_p in enumerate(reversed(self.recent_snapshots[-5:])):
            lbl = ctk.CTkLabel(self.gallery_strip, text=f"📷 Snap #{idx+1}\n{snap_p.name[:12]}", font=ThemeEngine.font_caption())
            lbl.grid(row=0, column=idx, padx=8, pady=8)
