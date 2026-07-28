"""
Campus Helpdesk Robot – Phase 3: Core Event System
===================================================

Module: campus_helpdesk.interaction.events
File:   src/campus_helpdesk/interaction/events.py
Version: 1.0

This module defines the complete, strongly-typed, immutable event model for
the Real-Time Interaction Engine.  Every inter-service communication in the
robot runtime travels as an :class:`EventEnvelope` containing a typed payload.

Design goals
------------
* **Strongly typed** – every event carries a concrete payload dataclass; no
  raw ``dict`` payloads in production paths.
* **Immutable** – all envelope and payload types are frozen dataclasses so
  they can be safely shared across threads without locking.
* **Hashable** – envelopes can be stored in sets and used as dict keys,
  enabling efficient deduplication in the event bus.
* **Thread-safe** – frozen dataclasses provide structural immutability;
  UUID generation and timestamp creation use the standard library, which is
  thread-safe on all CPython versions.
* **Serialisable** – full round-trip support via ``to_dict`` / ``from_dict``
  / ``to_json`` / ``from_json``.
* **Versioned** – every envelope carries a schema version string so that
  consumers can gracefully handle future schema additions.
* **Self-documenting** – every :class:`EventType` value carries docstring
  metadata describing its producer, consumers, and expected payload type.

Architecture position
---------------------
::

    Hardware Adapters          (camera, mic, speaker)
            │
            ▼
    Services                   (camera_service, vad_service, …)
            │
            ▼
    ┌──────────────────┐
    │   EVENT BUS      │  ← consumes EventEnvelope objects defined here
    └──────────────────┘
            │
            ▼
    Interaction Manager (FSM)

Changelog
---------
* 1.0 (2026-07-28) – Initial implementation for Task 12.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, unique
from typing import Any

# ---------------------------------------------------------------------------
# Schema version – bump MINOR for additive changes, MAJOR for breaking ones.
# ---------------------------------------------------------------------------
EVENT_SCHEMA_VERSION: str = "1.0"


# ---------------------------------------------------------------------------
# EventType
# ---------------------------------------------------------------------------


@unique
class EventType(str, Enum):
    """Canonical set of events that flow through the Interaction Engine bus.

    Every value is a plain string so that events can be serialised to JSON
    without a custom encoder and deserialized without the enum module being
    imported by the consumer.

    **Naming convention**: ``<DOMAIN>_<VERB>`` in upper-snake-case.

    Each member's docstring documents:

    * **Producer** – which service emits this event.
    * **Consumers** – which services subscribe to this event.
    * **Payload** – the expected payload type.
    """

    # ---- System lifecycle --------------------------------------------------

    SYSTEM_STARTING = "SYSTEM_STARTING"
    """Emitted once during bootstrap before any service is ready.

    Producer:  ``engine.py`` (bootstrap)
    Consumers: ``logging_service``, ``metrics_service``, ``ui_service``
    Payload:   :class:`SystemPayload`
    """

    SYSTEM_READY = "SYSTEM_READY"
    """Emitted when all services have passed their health checks and the FSM
    enters the IDLE state.

    Producer:  ``interaction_manager``
    Consumers: ``ui_service``, ``logging_service``, ``health_monitor``
    Payload:   :class:`SystemPayload`
    """

    SYSTEM_SHUTDOWN = "SYSTEM_SHUTDOWN"
    """Emitted when a graceful shutdown is requested (SIGTERM / admin command).

    Producer:  ``interaction_manager``
    Consumers: all services
    Payload:   :class:`SystemPayload`
    """

    # ---- Person detection --------------------------------------------------

    PERSON_DETECTED = "PERSON_DETECTED"
    """A person has appeared in the camera frame with sufficient confidence.

    The camera service applies a debounce window of ≥1 s between repeated
    emissions of this event to prevent rapid toggling.

    Producer:  ``camera_service``
    Consumers: ``interaction_manager``, ``ui_service``
    Payload:   :class:`PersonDetectedPayload`
    """

    PERSON_LEFT = "PERSON_LEFT"
    """No person has been detected for the configured leave-timeout period.

    Producer:  ``camera_service``
    Consumers: ``interaction_manager``, ``ui_service``
    Payload:   :class:`PersonLeftPayload`
    """

    # ---- Voice activity ----------------------------------------------------

    VOICE_STARTED = "VOICE_STARTED"
    """Voice Activity Detection (VAD) has detected the onset of speech.

    The VAD service buffers audio from this point until :data:`VOICE_STOPPED`.

    Producer:  ``vad_service``
    Consumers: ``interaction_manager``, ``ui_service``
    Payload:   :class:`VoicePayload`
    """

    VOICE_STOPPED = "VOICE_STOPPED"
    """VAD has detected the end of a speech segment (silence timeout elapsed).

    The payload includes the path of the buffered audio segment file that the
    STT service should transcribe.

    Producer:  ``vad_service``
    Consumers: ``interaction_manager``, ``stt_service``
    Payload:   :class:`VoicePayload`
    """

    # ---- Speech-to-text ----------------------------------------------------

    TRANSCRIPT_PARTIAL = "TRANSCRIPT_PARTIAL"
    """An intermediate (streaming) transcript result from Faster-Whisper.

    Partial results are displayed in the UI but not forwarded to the RAG
    pipeline.

    Producer:  ``stt_service``
    Consumers: ``ui_service``
    Payload:   :class:`TranscriptPayload`
    """

    TRANSCRIPT_FINAL = "TRANSCRIPT_FINAL"
    """The final, committed transcript of the user's utterance.

    Triggers the RAG pipeline.

    Producer:  ``stt_service``
    Consumers: ``interaction_manager``, ``rag_service``, ``ui_service``
    Payload:   :class:`TranscriptPayload`
    """

    # ---- RAG pipeline ------------------------------------------------------

    QUERY_STARTED = "QUERY_STARTED"
    """The RAG service has begun processing the user query.

    Used to update the UI ("Searching…") and start latency tracking.

    Producer:  ``rag_service``
    Consumers: ``interaction_manager``, ``ui_service``, ``logging_service``
    Payload:   :class:`QueryPayload`
    """

    QUERY_COMPLETED = "QUERY_COMPLETED"
    """The RAG pipeline (retrieval + reranking + confidence) has finished.

    Emitted immediately before the LLM generation request is dispatched.

    Producer:  ``rag_service``
    Consumers: ``interaction_manager``, ``logging_service``
    Payload:   :class:`QueryPayload`
    """

    ANSWER_READY = "ANSWER_READY"
    """The LLM has generated a final answer and it is ready for playback.

    Triggers TTS synthesis and UI answer display.

    Producer:  ``rag_service``
    Consumers: ``interaction_manager``, ``tts_service``, ``ui_service``
    Payload:   :class:`AnswerPayload`
    """

    # ---- Text-to-speech ----------------------------------------------------

    TTS_STARTED = "TTS_STARTED"
    """Piper TTS has begun synthesising and streaming audio to the speaker.

    Producer:  ``tts_service``
    Consumers: ``interaction_manager``, ``ui_service``
    Payload:   :class:`TTSPayload`
    """

    TTS_COMPLETED = "TTS_COMPLETED"
    """TTS playback has finished naturally.

    Triggers the FSM transition SPEAKING → READY.

    Producer:  ``tts_service``
    Consumers: ``interaction_manager``, ``ui_service``
    Payload:   :class:`TTSPayload`
    """

    TTS_INTERRUPTED = "TTS_INTERRUPTED"
    """TTS playback was interrupted (user began speaking again, or PERSON_LEFT).

    Producer:  ``tts_service``
    Consumers: ``interaction_manager``, ``ui_service``
    Payload:   :class:`TTSPayload`
    """

    # ---- Session lifecycle -------------------------------------------------

    SESSION_STARTED = "SESSION_STARTED"
    """A new conversation session has been assigned a unique session_id.

    Emitted when the FSM transitions from IDLE/READY to LISTENING.

    Producer:  ``interaction_manager``
    Consumers: ``rag_service``, ``logging_service``, ``metrics_service``
    Payload:   :class:`SessionPayload`
    """

    SESSION_ENDED = "SESSION_ENDED"
    """The conversation session has ended (person left or explicit reset).

    Producer:  ``interaction_manager``
    Consumers: ``rag_service``, ``logging_service``, ``metrics_service``
    Payload:   :class:`SessionPayload`
    """

    # ---- Diagnostics -------------------------------------------------------

    ERROR = "ERROR"
    """A recoverable or fatal error has occurred in a service.

    Fatal errors (``is_fatal=True``) trigger an FSM transition to the ERROR
    state.  Non-fatal errors are logged and counted but do not affect the FSM.

    Producer:  any service
    Consumers: ``interaction_manager``, ``logging_service``, ``health_monitor``
    Payload:   :class:`ErrorPayload`
    """

    WARNING = "WARNING"
    """A degraded-but-continuing condition (high CPU, queue depth, etc.).

    Producer:  ``health_monitor``
    Consumers: ``logging_service``, ``metrics_service``
    Payload:   :class:`WarningPayload`
    """

    TIMEOUT = "TIMEOUT"
    """An FSM state has exceeded its configured timeout.

    Emitted by the Interaction Manager's internal timer before executing the
    timeout transition.

    Producer:  ``interaction_manager``
    Consumers: ``interaction_manager``, ``logging_service``
    Payload:   :class:`TimeoutPayload`
    """

    # ---- Camera Streaming & Lifecycle ---------------------------------------

    CAMERA_STARTED = "CAMERA_STARTED"
    """Emitted when the Camera Service starts the background capture loop.

    Producer:  ``camera_service``
    Consumers: ``ui_service``, ``logging_service``
    Payload:   :class:`CameraPayload`
    """

    CAMERA_STOPPED = "CAMERA_STOPPED"
    """Emitted when the Camera Service cleanly stops the capture loop.

    Producer:  ``camera_service``
    Consumers: ``ui_service``, ``logging_service``
    Payload:   :class:`CameraPayload`
    """

    FRAME_CAPTURED = "FRAME_CAPTURED"
    """Emitted when a new frame is successfully acquired.

    Producer:  ``camera_service``
    Consumers: ``person_detector_service``, ``ui_service``
    Payload:   :class:`CameraPayload`
    """

    CAMERA_DISCONNECTED = "CAMERA_DISCONNECTED"
    """Emitted when the camera fails to read and begins auto-reconnect logic.

    Producer:  ``camera_service``
    Consumers: ``interaction_manager``, ``ui_service``
    Payload:   :class:`CameraPayload`
    """

    CAMERA_RECONNECTED = "CAMERA_RECONNECTED"
    """Emitted when the camera successfully re-establishes connection.

    Producer:  ``camera_service``
    Consumers: ``interaction_manager``, ``ui_service``
    Payload:   :class:`CameraPayload`
    """

    CAMERA_ERROR = "CAMERA_ERROR"
    """Emitted on unrecoverable camera hardware or API exceptions.

    Producer:  ``camera_service``
    Consumers: ``interaction_manager``, ``logging_service``
    Payload:   :class:`CameraPayload`
    """


# ---------------------------------------------------------------------------
# Priority
# ---------------------------------------------------------------------------


@unique
class EventPriority(int, Enum):
    """Processing priority for events in the bus queue.

    The event bus processes higher-priority events before lower-priority ones
    when the queue depth is non-trivial.  For the vast majority of events the
    default :attr:`NORMAL` priority is appropriate.

    Values are integers so that direct comparison (``>``, ``<``) works.
    """

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


# ---------------------------------------------------------------------------
# Payload models
# ---------------------------------------------------------------------------
# All payload types are frozen dataclasses so they can be embedded inside a
# frozen EventEnvelope without violating immutability.  Each type provides
# ``to_dict`` / ``from_dict`` helpers that match the envelope's serialisation
# contract.


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(tz=timezone.utc)


@dataclass(frozen=True)
class SystemPayload:
    """Payload for system lifecycle events (:data:`EventType.SYSTEM_STARTING`,
    :data:`EventType.SYSTEM_READY`, :data:`EventType.SYSTEM_SHUTDOWN`).

    Attributes
    ----------
    profile:
        Active deployment profile (e.g. ``"development"``,
        ``"standalone_robot"``, ``"edge_deployment"``).
    message:
        Human-readable description of the system state change.
    services_healthy:
        Number of services that passed their health check at the time of
        emission.  ``None`` for ``SYSTEM_STARTING`` (checks not yet run).
    """

    profile: str
    message: str
    services_healthy: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "message": self.message,
            "services_healthy": self.services_healthy,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SystemPayload":
        return cls(
            profile=str(data["profile"]),
            message=str(data["message"]),
            services_healthy=data.get("services_healthy"),
        )


@dataclass(frozen=True)
class PersonDetectedPayload:
    """Payload for :data:`EventType.PERSON_DETECTED`.

    Attributes
    ----------
    confidence:
        Detection confidence in ``[0.0, 1.0]`` reported by OpenCV model.
    bounding_box:
        ``(x, y, width, height)`` pixel coordinates of the detected person,
        or ``None`` when bounding-box data is unavailable.
    camera_index:
        Index of the camera that produced the detection.
    """

    confidence: float
    camera_index: int = 0
    bounding_box: tuple[int, int, int, int] | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"PersonDetectedPayload.confidence must be in [0.0, 1.0], "
                f"got {self.confidence!r}"
            )
        if self.camera_index < 0:
            raise ValueError(
                f"PersonDetectedPayload.camera_index must be ≥ 0, "
                f"got {self.camera_index!r}"
            )
        if self.bounding_box is not None and len(self.bounding_box) != 4:
            raise ValueError(
                "PersonDetectedPayload.bounding_box must be a 4-tuple "
                f"(x, y, w, h), got {self.bounding_box!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "confidence": self.confidence,
            "camera_index": self.camera_index,
            "bounding_box": list(self.bounding_box) if self.bounding_box else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PersonDetectedPayload":
        bb = data.get("bounding_box")
        return cls(
            confidence=float(data["confidence"]),
            camera_index=int(data.get("camera_index", 0)),
            bounding_box=tuple(bb) if bb is not None else None,  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class PersonLeftPayload:
    """Payload for :data:`EventType.PERSON_LEFT`.

    Attributes
    ----------
    last_seen_at:
        UTC timestamp of the last frame that contained a detected person.
    frames_without_detection:
        How many consecutive frames were processed without a detection before
        this event was emitted.
    """

    last_seen_at: datetime
    frames_without_detection: int

    def __post_init__(self) -> None:
        if self.last_seen_at.tzinfo is None:
            raise ValueError(
                "PersonLeftPayload.last_seen_at must be timezone-aware."
            )
        if self.frames_without_detection < 0:
            raise ValueError(
                "PersonLeftPayload.frames_without_detection must be ≥ 0, "
                f"got {self.frames_without_detection!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "last_seen_at": self.last_seen_at.isoformat(),
            "frames_without_detection": self.frames_without_detection,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PersonLeftPayload":
        return cls(
            last_seen_at=datetime.fromisoformat(data["last_seen_at"]),
            frames_without_detection=int(data["frames_without_detection"]),
        )


@dataclass(frozen=True)
class VoicePayload:
    """Payload for :data:`EventType.VOICE_STARTED` and
    :data:`EventType.VOICE_STOPPED`.

    Attributes
    ----------
    audio_chunk_id:
        Unique identifier for the audio buffer associated with this VAD event.
        All events for the same recording share the same ``audio_chunk_id``.
    duration_ms:
        Duration of the captured speech segment in milliseconds.
        ``0`` for ``VOICE_STARTED`` (segment is still open).
    audio_segment_path:
        Path to the WAV file written by the VAD service.  Only populated on
        ``VOICE_STOPPED``; ``None`` for ``VOICE_STARTED``.
    sample_rate:
        Audio sample rate in Hz (default 16 000 Hz for Whisper compatibility).
    """

    audio_chunk_id: str
    duration_ms: int = 0
    audio_segment_path: str | None = None
    sample_rate: int = 16_000

    def __post_init__(self) -> None:
        if not self.audio_chunk_id:
            raise ValueError("VoicePayload.audio_chunk_id must not be empty.")
        if self.duration_ms < 0:
            raise ValueError(
                f"VoicePayload.duration_ms must be ≥ 0, got {self.duration_ms!r}"
            )
        if self.sample_rate <= 0:
            raise ValueError(
                f"VoicePayload.sample_rate must be > 0, got {self.sample_rate!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "audio_chunk_id": self.audio_chunk_id,
            "duration_ms": self.duration_ms,
            "audio_segment_path": self.audio_segment_path,
            "sample_rate": self.sample_rate,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VoicePayload":
        return cls(
            audio_chunk_id=str(data["audio_chunk_id"]),
            duration_ms=int(data.get("duration_ms", 0)),
            audio_segment_path=data.get("audio_segment_path"),
            sample_rate=int(data.get("sample_rate", 16_000)),
        )


@dataclass(frozen=True)
class TranscriptPayload:
    """Payload for :data:`EventType.TRANSCRIPT_PARTIAL` and
    :data:`EventType.TRANSCRIPT_FINAL`.

    Attributes
    ----------
    text:
        The transcribed text string.  May be empty for partial results during
        silence.
    confidence:
        Overall transcription confidence in ``[0.0, 1.0]`` as reported by
        Faster-Whisper.  ``None`` when not available (partial results).
    language:
        BCP-47 language code detected by Whisper (e.g. ``"en"``).
    duration_ms:
        Duration of the audio segment that was transcribed, in milliseconds.
    is_final:
        ``True`` for :data:`EventType.TRANSCRIPT_FINAL`, ``False`` for
        :data:`EventType.TRANSCRIPT_PARTIAL`.
    audio_chunk_id:
        References the :attr:`VoicePayload.audio_chunk_id` that was the input
        source for this transcript.
    """

    text: str
    is_final: bool
    audio_chunk_id: str
    language: str = "en"
    confidence: float | None = None
    duration_ms: int = 0

    def __post_init__(self) -> None:
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"TranscriptPayload.confidence must be in [0.0, 1.0], "
                f"got {self.confidence!r}"
            )
        if self.duration_ms < 0:
            raise ValueError(
                f"TranscriptPayload.duration_ms must be ≥ 0, "
                f"got {self.duration_ms!r}"
            )
        if not self.audio_chunk_id:
            raise ValueError("TranscriptPayload.audio_chunk_id must not be empty.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "is_final": self.is_final,
            "audio_chunk_id": self.audio_chunk_id,
            "language": self.language,
            "confidence": self.confidence,
            "duration_ms": self.duration_ms,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TranscriptPayload":
        return cls(
            text=str(data["text"]),
            is_final=bool(data["is_final"]),
            audio_chunk_id=str(data["audio_chunk_id"]),
            language=str(data.get("language", "en")),
            confidence=float(data["confidence"]) if data.get("confidence") is not None else None,
            duration_ms=int(data.get("duration_ms", 0)),
        )


@dataclass(frozen=True)
class QueryPayload:
    """Payload for :data:`EventType.QUERY_STARTED` and
    :data:`EventType.QUERY_COMPLETED`.

    Attributes
    ----------
    query:
        The (possibly rewritten) standalone query string sent to the retriever.
    chunks_retrieved:
        Number of chunks returned by the HybridRetriever.  ``0`` during
        ``QUERY_STARTED`` (retrieval not yet complete).
    retrieval_duration_ms:
        Time taken by retrieval + reranking in milliseconds.  ``0`` during
        ``QUERY_STARTED``.
    confidence_score:
        Normalised confidence score ``[0.0, 1.0]`` from the ConfidenceEngine.
        ``None`` during ``QUERY_STARTED``.
    """

    query: str
    chunks_retrieved: int = 0
    retrieval_duration_ms: int = 0
    confidence_score: float | None = None

    def __post_init__(self) -> None:
        if not self.query.strip():
            raise ValueError("QueryPayload.query must not be blank.")
        if self.chunks_retrieved < 0:
            raise ValueError(
                f"QueryPayload.chunks_retrieved must be ≥ 0, "
                f"got {self.chunks_retrieved!r}"
            )
        if self.confidence_score is not None and not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError(
                f"QueryPayload.confidence_score must be in [0.0, 1.0], "
                f"got {self.confidence_score!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "chunks_retrieved": self.chunks_retrieved,
            "retrieval_duration_ms": self.retrieval_duration_ms,
            "confidence_score": self.confidence_score,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QueryPayload":
        return cls(
            query=str(data["query"]),
            chunks_retrieved=int(data.get("chunks_retrieved", 0)),
            retrieval_duration_ms=int(data.get("retrieval_duration_ms", 0)),
            confidence_score=(
                float(data["confidence_score"])
                if data.get("confidence_score") is not None
                else None
            ),
        )


@dataclass(frozen=True)
class AnswerPayload:
    """Payload for :data:`EventType.ANSWER_READY`.

    Attributes
    ----------
    answer:
        The final answer text generated by the LLM via the InferenceAdapter.
    confidence_score:
        Normalised confidence score ``[0.0, 1.0]`` from the ConfidenceEngine.
    confidence_level:
        Human-readable tier: ``"HIGH"``, ``"MEDIUM"``, or ``"LOW"``.
    sources:
        List of source document names cited in the answer.  May be empty.
    inference_duration_ms:
        Time taken by the InferenceAdapter (LLM generation) in milliseconds.
    query:
        The query string that produced this answer (for structured logging).
    """

    answer: str
    confidence_score: float
    confidence_level: str
    sources: tuple[str, ...]
    query: str
    inference_duration_ms: int = 0

    def __post_init__(self) -> None:
        if not self.answer.strip():
            raise ValueError("AnswerPayload.answer must not be blank.")
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError(
                f"AnswerPayload.confidence_score must be in [0.0, 1.0], "
                f"got {self.confidence_score!r}"
            )
        valid_levels = {"HIGH", "MEDIUM", "LOW"}
        if self.confidence_level not in valid_levels:
            raise ValueError(
                f"AnswerPayload.confidence_level must be one of {valid_levels}, "
                f"got {self.confidence_level!r}"
            )
        if not self.query.strip():
            raise ValueError("AnswerPayload.query must not be blank.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "confidence_score": self.confidence_score,
            "confidence_level": self.confidence_level,
            "sources": list(self.sources),
            "query": self.query,
            "inference_duration_ms": self.inference_duration_ms,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnswerPayload":
        return cls(
            answer=str(data["answer"]),
            confidence_score=float(data["confidence_score"]),
            confidence_level=str(data["confidence_level"]),
            sources=tuple(data.get("sources", [])),
            query=str(data["query"]),
            inference_duration_ms=int(data.get("inference_duration_ms", 0)),
        )


@dataclass(frozen=True)
class TTSPayload:
    """Payload for :data:`EventType.TTS_STARTED`, :data:`EventType.TTS_COMPLETED`,
    and :data:`EventType.TTS_INTERRUPTED`.

    Attributes
    ----------
    text:
        The text string that is being (or was) synthesised.
    voice_model:
        Name of the Piper TTS voice model used (e.g.
        ``"en_US-lessac-medium"``).
    duration_ms:
        Actual playback duration in milliseconds.  ``0`` for ``TTS_STARTED``
        (not yet known).
    interrupted_at_ms:
        Milliseconds into playback when interruption occurred.  ``None`` for
        non-interrupted events.
    """

    text: str
    voice_model: str
    duration_ms: int = 0
    interrupted_at_ms: int | None = None

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("TTSPayload.text must not be blank.")
        if not self.voice_model.strip():
            raise ValueError("TTSPayload.voice_model must not be blank.")
        if self.duration_ms < 0:
            raise ValueError(
                f"TTSPayload.duration_ms must be ≥ 0, got {self.duration_ms!r}"
            )
        if self.interrupted_at_ms is not None and self.interrupted_at_ms < 0:
            raise ValueError(
                f"TTSPayload.interrupted_at_ms must be ≥ 0, "
                f"got {self.interrupted_at_ms!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "voice_model": self.voice_model,
            "duration_ms": self.duration_ms,
            "interrupted_at_ms": self.interrupted_at_ms,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TTSPayload":
        return cls(
            text=str(data["text"]),
            voice_model=str(data["voice_model"]),
            duration_ms=int(data.get("duration_ms", 0)),
            interrupted_at_ms=(
                int(data["interrupted_at_ms"])
                if data.get("interrupted_at_ms") is not None
                else None
            ),
        )


@dataclass(frozen=True)
class SessionPayload:
    """Payload for :data:`EventType.SESSION_STARTED` and
    :data:`EventType.SESSION_ENDED`.

    Attributes
    ----------
    reason:
        Human-readable reason for the session transition
        (e.g. ``"person_detected"``, ``"person_left"``, ``"reset_requested"``).
    turns:
        Number of completed question-answer turns within the session.
        ``0`` at ``SESSION_STARTED``; populated at ``SESSION_ENDED``.
    """

    reason: str
    turns: int = 0

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise ValueError("SessionPayload.reason must not be blank.")
        if self.turns < 0:
            raise ValueError(
                f"SessionPayload.turns must be ≥ 0, got {self.turns!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {"reason": self.reason, "turns": self.turns}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionPayload":
        return cls(
            reason=str(data["reason"]),
            turns=int(data.get("turns", 0)),
        )


@dataclass(frozen=True)
class ErrorPayload:
    """Payload for :data:`EventType.ERROR`.

    Attributes
    ----------
    service:
        Name of the service that raised the error (e.g. ``"stt_service"``).
    error_type:
        Exception class name or short error category string
        (e.g. ``"OllamaTimeoutError"``).
    message:
        Human-readable error description.
    is_fatal:
        ``True`` if the error requires an FSM transition to the ERROR state.
        ``False`` for degraded-but-continuing conditions.
    traceback:
        Optional formatted traceback string for structured logging.
    """

    service: str
    error_type: str
    message: str
    is_fatal: bool = False
    traceback: str | None = None

    def __post_init__(self) -> None:
        if not self.service.strip():
            raise ValueError("ErrorPayload.service must not be blank.")
        if not self.error_type.strip():
            raise ValueError("ErrorPayload.error_type must not be blank.")
        if not self.message.strip():
            raise ValueError("ErrorPayload.message must not be blank.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "service": self.service,
            "error_type": self.error_type,
            "message": self.message,
            "is_fatal": self.is_fatal,
            "traceback": self.traceback,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ErrorPayload":
        return cls(
            service=str(data["service"]),
            error_type=str(data["error_type"]),
            message=str(data["message"]),
            is_fatal=bool(data.get("is_fatal", False)),
            traceback=data.get("traceback"),
        )


@dataclass(frozen=True)
class WarningPayload:
    """Payload for :data:`EventType.WARNING`.

    Attributes
    ----------
    service:
        Name of the service reporting the degraded condition.
    metric:
        Name of the metric that triggered the warning
        (e.g. ``"cpu_percent"``, ``"queue_depth"``).
    value:
        Current value of the metric.
    threshold:
        Configured threshold that was exceeded.
    message:
        Human-readable description.
    """

    service: str
    metric: str
    value: float
    threshold: float
    message: str

    def __post_init__(self) -> None:
        if not self.service.strip():
            raise ValueError("WarningPayload.service must not be blank.")
        if not self.metric.strip():
            raise ValueError("WarningPayload.metric must not be blank.")
        if not self.message.strip():
            raise ValueError("WarningPayload.message must not be blank.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "service": self.service,
            "metric": self.metric,
            "value": self.value,
            "threshold": self.threshold,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WarningPayload":
        return cls(
            service=str(data["service"]),
            metric=str(data["metric"]),
            value=float(data["value"]),
            threshold=float(data["threshold"]),
            message=str(data["message"]),
        )


@dataclass(frozen=True)
class TimeoutPayload:
    """Payload for :data:`EventType.TIMEOUT`.

    Attributes
    ----------
    state:
        Name of the FSM state that timed out (e.g. ``"PROCESSING"``).
    timeout_duration_ms:
        The configured timeout duration in milliseconds.
    elapsed_ms:
        Actual elapsed time in milliseconds when the timeout fired.
    """

    state: str
    timeout_duration_ms: int
    elapsed_ms: int

    def __post_init__(self) -> None:
        if not self.state.strip():
            raise ValueError("TimeoutPayload.state must not be blank.")
        if self.timeout_duration_ms <= 0:
            raise ValueError(
                f"TimeoutPayload.timeout_duration_ms must be > 0, "
                f"got {self.timeout_duration_ms!r}"
            )
        if self.elapsed_ms < 0:
            raise ValueError(
                f"TimeoutPayload.elapsed_ms must be ≥ 0, "
                f"got {self.elapsed_ms!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "timeout_duration_ms": self.timeout_duration_ms,
            "elapsed_ms": self.elapsed_ms,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TimeoutPayload":
        return cls(
            state=str(data["state"]),
            timeout_duration_ms=int(data["timeout_duration_ms"]),
            elapsed_ms=int(data["elapsed_ms"]),
        )


@dataclass(frozen=True)
class CameraPayload:
    """Payload for camera streaming and lifecycle events.

    Attributes
    ----------
    frame_id:
        Unique UUID identifier for this frame.
    timestamp:
        UTC time when the frame was acquired.
    resolution:
        Resolution string (e.g. "1280x720").
    frame_number:
        Monotonically increasing sequence number for this capture session.
    capture_latency_ms:
        Overhead time taken by OpenCV read and frame dispatching in milliseconds.
    camera_index:
        System camera index (e.g. 0).
    status:
        Optional status description for lifecycle changes (e.g. "Connected").
    frame_data:
        Raw bytes (e.g., JPEG/PNG or raw RGB) representing the frame image.
        This field is excluded from dict/JSON serialization to prevent high copying/parsing overhead.
    """

    frame_id: str
    timestamp: datetime
    resolution: str
    frame_number: int
    capture_latency_ms: float
    camera_index: int = 0
    status: str | None = None
    frame_data: bytes | None = None

    def __post_init__(self) -> None:
        if not self.frame_id:
            raise ValueError("CameraPayload.frame_id must not be empty.")
        if self.timestamp.tzinfo is None:
            raise ValueError("CameraPayload.timestamp must be timezone-aware.")
        if not self.resolution.strip():
            raise ValueError("CameraPayload.resolution must not be blank.")
        if self.frame_number < 0:
            raise ValueError("CameraPayload.frame_number must be >= 0.")
        if self.capture_latency_ms < 0:
            raise ValueError("CameraPayload.capture_latency_ms must be >= 0.")
        if self.camera_index < 0:
            raise ValueError("CameraPayload.camera_index must be >= 0.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp.isoformat(),
            "resolution": self.resolution,
            "frame_number": self.frame_number,
            "capture_latency_ms": self.capture_latency_ms,
            "camera_index": self.camera_index,
            "status": self.status,
            # frame_data intentionally omitted to keep dict serialisation lightweight
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CameraPayload":
        return cls(
            frame_id=str(data["frame_id"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            resolution=str(data["resolution"]),
            frame_number=int(data["frame_number"]),
            capture_latency_ms=float(data["capture_latency_ms"]),
            camera_index=int(data.get("camera_index", 0)),
            status=data.get("status"),
            frame_data=None,
        )


# ---------------------------------------------------------------------------
# Union type alias for all known payload types
# ---------------------------------------------------------------------------

AnyPayload = (
    SystemPayload
    | PersonDetectedPayload
    | PersonLeftPayload
    | VoicePayload
    | TranscriptPayload
    | QueryPayload
    | AnswerPayload
    | TTSPayload
    | SessionPayload
    | ErrorPayload
    | WarningPayload
    | TimeoutPayload
    | CameraPayload
)

# Maps EventType → expected payload class for runtime validation.
EVENT_PAYLOAD_MAP: dict[EventType, type] = {
    EventType.SYSTEM_STARTING: SystemPayload,
    EventType.SYSTEM_READY: SystemPayload,
    EventType.SYSTEM_SHUTDOWN: SystemPayload,
    EventType.PERSON_DETECTED: PersonDetectedPayload,
    EventType.PERSON_LEFT: PersonLeftPayload,
    EventType.VOICE_STARTED: VoicePayload,
    EventType.VOICE_STOPPED: VoicePayload,
    EventType.TRANSCRIPT_PARTIAL: TranscriptPayload,
    EventType.TRANSCRIPT_FINAL: TranscriptPayload,
    EventType.QUERY_STARTED: QueryPayload,
    EventType.QUERY_COMPLETED: QueryPayload,
    EventType.ANSWER_READY: AnswerPayload,
    EventType.TTS_STARTED: TTSPayload,
    EventType.TTS_COMPLETED: TTSPayload,
    EventType.TTS_INTERRUPTED: TTSPayload,
    EventType.SESSION_STARTED: SessionPayload,
    EventType.SESSION_ENDED: SessionPayload,
    EventType.ERROR: ErrorPayload,
    EventType.WARNING: WarningPayload,
    EventType.TIMEOUT: TimeoutPayload,
    EventType.CAMERA_STARTED: CameraPayload,
    EventType.CAMERA_STOPPED: CameraPayload,
    EventType.FRAME_CAPTURED: CameraPayload,
    EventType.CAMERA_DISCONNECTED: CameraPayload,
    EventType.CAMERA_RECONNECTED: CameraPayload,
    EventType.CAMERA_ERROR: CameraPayload,
}

# Maps payload class name string → class, used during deserialisation.
_PAYLOAD_CLASS_MAP: dict[str, type] = {
    cls.__name__: cls
    for cls in (
        SystemPayload,
        PersonDetectedPayload,
        PersonLeftPayload,
        VoicePayload,
        TranscriptPayload,
        QueryPayload,
        AnswerPayload,
        TTSPayload,
        SessionPayload,
        ErrorPayload,
        WarningPayload,
        TimeoutPayload,
        CameraPayload,
    )
}


# ---------------------------------------------------------------------------
# EventEnvelope
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EventEnvelope:
    """Immutable, hashable container that carries a typed payload across the
    Event Bus.

    Every service publishes and subscribes using :class:`EventEnvelope`
    objects.  The envelope provides traceability (UUIDs, timestamps,
    correlation chains) and schema versioning independent of the payload.

    Attributes
    ----------
    event_type:
        The :class:`EventType` discriminator value.
    source:
        Name of the service that created this event
        (e.g. ``"camera_service"``).
    payload:
        A strongly-typed payload dataclass instance.  The runtime type must
        match :data:`EVENT_PAYLOAD_MAP` for the given ``event_type``.
    event_id:
        Globally unique identifier (UUID4) for this specific envelope.
        Auto-generated if not supplied.
    session_id:
        Session identifier shared across all events belonging to the same
        conversation turn.  ``None`` for system-level events.
    correlation_id:
        ``event_id`` of the parent event that caused this one, enabling
        event-chain tracing in logs.  ``None`` for root events.
    timestamp:
        UTC creation time of the envelope.  Always timezone-aware.
    priority:
        Bus queue priority.  Defaults to :attr:`EventPriority.NORMAL`.
    metadata:
        Optional supplementary key-value pairs for structured logging
        (e.g. ``{"deployment_profile": "standalone_robot"}``).
        Stored as a frozen mapping via an immutable tuple-of-pairs.
    version:
        Schema version string.  Defaults to :data:`EVENT_SCHEMA_VERSION`.

    Notes
    -----
    *Immutability*: all mutable default arguments (timestamp, metadata) are
    handled through ``field(default_factory=…)`` or ``__post_init__``
    coercion — no mutable defaults leak through the frozen dataclass contract.

    *Hashability*: because the dataclass is frozen and all fields are hashable
    (UUID strings, datetime, tuples), :class:`EventEnvelope` instances can be
    stored in sets and used as dict keys.
    """

    event_type: EventType
    source: str
    payload: AnyPayload  # type: ignore[valid-type]  # union alias accepted at runtime

    # Optional / auto-populated fields
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str | None = None
    correlation_id: str | None = None
    timestamp: datetime = field(default_factory=_utcnow)
    priority: EventPriority = EventPriority.NORMAL
    # Metadata stored as a tuple of (key, value) pairs to remain hashable.
    metadata: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    version: str = EVENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        # ----- source validation -------------------------------------------
        if not self.source.strip():
            raise ValueError("EventEnvelope.source must not be blank.")

        # ----- timestamp must be timezone-aware ----------------------------
        if self.timestamp.tzinfo is None:
            raise ValueError(
                "EventEnvelope.timestamp must be timezone-aware (use "
                "datetime.now(tz=timezone.utc))."
            )

        # ----- event_id must be a valid UUID4 ------------------------------
        try:
            parsed = uuid.UUID(self.event_id)
        except (ValueError, AttributeError) as exc:
            raise ValueError(
                f"EventEnvelope.event_id must be a valid UUID string, "
                f"got {self.event_id!r}"
            ) from exc
        if parsed.version != 4:
            raise ValueError(
                f"EventEnvelope.event_id must be a UUID version 4, "
                f"got version {parsed.version}"
            )

        # ----- correlation_id must be a valid UUID if supplied -------------
        if self.correlation_id is not None:
            try:
                uuid.UUID(self.correlation_id)
            except (ValueError, AttributeError) as exc:
                raise ValueError(
                    f"EventEnvelope.correlation_id must be a valid UUID string "
                    f"or None, got {self.correlation_id!r}"
                ) from exc

        # ----- payload type must match EVENT_PAYLOAD_MAP -------------------
        expected_cls = EVENT_PAYLOAD_MAP.get(self.event_type)
        if expected_cls is not None and not isinstance(self.payload, expected_cls):
            raise TypeError(
                f"EventEnvelope: event_type {self.event_type.value!r} expects "
                f"payload of type {expected_cls.__name__}, "
                f"got {type(self.payload).__name__}"
            )

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    def get_metadata(self) -> dict[str, str]:
        """Return metadata as a plain dictionary (creates a new dict each call)."""
        return dict(self.metadata)

    def with_metadata(self, **kwargs: str) -> "EventEnvelope":
        """Return a new envelope with additional metadata entries merged in."""
        existing = self.get_metadata()
        existing.update(kwargs)
        return EventEnvelope(
            event_type=self.event_type,
            source=self.source,
            payload=self.payload,
            event_id=self.event_id,
            session_id=self.session_id,
            correlation_id=self.correlation_id,
            timestamp=self.timestamp,
            priority=self.priority,
            metadata=tuple(existing.items()),
            version=self.version,
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialise the envelope to a plain Python dictionary.

        The ``payload`` field is serialised via its own ``to_dict()`` method
        and the payload class name is stored under ``"payload_type"`` so that
        ``from_dict`` can reconstruct the correct class.
        """
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "source": self.source,
            "session_id": self.session_id,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.value,
            "payload_type": type(self.payload).__name__,
            "payload": self.payload.to_dict(),
            "metadata": list(self.metadata),
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EventEnvelope":
        """Deserialise an envelope from a plain Python dictionary.

        Raises
        ------
        KeyError
            If a required field is missing from ``data``.
        ValueError
            If ``event_type`` or ``payload_type`` is unknown.
        """
        event_type = EventType(data["event_type"])
        payload_type_name: str = data["payload_type"]
        payload_cls = _PAYLOAD_CLASS_MAP.get(payload_type_name)
        if payload_cls is None:
            raise ValueError(
                f"Unknown payload_type {payload_type_name!r}. "
                f"Known types: {list(_PAYLOAD_CLASS_MAP)}"
            )
        payload = payload_cls.from_dict(data["payload"])

        raw_meta = data.get("metadata", [])
        metadata: tuple[tuple[str, str], ...] = tuple(
            (str(k), str(v)) for k, v in raw_meta
        )

        return cls(
            event_id=str(data["event_id"]),
            event_type=event_type,
            source=str(data["source"]),
            session_id=data.get("session_id"),
            correlation_id=data.get("correlation_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            priority=EventPriority(data.get("priority", EventPriority.NORMAL.value)),
            payload=payload,
            metadata=metadata,
            version=str(data.get("version", EVENT_SCHEMA_VERSION)),
        )

    def to_json(self, *, indent: int | None = None) -> str:
        """Serialise the envelope to a JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_json(cls, raw: str) -> "EventEnvelope":
        """Deserialise an envelope from a JSON string."""
        return cls.from_dict(json.loads(raw))

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        event_type: EventType,
        source: str,
        payload: AnyPayload,  # type: ignore[valid-type]
        *,
        session_id: str | None = None,
        correlation_id: str | None = None,
        priority: EventPriority = EventPriority.NORMAL,
        metadata: dict[str, str] | None = None,
    ) -> "EventEnvelope":
        """Convenience factory that auto-generates ``event_id`` and ``timestamp``.

        Parameters
        ----------
        event_type:
            The :class:`EventType` for this event.
        source:
            Name of the emitting service.
        payload:
            A typed payload instance matching the event type.
        session_id:
            Optional conversation session identifier.
        correlation_id:
            Optional parent ``event_id`` for chain tracing.
        priority:
            Queue priority.  Defaults to :attr:`EventPriority.NORMAL`.
        metadata:
            Optional supplementary key-value pairs.
        """
        return cls(
            event_type=event_type,
            source=source,
            payload=payload,
            session_id=session_id,
            correlation_id=correlation_id,
            priority=priority,
            metadata=tuple((metadata or {}).items()),
        )

    def reply(
        self,
        event_type: EventType,
        source: str,
        payload: AnyPayload,  # type: ignore[valid-type]
        *,
        priority: EventPriority = EventPriority.NORMAL,
    ) -> "EventEnvelope":
        """Create a new envelope that is a response to this one.

        The returned envelope inherits ``session_id`` from this envelope and
        sets ``correlation_id`` to this envelope's ``event_id``.
        """
        return EventEnvelope.create(
            event_type=event_type,
            source=source,
            payload=payload,
            session_id=self.session_id,
            correlation_id=self.event_id,
            priority=priority,
        )


# ---------------------------------------------------------------------------
# Public API surface
# ---------------------------------------------------------------------------

__all__ = [
    # Version constant
    "EVENT_SCHEMA_VERSION",
    # Enums
    "EventType",
    "EventPriority",
    # Payload types
    "SystemPayload",
    "PersonDetectedPayload",
    "PersonLeftPayload",
    "VoicePayload",
    "TranscriptPayload",
    "QueryPayload",
    "AnswerPayload",
    "TTSPayload",
    "SessionPayload",
    "ErrorPayload",
    "WarningPayload",
    "TimeoutPayload",
    "CameraPayload",
    # Union alias
    "AnyPayload",
    # Lookup maps
    "EVENT_PAYLOAD_MAP",
    # Envelope
    "EventEnvelope",
]
