"""
Tests for campus_helpdesk.services.inference_adapter
===================================================

Coverage:
1.  Mock backend operations
2.  Service start, stop, shutdown lifecycle transitions
3.  Query starts, completed processing, and publishing of ANSWER_READY
4.  Timeout configurations and error recovery (emitting ERROR)
5.  Edge cases (empty transcript, backend exception)
6.  FIFO worker queue sequential processing under load
7.  Queue and adapter processing overhead benchmarks (< 5 ms)
"""

from __future__ import annotations

import time
import uuid
import threading
import pytest

from campus_helpdesk.interaction.event_bus import EventBus
from campus_helpdesk.interaction.events import (
    AnswerPayload,
    ErrorPayload,
    EventEnvelope,
    EventType,
    QueryPayload,
    TranscriptPayload,
)
from campus_helpdesk.services.inference_adapter import (
    InferenceAdapter,
    MockInferenceBackend,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_transcript_event(text: str, chunk_id: str) -> EventEnvelope:
    return EventEnvelope.create(
        event_type=EventType.TRANSCRIPT_FINAL,
        source="stt",
        payload=TranscriptPayload(
            text=text,
            is_final=True,
            language="en",
            confidence=0.95,
            duration_ms=1200,
            audio_chunk_id=chunk_id,
        ),
        session_id="session-456",
    )


@pytest.fixture
def bus() -> EventBus:
    b = EventBus(maxsize=1000, max_workers=2, name="test-inference-bus")
    yield b
    b.shutdown(timeout=3.0)


@pytest.fixture
def mock_backend() -> MockInferenceBackend:
    return MockInferenceBackend()


@pytest.fixture
def adapter(bus: EventBus, mock_backend: MockInferenceBackend) -> InferenceAdapter:
    srv = InferenceAdapter(
        event_bus=bus,
        backend=mock_backend,
        timeout_seconds=0.5,  # Shorten for fast timeout testing
        name="test-inference-adapter",
    )
    yield srv
    srv.shutdown()


# ===========================================================================
# 1. Backend & Lifecycle
# ===========================================================================


class TestInferenceLifecycle:
    def test_mock_backend_query(self, mock_backend: MockInferenceBackend) -> None:
        ans, cites, conf, level = mock_backend.query("where is library", "session-1")
        assert ans == "The central library is open from 8 AM to 8 PM."
        assert cites == ["library_rules.md", "campus_map.pdf"]
        assert conf == 0.92
        assert level == "HIGH"

    def test_start_stop_subscribes(self, bus: EventBus, adapter: InferenceAdapter) -> None:
        assert adapter.is_running() is False
        adapter.start()
        assert adapter.is_running() is True

        subs = bus.registered_subscribers()
        assert subs.get("TRANSCRIPT_FINAL", 0) == 1

        adapter.stop()
        assert adapter.is_running() is False
        subs = bus.registered_subscribers()
        assert subs.get("TRANSCRIPT_FINAL", 0) == 0


# ===========================================================================
# 2. Event Routing & Output Generation
# ===========================================================================


class TestInferenceEventRouting:
    def test_happy_path_emits_query_started_and_answer_ready(
        self, bus: EventBus, adapter: InferenceAdapter
    ) -> None:
        started_events: list[EventEnvelope] = []
        ready_events: list[EventEnvelope] = []
        done_start = threading.Event()
        done_ready = threading.Event()

        bus.subscribe(
            lambda e: [started_events.append(e), done_start.set()],
            EventType.QUERY_STARTED,
            source="spy",
        )
        bus.subscribe(
            lambda e: [ready_events.append(e), done_ready.set()],
            EventType.ANSWER_READY,
            source="spy",
        )

        adapter.start()
        bus.publish_sync(_make_transcript_event("Where is the library?", "chunk-111"))

        assert done_start.wait(timeout=3.0)
        assert len(started_events) == 1
        assert started_events[0].payload.query == "Where is the library?"

        assert done_ready.wait(timeout=3.0)
        assert len(ready_events) == 1
        
        payload = ready_events[0].payload
        assert isinstance(payload, AnswerPayload)
        assert "central library" in payload.answer
        assert payload.confidence_score == 0.92
        assert payload.confidence_level == "HIGH"
        assert "library_rules.md" in payload.sources
        assert payload.inference_duration_ms > 0.0

    def test_empty_transcript_publishes_error(
        self, bus: EventBus, adapter: InferenceAdapter
    ) -> None:
        errors: list[EventEnvelope] = []
        done = threading.Event()

        bus.subscribe(
            lambda e: [errors.append(e), done.set()],
            EventType.ERROR,
            source="spy",
        )

        adapter.start()
        bus.publish_sync(_make_transcript_event("   ", "chunk-empty"))

        assert done.wait(timeout=3.0)
        assert len(errors) == 1
        assert errors[0].payload.error_type == "InvalidTranscriptError"

    def test_backend_exception_publishes_error(
        self, bus: EventBus, adapter: InferenceAdapter, mock_backend: MockInferenceBackend
    ) -> None:
        errors: list[EventEnvelope] = []
        done = threading.Event()

        bus.subscribe(
            lambda e: [errors.append(e), done.set()],
            EventType.ERROR,
            source="spy",
        )

        mock_backend.should_fail = True
        adapter.start()
        bus.publish_sync(_make_transcript_event("How to register?", "chunk-fail"))

        assert done.wait(timeout=3.0)
        assert len(errors) == 1
        assert errors[0].payload.error_type == "InferenceBackendError"
        assert "Database connection" in errors[0].payload.message


# ===========================================================================
# 3. Timeout Recovery
# ===========================================================================


class TestInferenceTimeouts:
    def test_query_timeout_publishes_error(
        self, bus: EventBus, adapter: InferenceAdapter, mock_backend: MockInferenceBackend
    ) -> None:
        errors: list[EventEnvelope] = []
        done = threading.Event()

        bus.subscribe(
            lambda e: [errors.append(e), done.set()],
            EventType.ERROR,
            source="spy",
        )

        # Force backend query delay longer than the adapter's 0.5s limit
        mock_backend.simulate_delay_sec = 0.8
        adapter.start()
        bus.publish_sync(_make_transcript_event("Slow query", "chunk-slow"))

        assert done.wait(timeout=3.0)
        assert len(errors) == 1
        assert errors[0].payload.error_type == "InferenceTimeoutError"


# ===========================================================================
# 4. FIFO Queue Ordering
# ===========================================================================


class TestFIFOQueue:
    def test_sequential_processing_under_load(
        self, bus: EventBus, adapter: InferenceAdapter
    ) -> None:
        processed_queries: list[str] = []
        done = threading.Event()

        bus.subscribe(
            lambda e: [processed_queries.append(e.payload.query), done.set() if len(processed_queries) >= 5 else None],
            EventType.ANSWER_READY,
            source="spy",
        )

        adapter.start()

        # Send 5 events in quick succession
        for i in range(5):
            bus.publish(_make_transcript_event(f"Query {i}", f"chunk-{i}"))

        assert done.wait(timeout=5.0)
        assert len(processed_queries) == 5
        # Verify FIFO order
        assert processed_queries == [f"Query {i}" for i in range(5)]


# ===========================================================================
# 5. Benchmarks
# ===========================================================================


class TestBenchmarks:
    N = 1000

    def test_queue_and_adapter_overhead(self, bus: EventBus, mock_backend: MockInferenceBackend) -> None:
        # Benchmark overhead by bypassing delays
        mock_backend.simulate_delay_sec = 0.0
        
        srv = InferenceAdapter(event_bus=bus, backend=mock_backend, timeout_seconds=1.0)
        srv.start()

        t0 = time.perf_counter()
        for i in range(self.N):
            bus.publish(_make_transcript_event(f"Bench {i}", f"chunk-{i}"))

        # Wait for all items to complete
        while srv.diagnostics()["requests_processed"] < self.N:
            time.sleep(0.01)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        avg_ms = elapsed_ms / self.N

        srv.shutdown()

        print(
            f"\n[Benchmark] Inference Adapter Overhead: {elapsed_ms:.1f} ms for {self.N} requests "
            f"(avg {avg_ms:.3f} ms/request)"
        )
        # Bounded adapter/queue overhead must be < 5.0 ms/request
        assert avg_ms < 5.0
