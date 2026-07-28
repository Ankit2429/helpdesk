"""
Campus Helpdesk Robot – Phase 3: Inference Adapter
==================================================

Module: campus_helpdesk.services.inference_adapter
File:   src/campus_helpdesk/services/inference_adapter.py
Version: 1.0

This service bridges the Interaction Runtime and the existing offline RAG/LLM
query pipeline. It consumes ``TRANSCRIPT_FINAL`` events, enqueues them in a
FIFO worker queue, executes queries via an abstract backend, and publishes
``QUERY_STARTED`` and ``ANSWER_READY`` events.

Thread Model
------------
*  **Worker Thread** – dedicated loop (``InferenceAdapter-worker``) pulling
   queries from a FIFO queue and processing them sequentially to prevent overlapping
   CPU/GPU model loading.
*  **Thread Safety** – all state updates, metrics, and diagnostics are protected
   by a reentrant lock (``threading.RLock``).
"""

from __future__ import annotations

import logging
import queue
import time
import uuid
import threading
from abc import ABC, abstractmethod
from typing import Any

from campus_helpdesk.interaction.event_bus import EventBus, SubscriptionHandle
from campus_helpdesk.interaction.events import (
    AnswerPayload,
    EventEnvelope,
    EventType,
    QueryPayload,
    TranscriptPayload,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Backend Abstraction
# ---------------------------------------------------------------------------


class BaseInferenceBackend(ABC):
    """Abstract base class for inference engines (RAG pipeline, Mock, etc.)."""

    @abstractmethod
    def query(self, text: str, session_id: str) -> tuple[str, list[str], float, str]:
        """Submit a query to the backend.

        Parameters
        ----------
        text:
            Standalone user query string.
        session_id:
            Conversational session identifier.

        Returns
        -------
        answer:
            Generated response string.
        citations:
            List of cited document sources.
        confidence_score:
            Confidence score in range [0.0, 1.0].
        confidence_level:
            Confidence tier string ("HIGH", "MEDIUM", or "LOW").
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the inference backend implementation."""
        pass


class LocalRAGBackend(BaseInferenceBackend):
    """Bridges to the existing RAGChatService and Ollama pipeline."""

    def __init__(self, chat_service: Any) -> None:
        """
        Parameters
        ----------
        chat_service:
            An instance of RAGChatService.
        """
        self._chat_service = chat_service

    def query(self, text: str, session_id: str) -> tuple[str, list[str], float, str]:
        # Invoke RAGChatService respond method
        result = self._chat_service.respond(text, session_id=session_id)
        # Parse return attributes
        answer = getattr(result, "reply", "")
        citations = getattr(result, "supporting_sources", [])
        confidence_score = getattr(result, "confidence_score", 1.0)
        confidence_level = getattr(result, "confidence_level", "HIGH")
        return answer, citations, confidence_score, confidence_level

    @property
    def name(self) -> str:
        return "LocalRAGBackend"


class MockInferenceBackend(BaseInferenceBackend):
    """Mock backend returning deterministic responses for unit testing."""

    def __init__(self, name: str = "MockInferenceBackend") -> None:
        self._name = name
        self.mock_answer = "The central library is open from 8 AM to 8 PM."
        self.mock_citations = ["library_rules.md", "campus_map.pdf"]
        self.mock_confidence = 0.92
        self.mock_confidence_level = "HIGH"
        self.should_fail = False
        self.simulate_delay_sec = 0.05

    def query(self, text: str, session_id: str) -> tuple[str, list[str], float, str]:
        if self.should_fail:
            raise RuntimeError("Database connection timed out")

        if self.simulate_delay_sec > 0:
            time.sleep(self.simulate_delay_sec)

        # Handle empty/invalid query edge case
        if not text.strip():
            return "I didn't hear a valid question.", [], 0.0, "LOW"

        return (
            self.mock_answer,
            self.mock_citations,
            self.mock_confidence,
            self.mock_confidence_level,
        )

    @property
    def name(self) -> str:
        return self._name


# ---------------------------------------------------------------------------
# Inference Adapter
# ---------------------------------------------------------------------------


class InferenceAdapter:
    """Consumes final transcripts, runs the RAG backend, and emits Answer events.

    Parameters
    ----------
    event_bus:
        Central Event Bus instance.
    backend:
        Implementation of BaseInferenceBackend. Defaults to Mock.
    timeout_seconds:
        Maximum permitted execution duration for backend queries.
    """

    def __init__(
        self,
        event_bus: EventBus,
        backend: BaseInferenceBackend | None = None,
        timeout_seconds: float = 10.0,
        name: str = "inference_adapter",
    ) -> None:
        self._bus = event_bus
        self._backend = backend or MockInferenceBackend()
        self._timeout_seconds = timeout_seconds
        self._name = name

        self._lock = threading.RLock()
        self._queue: queue.Queue[EventEnvelope] = queue.Queue()
        self._running = False
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None
        self._sub_handle: SubscriptionHandle | None = None

        # Diagnostics & Metrics
        self._requests_processed = 0
        self._total_latency_ms = 0.0
        self._failures = 0
        self._timeouts = 0
        self._start_time: float | None = None

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
            self._start_time = time.perf_counter()

            # Subscribe to TRANSCRIPT_FINAL
            self._sub_handle = self._bus.subscribe(
                self._enqueue_request,
                event_types=EventType.TRANSCRIPT_FINAL,
                source=self._name,
            )

            # Start Worker Thread
            self._worker = threading.Thread(
                target=self._worker_loop,
                name=f"{self._name}-worker",
                daemon=True,
            )
            self._worker.start()
            logger.info("InferenceAdapter started with backend: %s", self._backend.name)

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

        logger.info("InferenceAdapter stopped.")

    def shutdown(self) -> None:
        """Complete clean resource termination."""
        self.stop()

    def is_running(self) -> bool:
        """Query running status."""
        with self._lock:
            return self._running

    # ─────────────────────────────────────────────────────────────────────────
    # Queue Ingestion & Worker Thread
    # ─────────────────────────────────────────────────────────────────────────

    def _enqueue_request(self, event: EventEnvelope) -> None:
        """Enqueues incoming TRANSCRIPT_FINAL events."""
        if not self.is_running():
            return
        self._queue.put(event)

    def _worker_loop(self) -> None:
        """FIFO worker loop pulling transcripts and running queries."""
        while not self._stop_event.is_set():
            try:
                event = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue

            try:
                self._process_request(event)
            except Exception as exc:
                logger.exception("InferenceAdapter: Unhandled exception in worker: %s", exc)
                with self._lock:
                    self._failures += 1
                self._publish_error(
                    "InferenceAdapterWorkerError",
                    f"Inference processing crashed: {exc}",
                    event,
                )
            finally:
                self._queue.task_done()

    def _process_request(self, event: EventEnvelope) -> None:
        payload = event.payload
        if not isinstance(payload, TranscriptPayload) or not payload.text or not payload.text.strip():
            logger.warning("InferenceAdapter: Received invalid or empty transcript payload.")
            self._publish_error(
                "InvalidTranscriptError",
                "Transcript is empty or missing payload text.",
                event,
            )
            return

        session_id = event.session_id or "default"
        query_text = payload.text.strip()

        # 1. Publish QUERY_STARTED
        self._bus.publish(
            EventEnvelope.create(
                event_type=EventType.QUERY_STARTED,
                source=self._name,
                payload=QueryPayload(
                    query=query_text,
                    chunks_retrieved=0,
                    retrieval_duration_ms=0,
                    confidence_score=None,
                ),
                session_id=session_id,
                correlation_id=event.event_id,
            )
        )

        t_start = time.perf_counter()
        
        # Execute query within a timeout wrapper
        result_container: list[Any] = []
        error_container: list[Exception] = []

        def run_query() -> None:
            try:
                res = self._backend.query(query_text, session_id)
                result_container.append(res)
            except Exception as e:
                error_container.append(e)

        query_thread = threading.Thread(
            target=run_query,
            name=f"{self._name}-query-executor",
            daemon=True,
        )
        query_thread.start()
        query_thread.join(timeout=self._timeout_seconds)

        t_end = time.perf_counter()
        latency_ms = (t_end - t_start) * 1000

        # Handle Timeout
        if query_thread.is_alive():
            with self._lock:
                self._timeouts += 1
                self._failures += 1
            logger.error("InferenceAdapter: Query execution timed out after %.2fs", self._timeout_seconds)
            self._publish_error(
                "InferenceTimeoutError",
                f"Inference query timed out after {self._timeout_seconds} seconds.",
                event,
            )
            return

        # Handle Backend Exceptions
        if error_container:
            with self._lock:
                self._failures += 1
            exc = error_container[0]
            logger.error("InferenceAdapter: Backend exception during query: %s", exc)
            self._publish_error(
                "InferenceBackendError",
                f"Backend query execution failed: {exc}",
                event,
            )
            return

        # Extract Results
        if not result_container:
            with self._lock:
                self._failures += 1
            self._publish_error(
                "InferenceEmptyResponseError",
                "Backend returned no response.",
                event,
            )
            return

        answer, citations, score, level = result_container[0]

        with self._lock:
            self._requests_processed += 1
            self._total_latency_ms += latency_ms

        # 2. Publish ANSWER_READY
        self._bus.publish(
            EventEnvelope.create(
                event_type=EventType.ANSWER_READY,
                source=self._name,
                payload=AnswerPayload(
                    answer=answer,
                    confidence_score=score,
                    confidence_level=level,
                    sources=tuple(citations),
                    query=query_text,
                    inference_duration_ms=int(latency_ms),
                ),
                session_id=session_id,
                correlation_id=event.event_id,
            )
        )

    def _publish_error(self, err_type: str, msg: str, trigger_event: EventEnvelope) -> None:
        """Publish ERROR events to notify system FSM and InteractionManager."""
        from campus_helpdesk.interaction.events import ErrorPayload
        self._bus.publish(
            EventEnvelope.create(
                event_type=EventType.ERROR,
                source=self._name,
                payload=ErrorPayload(
                    service=self._name,
                    error_type=err_type,
                    message=msg,
                    is_fatal=False,
                ),
                session_id=trigger_event.session_id,
                correlation_id=trigger_event.event_id,
            )
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Diagnostics & Status APIs
    # ─────────────────────────────────────────────────────────────────────────

    def diagnostics(self) -> dict[str, Any]:
        """Get diagnostics statistics payload."""
        with self._lock:
            avg_latency = (
                self._total_latency_ms / self._requests_processed if self._requests_processed > 0 else 0.0
            )
            uptime_sec = time.perf_counter() - self._start_time if self._start_time else 0.0

            return {
                "requests_processed": self._requests_processed,
                "average_inference_latency_ms": round(avg_latency, 3),
                "queue_depth": self._queue.qsize(),
                "backend_name": self._backend.name,
                "failures": self._failures,
                "timeouts": self._timeouts,
                "worker_status": "running" if (self._worker and self._worker.is_alive()) else "stopped",
                "uptime_seconds": round(uptime_sec, 3),
            }
