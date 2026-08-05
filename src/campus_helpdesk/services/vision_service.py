"""
Campus Helpdesk Robot – Phase 3: Vision Service
===============================================

Module: campus_helpdesk.services.vision_service
File:   src/campus_helpdesk/services/vision_service.py
Version: 1.0

This service manages person perception for the Interaction Engine. It consumes
``FRAME_CAPTURED`` events from the Event Bus, runs a person detection pipeline
via an extensible detector abstraction, applies debouncing logic to prevent
flicker, and publishes ``PERSON_DETECTED`` and ``PERSON_LEFT`` events.

Thread Model
------------
*  **Worker Thread** – dedicated loop (``VisionService-worker``) pulling
   frames from an internal bounded queue (size=1, newest frame wins) to avoid
   blocking the camera publisher thread or event bus.
*  **Thread Safety** – all state updates, hook/metric changes, and diagnostics
   queries are protected by a reentrant lock (``threading.RLock``).
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

import cv2
import numpy as np

from campus_helpdesk.interaction.event_bus import EventBus, SubscriptionHandle
from campus_helpdesk.interaction.events import (
    CameraPayload,
    EventEnvelope,
    EventType,
    PersonDetectedPayload,
    PersonLeftPayload,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Detector Abstraction
# ---------------------------------------------------------------------------


class BasePersonDetector(ABC):
    """Abstract base class for all person detection algorithms.

    Allows replacing HOG with YOLO, MediaPipe, etc. without modifying
    service code.
    """

    @abstractmethod
    def detect(
        self, frame: np.ndarray
    ) -> tuple[bool, float, tuple[int, int, int, int] | None]:
        """Detect a person in the given frame.

        Parameters
        ----------
        frame:
            NumPy array representing BGR image frame.

        Returns
        -------
        detected:
            True if a person is found; False otherwise.
        confidence:
            Score in range [0.0, 1.0].
        bounding_box:
            Optional tuple of (x, y, width, height) of the detected person.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the detector implementation."""
        pass


class HOGPersonDetector(BasePersonDetector):
    """Person detector using OpenCV Histogram of Oriented Gradients (HOG)."""

    def __init__(self) -> None:
        try:
            if hasattr(cv2, "HOGDescriptor"):
                self._hog = cv2.HOGDescriptor()
                if hasattr(cv2.HOGDescriptor, "getDefaultPeopleDetector"):
                    self._hog.setSVMDetector(cv2.HOGDescriptor.getDefaultPeopleDetector())
                elif hasattr(cv2, "HOGDescriptor_getDefaultPeopleDetector"):
                    self._hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        except Exception as exc:
            logger.warning("[HOGPersonDetector] OpenCV HOG initialization fallback: %s", exc, exc_info=True)
            self._hog = None

    def detect(
        self, frame: np.ndarray
    ) -> tuple[bool, float, tuple[int, int, int, int] | None]:
        if self._hog is None or frame is None or frame.size == 0:
            return False, 0.0, None

        # Resize frame to speed up SVM detection
        h, w = frame.shape[:2]
        scale = 1.0
        if w > 640:
            scale = 640.0 / w
            frame = cv2.resize(frame, (640, int(h * scale)))

        # Run HOG detector
        # hitThreshold=0, winStride=(8,8), padding=(32,32), scale=1.05
        boxes, weights = self._hog.detectMultiScale(
            frame, winStride=(8, 8), padding=(16, 16), scale=1.05
        )

        if len(boxes) > 0:
            # Map back to original coordinate space
            bx, by, bw, bh = boxes[0]
            orig_box = (
                int(bx / scale),
                int(by / scale),
                int(bw / scale),
                int(bh / scale),
            )
            confidence = float(weights[0])
            # Normalise SVM weights to [0.0, 1.0] range
            confidence = min(max(confidence / 2.0, 0.0), 1.0)
            return True, confidence, orig_box

        return False, 0.0, None

    @property
    def name(self) -> str:
        return "OpenCV_HOG_PeopleDetector"


class MockPersonDetector(BasePersonDetector):
    """Mock detector for unit tests and headless environments."""

    def __init__(self, name: str = "MockPersonDetector") -> None:
        self._name = name
        self.should_detect = False
        self.confidence = 0.95
        self.box = (10, 20, 100, 200)

    def detect(
        self, frame: np.ndarray
    ) -> tuple[bool, float, tuple[int, int, int, int] | None]:
        if self.should_detect:
            return True, self.confidence, self.box
        return False, 0.0, None

    @property
    def name(self) -> str:
        return self._name


# ---------------------------------------------------------------------------
# Vision Service
# ---------------------------------------------------------------------------


class VisionService:
    """Consumes frame events, runs person detection, and debounces presence states.

    Parameters
    ----------
    event_bus:
        Central Event Bus instance.
    detector:
        Implementation of BasePersonDetector. Defaults to HOG.
    min_hits:
        Consecutive frame hits required to publish PERSON_DETECTED.
    min_misses:
        Consecutive frame misses required to publish PERSON_LEFT.
    """

    def __init__(
        self,
        event_bus: EventBus,
        detector: BasePersonDetector | None = None,
        min_hits: int = 3,
        min_misses: int = 10,
        name: str = "vision_service",
    ) -> None:
        self._bus = event_bus
        self._detector = detector or HOGPersonDetector()
        self._min_hits = min_hits
        self._min_misses = min_misses
        self._name = name

        self._lock = threading.RLock()
        self._queue: queue.Queue[EventEnvelope] = queue.Queue(maxsize=1)
        self._running = False
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None
        self._sub_handle: SubscriptionHandle | None = None

        # Perception State
        self._person_present = False
        self._last_detection_time: float | None = None
        self._consecutive_hits = 0
        self._consecutive_misses = 0
        self._last_confidence = 0.0

        # Performance Metrics
        self._frames_processed = 0
        self._frames_skipped = 0
        self._total_detect_ms = 0.0
        self._last_fps_time = time.perf_counter()
        self._fps_frame_count = 0
        self._current_fps = 0.0

    # ─────────────────────────────────────────────────────────────────────────
    # Public Lifecycle APIs
    # ─────────────────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the subscriber and dedicated processing worker thread."""
        with self._lock:
            if self._running:
                return

            self._running = True
            self._stop_event.clear()

            # Subscribe to FRAME_CAPTURED
            self._sub_handle = self._bus.subscribe(
                self._enqueue_frame,
                event_types=EventType.FRAME_CAPTURED,
                source=self._name,
            )

            # Start Worker Thread
            self._worker = threading.Thread(
                target=self._worker_loop,
                name=f"{self._name}-worker",
                daemon=True,
            )
            self._worker.start()
            logger.info("VisionService started with detector: %s", self._detector.name)

    def stop(self) -> None:
        """Stop worker thread and unsubscribe from the event bus."""
        with self._lock:
            if not self._running:
                return

            self._running = False
            self._stop_event.set()

            if self._sub_handle:
                self._bus.unsubscribe(self._sub_handle)
                self._sub_handle = None

        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=3.0)

        # Clear remaining queue items
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

        logger.info("VisionService stopped.")

    def shutdown(self) -> None:
        """Complete clean resource termination."""
        self.stop()

    def is_running(self) -> bool:
        """Query running status."""
        with self._lock:
            return self._running

    # ─────────────────────────────────────────────────────────────────────────
    # Core Processing Loop
    # ─────────────────────────────────────────────────────────────────────────

    def _enqueue_frame(self, event: EventEnvelope) -> None:
        """Enqueues FRAME_CAPTURED events. Drops older frame if full (newest wins)."""
        if not self.is_running():
            return

        try:
            # Bounded queue (size 1): drop older frame if worker thread is busy
            self._queue.put_nowait(event)
        except queue.Full:
            # Remove old frame, push new frame
            try:
                self._queue.get_nowait()
                with self._lock:
                    self._frames_skipped += 1
                self._queue.put_nowait(event)
            except (queue.Empty, queue.Full):
                pass

    def _worker_loop(self) -> None:
        """Performs frame decoding, person detection, and state debouncing."""
        self._last_fps_time = time.perf_counter()
        self._fps_frame_count = 0

        while not self._stop_event.is_set():
            try:
                event = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue

            # Process frame
            self._process_frame(event)

    def _process_frame(self, event: EventEnvelope) -> None:
        payload = event.payload
        if not isinstance(payload, CameraPayload) or not payload.frame_data:
            return

        t_start = time.perf_counter()

        # Decode image from JPEG bytes
        img_np = np.frombuffer(payload.frame_data, dtype=np.uint8)
        frame = cv2.imdecode(img_np, cv2.IMREAD_COLOR)

        if frame is None:
            return

        # Execute Person Detection
        detected, confidence, bbox = self._detector.detect(frame)

        t_end = time.perf_counter()
        latency_ms = (t_end - t_start) * 1000

        with self._lock:
            self._frames_processed += 1
            self._total_detect_ms += latency_ms
            self._last_confidence = confidence

            # FPS metrics tracking
            self._fps_frame_count += 1
            now = time.perf_counter()
            if now - self._last_fps_time >= 1.0:
                self._current_fps = self._fps_frame_count / (now - self._last_fps_time)
                self._fps_frame_count = 0
                self._last_fps_time = now

            # Debounce Presence State
            if detected:
                self._consecutive_hits += 1
                self._consecutive_misses = 0
                self._last_detection_time = time.time()
            else:
                self._consecutive_misses += 1
                self._consecutive_hits = 0

            # Evaluate presence state transition
            self._evaluate_state_transitions(confidence, bbox, event)

    def _evaluate_state_transitions(
        self,
        confidence: float,
        bbox: tuple[int, int, int, int] | None,
        trigger_event: EventEnvelope,
    ) -> None:
        """Validates hits/misses counts against thresholds and publishes events."""
        # 1. State change: Absent -> Present
        if not self._person_present and self._consecutive_hits >= self._min_hits:
            self._person_present = True
            logger.info(
                "Vision: Person detected (hits=%d, confidence=%.2f)",
                self._consecutive_hits,
                confidence,
            )
            # Publish PERSON_DETECTED
            self._bus.publish(
                EventEnvelope.create(
                    event_type=EventType.PERSON_DETECTED,
                    source=self._name,
                    payload=PersonDetectedPayload(
                        confidence=confidence,
                        bounding_box=bbox,
                        camera_index=getattr(trigger_event.payload, "camera_index", 0),
                    ),
                    session_id=trigger_event.session_id,
                    correlation_id=trigger_event.event_id,
                )
            )

        # 2. State change: Present -> Absent
        elif self._person_present and self._consecutive_misses >= self._min_misses:
            self._person_present = False
            logger.info("Vision: Person left (misses=%d)", self._consecutive_misses)
            # Publish PERSON_LEFT
            last_seen = self._last_detection_time or time.time()
            self._bus.publish(
                EventEnvelope.create(
                    event_type=EventType.PERSON_LEFT,
                    source=self._name,
                    payload=PersonLeftPayload(
                        last_seen_at=datetime.fromtimestamp(last_seen, UTC),
                        frames_without_detection=self._consecutive_misses,
                    ),
                    session_id=trigger_event.session_id,
                    correlation_id=trigger_event.event_id,
                )
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Diagnostics & Status Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def diagnostics(self) -> dict[str, Any]:
        """Get diagnostics statistics payload."""
        with self._lock:
            avg_latency = (
                self._total_detect_ms / self._frames_processed if self._frames_processed > 0 else 0.0
            )

            return {
                "detector_name": self._detector.name,
                "person_present": self._person_present,
                "current_fps": round(self._current_fps, 2),
                "frames_processed": self._frames_processed,
                "frames_skipped": self._frames_skipped,
                "avg_detection_latency_ms": round(avg_latency, 3),
                "last_detection_confidence": round(self._last_confidence, 3),
                "consecutive_hits": self._consecutive_hits,
                "consecutive_misses": self._consecutive_misses,
            }
