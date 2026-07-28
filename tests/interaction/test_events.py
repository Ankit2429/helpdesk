"""
Tests for campus_helpdesk.interaction.events
============================================

Covers:
- EventType enum completeness and value correctness
- EventPriority ordering and comparison
- All payload types: construction, validation, to_dict, from_dict
- EventEnvelope: creation, validation, serialisation, deserialisation,
  hashing, equality, factory helpers, reply chaining
- Round-trip JSON / dict serialisation preserves all fields
- Invalid envelopes and payloads are rejected with clear errors
- Timezone-aware timestamp handling
- UUID generation and validation
- Benchmarks (creation, serialisation, deserialisation latency)
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import pytest

from campus_helpdesk.interaction.events import (
    EVENT_PAYLOAD_MAP,
    EVENT_SCHEMA_VERSION,
    AnswerPayload,
    AnyPayload,
    ErrorPayload,
    EventEnvelope,
    EventPriority,
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
    WarningPayload,
    CameraPayload,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SESSION = str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _make_system_payload(**kw: Any) -> SystemPayload:
    return SystemPayload(
        profile=kw.get("profile", "development"),
        message=kw.get("message", "System starting"),
        services_healthy=kw.get("services_healthy", None),
    )


def _make_envelope(
    event_type: EventType = EventType.SYSTEM_STARTING,
    payload: AnyPayload | None = None,
    **kw: Any,
) -> EventEnvelope:
    if payload is None:
        payload = _make_system_payload()
    return EventEnvelope.create(
        event_type=event_type,
        source=kw.get("source", "test_service"),
        payload=payload,
        session_id=kw.get("session_id", _SESSION),
    )


# ===========================================================================
# 1. EventType enum
# ===========================================================================


class TestEventTypeEnum:
    """Validate the EventType enum definition."""

    REQUIRED_MEMBERS = {
        "SYSTEM_STARTING",
        "SYSTEM_READY",
        "SYSTEM_SHUTDOWN",
        "PERSON_DETECTED",
        "PERSON_LEFT",
        "VOICE_STARTED",
        "VOICE_STOPPED",
        "TRANSCRIPT_PARTIAL",
        "TRANSCRIPT_FINAL",
        "QUERY_STARTED",
        "QUERY_COMPLETED",
        "ANSWER_READY",
        "TTS_STARTED",
        "TTS_COMPLETED",
        "TTS_INTERRUPTED",
        "SESSION_STARTED",
        "SESSION_ENDED",
        "ERROR",
        "WARNING",
        "TIMEOUT",
    }

    def test_all_required_members_present(self) -> None:
        actual = {m.name for m in EventType}
        missing = self.REQUIRED_MEMBERS - actual
        assert not missing, f"Missing EventType members: {missing}"

    def test_member_count_matches_payload_map(self) -> None:
        """Every EventType must have an entry in EVENT_PAYLOAD_MAP."""
        mapped = set(EVENT_PAYLOAD_MAP)
        for et in EventType:
            assert et in mapped, f"EventType.{et.name} has no entry in EVENT_PAYLOAD_MAP"

    def test_values_are_strings(self) -> None:
        for et in EventType:
            assert isinstance(et.value, str), f"{et.name}.value should be str"

    def test_value_equals_name(self) -> None:
        """Enum values are the string version of their name (upper-snake-case)."""
        for et in EventType:
            assert et.value == et.name

    def test_lookup_by_value(self) -> None:
        assert EventType("PERSON_DETECTED") is EventType.PERSON_DETECTED

    def test_unknown_value_raises(self) -> None:
        with pytest.raises(ValueError):
            EventType("NOT_AN_EVENT")

    def test_is_str_subclass(self) -> None:
        assert isinstance(EventType.SYSTEM_READY, str)


# ===========================================================================
# 2. EventPriority enum
# ===========================================================================


class TestEventPriority:
    def test_members_present(self) -> None:
        for name in ("LOW", "NORMAL", "HIGH", "CRITICAL"):
            assert hasattr(EventPriority, name)

    def test_ordering(self) -> None:
        assert EventPriority.LOW < EventPriority.NORMAL
        assert EventPriority.NORMAL < EventPriority.HIGH
        assert EventPriority.HIGH < EventPriority.CRITICAL

    def test_values_are_int(self) -> None:
        for ep in EventPriority:
            assert isinstance(ep.value, int)

    def test_default_is_normal(self) -> None:
        env = _make_envelope()
        assert env.priority is EventPriority.NORMAL


# ===========================================================================
# 3. Payload types
# ===========================================================================


class TestSystemPayload:
    def test_basic_construction(self) -> None:
        p = SystemPayload(profile="standalone_robot", message="booting")
        assert p.profile == "standalone_robot"
        assert p.message == "booting"
        assert p.services_healthy is None

    def test_with_services_healthy(self) -> None:
        p = SystemPayload(profile="dev", message="ready", services_healthy=7)
        assert p.services_healthy == 7

    def test_frozen(self) -> None:
        p = SystemPayload(profile="dev", message="x")
        with pytest.raises(Exception):
            p.profile = "changed"  # type: ignore[misc]

    def test_round_trip_dict(self) -> None:
        p = SystemPayload(profile="edge", message="shutdown", services_healthy=3)
        assert SystemPayload.from_dict(p.to_dict()) == p


class TestPersonDetectedPayload:
    def test_basic(self) -> None:
        p = PersonDetectedPayload(confidence=0.85)
        assert p.confidence == 0.85
        assert p.camera_index == 0
        assert p.bounding_box is None

    def test_with_bbox(self) -> None:
        p = PersonDetectedPayload(confidence=0.9, bounding_box=(10, 20, 100, 200))
        assert p.bounding_box == (10, 20, 100, 200)

    def test_confidence_out_of_range_high(self) -> None:
        with pytest.raises(ValueError, match="confidence"):
            PersonDetectedPayload(confidence=1.1)

    def test_confidence_out_of_range_low(self) -> None:
        with pytest.raises(ValueError, match="confidence"):
            PersonDetectedPayload(confidence=-0.1)

    def test_negative_camera_index(self) -> None:
        with pytest.raises(ValueError, match="camera_index"):
            PersonDetectedPayload(confidence=0.5, camera_index=-1)

    def test_invalid_bbox_length(self) -> None:
        with pytest.raises(ValueError, match="bounding_box"):
            PersonDetectedPayload(confidence=0.5, bounding_box=(1, 2, 3))  # type: ignore[arg-type]

    def test_round_trip_dict(self) -> None:
        p = PersonDetectedPayload(confidence=0.76, camera_index=1, bounding_box=(5, 10, 50, 80))
        assert PersonDetectedPayload.from_dict(p.to_dict()) == p

    def test_round_trip_no_bbox(self) -> None:
        p = PersonDetectedPayload(confidence=0.6)
        assert PersonDetectedPayload.from_dict(p.to_dict()) == p

    def test_confidence_boundary_values(self) -> None:
        # Exact bounds should not raise
        PersonDetectedPayload(confidence=0.0)
        PersonDetectedPayload(confidence=1.0)


class TestPersonLeftPayload:
    def test_basic(self) -> None:
        ts = _now()
        p = PersonLeftPayload(last_seen_at=ts, frames_without_detection=5)
        assert p.frames_without_detection == 5

    def test_naive_timestamp_rejected(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            PersonLeftPayload(
                last_seen_at=datetime(2026, 1, 1),  # naive
                frames_without_detection=1,
            )

    def test_negative_frames_rejected(self) -> None:
        with pytest.raises(ValueError, match="frames_without_detection"):
            PersonLeftPayload(last_seen_at=_now(), frames_without_detection=-1)

    def test_round_trip(self) -> None:
        p = PersonLeftPayload(last_seen_at=_now(), frames_without_detection=10)
        assert PersonLeftPayload.from_dict(p.to_dict()) == p


class TestVoicePayload:
    def test_basic(self) -> None:
        p = VoicePayload(audio_chunk_id="chunk-1")
        assert p.duration_ms == 0
        assert p.audio_segment_path is None
        assert p.sample_rate == 16_000

    def test_with_path(self) -> None:
        p = VoicePayload(
            audio_chunk_id="chunk-2",
            duration_ms=2500,
            audio_segment_path="/tmp/audio.wav",
        )
        assert p.audio_segment_path == "/tmp/audio.wav"

    def test_empty_chunk_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="audio_chunk_id"):
            VoicePayload(audio_chunk_id="")

    def test_negative_duration_rejected(self) -> None:
        with pytest.raises(ValueError, match="duration_ms"):
            VoicePayload(audio_chunk_id="c", duration_ms=-1)

    def test_zero_sample_rate_rejected(self) -> None:
        with pytest.raises(ValueError, match="sample_rate"):
            VoicePayload(audio_chunk_id="c", sample_rate=0)

    def test_round_trip(self) -> None:
        p = VoicePayload(
            audio_chunk_id="abc",
            duration_ms=1200,
            audio_segment_path="/data/audio.wav",
            sample_rate=22_050,
        )
        assert VoicePayload.from_dict(p.to_dict()) == p


class TestTranscriptPayload:
    def test_basic(self) -> None:
        p = TranscriptPayload(
            text="hello world",
            is_final=True,
            audio_chunk_id="c1",
        )
        assert p.language == "en"
        assert p.confidence is None

    def test_with_confidence(self) -> None:
        p = TranscriptPayload(
            text="test",
            is_final=False,
            audio_chunk_id="c2",
            confidence=0.93,
        )
        assert p.confidence == pytest.approx(0.93)

    def test_invalid_confidence(self) -> None:
        with pytest.raises(ValueError, match="confidence"):
            TranscriptPayload(
                text="x", is_final=True, audio_chunk_id="c", confidence=1.5
            )

    def test_empty_chunk_id(self) -> None:
        with pytest.raises(ValueError, match="audio_chunk_id"):
            TranscriptPayload(text="x", is_final=True, audio_chunk_id="")

    def test_negative_duration(self) -> None:
        with pytest.raises(ValueError, match="duration_ms"):
            TranscriptPayload(
                text="x", is_final=True, audio_chunk_id="c", duration_ms=-5
            )

    def test_round_trip_with_confidence(self) -> None:
        p = TranscriptPayload(
            text="where is the library",
            is_final=True,
            audio_chunk_id="c-99",
            confidence=0.88,
            duration_ms=3200,
            language="en",
        )
        assert TranscriptPayload.from_dict(p.to_dict()) == p

    def test_round_trip_no_confidence(self) -> None:
        p = TranscriptPayload(text="hello", is_final=False, audio_chunk_id="c0")
        assert TranscriptPayload.from_dict(p.to_dict()) == p


class TestQueryPayload:
    def test_basic(self) -> None:
        p = QueryPayload(query="Where is the library?")
        assert p.chunks_retrieved == 0
        assert p.confidence_score is None

    def test_blank_query_rejected(self) -> None:
        with pytest.raises(ValueError, match="query"):
            QueryPayload(query="   ")

    def test_negative_chunks(self) -> None:
        with pytest.raises(ValueError, match="chunks_retrieved"):
            QueryPayload(query="q", chunks_retrieved=-1)

    def test_invalid_confidence(self) -> None:
        with pytest.raises(ValueError, match="confidence_score"):
            QueryPayload(query="q", confidence_score=1.5)

    def test_round_trip(self) -> None:
        p = QueryPayload(
            query="What are library timings?",
            chunks_retrieved=8,
            retrieval_duration_ms=420,
            confidence_score=0.81,
        )
        assert QueryPayload.from_dict(p.to_dict()) == p


class TestAnswerPayload:
    def test_basic(self) -> None:
        p = AnswerPayload(
            answer="The library is on Block C.",
            confidence_score=0.9,
            confidence_level="HIGH",
            sources=("library_information.md",),
            query="Where is the library?",
        )
        assert p.sources == ("library_information.md",)

    def test_blank_answer_rejected(self) -> None:
        with pytest.raises(ValueError, match="answer"):
            AnswerPayload(
                answer="  ",
                confidence_score=0.9,
                confidence_level="HIGH",
                sources=(),
                query="q",
            )

    def test_invalid_confidence_level(self) -> None:
        with pytest.raises(ValueError, match="confidence_level"):
            AnswerPayload(
                answer="A",
                confidence_score=0.5,
                confidence_level="VERY_HIGH",
                sources=(),
                query="q",
            )

    def test_confidence_score_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="confidence_score"):
            AnswerPayload(
                answer="A",
                confidence_score=-0.1,
                confidence_level="LOW",
                sources=(),
                query="q",
            )

    def test_blank_query_rejected(self) -> None:
        with pytest.raises(ValueError, match="query"):
            AnswerPayload(
                answer="A",
                confidence_score=0.5,
                confidence_level="MEDIUM",
                sources=(),
                query="",
            )

    @pytest.mark.parametrize("level", ["HIGH", "MEDIUM", "LOW"])
    def test_valid_confidence_levels(self, level: str) -> None:
        p = AnswerPayload(
            answer="Valid answer text.",
            confidence_score=0.6,
            confidence_level=level,
            sources=("src.md",),
            query="q",
        )
        assert p.confidence_level == level

    def test_round_trip(self) -> None:
        p = AnswerPayload(
            answer="Library is on floor 2.",
            confidence_score=0.75,
            confidence_level="MEDIUM",
            sources=("lib.md", "campus.md"),
            query="Where?",
            inference_duration_ms=1800,
        )
        assert AnswerPayload.from_dict(p.to_dict()) == p


class TestTTSPayload:
    def test_basic(self) -> None:
        p = TTSPayload(text="Hello!", voice_model="en_US-lessac-medium")
        assert p.duration_ms == 0
        assert p.interrupted_at_ms is None

    def test_blank_text_rejected(self) -> None:
        with pytest.raises(ValueError, match="text"):
            TTSPayload(text="", voice_model="model")

    def test_blank_voice_model_rejected(self) -> None:
        with pytest.raises(ValueError, match="voice_model"):
            TTSPayload(text="hello", voice_model="  ")

    def test_negative_duration_rejected(self) -> None:
        with pytest.raises(ValueError, match="duration_ms"):
            TTSPayload(text="x", voice_model="m", duration_ms=-1)

    def test_negative_interrupted_at_ms_rejected(self) -> None:
        with pytest.raises(ValueError, match="interrupted_at_ms"):
            TTSPayload(text="x", voice_model="m", interrupted_at_ms=-5)

    def test_round_trip_with_interruption(self) -> None:
        p = TTSPayload(
            text="The library opens at 9 AM.",
            voice_model="en_US-lessac-medium",
            duration_ms=3000,
            interrupted_at_ms=1200,
        )
        assert TTSPayload.from_dict(p.to_dict()) == p

    def test_round_trip_no_interruption(self) -> None:
        p = TTSPayload(text="Done.", voice_model="model", duration_ms=500)
        assert TTSPayload.from_dict(p.to_dict()) == p


class TestSessionPayload:
    def test_basic(self) -> None:
        p = SessionPayload(reason="person_detected")
        assert p.turns == 0

    def test_blank_reason_rejected(self) -> None:
        with pytest.raises(ValueError, match="reason"):
            SessionPayload(reason="")

    def test_negative_turns_rejected(self) -> None:
        with pytest.raises(ValueError, match="turns"):
            SessionPayload(reason="x", turns=-1)

    def test_round_trip(self) -> None:
        p = SessionPayload(reason="person_left", turns=3)
        assert SessionPayload.from_dict(p.to_dict()) == p


class TestErrorPayload:
    def test_basic(self) -> None:
        p = ErrorPayload(
            service="stt_service",
            error_type="WhisperTimeoutError",
            message="Whisper did not respond",
        )
        assert not p.is_fatal
        assert p.traceback is None

    def test_fatal_flag(self) -> None:
        p = ErrorPayload(
            service="health_monitor",
            error_type="CriticalFailure",
            message="All services down",
            is_fatal=True,
        )
        assert p.is_fatal

    def test_blank_service_rejected(self) -> None:
        with pytest.raises(ValueError, match="service"):
            ErrorPayload(service="", error_type="E", message="m")

    def test_blank_error_type_rejected(self) -> None:
        with pytest.raises(ValueError, match="error_type"):
            ErrorPayload(service="s", error_type="", message="m")

    def test_blank_message_rejected(self) -> None:
        with pytest.raises(ValueError, match="message"):
            ErrorPayload(service="s", error_type="E", message="  ")

    def test_round_trip_with_traceback(self) -> None:
        p = ErrorPayload(
            service="rag_service",
            error_type="TimeoutError",
            message="LLM timed out",
            is_fatal=False,
            traceback="Traceback...\nline 42",
        )
        assert ErrorPayload.from_dict(p.to_dict()) == p


class TestWarningPayload:
    def test_basic(self) -> None:
        p = WarningPayload(
            service="health_monitor",
            metric="cpu_percent",
            value=82.5,
            threshold=80.0,
            message="CPU above threshold",
        )
        assert p.value == pytest.approx(82.5)

    def test_blank_service_rejected(self) -> None:
        with pytest.raises(ValueError, match="service"):
            WarningPayload(service="", metric="m", value=1, threshold=0, message="x")

    def test_round_trip(self) -> None:
        p = WarningPayload(
            service="health_monitor",
            metric="queue_depth",
            value=55.0,
            threshold=50.0,
            message="Queue is deep",
        )
        assert WarningPayload.from_dict(p.to_dict()) == p


class TestTimeoutPayload:
    def test_basic(self) -> None:
        p = TimeoutPayload(state="PROCESSING", timeout_duration_ms=8000, elapsed_ms=8001)
        assert p.state == "PROCESSING"

    def test_blank_state_rejected(self) -> None:
        with pytest.raises(ValueError, match="state"):
            TimeoutPayload(state="  ", timeout_duration_ms=1000, elapsed_ms=1001)

    def test_zero_timeout_rejected(self) -> None:
        with pytest.raises(ValueError, match="timeout_duration_ms"):
            TimeoutPayload(state="PROCESSING", timeout_duration_ms=0, elapsed_ms=0)

    def test_negative_elapsed_rejected(self) -> None:
        with pytest.raises(ValueError, match="elapsed_ms"):
            TimeoutPayload(state="PROCESSING", timeout_duration_ms=1000, elapsed_ms=-1)

    def test_round_trip(self) -> None:
        p = TimeoutPayload(state="LISTENING", timeout_duration_ms=10_000, elapsed_ms=10_001)
        assert TimeoutPayload.from_dict(p.to_dict()) == p


class TestCameraPayload:
    def test_basic(self) -> None:
        p = CameraPayload(
            frame_id="frame-123",
            timestamp=_now(),
            resolution="1280x720",
            frame_number=10,
            capture_latency_ms=1.5,
            frame_data=b"dummy",
        )
        assert p.frame_number == 10
        assert p.frame_data == b"dummy"

    def test_invalid_fields_rejected(self) -> None:
        with pytest.raises(ValueError, match="frame_id"):
            CameraPayload(
                frame_id="",
                timestamp=_now(),
                resolution="1280x720",
                frame_number=1,
                capture_latency_ms=1.0,
            )
        with pytest.raises(ValueError, match="timezone-aware"):
            CameraPayload(
                frame_id="id",
                timestamp=datetime(2026, 1, 1),
                resolution="1280x720",
                frame_number=1,
                capture_latency_ms=1.0,
            )

    def test_round_trip_omits_frame_data(self) -> None:
        p = CameraPayload(
            frame_id="frame-uuid",
            timestamp=_now(),
            resolution="640x480",
            frame_number=42,
            capture_latency_ms=0.8,
            frame_data=b"image-bytes",
        )
        d = p.to_dict()
        assert "frame_data" not in d
        restored = CameraPayload.from_dict(d)
        assert restored.frame_id == p.frame_id
        assert restored.frame_data is None


# ===========================================================================
# 4. EventEnvelope – construction and validation
# ===========================================================================


class TestEventEnvelopeConstruction:
    def test_basic_creation_via_factory(self) -> None:
        env = _make_envelope()
        assert env.event_type is EventType.SYSTEM_STARTING
        assert env.source == "test_service"
        assert env.version == EVENT_SCHEMA_VERSION
        assert env.priority is EventPriority.NORMAL

    def test_auto_event_id_is_uuid4(self) -> None:
        env = _make_envelope()
        parsed = uuid.UUID(env.event_id)
        assert parsed.version == 4

    def test_event_ids_are_unique(self) -> None:
        ids = {_make_envelope().event_id for _ in range(100)}
        assert len(ids) == 100

    def test_timestamp_is_utc(self) -> None:
        env = _make_envelope()
        assert env.timestamp.tzinfo is not None
        assert env.timestamp.tzinfo == timezone.utc

    def test_timestamp_is_recent(self) -> None:
        before = _now()
        env = _make_envelope()
        after = _now()
        assert before <= env.timestamp <= after

    def test_blank_source_rejected(self) -> None:
        with pytest.raises(ValueError, match="source"):
            EventEnvelope(
                event_type=EventType.SYSTEM_STARTING,
                source="  ",
                payload=_make_system_payload(),
            )

    def test_naive_timestamp_rejected(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            EventEnvelope(
                event_type=EventType.SYSTEM_STARTING,
                source="svc",
                payload=_make_system_payload(),
                timestamp=datetime(2026, 1, 1),  # naive
            )

    def test_invalid_uuid_rejected(self) -> None:
        with pytest.raises(ValueError, match="UUID"):
            EventEnvelope(
                event_type=EventType.SYSTEM_STARTING,
                source="svc",
                payload=_make_system_payload(),
                event_id="not-a-uuid",
            )

    def test_wrong_payload_type_rejected(self) -> None:
        """Envelope should reject mismatched payload types."""
        with pytest.raises(TypeError, match="payload"):
            EventEnvelope.create(
                event_type=EventType.PERSON_DETECTED,
                source="svc",
                payload=_make_system_payload(),  # wrong type
            )

    def test_correct_payload_type_accepted(self) -> None:
        env = EventEnvelope.create(
            event_type=EventType.PERSON_DETECTED,
            source="camera_service",
            payload=PersonDetectedPayload(confidence=0.9),
        )
        assert env.event_type is EventType.PERSON_DETECTED

    def test_invalid_correlation_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="correlation_id"):
            EventEnvelope(
                event_type=EventType.SYSTEM_STARTING,
                source="svc",
                payload=_make_system_payload(),
                correlation_id="not-a-uuid",
            )

    def test_valid_correlation_id_accepted(self) -> None:
        parent_id = str(uuid.uuid4())
        env = EventEnvelope.create(
            event_type=EventType.SYSTEM_READY,
            source="svc",
            payload=_make_system_payload(message="ready"),
            correlation_id=parent_id,
        )
        assert env.correlation_id == parent_id

    def test_uuid_version_1_rejected(self) -> None:
        """Only UUID4 is accepted for event_id."""
        v1 = str(uuid.uuid1())
        with pytest.raises(ValueError, match="version 4"):
            EventEnvelope(
                event_type=EventType.SYSTEM_STARTING,
                source="svc",
                payload=_make_system_payload(),
                event_id=v1,
            )


# ===========================================================================
# 5. EventEnvelope – hashing and equality
# ===========================================================================


class TestEventEnvelopeHashingAndEquality:
    def test_two_identical_envelopes_are_equal(self) -> None:
        ts = _now()
        eid = str(uuid.uuid4())
        payload = _make_system_payload()
        a = EventEnvelope(
            event_type=EventType.SYSTEM_STARTING,
            source="svc",
            payload=payload,
            event_id=eid,
            timestamp=ts,
        )
        b = EventEnvelope(
            event_type=EventType.SYSTEM_STARTING,
            source="svc",
            payload=payload,
            event_id=eid,
            timestamp=ts,
        )
        assert a == b

    def test_different_event_ids_not_equal(self) -> None:
        ts = _now()
        payload = _make_system_payload()
        a = EventEnvelope(
            event_type=EventType.SYSTEM_STARTING,
            source="svc",
            payload=payload,
            event_id=str(uuid.uuid4()),
            timestamp=ts,
        )
        b = EventEnvelope(
            event_type=EventType.SYSTEM_STARTING,
            source="svc",
            payload=payload,
            event_id=str(uuid.uuid4()),
            timestamp=ts,
        )
        assert a != b

    def test_envelope_is_hashable(self) -> None:
        env = _make_envelope()
        s = {env}
        assert env in s

    def test_envelope_usable_as_dict_key(self) -> None:
        env = _make_envelope()
        d = {env: "processed"}
        assert d[env] == "processed"

    def test_set_deduplication(self) -> None:
        """Inserting the same envelope twice results in one set member."""
        ts = _now()
        eid = str(uuid.uuid4())
        payload = _make_system_payload()

        def _make() -> EventEnvelope:
            return EventEnvelope(
                event_type=EventType.SYSTEM_STARTING,
                source="svc",
                payload=payload,
                event_id=eid,
                timestamp=ts,
            )

        s = {_make(), _make()}
        assert len(s) == 1


# ===========================================================================
# 6. Serialisation – to_dict / from_dict / to_json / from_json
# ===========================================================================


class TestEventEnvelopeSerialisation:
    def _full_envelope(self) -> EventEnvelope:
        return EventEnvelope.create(
            event_type=EventType.SYSTEM_STARTING,
            source="engine",
            payload=SystemPayload(profile="standalone_robot", message="booting", services_healthy=0),
            session_id=_SESSION,
            priority=EventPriority.HIGH,
            metadata={"deployment_profile": "standalone_robot", "pi_model": "pi5"},
        )

    def test_to_dict_contains_all_keys(self) -> None:
        d = self._full_envelope().to_dict()
        expected_keys = {
            "event_id",
            "event_type",
            "source",
            "session_id",
            "correlation_id",
            "timestamp",
            "priority",
            "payload_type",
            "payload",
            "metadata",
            "version",
        }
        assert expected_keys.issubset(d.keys())

    def test_to_dict_event_type_is_string(self) -> None:
        d = self._full_envelope().to_dict()
        assert isinstance(d["event_type"], str)
        assert d["event_type"] == "SYSTEM_STARTING"

    def test_to_dict_priority_is_int(self) -> None:
        d = self._full_envelope().to_dict()
        assert isinstance(d["priority"], int)

    def test_to_dict_timestamp_is_iso_string(self) -> None:
        d = self._full_envelope().to_dict()
        ts = datetime.fromisoformat(d["timestamp"])
        assert ts.tzinfo is not None

    def test_round_trip_dict(self) -> None:
        env = self._full_envelope()
        restored = EventEnvelope.from_dict(env.to_dict())
        assert restored == env

    def test_round_trip_json(self) -> None:
        env = self._full_envelope()
        restored = EventEnvelope.from_json(env.to_json())
        assert restored == env

    def test_json_is_valid(self) -> None:
        raw = self._full_envelope().to_json()
        parsed = json.loads(raw)
        assert isinstance(parsed, dict)

    def test_json_indented(self) -> None:
        raw = self._full_envelope().to_json(indent=2)
        assert "\n" in raw

    def test_metadata_preserved_round_trip(self) -> None:
        env = self._full_envelope()
        restored = EventEnvelope.from_dict(env.to_dict())
        assert restored.get_metadata() == {"deployment_profile": "standalone_robot", "pi_model": "pi5"}

    def test_session_id_preserved(self) -> None:
        env = self._full_envelope()
        restored = EventEnvelope.from_dict(env.to_dict())
        assert restored.session_id == _SESSION

    def test_version_preserved(self) -> None:
        env = self._full_envelope()
        d = env.to_dict()
        assert d["version"] == EVENT_SCHEMA_VERSION
        restored = EventEnvelope.from_dict(d)
        assert restored.version == EVENT_SCHEMA_VERSION

    def test_unknown_payload_type_raises(self) -> None:
        d = self._full_envelope().to_dict()
        d["payload_type"] = "GhostPayload"
        with pytest.raises(ValueError, match="Unknown payload_type"):
            EventEnvelope.from_dict(d)

    def test_unknown_event_type_raises(self) -> None:
        d = self._full_envelope().to_dict()
        d["event_type"] = "BANANA_DETECTED"
        with pytest.raises(ValueError):
            EventEnvelope.from_dict(d)

    def test_missing_event_type_raises(self) -> None:
        d = self._full_envelope().to_dict()
        del d["event_type"]
        with pytest.raises(KeyError):
            EventEnvelope.from_dict(d)

    @pytest.mark.parametrize(
        "event_type, payload",
        [
            (EventType.PERSON_DETECTED, PersonDetectedPayload(confidence=0.85)),
            (EventType.PERSON_LEFT, PersonLeftPayload(last_seen_at=_now(), frames_without_detection=3)),
            (EventType.VOICE_STARTED, VoicePayload(audio_chunk_id="c1")),
            (EventType.VOICE_STOPPED, VoicePayload(audio_chunk_id="c2", duration_ms=2000, audio_segment_path="/tmp/a.wav")),
            (EventType.TRANSCRIPT_FINAL, TranscriptPayload(text="hello", is_final=True, audio_chunk_id="c3")),
            (EventType.QUERY_STARTED, QueryPayload(query="What time?")),
            (EventType.ANSWER_READY, AnswerPayload(answer="9 AM.", confidence_score=0.9, confidence_level="HIGH", sources=("lib.md",), query="q")),
            (EventType.TTS_STARTED, TTSPayload(text="Hello!", voice_model="model")),
            (EventType.SESSION_STARTED, SessionPayload(reason="person_detected")),
            (EventType.ERROR, ErrorPayload(service="svc", error_type="E", message="oops")),
            (EventType.WARNING, WarningPayload(service="h", metric="cpu", value=85.0, threshold=80.0, message="high")),
            (EventType.TIMEOUT, TimeoutPayload(state="PROCESSING", timeout_duration_ms=8000, elapsed_ms=8001)),
            (EventType.FRAME_CAPTURED, CameraPayload(frame_id="fid", timestamp=_now(), resolution="1280x720", frame_number=5, capture_latency_ms=1.2, frame_data=None)),
        ],
    )
    def test_round_trip_all_event_types(
        self, event_type: EventType, payload: AnyPayload
    ) -> None:
        env = EventEnvelope.create(
            event_type=event_type,
            source="test_service",
            payload=payload,
            session_id=_SESSION,
        )
        restored = EventEnvelope.from_json(env.to_json())
        assert restored == env


# ===========================================================================
# 7. Factory helpers and reply chaining
# ===========================================================================


class TestEventEnvelopeFactories:
    def test_create_generates_event_id(self) -> None:
        env = EventEnvelope.create(
            event_type=EventType.SYSTEM_READY,
            source="manager",
            payload=_make_system_payload(message="ready"),
        )
        assert uuid.UUID(env.event_id).version == 4

    def test_with_metadata_returns_new_envelope(self) -> None:
        env = _make_envelope()
        enriched = env.with_metadata(foo="bar", profile="pi5")
        assert enriched is not env
        assert enriched.get_metadata() == {"foo": "bar", "profile": "pi5"}
        assert env.get_metadata() == {}  # original unchanged

    def test_with_metadata_merges_existing(self) -> None:
        env = EventEnvelope.create(
            event_type=EventType.SYSTEM_STARTING,
            source="svc",
            payload=_make_system_payload(),
            metadata={"a": "1"},
        )
        enriched = env.with_metadata(b="2")
        assert enriched.get_metadata() == {"a": "1", "b": "2"}

    def test_reply_sets_correlation_id(self) -> None:
        parent = _make_envelope(session_id=_SESSION)
        child = parent.reply(
            event_type=EventType.SYSTEM_READY,
            source="manager",
            payload=_make_system_payload(message="ready"),
        )
        assert child.correlation_id == parent.event_id

    def test_reply_inherits_session_id(self) -> None:
        parent = _make_envelope(session_id=_SESSION)
        child = parent.reply(
            event_type=EventType.SYSTEM_READY,
            source="manager",
            payload=_make_system_payload(message="ready"),
        )
        assert child.session_id == _SESSION

    def test_reply_different_event_id(self) -> None:
        parent = _make_envelope()
        child = parent.reply(
            event_type=EventType.SYSTEM_READY,
            source="manager",
            payload=_make_system_payload(message="ready"),
        )
        assert child.event_id != parent.event_id

    def test_create_with_priority(self) -> None:
        env = EventEnvelope.create(
            event_type=EventType.ERROR,
            source="monitor",
            payload=ErrorPayload(service="s", error_type="E", message="Fatal"),
            priority=EventPriority.CRITICAL,
        )
        assert env.priority is EventPriority.CRITICAL


# ===========================================================================
# 8. Timezone handling
# ===========================================================================


class TestTimezoneHandling:
    def test_auto_timestamp_is_utc(self) -> None:
        env = _make_envelope()
        assert env.timestamp.tzinfo == timezone.utc

    def test_isoformat_preserves_utc_offset(self) -> None:
        env = _make_envelope()
        d = env.to_dict()
        ts_str: str = d["timestamp"]
        # ISO format for UTC includes +00:00 or Z
        restored = datetime.fromisoformat(ts_str)
        assert restored.tzinfo is not None

    def test_round_trip_preserves_timestamp(self) -> None:
        env = _make_envelope()
        restored = EventEnvelope.from_dict(env.to_dict())
        assert restored.timestamp == env.timestamp

    def test_person_left_naive_timestamp_rejected(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            PersonLeftPayload(
                last_seen_at=datetime(2026, 7, 28, 12, 0, 0),
                frames_without_detection=3,
            )


# ===========================================================================
# 9. Schema version
# ===========================================================================


class TestSchemaVersion:
    def test_default_version(self) -> None:
        env = _make_envelope()
        assert env.version == "1.0"

    def test_schema_constant_value(self) -> None:
        assert EVENT_SCHEMA_VERSION == "1.0"

    def test_version_in_dict(self) -> None:
        d = _make_envelope().to_dict()
        assert d["version"] == "1.0"

    def test_version_survives_round_trip(self) -> None:
        env = _make_envelope()
        restored = EventEnvelope.from_json(env.to_json())
        assert restored.version == env.version


# ===========================================================================
# 10. Immutability
# ===========================================================================


class TestImmutability:
    def test_envelope_is_frozen(self) -> None:
        env = _make_envelope()
        with pytest.raises(Exception):
            env.source = "modified"  # type: ignore[misc]

    def test_payload_is_frozen(self) -> None:
        p = SystemPayload(profile="dev", message="x")
        with pytest.raises(Exception):
            p.profile = "changed"  # type: ignore[misc]

    def test_metadata_tuple_immutable(self) -> None:
        env = _make_envelope()
        assert isinstance(env.metadata, tuple)

    def test_answer_sources_are_tuple(self) -> None:
        p = AnswerPayload(
            answer="A",
            confidence_score=0.8,
            confidence_level="HIGH",
            sources=("a.md", "b.md"),
            query="q",
        )
        assert isinstance(p.sources, tuple)


# ===========================================================================
# 11. Benchmarks
# ===========================================================================


class TestBenchmarks:
    """Light benchmarks – document approximate latencies.

    These tests always pass; they print timing data to stdout so that CI logs
    capture performance regressions over time.
    """

    N = 1_000

    def _make_full_payload(self) -> AnswerPayload:
        return AnswerPayload(
            answer="The Central Library is located on Block C, Second Floor.",
            confidence_score=0.92,
            confidence_level="HIGH",
            sources=("library_information.md", "campus_map.md"),
            query="Where is the Central Library?",
            inference_duration_ms=1250,
        )

    def test_event_creation_latency(self) -> None:
        payload = self._make_full_payload()
        t0 = time.perf_counter()
        for _ in range(self.N):
            EventEnvelope.create(
                event_type=EventType.ANSWER_READY,
                source="rag_service",
                payload=payload,
                session_id=_SESSION,
            )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        avg_us = (elapsed_ms / self.N) * 1000
        print(
            f"\n[Benchmark] EventEnvelope creation: "
            f"{elapsed_ms:.1f} ms for {self.N} events "
            f"(avg {avg_us:.1f} µs/event)"
        )
        # Sanity: must complete in < 5 s on any reasonable machine
        assert elapsed_ms < 5_000

    def test_serialisation_latency(self) -> None:
        payload = self._make_full_payload()
        env = EventEnvelope.create(
            event_type=EventType.ANSWER_READY,
            source="rag_service",
            payload=payload,
            session_id=_SESSION,
        )
        t0 = time.perf_counter()
        for _ in range(self.N):
            env.to_json()
        elapsed_ms = (time.perf_counter() - t0) * 1000
        avg_us = (elapsed_ms / self.N) * 1000
        print(
            f"\n[Benchmark] EventEnvelope.to_json: "
            f"{elapsed_ms:.1f} ms for {self.N} events "
            f"(avg {avg_us:.1f} µs/event)"
        )
        assert elapsed_ms < 5_000

    def test_deserialisation_latency(self) -> None:
        payload = self._make_full_payload()
        env = EventEnvelope.create(
            event_type=EventType.ANSWER_READY,
            source="rag_service",
            payload=payload,
            session_id=_SESSION,
        )
        raw = env.to_json()
        t0 = time.perf_counter()
        for _ in range(self.N):
            EventEnvelope.from_json(raw)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        avg_us = (elapsed_ms / self.N) * 1000
        print(
            f"\n[Benchmark] EventEnvelope.from_json: "
            f"{elapsed_ms:.1f} ms for {self.N} events "
            f"(avg {avg_us:.1f} µs/event)"
        )
        assert elapsed_ms < 5_000

    def test_memory_footprint_reasonable(self) -> None:
        """Creating 10 000 envelopes should not exhaust memory on any target device."""
        payload = self._make_full_payload()
        envelopes = [
            EventEnvelope.create(
                event_type=EventType.ANSWER_READY,
                source="rag_service",
                payload=payload,
                session_id=_SESSION,
            )
            for _ in range(10_000)
        ]
        # If we got here without MemoryError, the test passes.
        assert len(envelopes) == 10_000
        print(f"\n[Benchmark] Created 10 000 EventEnvelope instances without error.")
