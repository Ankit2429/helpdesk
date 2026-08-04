"""CustomTkinter Live Camera & Vision Panel Component.

Displays live OpenCV camera feed with person detection overlays, start/stop controls,
snapshot capture button, status overlay, and recent capture thumbnail gallery.
"""

import datetime
from pathlib import Path
import threading
import time
from typing import Any, Callable, List, Optional
import tkinter as tk
import customtkinter as ctk

import cv2
import numpy as np
from PIL import Image, ImageTk

from campus_helpdesk.infrastructure.vision.person_detector import PersonDetector
from campus_helpdesk.presentation.theme import ThemeEngine
import logging


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"campus_helpdesk.{name}")

logger = get_logger("camera_view")

SNAPSHOTS_DIR: Path = Path("storage/snapshots")


class CameraView(ctk.CTkFrame):
    """CustomTkinter Live Camera View Component."""

    def __init__(
        self,
        master: Any,
        theme_engine: ThemeEngine,
        person_detector: Optional[PersonDetector] = None,
        webcam_index: int = 0,
        on_greeting_triggered: Optional[Callable[[str, str], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.theme_engine = theme_engine
        self.on_greeting_triggered = on_greeting_triggered
        self.detector = person_detector or PersonDetector(on_greeting_triggered=self.on_greeting_triggered)
        self.webcam_index = webcam_index

        self.cap: Optional[cv2.VideoCapture] = None
        self.is_streaming = False
        self.recent_snapshots: List[Path] = []
        self.snapshots_dir = SNAPSHOTS_DIR
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self._current_img_tk = None  # Persistent reference prevents GC black screen

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

        ctk.CTkLabel(
            header,
            text="📷 Live Vision Camera Stream & Person Detector",
            font=ThemeEngine.font_card_title(),
            text_color=c.text_main,
            wraplength=380,
            justify="left",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=12)

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
        """Initialize singleton hardware camera stream via CameraManager."""
        from campus_helpdesk.infrastructure.vision.camera_manager import CameraManager

        if self.is_streaming:
            return

        logger.info("CameraView: Starting camera stream via singleton CameraManager...")
        self.video_label.config(text="🔄 Initializing camera device...")

        mgr = CameraManager.get_instance()
        if self.detector:
            mgr.set_detector(self.detector)

        success = mgr.start_camera(
            requested_index=self.webcam_index,
            resolution=(1280, 720),
            target_fps=30,
        )

        if not success:
            logger.error("CameraView init failed via CameraManager.")
            self.video_label.config(
                text="⚠️ Failed opening camera device.\nCheck camera connection or privacy settings."
            )
            return

        self.is_streaming = True
        self.stream_btn.configure(
            text="⏹ Stop Stream",
            fg_color=self.theme_engine.colors.accent_danger,
            hover_color="#B91C1C",
        )
        logger.info("CameraView stream started successfully via singleton CameraManager.")
        # Start main-thread recursive poll loop — correct Tkinter video pattern
        self._poll_frame()

    def stop_stream(self) -> None:
        """Stop video stream and release hardware resources cleanly via CameraManager."""
        from campus_helpdesk.infrastructure.vision.camera_manager import CameraManager

        self.is_streaming = False
        mgr = CameraManager.get_instance()
        mgr.stop_camera()

        self.stream_btn.configure(
            text="▶ Start Stream",
            fg_color=self.theme_engine.colors.accent_success,
            hover_color="#047857",
        )
        self.video_label.config(text="Camera Stream Stopped\nTap 'Start Stream' to launch camera feed")
        logger.info("CameraView video stream stopped.")

    def _poll_frame(self) -> None:
        """Main-thread recursive poll at 30 FPS — fast PIL scaling and render."""
        from campus_helpdesk.infrastructure.vision.camera_manager import CameraManager

        if not self.is_streaming:
            return

        mgr = CameraManager.get_instance()

        if not mgr.is_running():
            self.video_label.config(
                image="",
                text="📷 Camera Offline\nReconnecting...",
            )
            mgr.start_camera(requested_index=self.webcam_index, resolution=(1280, 720), target_fps=30)
            self.after(500, self._poll_frame)
            return

        raw_frame, ann_frame, diag = mgr.get_latest_frame()
        frame_to_render = ann_frame if ann_frame is not None else raw_frame

        if frame_to_render is not None and frame_to_render.size > 0:
            fps = diag.get("fps", 30.0)
            person_detected = diag.get("person_detected", False)
            info = diag.get("info", {})

            annotated_copy = frame_to_render.copy()
            h_f, w_f = annotated_copy.shape[:2]

            # Top Badge Bar Overlay
            cv2.rectangle(annotated_copy, (0, 0), (w_f, 40), (20, 20, 20), -1)
            fps_str = f"FPS: {fps:.1f} | Device: Cam #{self.webcam_index} ({info.get('backend_name', 'DirectShow')}) @ {w_f}x{h_f}"
            cv2.putText(annotated_copy, fps_str, (12, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2, cv2.LINE_AA)

            # Bottom Status Overlay
            cv2.rectangle(annotated_copy, (0, h_f - 40), (w_f, h_f), (20, 20, 20), -1)
            active_lang = getattr(getattr(self.detector, "intent_engine", None), "active_language", "en").upper()
            state_str = getattr(getattr(self.detector, "intent_engine", None), "state", "READY")
            state_name = getattr(state_str, "value", str(state_str))

            if person_detected:
                overlay_text = f"ACTIVE USER: ENGAGED | State: {state_name} | Lang: {active_lang}"
                status_color = (0, 255, 0)
            else:
                overlay_text = f"PERCEPTION: SEARCHING | State: {state_name} | Target: 30 FPS | Lang: {active_lang}"
                status_color = (255, 200, 0)

            cv2.putText(annotated_copy, overlay_text, (12, h_f - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.52, status_color, 2, cv2.LINE_AA)

            # Fast BGR→RGB conversion
            rgb = cv2.cvtColor(annotated_copy, cv2.COLOR_BGR2RGB)

            w = max(320, self.video_frame.winfo_width() - 16)
            h = max(240, self.video_frame.winfo_height() - 16)
            ih, iw = rgb.shape[:2]
            scale = min(w / float(iw), h / float(ih))
            nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))

            img = Image.fromarray(rgb).resize((nw, nh), Image.Resampling.NEAREST)
            img_tk = ImageTk.PhotoImage(image=img)

            self._current_img_tk = img_tk
            self.video_label.config(image=self._current_img_tk, text="")

        # Reschedule at 33ms (30 FPS target)
        self.after(33, self._poll_frame)

    def take_snapshot(self) -> None:
        """Capture current snapshot image via CameraManager."""
        from campus_helpdesk.infrastructure.vision.camera_manager import CameraManager

        if not self.is_streaming:
            return

        mgr = CameraManager.get_instance()
        raw_frame, ann_frame, _ = mgr.get_latest_frame()
        frame = ann_frame if ann_frame is not None else raw_frame
        if frame is not None and frame.size > 0:
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
        """Redraw snapshot gallery strip with image thumbnails."""
        for child in self.gallery_strip.winfo_children():
            child.destroy()

        if not self.recent_snapshots:
            ctk.CTkLabel(
                self.gallery_strip,
                text="No snapshots captured yet.",
                font=ThemeEngine.font_caption(),
                text_color=self.theme_engine.colors.text_muted,
            ).grid(row=0, column=0, padx=8, pady=8)
            return

        for idx, snap_p in enumerate(reversed(self.recent_snapshots[-5:])):
            card = ctk.CTkFrame(
                self.gallery_strip,
                fg_color=self.theme_engine.colors.panel_bg,
                border_width=1,
                border_color=self.theme_engine.colors.border_color,
                corner_radius=8,
            )
            card.grid(row=0, column=idx, padx=6, pady=4)

            # Display thumbnail image
            try:
                pil_img = Image.open(snap_p).resize((64, 48), Image.Resampling.NEAREST)
                tk_img = ImageTk.PhotoImage(pil_img)
                lbl_img = tk.Label(card, image=tk_img, bg=self.theme_engine.colors.panel_bg)
                lbl_img.image = tk_img
                lbl_img.pack(padx=4, pady=(4, 2))
            except Exception as e:
                logger.warning(f"Could not load thumbnail for {snap_p}: {e}")

            time_label = snap_p.stem.replace("snapshot_", "").replace("_", " ")
            ctk.CTkLabel(
                card,
                text=f"Snap #{idx+1}\n{time_label[-8:]}",
                font=ctk.CTkFont(family="Segoe UI", size=9),
                text_color=self.theme_engine.colors.text_muted,
            ).pack(padx=4, pady=(0, 4))