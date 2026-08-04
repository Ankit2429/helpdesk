"""
src/campus_helpdesk/infrastructure/vision/camera_manager.py

Singleton CameraManager for AUNTII Helpdesk Robot.
Guarantees EXACTLY ONE VideoCapture instance exists in the application.
Distributes latest captured frames asynchronously to subscribers (UI views & vision services)
without frame buffer buildup or thread contention.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import Any

import cv2
import numpy as np

from campus_helpdesk.infrastructure.vision.camera_utils import open_camera_intelligently

logger = logging.getLogger("campus_helpdesk.camera_manager")


class CameraManager:
    """
    Thread-safe Singleton Camera Manager owning the physical webcam device.
    """

    _instance: CameraManager | None = None
    _singleton_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> CameraManager:
        """Retrieve singleton instance of CameraManager."""
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self) -> None:
        if CameraManager._instance is not None:
            raise RuntimeError("CameraManager is a singleton. Use CameraManager.get_instance() instead.")

        self._lock = threading.RLock()
        self._cap: cv2.VideoCapture | None = None
        self._camera_info: dict[str, Any] = {}

        self._latest_frame: np.ndarray | None = None
        self._latest_annotated_frame: np.ndarray | None = None
        self._frame_timestamp: float = 0.0

        self._subscribers: list[Callable[[np.ndarray], None]] = []
        self._running = False
        self._capture_thread: threading.Thread | None = None

        # Diagnostics & Metrics
        self._frames_captured = 0
        self._frames_dropped = 0
        self._fps = 0.0
        self._acquisition_latency_ms = 0.0
        self._detection_latency_ms = 0.0

        # Async Person Detection Thread
        self._detector: Any | None = None
        self._detection_thread: threading.Thread | None = None
        self._person_detected = False

    def is_running(self) -> bool:
        """Check if camera capture thread is currently active."""
        with self._lock:
            return self._running and self._cap is not None and self._cap.isOpened()

    def set_detector(self, detector: Any) -> None:
        """Set detector instance for async person detection."""
        with self._lock:
            self._detector = detector

    def start_camera(
        self,
        requested_index: int = 0,
        resolution: tuple[int, int] = (1280, 720),
        target_fps: int = 30,
    ) -> bool:
        """
        Initialize the single physical camera device and launch dedicated capture thread.

        Returns:
            True if camera started successfully, False otherwise.
        """
        with self._lock:
            if self.is_running():
                logger.info("CameraManager is already running.")
                return True

            logger.info("CameraManager: Initializing singleton hardware camera...")
            cap, meta = open_camera_intelligently(
                requested_index=requested_index,
                resolution=resolution,
                target_fps=target_fps,
                fallback_indices=[0, 1, 2],
            )

            if not cap or not cap.isOpened() or meta.get("status") == "failed":
                logger.error("CameraManager: Hardware initialization failed.")
                return False

            self._cap = cap
            self._camera_info = meta
            self._running = True

            # Launch dedicated capture thread
            self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True, name="CameraManager-Capture")
            self._capture_thread.start()

            # Launch async detection thread
            self._detection_thread = threading.Thread(target=self._detection_loop, daemon=True, name="CameraManager-Detection")
            self._detection_thread.start()

            logger.info(
                f"[CameraManager Started] Single VideoCapture active on Index {meta['index']} "
                f"({meta['backend_name']}) @ {meta['width']}x{meta['height']}"
            )
            return True

    def stop_camera(self) -> None:
        """Stop camera capture thread and release VideoCapture hardware resource."""
        with self._lock:
            self._running = False
            if self._cap:
                try:
                    self._cap.release()
                except Exception as exc:
                    logger.warning(f"Error releasing VideoCapture in CameraManager: {exc}")
                self._cap = None

            try:
                cv2.destroyAllWindows()
            except Exception:
                pass

            self._latest_frame = None
            self._latest_annotated_frame = None
            logger.info("CameraManager stopped and VideoCapture released.")

    def get_latest_frame(self) -> tuple[np.ndarray | None, np.ndarray | None, dict[str, Any]]:
        """
        Retrieve a copy of the latest captured frame, annotated frame, and diagnostics.

        Returns:
            Tuple of (raw_frame, annotated_frame, diagnostics_dict)
        """
        with self._lock:
            raw = self._latest_frame.copy() if self._latest_frame is not None else None
            ann = self._latest_annotated_frame.copy() if self._latest_annotated_frame is not None else raw
            diag = {
                "running": self._running,
                "fps": self._fps,
                "acquisition_ms": self._acquisition_latency_ms,
                "detection_ms": self._detection_latency_ms,
                "person_detected": self._person_detected,
                "info": self._camera_info,
            }
            return raw, ann, diag

    def subscribe(self, callback: Callable[[np.ndarray], None]) -> None:
        """Subscribe a listener callback to receive new frames."""
        with self._lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[np.ndarray], None]) -> None:
        """Unsubscribe a listener callback."""
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    def _capture_loop(self) -> None:
        """Dedicated high-priority capture thread running at target FPS."""
        prev_time = time.perf_counter()
        consecutive_drops = 0

        # Sensor Warmup: Flush first 5 frames to let auto-exposure and auto-gain balance
        for _ in range(5):
            if self._cap and self._cap.isOpened():
                self._cap.read()
                time.sleep(0.02)

        while self._running and self._cap and self._cap.isOpened():
            t_start = time.perf_counter()
            ret, frame = self._cap.read()
            t_end = time.perf_counter()

            if not ret or frame is None:
                self._frames_dropped += 1
                consecutive_drops += 1
                if consecutive_drops >= 5:
                    logger.warning("CameraManager: Consecutive frame drops detected. Retrying read...")
                    time.sleep(0.05)
                continue

            consecutive_drops = 0
            self._frames_captured += 1
            self._acquisition_latency_ms = (t_end - t_start) * 1000

            # Calculate FPS
            curr_time = time.perf_counter()
            self._fps = round(1.0 / max(0.001, curr_time - prev_time), 1)
            prev_time = curr_time

            with self._lock:
                self._latest_frame = frame
                self._frame_timestamp = curr_time
                if self._latest_annotated_frame is None:
                    self._latest_annotated_frame = frame

            # Notify active subscribers safely
            with self._lock:
                subs = list(self._subscribers)
            for sub in subs:
                try:
                    sub(frame)
                except Exception as err:
                    logger.debug(f"Subscriber error: {err}")

            # Sleep briefly to maintain 30 FPS target (~33ms total loop period)
            loop_duration = time.perf_counter() - t_start
            sleep_time = max(0.001, (1.0 / 30.0) - loop_duration)
            time.sleep(sleep_time)

    def _detection_loop(self) -> None:
        """Dedicated async thread running face/person detection out-of-band."""
        while self._running:
            raw_frame = None
            with self._lock:
                if self._latest_frame is not None:
                    raw_frame = self._latest_frame.copy()
                detector = self._detector

            if raw_frame is not None and detector is not None:
                det_start = time.perf_counter()
                try:
                    if hasattr(detector, "detect_in_frame"):
                        res = detector.detect_in_frame(raw_frame)
                        det_end = time.perf_counter()
                        with self._lock:
                            self._latest_annotated_frame = res.annotated_frame
                            self._person_detected = res.person_detected
                            self._detection_latency_ms = (det_end - det_start) * 1000
                except Exception as exc:
                    logger.debug(f"Async detection loop exception: {exc}")

            time.sleep(0.05)  # Run detection at ~20 FPS out-of-band
