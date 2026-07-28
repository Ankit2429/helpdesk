"""
Tests for campus_helpdesk.services.vad_service
==============================================

Coverage:
1.  VADService initialization and Mock Microphone fallback
2.  Service start, stop, shutdown lifecycle transitions
3.  WebRTC VAD classification logic validation
4.  Debouncing logic (speech_frames_threshold=3, silence_frames_threshold=5)
5.  Event publication (VOICE_STARTED, VOICE_STOPPED, files written)
6.  Thread safety of start / stop
7.  Latency benchmarks (VAD processing overhead < 5 ms/frame)
"""

from __future__ import annotations

import os
import time
import uuid
import threading
import pytest
import numpy as np

from campus_helpdesk.interaction.event_bus import EventBus
from campus_helpdesk.interaction.events import EventEnvelope, EventType, VoicePayload
from campus_helpdesk.services.vad_service import VADService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def bus() -> EventBus:
    b = EventBus(maxsize=1000, max_workers=2, name="test-vad-bus")
    yield b
    b.shutdown(timeout=3.0)


@pytest.fixture
def vad(bus: EventBus) -> VADService:
    # Index 99 selects a non-existent audio index, forcing Mock Fallback
    srv = VADService(
        event_bus=bus,
        sample_rate=16000,
        frame_duration_ms=30,
        aggressiveness=2,
        speech_frames_threshold=3,
        silence_frames_threshold=5,
        device_index=99,
        use_mock_fallback=True,
    )
    yield srv
    srv.shutdown()


# ===========================================================================
# 1. Lifecycle & Fallback Initialization
# ===========================================================================


class TestVADLifecycle:
    def test_mock_fallback_lifecycle(self, bus: EventBus, vad: VADService) -> None:
        assert vad.is_running() is False
        assert vad.is_speaking() is False

        done_started = threading.Event()
        done_stopped = threading.Event()

        bus.subscribe(lambda _: done_started.set(), EventType.MICROPHONE_STARTED, source="spy")
        bus.subscribe(lambda _: done_stopped.set(), EventType.MICROPHONE_STOPPED, source="spy")

        vad.start()
        assert vad.is_running() is True
        assert vad.health()["is_mock"] is True

        assert done_started.wait(timeout=2.0)

        vad.stop()
        assert vad.is_running() is False
        assert done_stopped.wait(timeout=2.0)


# ===========================================================================
# 2. VAD Debouncing & Segment Saving
# ===========================================================================


class TestVADDebouncing:
    def test_speech_onset_and_offset_events(
        self, bus: EventBus, vad: VADService
    ) -> None:
        started_events: list[EventEnvelope] = []
        stopped_events: list[EventEnvelope] = []
        done_start = threading.Event()
        done_stop = threading.Event()

        bus.subscribe(
            lambda e: [started_events.append(e), done_start.set()],
            EventType.VOICE_STARTED,
            source="spy",
        )
        bus.subscribe(
            lambda e: [stopped_events.append(e), done_stop.set()],
            EventType.VOICE_STOPPED,
            source="spy",
        )

        # Generate mock audio arrays
        # Speaking frame: 400Hz high amplitude sine wave
        t = np.arange(480) / 16000.0
        speaking_frame = (np.sin(2 * np.pi * 400.0 * t) * 12000).astype(np.int16).tobytes()

        # Silent frame: flat zeros (webrtcvad classifies this deterministically as silence)
        silent_frame = np.zeros(480, dtype=np.int16).tobytes()

        # Start ONLY the worker thread to bypass mock mic loop ingestion
        vad._running = True
        vad._stop_event.clear()
        vad._worker = threading.Thread(
            target=vad._worker_loop,
            name=f"{vad._name}-worker",
            daemon=True,
        )
        vad._worker.start()

        # Send 2 speech frames (threshold is 3) -> should not trigger start
        vad._queue.put(speaking_frame)
        vad._queue.put(speaking_frame)
        time.sleep(0.2)
        print(f"DEBUG: after 2 speech frames, is_speaking={vad.is_speaking()}, speech_count={vad._consecutive_speech}")
        assert len(started_events) == 0

        # Send 3rd speech frame -> should trigger VOICE_STARTED
        vad._queue.put(speaking_frame)
        time.sleep(0.2)
        print(f"DEBUG: after 3 speech frames, is_speaking={vad.is_speaking()}, speech_count={vad._consecutive_speech}")
        assert len(started_events) == 1
        assert vad.is_speaking() is True

        # Send 4th speech frame -> duplicate check, should NOT publish another start event
        vad._queue.put(speaking_frame)
        time.sleep(0.2)
        assert len(started_events) == 1

        # Now send silence frames to trigger VOICE_STOPPED (threshold is 5)
        # WebRTC VAD is adaptive and stateful: after a high-amplitude speech segment,
        # its internal noise floor estimator takes 3-4 frames to decay and register silence.
        # We send 9 silence frames to cover decay + 5 consecutive silence threshold.
        for idx in range(9):
            vad._queue.put(silent_frame)
            time.sleep(0.02)
        
        assert done_stop.wait(timeout=3.0)
        assert len(stopped_events) == 1
        assert vad.is_speaking() is False

        # Validate voice stopped payload details
        payload = stopped_events[0].payload
        assert isinstance(payload, VoicePayload)
        # Total buffered frames should include the speech segment frames and the silence decay frames
        assert payload.duration_ms > 0
        assert payload.audio_segment_path is not None
        assert os.path.exists(payload.audio_segment_path)

        # Cleanup wav
        if os.path.exists(payload.audio_segment_path):
            os.remove(payload.audio_segment_path)


# ===========================================================================
# 3. Thread Safety
# ===========================================================================


class TestThreadSafety:
    def test_concurrent_start_stop(self, vad: VADService) -> None:
        errors: list[Exception] = []

        def worker() -> None:
            try:
                for _ in range(3):
                    vad.start()
                    time.sleep(0.01)
                    vad.stop()
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
# 4. Benchmarks
# ===========================================================================


class TestBenchmarks:
    N = 1000

    def test_vad_processing_latency(self, vad: VADService) -> None:
        # Generate raw 30ms mono 16kHz frames (480 samples, 960 bytes)
        frame = np.zeros(480, dtype=np.int16).tobytes()

        t0 = time.perf_counter()
        for _ in range(self.N):
            vad._classify_frame(frame)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        avg_ms = elapsed_ms / self.N

        print(
            f"\n[Benchmark] VAD classification: {elapsed_ms:.1f} ms for {self.N} frames "
            f"(avg {avg_ms:.3f} ms/frame)"
        )
        # Average VAD classification latency must be < 5.0 ms/frame (WebRTC VAD typically takes < 0.1 ms)
        assert avg_ms < 5.0
