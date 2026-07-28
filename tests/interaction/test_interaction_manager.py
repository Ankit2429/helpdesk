"""
Tests for campus_helpdesk.interaction.interaction_manager
==========================================================

Coverage:
1.  Normal Interaction Flow lifecycle (BOOT -> ... -> IDLE)
2.  State validation (unexpected events ignored in wrong states)
3.  Context updates (session_id, correlation_id, etc.)
4.  Event publishing validation (QUERY_STARTED published, SESSION_ENDED, etc.)
5.  State timeouts recovery handling (READY -> IDLE, SPEAKING -> READY, etc.)
6.  Error recovery handling (Fatal error -> ERROR transition)
7.  Diagnostics API verification
8.  Thread safety stress test (concurrent events)
9.  Benchmarks (average handling latency < 100 µs)
"""

from __future__ import annotations

import time
import uuid
import threading
from typing import Any

import pytest

from campus_helpdesk.interaction.event_bus import EventBus
from campus_helpdesk.interaction.events import (
    AnswerPayload,
    ErrorPayload,
    EventEnvelope,
    EventType,
    PersonDetectedPayload,
    PersonLeftPayload,
    QueryPayload,
    SessionPayload,
    SystemPayload,
    TimeoutPayload,
    TranscriptPayload,
    TTSPayload,
    VoicePayload,
)
from campus_helpdesk.interaction.robot_state import RobotState, RobotStateMachine
from campus_helpdesk.interaction.interaction_manager import InteractionManager

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def bus() -> EventBus:
    b = EventBus(maxsize=1000, max_workers=2, name="test-manager-bus")
    yield b
    b.shutdown(timeout=3.0)


@pytest.fixture
def fsm() -> RobotStateMachine:
    return RobotStateMachine(initial_state=RobotState.BOOTING)


@pytest.fixture
def manager(bus: EventBus, fsm: RobotStateMachine) -> InteractionManager:
    im = InteractionManager(event_bus=bus, state_machine=fsm, name="TestManager")
    yield im
    im.shutdown()


# ===========================================================================
# 1. Normal Interaction Flow
# ===========================================================================


class TestNormalInteractionFlow:
    def test_complete_interaction_sequence(
        self, bus: EventBus, fsm: RobotStateMachine, manager: InteractionManager
    ) -> None:
        assert fsm.state is RobotState.BOOTING

        # 1. SYSTEM_READY -> INITIALIZING -> IDLE
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.SYSTEM_READY,
                source="test",
                payload=SystemPayload(profile="dev", message="boot ready"),
            ),
            timeout=3.0,
        )
        assert fsm.state is RobotState.IDLE

        # 2. PERSON_DETECTED -> READY
        session_event = None
        done = threading.Event()

        def capture_session_start(event: EventEnvelope) -> None:
            nonlocal session_event
            session_event = event
            done.set()

        bus.subscribe(
            capture_session_start, EventType.SESSION_STARTED, source="test-spy"
        )

        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.PERSON_DETECTED,
                source="camera_service",
                payload=PersonDetectedPayload(confidence=0.9),
            ),
            timeout=3.0,
        )
        assert fsm.state is RobotState.READY
        assert done.wait(timeout=2.0)
        assert session_event is not None
        assert manager.current_session() is not None

        # 3. VOICE_STARTED -> LISTENING
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.VOICE_STARTED,
                source="vad_service",
                payload=VoicePayload(audio_chunk_id="chunk-1"),
                session_id=manager.current_session(),
            ),
            timeout=3.0,
        )
        assert fsm.state is RobotState.LISTENING

        # 4. VOICE_STOPPED -> PROCESSING
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.VOICE_STOPPED,
                source="vad_service",
                payload=VoicePayload(audio_chunk_id="chunk-1", duration_ms=1000),
                session_id=manager.current_session(),
            ),
            timeout=3.0,
        )
        assert fsm.state is RobotState.PROCESSING

        # 5. TRANSCRIPT_FINAL -> Publish QUERY_STARTED
        query_started_event = None
        done_q = threading.Event()

        def capture_query_start(event: EventEnvelope) -> None:
            nonlocal query_started_event
            query_started_event = event
            done_q.set()

        bus.subscribe(
            capture_query_start, EventType.QUERY_STARTED, source="test-spy"
        )

        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.TRANSCRIPT_FINAL,
                source="stt_service",
                payload=TranscriptPayload(
                    text="where library", is_final=True, audio_chunk_id="chunk-1"
                ),
                session_id=manager.current_session(),
            ),
            timeout=3.0,
        )
        assert fsm.state is RobotState.PROCESSING
        assert done_q.wait(timeout=2.0)
        assert query_started_event is not None
        assert query_started_event.payload.query == "where library"

        # 6. QUERY_COMPLETED (Middle pipeline check) -> State stays PROCESSING
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.QUERY_COMPLETED,
                source="rag_service",
                payload=QueryPayload(query="where library", chunks_retrieved=2),
                session_id=manager.current_session(),
            ),
            timeout=3.0,
        )
        assert fsm.state is RobotState.PROCESSING

        # 7. ANSWER_READY -> SPEAKING
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.ANSWER_READY,
                source="rag_service",
                payload=AnswerPayload(
                    answer="block c",
                    confidence_score=0.9,
                    confidence_level="HIGH",
                    sources=(),
                    query="where library",
                ),
                session_id=manager.current_session(),
            ),
            timeout=3.0,
        )
        assert fsm.state is RobotState.SPEAKING

        # 8. TTS_COMPLETED -> READY
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.TTS_COMPLETED,
                source="tts_service",
                payload=TTSPayload(text="block c", voice_model="m"),
                session_id=manager.current_session(),
            ),
            timeout=3.0,
        )
        assert fsm.state is RobotState.READY

        # 9. PERSON_LEFT -> IDLE + SESSION_ENDED
        done_e = threading.Event()
        session_ended_event = None

        def capture_session_end(event: EventEnvelope) -> None:
            nonlocal session_ended_event
            session_ended_event = event
            done_e.set()

        bus.subscribe(
            capture_session_end, EventType.SESSION_ENDED, source="test-spy"
        )

        from datetime import timezone, datetime
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.PERSON_LEFT,
                source="camera_service",
                payload=PersonLeftPayload(last_seen_at=datetime.now(timezone.utc), frames_without_detection=10),
                session_id=manager.current_session(),
            ),
            timeout=3.0,
        )
        assert fsm.state is RobotState.IDLE
        assert done_e.wait(timeout=2.0)
        assert session_ended_event is not None
        assert manager.current_session() is None


# ===========================================================================
# 2. State Validation (Ignore unexpected events)
# ===========================================================================


class TestStateValidation:
    def test_ignores_invalid_events_for_state(
        self, bus: EventBus, fsm: RobotStateMachine, manager: InteractionManager
    ) -> None:
        # FSM is in BOOTING. An incoming TTS_COMPLETED is invalid.
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.TTS_COMPLETED,
                source="tts",
                payload=TTSPayload(text="hi", voice_model="m"),
            ),
            timeout=3.0,
        )
        assert fsm.state is RobotState.BOOTING

        # Change state to IDLE
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.SYSTEM_READY,
                source="test",
                payload=SystemPayload(profile="dev", message="boot ready"),
            ),
            timeout=3.0,
        )
        assert fsm.state is RobotState.IDLE

        # IDLE receives VOICE_STARTED -> invalid, ignore
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.VOICE_STARTED,
                source="vad",
                payload=VoicePayload(audio_chunk_id="chunk"),
            ),
            timeout=3.0,
        )
        assert fsm.state is RobotState.IDLE


# ===========================================================================
# 3. Timeout Recovery
# ===========================================================================


class TestTimeouts:
    def test_ready_timeout_recovers_to_idle(
        self, bus: EventBus, fsm: RobotStateMachine, manager: InteractionManager
    ) -> None:
        # Move to READY
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.SYSTEM_READY,
                source="test",
                payload=SystemPayload(profile="dev", message="ready"),
            ),
            timeout=3.0,
        )
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.PERSON_DETECTED,
                source="camera",
                payload=PersonDetectedPayload(confidence=0.9),
            ),
            timeout=3.0,
        )
        assert fsm.state is RobotState.READY

        # Configure short timeout (1 millisecond) for test checking
        fsm.configure_timeout(RobotState.READY, 0.001)

        # Wait for the monitor thread to detect it and publish TIMEOUT
        done = threading.Event()
        bus.subscribe(
            lambda _: done.set(), EventType.SESSION_ENDED, source="test-spy"
        )

        assert done.wait(timeout=5.0), "Timeout recovery failed to trigger"
        assert fsm.state is RobotState.IDLE
        assert manager.current_session() is None

    def test_processing_timeout_recovers_to_ready(
        self, bus: EventBus, fsm: RobotStateMachine, manager: InteractionManager
    ) -> None:
        # Move to PROCESSING
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.SYSTEM_READY,
                source="test",
                payload=SystemPayload(profile="dev", message="ready"),
            ),
            timeout=3.0,
        )
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.PERSON_DETECTED,
                source="camera",
                payload=PersonDetectedPayload(confidence=0.9),
            ),
            timeout=3.0,
        )
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.VOICE_STARTED,
                source="vad",
                payload=VoicePayload(audio_chunk_id="chunk"),
                session_id=manager.current_session(),
            ),
            timeout=3.0,
        )
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.VOICE_STOPPED,
                source="vad",
                payload=VoicePayload(audio_chunk_id="chunk"),
                session_id=manager.current_session(),
            ),
            timeout=3.0,
        )
        assert fsm.state is RobotState.PROCESSING

        # Configure short processing timeout
        fsm.configure_timeout(RobotState.PROCESSING, 0.001)

        # Wait for FSM state reset back to READY
        time.sleep(1.0)
        assert fsm.state is RobotState.READY
        # Session should still exist (recoverable timeout)
        assert manager.current_session() is not None


# ===========================================================================
# 4. Error Handling
# ===========================================================================


class TestErrorHandling:
    def test_fatal_error_moves_to_error_state(
        self, bus: EventBus, fsm: RobotStateMachine, manager: InteractionManager
    ) -> None:
        # Publish a non-fatal error -> FSM should stay in BOOTING
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.ERROR,
                source="stt",
                payload=ErrorPayload(
                    service="stt", error_type="E", message="non-fatal", is_fatal=False
                ),
            ),
            timeout=3.0,
        )
        assert fsm.state is RobotState.BOOTING

        # Publish a fatal error -> FSM transitions to ERROR
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.ERROR,
                source="stt",
                payload=ErrorPayload(
                    service="stt", error_type="E", message="fatal crash", is_fatal=True
                ),
            ),
            timeout=3.0,
        )
        assert fsm.state is RobotState.ERROR


# ===========================================================================
# 5. Diagnostics & Context
# ===========================================================================


class TestDiagnosticsAndContext:
    def test_diagnostics_and_context(
        self, bus: EventBus, fsm: RobotStateMachine, manager: InteractionManager
    ) -> None:
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.SYSTEM_READY,
                source="test",
                payload=SystemPayload(profile="dev", message="ready"),
            ),
            timeout=3.0,
        )
        assert manager.current_state() is RobotState.IDLE
        assert manager.event_count() == 1
        assert manager.uptime() >= 0.0
        assert manager.last_event() is not None

        ctx = manager.current_context()
        assert "session_id" in ctx
        assert "correlation_id" in ctx


# ===========================================================================
# 6. Stress Testing & Thread Safety
# ===========================================================================


class TestStressAndThreadSafety:
    def test_concurrent_event_flooding(
        self, bus: EventBus, fsm: RobotStateMachine, manager: InteractionManager
    ) -> None:
        # Setup FSM in READY
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.SYSTEM_READY,
                source="test",
                payload=SystemPayload(profile="dev", message="ready"),
            ),
            timeout=3.0,
        )
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.PERSON_DETECTED,
                source="camera",
                payload=PersonDetectedPayload(confidence=0.9),
            ),
            timeout=3.0,
        )
        assert fsm.state is RobotState.READY

        # Flood the manager with conflicting, simultaneous lifecycle events
        # from multiple threads.
        errors: list[Exception] = []

        def worker(et: EventType, payload: Any) -> None:
            try:
                bus.publish(
                    EventEnvelope.create(
                        event_type=et,
                        source="stress-thread",
                        payload=payload,
                        session_id=manager.current_session(),
                    )
                )
            except Exception as exc:
                errors.append(exc)

        from datetime import timezone, datetime
        threads = [
            threading.Thread(
                target=worker,
                args=(
                    EventType.VOICE_STARTED,
                    VoicePayload(audio_chunk_id="c"),
                ),
            ),
            threading.Thread(
                target=worker,
                args=(
                    EventType.PERSON_LEFT,
                    PersonLeftPayload(last_seen_at=datetime.now(timezone.utc), frames_without_detection=1),
                ),
            ),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # FSM state must cleanly transition to one of the allowed destination states
        assert fsm.state in {RobotState.LISTENING, RobotState.IDLE}
        assert not errors


# ===========================================================================
# 7. Benchmarks
# ===========================================================================


class TestBenchmarks:
    N = 5000

    def test_handling_latency(
        self, bus: EventBus, fsm: RobotStateMachine, manager: InteractionManager
    ) -> None:
        # FSM starts in READY
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.SYSTEM_READY,
                source="test",
                payload=SystemPayload(profile="dev", message="ready"),
            ),
            timeout=3.0,
        )
        bus.publish_sync(
            EventEnvelope.create(
                event_type=EventType.PERSON_DETECTED,
                source="camera",
                payload=PersonDetectedPayload(confidence=0.9),
            ),
            timeout=3.0,
        )

        # Measure direct overhead of manager.handle_event()
        event = EventEnvelope.create(
            event_type=EventType.VOICE_STARTED,
            source="vad",
            payload=VoicePayload(audio_chunk_id="chunk"),
            session_id=manager.current_session(),
        )

        t0 = time.perf_counter()
        for _ in range(self.N):
            # Explicitly call handle_event directly to isolate manager code processing time
            manager.handle_event(event)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        avg_us = (elapsed_ms / self.N) * 1000

        print(
            f"\n[Benchmark] Manager event processing: {elapsed_ms:.1f} ms for {self.N} events "
            f"(avg {avg_us:.2f} µs/event)"
        )
        assert avg_us < 100.0, f"Average event processing time {avg_us:.2f} µs exceeds 100 µs target"
