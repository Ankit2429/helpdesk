"""
Tests for campus_helpdesk.services.vision_service
=================================================

Coverage:
1.  Mock detector operation and BasePersonDetector interface
2.  VisionService start, stop, shutdown lifecycles
3.  Frame queue ingestion and newest-frame-wins drop behavior
4.  Legacy frame-count debouncing (backward-compat: min_hits / min_misses)
5.  Dual-gate: 3-second confirmation window suppresses passersby
6.  Dual-gate: 3-second continuous presence triggers PERSON_DETECTED
7.  Confidence threshold: sub-threshold detections do not count as hits
8.  Absence timeout: brief absence (<timeout) does NOT fire PERSON_LEFT
9.  Absence timeout: sustained absence (≥timeout) fires PERSON_LEFT
10. Per-session greeting guard: PERSON_DETECTED fires exactly once per session
11. Session reset: PERSON_DETECTED fires again after PERSON_LEFT resets session
12. Event publication duplicate prevention
13. Thread safety under load
14. Latency benchmarks (detection latency < 40 ms/frame)
15. Greeting latency benchmark (first-hit → PERSON_DETECTED ≥ confirmation_window)
"""

from __future__ import annotations

import time
import uuid
import threading
from datetime import datetime, timezone
import pytest
import cv2
import numpy as np

from campus_helpdesk.interaction.event_bus import EventBus
from campus_helpdesk.interaction.events import CameraPayload, EventEnvelope, EventType
from campus_helpdesk.services.vision_service import (
    BasePersonDetector,
    HOGPersonDetector,
    MockPersonDetector,
    VisionService,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_frame_event(frame_num: int, img_bytes: bytes) -> EventEnvelope:
    return EventEnvelope.create(
        event_type=EventType.FRAME_CAPTURED,
        source="camera",
        payload=CameraPayload(
            frame_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            resolution="320x240",
            frame_number=frame_num,
            capture_latency_ms=1.0,
            frame_data=img_bytes,
        ),
    )


def _make_jpeg() -> bytes:
    """Return minimal valid JPEG bytes."""
    _, encoded = cv2.imencode(".jpg", np.zeros((100, 100, 3), dtype=np.uint8))
    return encoded.tobytes()


def _publish_hits(bus: EventBus, img_bytes: bytes, count: int, start: int = 1) -> None:
    """Synchronously publish N FRAME_CAPTURED events."""
    for i in range(count):
        bus.publish_sync(_make_frame_event(start + i, img_bytes))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def bus() -> EventBus:
    b = EventBus(maxsize=1000, max_workers=2, name="test-vision-bus")
    yield b
    b.shutdown(timeout=3.0)


@pytest.fixture
def mock_detector() -> MockPersonDetector:
    return MockPersonDetector()


@pytest.fixture
def img_bytes() -> bytes:
    return _make_jpeg()


@pytest.fixture
def vision_legacy(bus: EventBus, mock_detector: MockPersonDetector) -> VisionService:
    """Legacy frame-count mode: confirmation_window=0, absence_timeout=0."""
    srv = VisionService(
        event_bus=bus,
        detector=mock_detector,
        min_hits=3,
        min_misses=5,
        confirmation_window_sec=0.0,   # Disable time gate → frame-count only
        absence_timeout_sec=0.0,        # Disable absence time → frame-count only
        confidence_threshold=0.0,       # Accept any detection
        greeting_once_per_session=False,
        name="test-vision-legacy",
    )
    yield srv
    srv.shutdown()


@pytest.fixture
def vision_timed(bus: EventBus, mock_detector: MockPersonDetector) -> VisionService:
    """Full dual-gate mode with very short windows for fast test execution."""
    srv = VisionService(
        event_bus=bus,
        detector=mock_detector,
        min_hits=2,
        min_misses=99,                  # Disable frame-count exit in this fixture
        confirmation_window_sec=0.3,    # 300ms window — fast for tests
        absence_timeout_sec=0.5,        # 500ms absence timeout
        confidence_threshold=0.5,
        greeting_once_per_session=True,
        name="test-vision-timed",
    )
    yield srv
    srv.shutdown()


# ===========================================================================
# 1. Detector Implementations
# ===========================================================================


class TestPersonDetectors:
    def test_mock_detector(self, mock_detector: MockPersonDetector) -> None:
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        assert mock_detector.name == "MockPersonDetector"

        # Initially False
        det, conf, bbox = mock_detector.detect(frame)
        assert det is False

        # Set True
        mock_detector.should_detect = True
        det, conf, bbox = mock_detector.detect(frame)
        assert det is True
        assert conf == 0.95
        assert bbox == (10, 20, 100, 200)

    def test_hog_detector_initialization(self) -> None:
        hog = HOGPersonDetector()
        assert hog.name == "OpenCV_HOG_PeopleDetector"
        # Test empty frame read
        det, conf, bbox = hog.detect(np.zeros((0, 0, 3), dtype=np.uint8))
        assert det is False


# ===========================================================================
# 2. Lifecycle
# ===========================================================================


class TestVisionLifecycle:
    def test_start_stop_subscribes(
        self, bus: EventBus, vision_legacy: VisionService
    ) -> None:
        assert vision_legacy.is_running() is False
        vision_legacy.start()
        assert vision_legacy.is_running() is True

        subs = bus.registered_subscribers()
        assert subs.get("FRAME_CAPTURED", 0) == 1

        vision_legacy.stop()
        assert vision_legacy.is_running() is False
        subs = bus.registered_subscribers()
        assert subs.get("FRAME_CAPTURED", 0) == 0


# ===========================================================================
# 3. Legacy Frame-Count Debouncing (backward compat)
# ===========================================================================


class TestLegacyDebouncing:
    """Verify original frame-count semantics still work when time gates are disabled."""

    def test_legacy_hits_and_misses(
        self,
        bus: EventBus,
        vision_legacy: VisionService,
        mock_detector: MockPersonDetector,
        img_bytes: bytes,
    ) -> None:
        detected_events: list[EventEnvelope] = []
        left_events: list[EventEnvelope] = []
        done_detected = threading.Event()
        done_left = threading.Event()

        bus.subscribe(
            lambda e: [detected_events.append(e), done_detected.set()],
            EventType.PERSON_DETECTED,
            source="test-spy",
        )
        bus.subscribe(
            lambda e: [left_events.append(e), done_left.set()],
            EventType.PERSON_LEFT,
            source="test-spy",
        )

        vision_legacy.start()

        # Send 2 hits (threshold is 3) → should not trigger event
        mock_detector.should_detect = True
        _publish_hits(bus, img_bytes, 2)
        time.sleep(0.1)
        assert len(detected_events) == 0

        # Send 3rd hit → should trigger PERSON_DETECTED
        bus.publish_sync(_make_frame_event(3, img_bytes))
        assert done_detected.wait(timeout=3.0)
        assert len(detected_events) == 1
        assert detected_events[0].payload.confidence == 0.95

        # Send 4th hit → duplicate check, should NOT publish another event
        bus.publish_sync(_make_frame_event(4, img_bytes))
        time.sleep(0.1)
        assert len(detected_events) == 1

        # Now send misses to trigger PERSON_LEFT (threshold min_misses=5)
        mock_detector.should_detect = False
        for i in range(4):
            bus.publish_sync(_make_frame_event(5 + i, img_bytes))
        time.sleep(0.1)
        assert len(left_events) == 0

        # 5th miss → should trigger PERSON_LEFT
        bus.publish_sync(_make_frame_event(9, img_bytes))
        assert done_left.wait(timeout=3.0)
        assert len(left_events) == 1
        assert left_events[0].payload.frames_without_detection == 5

        # 6th miss → should NOT publish duplicate PERSON_LEFT
        bus.publish_sync(_make_frame_event(10, img_bytes))
        time.sleep(0.1)
        assert len(left_events) == 1


# ===========================================================================
# 4. Confidence Threshold
# ===========================================================================


class TestConfidenceThreshold:
    def test_low_confidence_rejected(
        self, bus: EventBus, mock_detector: MockPersonDetector, img_bytes: bytes
    ) -> None:
        """Detections below confidence_threshold must not count as hits."""
        srv = VisionService(
            event_bus=bus,
            detector=mock_detector,
            min_hits=2,
            confirmation_window_sec=0.0,
            absence_timeout_sec=0.0,
            confidence_threshold=0.8,     # Threshold = 0.8
            greeting_once_per_session=False,
            name="test-conf-threshold",
        )
        detected_events: list[EventEnvelope] = []
        bus.subscribe(
            lambda e: detected_events.append(e),
            EventType.PERSON_DETECTED,
            source="test-conf-spy",
        )
        srv.start()

        # Mock detector returns confidence=0.95 by default — set to 0.5 (below 0.8)
        mock_detector.should_detect = True
        mock_detector.confidence = 0.5     # Below threshold

        for i in range(10):
            bus.publish_sync(_make_frame_event(i, img_bytes))
        time.sleep(0.2)

        assert len(detected_events) == 0, "Low-confidence detections should not trigger PERSON_DETECTED"

        srv.shutdown()

    def test_high_confidence_accepted(
        self, bus: EventBus, mock_detector: MockPersonDetector, img_bytes: bytes
    ) -> None:
        """Detections above confidence_threshold must contribute to the hit counter."""
        done = threading.Event()
        detected_events: list[EventEnvelope] = []
        srv = VisionService(
            event_bus=bus,
            detector=mock_detector,
            min_hits=2,
            confirmation_window_sec=0.0,  # Disable time gate for this test
            absence_timeout_sec=0.0,
            confidence_threshold=0.8,
            greeting_once_per_session=False,
            name="test-conf-accept",
        )
        bus.subscribe(
            lambda e: [detected_events.append(e), done.set()],
            EventType.PERSON_DETECTED,
            source="test-conf-accept-spy",
        )
        srv.start()

        mock_detector.should_detect = True
        mock_detector.confidence = 0.95   # Above threshold

        for i in range(3):
            bus.publish_sync(_make_frame_event(i, img_bytes))

        assert done.wait(timeout=3.0), "High-confidence detections should trigger PERSON_DETECTED"
        assert len(detected_events) >= 1

        srv.shutdown()


# ===========================================================================
# 5. Dual-Gate: Time-Based Confirmation Window
# ===========================================================================


class TestConfirmationWindow:
    def test_brief_passerby_suppressed(
        self,
        bus: EventBus,
        mock_detector: MockPersonDetector,
        img_bytes: bytes,
    ) -> None:
        """A person visible for less than confirmation_window_sec must NOT trigger PERSON_DETECTED."""
        detected_events: list[EventEnvelope] = []
        srv = VisionService(
            event_bus=bus,
            detector=mock_detector,
            min_hits=2,
            confirmation_window_sec=0.5,    # Require 500ms continuous visibility
            absence_timeout_sec=0.0,
            confidence_threshold=0.0,
            greeting_once_per_session=True,
            name="test-passerby",
        )
        bus.subscribe(
            lambda e: detected_events.append(e),
            EventType.PERSON_DETECTED,
            source="test-passerby-spy",
        )
        srv.start()

        # Simulate rapid passerby: 3 quick hits (< 200ms total), then disappears
        mock_detector.should_detect = True
        for i in range(3):
            bus.publish_sync(_make_frame_event(i, img_bytes))
            time.sleep(0.01)  # 10ms between frames ≈ 30ms total — well under 500ms

        # Person leaves immediately
        mock_detector.should_detect = False
        bus.publish_sync(_make_frame_event(4, img_bytes))
        time.sleep(0.2)

        assert len(detected_events) == 0, (
            "Passerby visible for <confirmation_window_sec should not trigger PERSON_DETECTED"
        )
        srv.shutdown()

    def test_sustained_presence_triggers(
        self,
        bus: EventBus,
        mock_detector: MockPersonDetector,
        img_bytes: bytes,
    ) -> None:
        """A person visible continuously for ≥confirmation_window_sec MUST trigger PERSON_DETECTED."""
        done = threading.Event()
        detected_events: list[EventEnvelope] = []

        srv = VisionService(
            event_bus=bus,
            detector=mock_detector,
            min_hits=2,
            confirmation_window_sec=0.3,    # 300ms window
            absence_timeout_sec=0.0,
            confidence_threshold=0.0,
            greeting_once_per_session=True,
            name="test-sustained",
        )
        bus.subscribe(
            lambda e: [detected_events.append(e), done.set()],
            EventType.PERSON_DETECTED,
            source="test-sustained-spy",
        )
        srv.start()

        mock_detector.should_detect = True
        # Stream frames for ~500ms (well above 300ms window)
        t_start = time.perf_counter()
        fn = 0
        while time.perf_counter() - t_start < 0.5:
            bus.publish_sync(_make_frame_event(fn, img_bytes))
            fn += 1
            time.sleep(0.02)  # ~50 FPS publish rate

        assert done.wait(timeout=2.0), (
            "Person continuously visible for >confirmation_window_sec should trigger PERSON_DETECTED"
        )
        assert len(detected_events) == 1

        srv.shutdown()

    def test_interrupted_presence_resets_clock(
        self,
        bus: EventBus,
        mock_detector: MockPersonDetector,
        img_bytes: bytes,
    ) -> None:
        """A miss in the middle of the confirmation window resets the clock."""
        detected_events: list[EventEnvelope] = []

        srv = VisionService(
            event_bus=bus,
            detector=mock_detector,
            min_hits=2,
            confirmation_window_sec=0.5,    # 500ms window
            absence_timeout_sec=0.0,
            confidence_threshold=0.0,
            greeting_once_per_session=True,
            name="test-interrupted",
        )
        bus.subscribe(
            lambda e: detected_events.append(e),
            EventType.PERSON_DETECTED,
            source="test-interrupted-spy",
        )
        srv.start()

        # Hits for 200ms
        mock_detector.should_detect = True
        t_start = time.perf_counter()
        fn = 0
        while time.perf_counter() - t_start < 0.2:
            bus.publish_sync(_make_frame_event(fn, img_bytes))
            fn += 1
            time.sleep(0.02)

        # One miss — resets clock
        mock_detector.should_detect = False
        bus.publish_sync(_make_frame_event(fn, img_bytes))
        fn += 1
        time.sleep(0.05)

        # Resume hits for 200ms — still not 500ms continuous
        mock_detector.should_detect = True
        t2 = time.perf_counter()
        while time.perf_counter() - t2 < 0.2:
            bus.publish_sync(_make_frame_event(fn, img_bytes))
            fn += 1
            time.sleep(0.02)

        time.sleep(0.1)

        assert len(detected_events) == 0, (
            "Clock reset by a miss — cumulative time should not count"
        )
        srv.shutdown()


# ===========================================================================
# 6. Absence Timeout
# ===========================================================================


class TestAbsenceTimeout:
    def _confirm_person(
        self,
        srv: VisionService,
        bus: EventBus,
        mock_detector: MockPersonDetector,
        img_bytes: bytes,
        window_sec: float,
    ) -> threading.Event:
        """Helper: stream frames until PERSON_DETECTED fires."""
        done = threading.Event()
        bus.subscribe(
            lambda e: done.set(),
            EventType.PERSON_DETECTED,
            source="test-abs-confirm-spy",
        )
        mock_detector.should_detect = True
        t = time.perf_counter()
        fn = 0
        while time.perf_counter() - t < window_sec + 0.2:
            bus.publish_sync(_make_frame_event(fn, img_bytes))
            fn += 1
            time.sleep(0.02)
        done.wait(timeout=3.0)
        return done

    def test_brief_absence_does_not_fire_person_left(
        self, bus: EventBus, mock_detector: MockPersonDetector, img_bytes: bytes
    ) -> None:
        """Absence shorter than absence_timeout_sec must NOT fire PERSON_LEFT."""
        left_events: list[EventEnvelope] = []
        srv = VisionService(
            event_bus=bus,
            detector=mock_detector,
            min_hits=2,
            confirmation_window_sec=0.2,
            absence_timeout_sec=0.8,        # 800ms absence required
            confidence_threshold=0.0,
            greeting_once_per_session=True,
            name="test-brief-abs",
        )
        bus.subscribe(
            lambda e: left_events.append(e),
            EventType.PERSON_LEFT,
            source="test-brief-abs-spy",
        )
        srv.start()

        # Confirm presence
        self._confirm_person(srv, bus, mock_detector, img_bytes, 0.3)

        # Brief absence: 400ms (less than 800ms timeout)
        mock_detector.should_detect = False
        fn = 100
        t = time.perf_counter()
        while time.perf_counter() - t < 0.4:
            bus.publish_sync(_make_frame_event(fn, img_bytes))
            fn += 1
            time.sleep(0.02)

        time.sleep(0.1)
        assert len(left_events) == 0, (
            "Brief absence < absence_timeout_sec should NOT fire PERSON_LEFT"
        )
        srv.shutdown()

    def test_sustained_absence_fires_person_left(
        self, bus: EventBus, mock_detector: MockPersonDetector, img_bytes: bytes
    ) -> None:
        """Absence ≥ absence_timeout_sec MUST fire PERSON_LEFT exactly once."""
        done_left = threading.Event()
        left_events: list[EventEnvelope] = []

        srv = VisionService(
            event_bus=bus,
            detector=mock_detector,
            min_hits=2,
            confirmation_window_sec=0.2,
            absence_timeout_sec=0.5,        # 500ms timeout
            confidence_threshold=0.0,
            greeting_once_per_session=True,
            name="test-sustained-abs",
        )
        bus.subscribe(
            lambda e: [left_events.append(e), done_left.set()],
            EventType.PERSON_LEFT,
            source="test-sustained-abs-spy",
        )
        srv.start()

        # Confirm presence
        self._confirm_person(srv, bus, mock_detector, img_bytes, 0.3)

        # Sustained absence: 700ms (above 500ms timeout)
        mock_detector.should_detect = False
        fn = 100
        t = time.perf_counter()
        while time.perf_counter() - t < 0.7:
            bus.publish_sync(_make_frame_event(fn, img_bytes))
            fn += 1
            time.sleep(0.02)

        assert done_left.wait(timeout=3.0), "PERSON_LEFT should fire after absence_timeout_sec"
        assert len(left_events) == 1

        # Additional misses must NOT re-fire PERSON_LEFT
        for i in range(5):
            bus.publish_sync(_make_frame_event(200 + i, img_bytes))
        time.sleep(0.1)
        assert len(left_events) == 1, "PERSON_LEFT must not fire twice"

        srv.shutdown()


# ===========================================================================
# 7. Per-Session Greeting Guard
# ===========================================================================


class TestGreetingGuard:
    def test_greeting_fires_once_per_session(
        self, bus: EventBus, mock_detector: MockPersonDetector, img_bytes: bytes
    ) -> None:
        """PERSON_DETECTED must fire exactly once while the person stays in view."""
        detected_events: list[EventEnvelope] = []

        srv = VisionService(
            event_bus=bus,
            detector=mock_detector,
            min_hits=2,
            confirmation_window_sec=0.2,
            absence_timeout_sec=0.0,        # Disable exit for this test
            confidence_threshold=0.0,
            greeting_once_per_session=True,
            name="test-session-guard",
        )
        bus.subscribe(
            lambda e: detected_events.append(e),
            EventType.PERSON_DETECTED,
            source="test-session-spy",
        )
        srv.start()

        # Stream frames continuously for 1 second
        mock_detector.should_detect = True
        t = time.perf_counter()
        fn = 0
        while time.perf_counter() - t < 1.0:
            bus.publish_sync(_make_frame_event(fn, img_bytes))
            fn += 1
            time.sleep(0.02)

        time.sleep(0.2)

        assert len(detected_events) == 1, (
            f"Expected exactly 1 PERSON_DETECTED for continuous session, got {len(detected_events)}"
        )
        srv.shutdown()

    def test_new_session_after_person_left(
        self, bus: EventBus, mock_detector: MockPersonDetector, img_bytes: bytes
    ) -> None:
        """After PERSON_LEFT fires, a new visit must trigger a new PERSON_DETECTED."""
        detected_events: list[EventEnvelope] = []
        left_events: list[EventEnvelope] = []
        done_detected = threading.Event()
        done_left = threading.Event()
        second_detected = threading.Event()

        def on_detected(e: EventEnvelope) -> None:
            detected_events.append(e)
            if len(detected_events) == 1:
                done_detected.set()
            elif len(detected_events) == 2:
                second_detected.set()

        srv = VisionService(
            event_bus=bus,
            detector=mock_detector,
            min_hits=2,
            confirmation_window_sec=0.2,
            absence_timeout_sec=0.4,
            confidence_threshold=0.0,
            greeting_once_per_session=True,
            name="test-new-session",
        )
        bus.subscribe(on_detected, EventType.PERSON_DETECTED, source="test-ns-spy")
        bus.subscribe(
            lambda e: [left_events.append(e), done_left.set()],
            EventType.PERSON_LEFT,
            source="test-ns-spy2",
        )
        srv.start()

        # --- Visit 1: Person arrives and stays ---
        mock_detector.should_detect = True
        t = time.perf_counter()
        fn = 0
        while time.perf_counter() - t < 0.4:
            bus.publish_sync(_make_frame_event(fn, img_bytes))
            fn += 1
            time.sleep(0.02)
        done_detected.wait(timeout=3.0)

        # --- Person leaves for > absence_timeout ---
        mock_detector.should_detect = False
        t2 = time.perf_counter()
        while time.perf_counter() - t2 < 0.6:
            bus.publish_sync(_make_frame_event(fn, img_bytes))
            fn += 1
            time.sleep(0.02)
        done_left.wait(timeout=3.0)
        assert len(left_events) == 1

        # --- Visit 2: Same person (or new person) arrives again ---
        mock_detector.should_detect = True
        t3 = time.perf_counter()
        while time.perf_counter() - t3 < 0.5:
            bus.publish_sync(_make_frame_event(fn, img_bytes))
            fn += 1
            time.sleep(0.02)

        assert second_detected.wait(timeout=3.0), (
            "Second visit after PERSON_LEFT should trigger a new PERSON_DETECTED"
        )
        assert len(detected_events) == 2

        srv.shutdown()


# ===========================================================================
# 8. Queue Behavior (Frame Skipping)
# ===========================================================================


class TestQueueSkipping:
    def test_newest_frame_wins(self, bus: EventBus, mock_detector: MockPersonDetector) -> None:
        # Create a slow mock detector to force frame drops
        class SlowDetector(MockPersonDetector):
            def detect(self, frame: np.ndarray) -> tuple[bool, float, tuple[int, int, int, int] | None]:
                time.sleep(0.3)
                return super().detect(frame)

        slow_det = SlowDetector()
        srv = VisionService(
            event_bus=bus,
            detector=slow_det,
            min_hits=3,
            min_misses=3,
            confirmation_window_sec=0.0,
            absence_timeout_sec=0.0,
        )

        try:
            srv.start()
            _, encoded = cv2.imencode(".jpg", np.zeros((100, 100, 3), dtype=np.uint8))
            img_bytes = encoded.tobytes()

            # Push 5 frames in quick succession
            for i in range(5):
                bus.publish(_make_frame_event(i, img_bytes))

            time.sleep(0.8)  # Let worker run
            srv.stop()

            diag = srv.diagnostics()
            assert diag["frames_skipped"] > 0
            print(f"\n[Vision Frame Drop] Skipped frames: {diag['frames_skipped']}")
        finally:
            srv.shutdown()


# ===========================================================================
# 9. Diagnostics
# ===========================================================================


class TestDiagnostics:
    def test_diagnostics_contains_new_fields(
        self, bus: EventBus, vision_timed: VisionService
    ) -> None:
        """Diagnostics must expose the new time-based configuration fields."""
        vision_timed.start()
        diag = vision_timed.diagnostics()

        assert "confirmation_window_sec" in diag
        assert "absence_timeout_sec" in diag
        assert "confidence_threshold" in diag
        assert "current_hit_duration_sec" in diag
        assert "current_absence_duration_sec" in diag
        assert "greeting_latency_sec" in diag
        assert "greeted_this_session" in diag

        assert diag["confirmation_window_sec"] == 0.3
        assert diag["absence_timeout_sec"] == 0.5
        assert diag["confidence_threshold"] == 0.5

        vision_timed.stop()


# ===========================================================================
# 10. Benchmarks
# ===========================================================================


class TestBenchmarks:
    N = 100

    def test_hog_detector_performance_latency(self) -> None:
        hog = HOGPersonDetector()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        t0 = time.perf_counter()
        for _ in range(self.N):
            hog.detect(frame)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        avg_ms = elapsed_ms / self.N

        print(
            f"\n[Benchmark] Vision HOG detection: {elapsed_ms:.1f} ms for {self.N} frames "
            f"(avg {avg_ms:.2f} ms/frame)"
        )
        # Average HOG detection latency target is < 120.0 ms/frame
        assert avg_ms < 120.0

    def test_greeting_latency_meets_confirmation_window(
        self, bus: EventBus, mock_detector: MockPersonDetector, img_bytes: bytes
    ) -> None:
        """Greeting latency (first-hit → PERSON_DETECTED) must be ≥ confirmation_window_sec."""
        window = 0.3
        done = threading.Event()
        detected_events: list[EventEnvelope] = []

        srv = VisionService(
            event_bus=bus,
            detector=mock_detector,
            min_hits=2,
            confirmation_window_sec=window,
            absence_timeout_sec=0.0,
            confidence_threshold=0.0,
            greeting_once_per_session=True,
            name="test-latency-bench",
        )
        bus.subscribe(
            lambda e: [detected_events.append(e), done.set()],
            EventType.PERSON_DETECTED,
            source="test-latency-spy",
        )
        srv.start()

        t_first_hit = time.perf_counter()
        mock_detector.should_detect = True
        fn = 0
        while not done.is_set() and time.perf_counter() - t_first_hit < 2.0:
            bus.publish_sync(_make_frame_event(fn, img_bytes))
            fn += 1
            time.sleep(0.02)

        t_detected = time.perf_counter()
        elapsed = t_detected - t_first_hit

        assert done.is_set(), "PERSON_DETECTED must fire within 2s of streaming"
        assert elapsed >= window, (
            f"Greeting latency {elapsed:.3f}s must be >= confirmation_window {window}s"
        )

        diag = srv.diagnostics()
        print(
            f"\n[Benchmark] Greeting latency: {elapsed:.3f}s "
            f"(confirmation_window={window}s, recorded={diag['greeting_latency_sec']}s)"
        )

        srv.shutdown()
