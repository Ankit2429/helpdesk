"""
Tests for campus_helpdesk.services.camera_service
==================================================

Coverage:
1.  Initialization and fallback to Mock Source
2.  Service start, stop, restart, shutdown lifecycles
3.  Frame capture loop execution
4.  Event publication (CAMERA_STARTED, CAMERA_STOPPED, FRAME_CAPTURED)
5.  Queue drop policy (non-blocking drops on overflow)
6.  Auto-reconnection logic (CAMERA_DISCONNECTED, CAMERA_RECONNECTED)
7.  Thread safety of start / stop
8.  Diagnostics and Health API monitoring
9.  Latency benchmarks (average capture overhead < 2 ms)
"""

from __future__ import annotations

import time
import uuid
import threading
import pytest

from campus_helpdesk.interaction.event_bus import EventBus
from campus_helpdesk.interaction.events import EventEnvelope, EventType, CameraPayload
from campus_helpdesk.services.camera_service import CameraService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def bus() -> EventBus:
    b = EventBus(maxsize=500, max_workers=2, name="test-camera-bus")
    yield b
    b.shutdown(timeout=3.0)


@pytest.fixture
def camera(bus: EventBus) -> CameraService:
    # Use index 99 to guarantee physical failure and force Mock Fallback
    srv = CameraService(
        event_bus=bus,
        camera_index=99,
        resolution=(320, 240),
        fps=60,
        auto_reconnect=True,
        reconnect_delay=0.1,
        use_mock_fallback=True,
    )
    yield srv
    srv.shutdown()


# ===========================================================================
# 1. Lifecycle & Fallback Initialization
# ===========================================================================


class TestCameraLifecycle:
    def test_mock_fallback_initialization(self, camera: CameraService) -> None:
        init_ok = camera.initialize()
        assert init_ok is True
        assert camera.is_connected() is True
        assert camera.health()["is_mock"] is True

    def test_start_stop_lifecycles(self, bus: EventBus, camera: CameraService) -> None:
        started_event = None
        stopped_event = None
        done_start = threading.Event()
        done_stop = threading.Event()

        bus.subscribe(
            lambda e: [setattr(TestCameraLifecycle, "started_event", e), done_start.set()],
            EventType.CAMERA_STARTED,
            source="test-spy",
        )
        bus.subscribe(
            lambda e: [setattr(TestCameraLifecycle, "stopped_event", e), done_stop.set()],
            EventType.CAMERA_STOPPED,
            source="test-spy",
        )

        camera.start()
        assert camera.is_running() is True

        assert done_start.wait(timeout=2.0)
        assert TestCameraLifecycle.started_event is not None

        camera.stop()
        assert camera.is_running() is False
        assert camera.is_connected() is False

        assert done_stop.wait(timeout=2.0)
        assert TestCameraLifecycle.stopped_event is not None


# ===========================================================================
# 2. Frame Capture Loop
# ===========================================================================


class TestFrameCapture:
    def test_frame_captured_published(self, bus: EventBus, camera: CameraService) -> None:
        captured_frames: list[EventEnvelope] = []
        done = threading.Event()

        def on_frame(event: EventEnvelope) -> None:
            captured_frames.append(event)
            if len(captured_frames) >= 3:
                done.set()

        bus.subscribe(on_frame, EventType.FRAME_CAPTURED, source="test-spy")

        camera.start()
        assert done.wait(timeout=4.0), f"Captured only {len(captured_frames)} frames"

        camera.stop()

        # Check payload
        payload = captured_frames[0].payload
        assert isinstance(payload, CameraPayload)
        assert payload.resolution == "320x240"
        assert payload.frame_data is not None
        assert len(payload.frame_data) > 0  # JPEG encoded data present


# ===========================================================================
# 3. Queue Overflow & Discard Policy
# ===========================================================================


class TestQueueOverflow:
    def test_dropped_frames_under_load(self, bus: EventBus) -> None:
        # Create a tiny bus queue so that it overflows when a subscriber is slow
        tiny_bus = EventBus(maxsize=1, overflow_drop=True, overflow_timeout=0.001)
        
        # Add a blocking subscriber to cause queue build-up
        blocking_event = threading.Event()
        def blocking_handler(event: EventEnvelope) -> None:
            blocking_event.wait(timeout=2.0)

        tiny_bus.subscribe(blocking_handler, EventType.FRAME_CAPTURED, source="slow-consumer")

        srv = CameraService(
            event_bus=tiny_bus,
            camera_index=98,
            resolution=(160, 120),
            fps=100,  # Fast capture to flood the queue
            use_mock_fallback=True,
        )

        try:
            srv.start()
            time.sleep(0.5)  # Let it capture and fail to publish
            srv.stop()

            blocking_event.set()  # release the blocking subscriber
            diag = srv.diagnostics()
            assert diag["frames_dropped"] > 0
            print(f"\n[Queue drop] Dropped frames: {diag['frames_dropped']}")
        finally:
            blocking_event.set()
            tiny_bus.shutdown()


# ===========================================================================
# 4. Auto-Reconnection & Recovery
# ===========================================================================


class TestAutoReconnect:
    def test_reconnect_lifecycle_emissions(self, bus: EventBus, camera: CameraService) -> None:
        disconnected = threading.Event()
        reconnected = threading.Event()

        bus.subscribe(lambda _: disconnected.set(), EventType.CAMERA_DISCONNECTED, source="spy")
        bus.subscribe(lambda _: reconnected.set(), EventType.CAMERA_RECONNECTED, source="spy")

        camera.start()
        time.sleep(0.1)

        # Force a simulated connection failure
        camera._handle_read_failure()

        assert disconnected.wait(timeout=3.0)
        assert reconnected.wait(timeout=3.0)
        assert camera.is_connected() is True
        assert camera.diagnostics()["reconnect_count"] >= 1


# ===========================================================================
# 5. Thread Safety
# ===========================================================================


class TestThreadSafety:
    def test_concurrent_start_stop(self, camera: CameraService) -> None:
        errors: list[Exception] = []

        def worker() -> None:
            try:
                for _ in range(5):
                    camera.start()
                    time.sleep(0.01)
                    camera.stop()
                    time.sleep(0.01)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors


# ===========================================================================
# 6. Benchmarks
# ===========================================================================


class TestBenchmarks:
    N = 1000

    def test_capture_overhead_latency(self, camera: CameraService) -> None:
        camera.initialize()

        t0 = time.perf_counter()
        for _ in range(self.N):
            ret, frame = camera._read_frame()

        elapsed_ms = (time.perf_counter() - t0) * 1000
        avg_ms = elapsed_ms / self.N

        print(
            f"\n[Benchmark] Camera capture read: {elapsed_ms:.1f} ms for {self.N} frames "
            f"(avg {avg_ms:.2f} ms/frame)"
        )
        # Average capture overhead should be < 2 ms on fallback mock matrix generation
        assert avg_ms < 2.0
