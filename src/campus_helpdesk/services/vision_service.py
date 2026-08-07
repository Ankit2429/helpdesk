"""
Campus Helpdesk Robot – Phase 3: Vision Service
===============================================

Module: campus_helpdesk.services.vision_service
File:   src/campus_helpdesk/services/vision_service.py
Version: 1.1  (Presence Detection Tuning)

This service manages person perception for the Interaction Engine. It consumes
``FRAME_CAPTURED`` events from the Event Bus, runs a person detection pipeline
via an extensible detector abstraction, applies debouncing logic to prevent
flicker, and publishes ``PERSON_DETECTED`` and ``PERSON_LEFT`` events.

Presence Detection Mechanism (v1.1)
------------------------------------
Detection uses a **dual-gate** model to eliminate false positives from
passersby, camera noise, and brief occlusions:

Gate 1 — Frame-count pre-filter:
    At least ``min_hits`` consecutive frames must contain a detection above
    ``confidence_threshold`` before the time gate starts counting.  This
    prevents single-frame glitches from ever starting the clock.

Gate 2 — Time-based confirmation window:
    The person must remain *continuously* visible for at least
    ``confirmation_window_sec`` seconds.  The clock resets to zero on any
    missed frame.  Only when *both* gates pass is PERSON_DETECTED published.

Exit gate — Absence timeout:
    Once a session is active, a person is considered to have left only after
    ``absence_timeout_sec`` continuous seconds without detection.  Brief head
    turns or detection dropouts within this window do NOT end the session.

Per-session greeting guard:
    PERSON_DETECTED is published *exactly once* per continuous presence
    session.  It is not re-published while the same person remains in view.
    The session resets (and PERSON_LEFT fires) after ``absence_timeout_sec``
    of continuous absence.

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

    Uses a dual-gate confirmation model to eliminate false positives:

    1. **Gate 1 – Frame pre-filter**: ``min_hits`` consecutive frames above
       ``confidence_threshold`` must occur before the clock starts.
    2. **Gate 2 – Time confirmation**: The person must be *continuously*
       visible for ``confirmation_window_sec`` seconds.  Any missed frame
       resets the clock.
    3. **Exit gate**: After presence is confirmed, PERSON_LEFT fires only
       after ``absence_timeout_sec`` continuous seconds of absence.
    4. **Session guard**: PERSON_DETECTED fires exactly once per presence
       session and does not repeat while the person remains in view.

    Parameters
    ----------
    event_bus:
        Central Event Bus instance.
    detector:
        Implementation of BasePersonDetector. Defaults to HOG.
    min_hits:
        Consecutive frame hits (above confidence_threshold) required before
        the time-confirmation clock starts. Default: 3.
    min_misses:
        Legacy parameter — kept for backward compatibility.  The actual
        exit trigger is now ``absence_timeout_sec``.  If
        ``absence_timeout_sec`` is None, falls back to frame-count mode
        using this value.  Default: 10.
    confirmation_window_sec:
        Minimum continuous presence duration (seconds) required before
        PERSON_DETECTED is published. Passersby or brief detections shorter
        than this window are silently ignored. Default: 3.0.
    absence_timeout_sec:
        Continuous absence duration (seconds) required before PERSON_LEFT
        is published and the session is reset. Brief gaps (head turns,
        occlusions) shorter than this window do NOT end the session.
        Default: 5.0.
    confidence_threshold:
        Minimum detector confidence score [0.0–1.0] for a frame hit to
        count toward the confirmation window. Detections below this value
        are treated as misses. Default: 0.3.
    greeting_once_per_session:
        If True, PERSON_DETECTED is published at most once per continuous
        presence session. The session resets (and a new greeting becomes
        possible) only after PERSON_LEFT fires. Default: True.
    """

    def __init__(
        self,
        event_bus: EventBus,
        detector: BasePersonDetector | None = None,
        min_hits: int = 3,
        min_misses: int = 10,
        confirmation_window_sec: float = 3.0,
        absence_timeout_sec: float = 5.0,
        confidence_threshold: float = 0.3,
        greeting_once_per_session: bool = True,
        name: str = "vision_service",
    ) -> None:
        self._bus = event_bus
        self._detector = detector or HOGPersonDetector()
        self._min_hits = min_hits
        self._min_misses = min_misses
        self._confirmation_window_sec = confirmation_window_sec
        self._absence_timeout_sec = absence_timeout_sec
        self._confidence_threshold = confidence_threshold
        self._greeting_once_per_session = greeting_once_per_session
        self._name = name

        self._lock = threading.RLock()
        self._queue: queue.Queue[EventEnvelope] = queue.Queue(maxsize=1)
        self._running = False
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None
        self._sub_handle: SubscriptionHandle | None = None

        # Perception State
        self._person_present = False
        self._greeted_this_session = False
        self._last_detection_time: float | None = None
        self._consecutive_hits = 0
        self._consecutive_misses = 0
        self._last_confidence = 0.0

        # Time-based gate timestamps
        # Set when the first consecutive qualified hit occurs; cleared on any miss.
        self._first_hit_time: float | None = None
        # Set when the first consecutive miss occurs after a confirmed session.
        self._first_miss_time: float | None = None

        # Performance Metrics
        self._frames_processed = 0
        self._frames_skipped = 0
        self._total_detect_ms = 0.0
        self._last_fps_time = time.perf_counter()
        self._fps_frame_count = 0
        self._current_fps = 0.0

        # Telemetry for benchmarking
        self._greeting_latency_sec: float | None = None  # first-hit → PERSON_DETECTED

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
            logger.info(
                "VisionService started | detector=%s | confirmation=%.1fs | absence_timeout=%.1fs | "
                "confidence_threshold=%.2f | greeting_once=%s",
                self._detector.name,
                self._confirmation_window_sec,
                self._absence_timeout_sec,
                self._confidence_threshold,
                self._greeting_once_per_session,
            )

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

            # ─────────────────────────────────────────────────────────────────
            # Gate 1: Confidence-filtered frame-count update
            # A "hit" only counts if the confidence clears the threshold.
            # ─────────────────────────────────────────────────────────────────
            qualified_hit = detected and confidence >= self._confidence_threshold

            if qualified_hit:
                self._consecutive_hits += 1
                self._consecutive_misses = 0
                self._last_detection_time = time.time()

                # Start time-gate clock on the first qualified hit in a streak
                if self._first_hit_time is None:
                    self._first_hit_time = time.time()

                # Reset absence clock (any hit cancels pending exit)
                self._first_miss_time = None

            else:
                self._consecutive_misses += 1
                self._consecutive_hits = 0
                # Any miss resets the pre-entry confirmation clock
                self._first_hit_time = None

                # Start absence clock when first miss occurs during active session
                if self._person_present and self._first_miss_time is None:
                    self._first_miss_time = time.time()

            # Evaluate state transitions with new dual-gate logic
            self._evaluate_state_transitions(confidence, bbox, event)

    def _evaluate_state_transitions(
        self,
        confidence: float,
        bbox: tuple[int, int, int, int] | None,
        trigger_event: EventEnvelope,
    ) -> None:
        """Validates dual-gate conditions and publishes presence events.

        Entry condition (Absent → Present):
            Gate 1: consecutive_hits >= min_hits
            Gate 2: first_hit_time is set AND (now - first_hit_time) >= confirmation_window_sec

        Exit condition (Present → Absent):
            first_miss_time is set AND (now - first_miss_time) >= absence_timeout_sec
            -OR- (legacy fallback) consecutive_misses >= min_misses when absence_timeout_sec <= 0
        """
        now = time.time()

        # ── 1. Entry: Absent ──→ Present ──────────────────────────────────
        if not self._person_present and not self._greeted_this_session:
            # Both gates must pass
            gate1_ok = self._consecutive_hits >= self._min_hits
            gate2_ok = (
                self._first_hit_time is not None
                and (now - self._first_hit_time) >= self._confirmation_window_sec
            )

            if gate1_ok and gate2_ok:
                self._person_present = True
                self._greeted_this_session = self._greeting_once_per_session

                # Record greeting latency (first-hit → confirmed)
                self._greeting_latency_sec = (
                    now - self._first_hit_time if self._first_hit_time else None
                )

                logger.info(
                    "Vision: Person confirmed present "
                    "(hits=%d, confidence=%.2f, continuous=%.1fs)",
                    self._consecutive_hits,
                    confidence,
                    self._greeting_latency_sec or 0.0,
                )

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

        # ── 2. Exit: Present ──→ Absent ───────────────────────────────────
        elif self._person_present:
            # Time-based exit gate
            absence_exceeded = (
                self._absence_timeout_sec > 0
                and self._first_miss_time is not None
                and (now - self._first_miss_time) >= self._absence_timeout_sec
            )
            # Legacy frame-count fallback (used when absence_timeout_sec <= 0)
            legacy_exit = (
                self._absence_timeout_sec <= 0
                and self._consecutive_misses >= self._min_misses
            )

            if absence_exceeded or legacy_exit:
                self._person_present = False
                self._greeted_this_session = False  # Reset for next visit
                self._first_hit_time = None
                self._first_miss_time = None

                logger.info(
                    "Vision: Person left (misses=%d, absence=%.1fs)",
                    self._consecutive_misses,
                    (now - self._first_miss_time) if self._first_miss_time else 0.0,
                )

                last_seen = self._last_detection_time or now
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
            now = time.time()
            current_hit_duration = (
                round(now - self._first_hit_time, 2) if self._first_hit_time else 0.0
            )
            current_absence_duration = (
                round(now - self._first_miss_time, 2) if self._first_miss_time else 0.0
            )

            return {
                "detector_name": self._detector.name,
                "person_present": self._person_present,
                "greeted_this_session": self._greeted_this_session,
                "current_fps": round(self._current_fps, 2),
                "frames_processed": self._frames_processed,
                "frames_skipped": self._frames_skipped,
                "avg_detection_latency_ms": round(avg_latency, 3),
                "last_detection_confidence": round(self._last_confidence, 3),
                "consecutive_hits": self._consecutive_hits,
                "consecutive_misses": self._consecutive_misses,
                # New time-based diagnostics
                "confirmation_window_sec": self._confirmation_window_sec,
                "absence_timeout_sec": self._absence_timeout_sec,
                "confidence_threshold": self._confidence_threshold,
                "current_hit_duration_sec": current_hit_duration,
                "current_absence_duration_sec": current_absence_duration,
                "greeting_latency_sec": self._greeting_latency_sec,
            }
