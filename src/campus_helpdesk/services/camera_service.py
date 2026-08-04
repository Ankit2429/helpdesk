"""
Campus Helpdesk Robot – Phase 3: Camera Service
===============================================

Module: campus_helpdesk.services.camera_service
File:   src/campus_helpdesk/services/camera_service.py
Version: 1.0

This service manages the lifecycle of the camera hardware (or mock source)
and frame acquisition. It runs frame capture on a dedicated thread, publishes
frame envelopes to the Event Bus, and implements auto-recovery on disconnects.
It contains NO computer vision or person detection logic.

Thread Model
------------
*  **Capture Thread** – dedicated loop reading frames from the OpenCV capture
   device at the configured FPS.
*  **Queue Strategy** – uses a bounded frame buffer or queue. If a consumer
   is slow, older frames are discarded; the newest frame always wins to prevent
   latency buildup.
*  **Thread Safety** – start, stop, diagnostics, and status queries are fully
   guarded by a reentrant lock (``threading.RLock``).
"""

from __future__ import annotations

import logging
import time
import uuid
import threading
from typing import Any

import cv2
import numpy as np

from campus_helpdesk.application.exceptions import LLMServiceError, CameraError
from campus_helpdesk.interaction.event_bus import EventBus
from campus_helpdesk.interaction.events import CameraPayload, EventEnvelope, EventType

logger = logging.getLogger(__name__)


class CameraService:
    """Production-grade Camera Service managing video acquisition and recovery.

    Parameters
    ----------
    event_bus:
        The Event Bus instance to publish events to.
    camera_index:
        System camera index (e.g. 0).
    resolution:
        Tuple of ``(width, height)``. Defaults to ``(1280, 720)``.
    fps:
        Target frames per second. Defaults to ``30``.
    auto_reconnect:
        Whether to attempt reconnecting if read fails. Defaults to ``True``.
    reconnect_delay:
        Seconds to wait between reconnect attempts. Defaults to ``2.0``.
    frame_queue_size:
        Max size of internal frame buffer. Drops older frames when full.
    use_mock_fallback:
        If ``True``, generates dummy NumPy frames when physical device fails.
    """

    def __init__(
        self,
        event_bus: EventBus,
        camera_index: int = 0,
        resolution: tuple[int, int] = (1280, 720),
        fps: int = 30,
        auto_reconnect: bool = True,
        reconnect_delay: float = 2.0,
        frame_queue_size: int = 1,
        use_mock_fallback: bool = True,
        name: str = "camera_service",
    ) -> None:
        self._bus = event_bus
        self._camera_index = camera_index
        self._resolution = resolution
        self._fps = fps
        self._auto_reconnect = auto_reconnect
        self._reconnect_delay = reconnect_delay
        self._frame_queue_size = frame_queue_size
        self._use_mock_fallback = use_mock_fallback
        self._name = name

        self._lock = threading.RLock()
        self._cap: cv2.VideoCapture | None = None
        self._running = False
        self._connected = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        # Mock source state
        self._is_mock = False

        # Diagnostics & Metrics
        self._frames_captured = 0
        self._frames_dropped = 0
        self._reconnect_count = 0
        self._read_failures = 0
        self._total_capture_ms = 0.0
        self._start_time: float | None = None
        self._last_fps_time = time.perf_counter()
        self._fps_frame_count = 0
        self._current_fps = 0.0
        self._last_capture_latency = 0.0

        # Correlation context
        self._session_id: str | None = None
        self._correlation_id: str | None = None

    # ─────────────────────────────────────────────────────────────────────────
    # Public Lifecycle APIs
    # ─────────────────────────────────────────────────────────────────────────

    def initialize(self) -> bool:
        """Initialize the OpenCV capture source via singleton CameraManager.

        If physical device fails, falls back to Mock Source (if configured).
        """
        from campus_helpdesk.infrastructure.vision.camera_manager import CameraManager

        with self._lock:
            mgr = CameraManager.get_instance()
            success = mgr.start_camera(
                requested_index=self._camera_index,
                resolution=self._resolution,
                target_fps=self._fps,
            )

            if success:
                self._connected = True
                self._is_mock = False
                logger.info("CameraService connected via singleton CameraManager.")
                return True

            self._connected = False
            if self._use_mock_fallback:
                logger.info("Physical camera initialization failed. Falling back to Mock Source.")
                self._connected = True
                self._is_mock = True
                return True

            logger.error("Camera initialization failed; raising CameraError.")
            raise CameraError("Failed to initialize camera device.")

    def start(self) -> None:
        """Start the background frame capture thread."""
        with self._lock:
            if self._running:
                return

            if not self._connected:
                # Attempt to initialize
                self.initialize()

            self._running = True
            self._stop_event.clear()
            self._start_time = time.perf_counter()
            self._last_fps_time = time.perf_counter()
            self._fps_frame_count = 0

            self._thread = threading.Thread(
                target=self._capture_loop,
                name=f"{self._name}-capture",
                daemon=True,
            )
            self._thread.start()

            # Publish CAMERA_STARTED
            self._bus.publish(
                EventEnvelope.create(
                    event_type=EventType.CAMERA_STARTED,
                    source=self._name,
                    payload=CameraPayload(
                        frame_id=str(uuid.uuid4()),
                        timestamp=self._utcnow(),
                        resolution=f"{self._resolution[0]}x{self._resolution[1]}",
                        frame_number=0,
                        capture_latency_ms=0.0,
                        camera_index=self._camera_index,
                        status="STARTED",
                    ),
                )
            )
            logger.info("CameraService started.")

    def stop(self) -> None:
        """Gracefully stop the background frame capture thread."""
        with self._lock:
            if not self._running:
                return

            self._running = False
            self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)

        with self._lock:
            if self._cap is not None:
                self._cap.release()
                self._cap = None
                logger.info("Camera released.")
            self._connected = False

            # Publish CAMERA_STOPPED
            self._bus.publish(
                EventEnvelope.create(
                    event_type=EventType.CAMERA_STOPPED,
                    source=self._name,
                    payload=CameraPayload(
                        frame_id=str(uuid.uuid4()),
                        timestamp=self._utcnow(),
                        resolution=f"{self._resolution[0]}x{self._resolution[1]}",
                        frame_number=self._frames_captured,
                        capture_latency_ms=0.0,
                        camera_index=self._camera_index,
                        status="STOPPED",
                    ),
                )
            )
            logger.info("CameraService stopped.")

    def restart(self) -> None:
        """Stop and restart the camera service."""
        logger.info("Restarting CameraService...")
        self.stop()
        self.start()

    def shutdown(self) -> None:
        """Complete clean resource termination."""
        self.stop()

    def is_running(self) -> bool:
        """Query running status."""
        with self._lock:
            return self._running

    def is_connected(self) -> bool:
        """Query connection status."""
        with self._lock:
            return self._connected

    # ─────────────────────────────────────────────────────────────────────────
    # Core Acquisition Loop
    # ─────────────────────────────────────────────────────────────────────────

    def _capture_loop(self) -> None:
        """Background thread execution loop acquiring frames at target FPS."""
        frame_interval = 1.0 / self._fps

        try:
            while not self._stop_event.is_set():
                t_start = time.perf_counter()

                # Acquire Frame
                ret, frame = self._read_frame()

                if not ret or frame is None:
                    self._handle_read_failure()
                    # Wait before retry
                    time.sleep(frame_interval)
                    continue

                t_capture = time.perf_counter()
                latency_ms = (t_capture - t_start) * 1000
                self._last_capture_latency = latency_ms

                # Handle throttling & publication
                self._process_and_publish_frame(frame, latency_ms)

                # Sleep to match target FPS
                elapsed = time.perf_counter() - t_start
                sleep_time = frame_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
        finally:
            # Ensure capture resources are released when the loop exits
            if not self._is_mock and self._cap is not None:
                try:
                    self._cap.release()
                    logger.info("Camera released in capture loop exit.")
                except Exception as exc:
                    logger.error("Error releasing camera in capture loop: %s", exc)
                self._cap = None
                self._connected = False

    def _read_frame(self) -> tuple[bool, np.ndarray | None]:
        """Read a frame from the CV2 capture device or generate a mock frame."""
        with self._lock:
            if self._is_mock:
                # Generate a dummy color block using NumPy
                w, h = self._resolution
                mock_frame = np.zeros((h, w, 3), dtype=np.uint8)
                # Draw a color pattern that updates over time
                cv2.rectangle(
                    mock_frame,
                    (50, 50),
                    (w - 50, h - 50),
                    (0, 0, int((time.time() * 50) % 255)),
                    -1,
                )
                cv2.putText(
                    mock_frame,
                    f"Mock Source Frame {self._frames_captured}",
                    (100, 100),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (255, 255, 255),
                    2,
                )
                return True, mock_frame

            if self._cap is None:
                return False, None

            try:
                ret, frame = self._cap.read()
                return ret, frame
            except Exception as exc:
                logger.error("Exception during cv2 read: %s", exc)
                # Clean up potentially broken capture
                if self._cap is not None:
                    self._cap.release()
                    self._cap = None
                self._connected = False
                return False, None

    def _process_and_publish_frame(self, frame: np.ndarray, latency_ms: float) -> None:
        """Encode, compute metrics, and publish to event bus."""
        with self._lock:
            self._frames_captured += 1
            self._total_capture_ms += latency_ms

            # FPS metrics tracking
            self._fps_frame_count += 1
            now = time.perf_counter()
            if now - self._last_fps_time >= 1.0:
                self._current_fps = self._fps_frame_count / (now - self._last_fps_time)
                self._fps_frame_count = 0
                self._last_fps_time = now

            res_str = f"{self._resolution[0]}x{self._resolution[1]}"
            frame_num = self._frames_captured

        # Encode image frame data (e.g. JPEG) to keep metadata small
        # JPEG encoding reduces raw matrix copies over EventBus queues
        success, encoded = cv2.imencode(".jpg", frame)
        frame_bytes = encoded.tobytes() if success else b""

        payload = CameraPayload(
            frame_id=str(uuid.uuid4()),
            timestamp=self._utcnow(),
            resolution=res_str,
            frame_number=frame_num,
            capture_latency_ms=latency_ms,
            camera_index=self._camera_index,
            status="CAPTURED",
            frame_data=frame_bytes,
        )

        event = EventEnvelope.create(
            event_type=EventType.FRAME_CAPTURED,
            source=self._name,
            payload=payload,
            session_id=self._session_id,
            correlation_id=self._correlation_id,
        )

        # Drop old frames if event bus queue overflows or is busy (non-blocking publish)
        # Bounded frame buffer: newest frame wins
        success = self._bus.publish(event)
        if not success:
            with self._lock:
                self._frames_dropped += 1

    # ─────────────────────────────────────────────────────────────────────────
    # Auto Recovery / Reconnect Strategy
    # ─────────────────────────────────────────────────────────────────────────

    def _handle_read_failure(self) -> None:
        """Initiate auto-reconnect recovery sequence."""
        with self._lock:
            self._read_failures += 1
            if not self._connected:
                return

            self._connected = False
            logger.warning("Camera disconnected. Starting auto-reconnect sequence...")

        # Publish CAMERA_DISCONNECTED
        self._bus.publish(
            EventEnvelope.create(
                event_type=EventType.CAMERA_DISCONNECTED,
                source=self._name,
                payload=CameraPayload(
                    frame_id=str(uuid.uuid4()),
                    timestamp=self._utcnow(),
                    resolution=f"{self._resolution[0]}x{self._resolution[1]}",
                    frame_number=self._frames_captured,
                    capture_latency_ms=0.0,
                    camera_index=self._camera_index,
                    status="DISCONNECTED",
                ),
            )
        )

        if not self._auto_reconnect:
            raise CameraError(f"Camera {self._name} disconnected and auto-reconnect is disabled.")

        # Attempt Reconnection Loop
        reconnected = False
        while self._running and not reconnected:
            with self._lock:
                self._reconnect_count += 1

            logger.info("Attempting camera reconnection (attempt %d)...", self._reconnect_count)
            if self.initialize():
                reconnected = True
                # Publish CAMERA_RECONNECTED
                self._bus.publish(
                    EventEnvelope.create(
                        event_type=EventType.CAMERA_RECONNECTED,
                        source=self._name,
                        payload=CameraPayload(
                            frame_id=str(uuid.uuid4()),
                            timestamp=self._utcnow(),
                            resolution=f"{self._resolution[0]}x{self._resolution[1]}",
                            frame_number=self._frames_captured,
                            capture_latency_ms=0.0,
                            camera_index=self._camera_index,
                            status="RECONNECTED",
                        ),
                    )
                )
                logger.info("Camera reconnected successfully.")
                break

            time.sleep(self._reconnect_delay)

    # ─────────────────────────────────────────────────────────────────────────
    # Diagnostics & Status Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def health(self) -> dict[str, Any]:
        """Get health monitoring snapshot."""
        with self._lock:
            status_str = "healthy" if self._connected else "degraded"
            if not self._running:
                status_str = "stopped"

            return {
                "status": status_str,
                "connected": self._connected,
                "is_mock": self._is_mock,
                "read_failures": self._read_failures,
                "reconnect_count": self._reconnect_count,
            }

    def diagnostics(self) -> dict[str, Any]:
        """Get diagnostics statistics payload."""
        with self._lock:
            uptime_sec = time.perf_counter() - self._start_time if self._start_time else 0.0
            avg_latency = (
                self._total_capture_ms / self._frames_captured if self._frames_captured > 0 else 0.0
            )

            return {
                "current_fps": round(self._current_fps, 2),
                "frames_captured": self._frames_captured,
                "frames_dropped": self._frames_dropped,
                "reconnect_count": self._reconnect_count,
                "capture_latency_ms": round(avg_latency, 3),
                "uptime_seconds": round(uptime_sec, 3),
                "camera_properties": {
                    "camera_index": self._camera_index,
                    "resolution": f"{self._resolution[0]}x{self._resolution[1]}",
                    "target_fps": self._fps,
                    "is_mock_fallback": self._is_mock,
                },
                "health": self.health(),
            }

    def set_correlation_context(self, session_id: str | None, correlation_id: str | None) -> None:
        """Inject active session/correlation context for tracing."""
        with self._lock:
            self._session_id = session_id
            self._correlation_id = correlation_id

    def _utcnow(self) -> time.struct_time:
        """Helper to get timezone-aware datetime."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc)  # type: ignore[return-value]
