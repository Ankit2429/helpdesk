"""
Campus Helpdesk Robot – Phase 3: Interaction Manager
===================================================

Module: campus_helpdesk.interaction.interaction_manager
File:   src/campus_helpdesk/interaction/interaction_manager.py
Version: 1.0

This module implements the central orchestration engine for the robot.
The Interaction Manager is the single component responsible for deciding
what happens next. It owns the interaction lifecycle, coordinates all
services via the Event Bus and Robot State Machine, and maintains lightweight
runtime context. It does not perform work (e.g. inference, transcription,
playback) itself; it only reacts to events and publishes follow-up control events.

Design Principles
-----------------
* **Event-Driven**: Communicates strictly via events on the `EventBus`.
* **State-Controlled**: Validates every event against the `RobotStateMachine`
  before transitioning or publishing downstream tasks.
* **Decoupled**: Contains no hardware, STT, TTS, OpenCV, or LLM code.
* **Thread-Safe**: Uses reentrant locking to guard updates to context and
  diagnostics metrics.
"""

from __future__ import annotations

import logging
import time
import uuid
import threading
from dataclasses import dataclass
from typing import Any

from campus_helpdesk.interaction.event_bus import EventBus, SubscriptionHandle
from campus_helpdesk.interaction.events import (
    AnswerPayload,
    ErrorPayload,
    EventEnvelope,
    EventType,
    QueryPayload,
    SessionPayload,
    SystemPayload,
    TimeoutPayload,
)
from campus_helpdesk.interaction.robot_state import (
    InvalidTransitionError,
    RobotState,
    RobotStateMachine,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# InteractionContext
# ---------------------------------------------------------------------------


@dataclass
class InteractionContext:
    """Lightweight, mutable runtime context for the active interaction."""

    session_id: str | None = None
    correlation_id: str | None = None
    interaction_id: str | None = None
    last_transcript_id: str | None = None
    last_answer_id: str | None = None

    def clear(self) -> None:
        """Reset all context fields."""
        self.session_id = None
        self.correlation_id = None
        self.interaction_id = None
        self.last_transcript_id = None
        self.last_answer_id = None


# ---------------------------------------------------------------------------
# InteractionManager
# ---------------------------------------------------------------------------


class InteractionManager:
    """Central orchestrator for the Campus Helpdesk Robot.

    Subscribes to events, coordinates state transitions, tracks current
    context, and publishes follow-up control events.
    """

    def __init__(
        self,
        event_bus: EventBus,
        state_machine: RobotStateMachine,
        name: str = "InteractionManager",
    ) -> None:
        self._bus = event_bus
        self._fsm = state_machine
        self._name = name
        self._lock = threading.RLock()

        # Context
        self._context = InteractionContext()

        # Statistics & Metrics
        self._event_count: int = 0
        self._last_event: EventEnvelope | None = None
        self._start_time = time.perf_counter()

        # Subscriptions
        self._handles: list[SubscriptionHandle] = []

        # Background timeout checking thread
        self._timeout_event = threading.Event()
        self._timeout_thread: threading.Thread | None = None

        self._subscribe_all()
        self._start_timeout_monitor()

        logger.info("%s initialized.", name)

    # ─────────────────────────────────────────────────────────────────────────
    # Subscriptions & Loop Setup
    # ─────────────────────────────────────────────────────────────────────────

    def _subscribe_all(self) -> None:
        """Register subscriptions for all relevant lifecycle events."""
        events_to_watch = [
            EventType.SYSTEM_READY,
            EventType.PERSON_DETECTED,
            EventType.PERSON_LEFT,
            EventType.VOICE_STARTED,
            EventType.VOICE_STOPPED,
            EventType.TRANSCRIPT_FINAL,
            EventType.QUERY_COMPLETED,
            EventType.ANSWER_READY,
            EventType.TTS_STARTED,
            EventType.TTS_COMPLETED,
            EventType.TTS_INTERRUPTED,
            EventType.TIMEOUT,
            EventType.ERROR,
        ]

        # Use a single wildcard subscription to guarantee in-order processing
        # of events on the manager side.
        handle = self._bus.subscribe(
            self.handle_event,
            event_types=events_to_watch,
            source=self._name,
        )
        self._handles.append(handle)

    def _start_timeout_monitor(self) -> None:
        """Launch background monitor to periodically check FSM timeouts."""
        self._timeout_thread = threading.Thread(
            target=self._timeout_loop,
            name=f"{self._name}-timeout-monitor",
            daemon=True,
        )
        self._timeout_thread.start()

    def _timeout_loop(self) -> None:
        """Periodic timeout evaluation loop."""
        while not self._timeout_event.is_set():
            time.sleep(0.5)
            if self._fsm.check_timeout():
                current_state = self._fsm.state
                limit = self._fsm.get_timeout(current_state) or 0.0
                elapsed = self._fsm.time_in_state()

                # Publish TIMEOUT event to the bus. We react to it inside handle_event.
                logger.warning(
                    "FSM: State %s timed out after %.1fs (limit=%.1fs)",
                    current_state.name,
                    elapsed,
                    limit,
                )
                self._bus.publish(
                    EventEnvelope.create(
                        event_type=EventType.TIMEOUT,
                        source=self._name,
                        payload=TimeoutPayload(
                            state=current_state.name,
                            timeout_duration_ms=int(limit * 1000),
                            elapsed_ms=int(elapsed * 1000),
                        ),
                    )
                )

    # ─────────────────────────────────────────────────────────────────────────
    # Core Event Handler
    # ─────────────────────────────────────────────────────────────────────────

    def handle_event(self, event: EventEnvelope) -> None:
        """Central event routing logic.

        Validates the event against the current state, handles transitions,
        updates interaction contexts, and dispatches follow-up events.
        """
        with self._lock:
            self._event_count += 1
            self._last_event = event

            et = event.event_type
            current_state = self._fsm.state

            # Correlation tracing
            if event.session_id:
                self._context.session_id = event.session_id
            self._context.correlation_id = event.event_id

            logger.debug(
                "Manager %s: Handling event %s in state %s",
                self._name,
                et.value,
                current_state.name,
            )

            # Route by EventType
            if et == EventType.SYSTEM_READY:
                self._handle_system_ready(event)
            elif et == EventType.PERSON_DETECTED:
                self._handle_person_detected(event)
            elif et == EventType.PERSON_LEFT:
                self._handle_person_left(event)
            elif et == EventType.VOICE_STARTED:
                self._handle_voice_started(event)
            elif et == EventType.VOICE_STOPPED:
                self._handle_voice_stopped(event)
            elif et == EventType.TRANSCRIPT_FINAL:
                self._handle_transcript_final(event)
            elif et == EventType.QUERY_COMPLETED:
                self._handle_query_completed(event)
            elif et == EventType.ANSWER_READY:
                self._handle_answer_ready(event)
            elif et in {EventType.TTS_STARTED, EventType.TTS_COMPLETED, EventType.TTS_INTERRUPTED}:
                self._handle_tts_lifecycle(event)
            elif et == EventType.TIMEOUT:
                self._handle_timeout(event)
            elif et == EventType.ERROR:
                self._handle_error(event)
            else:
                logger.warning("Manager: Unhandled event type %s ignored.", et.value)

    # ─────────────────────────────────────────────────────────────────────────
    # Handler Implementations
    # ─────────────────────────────────────────────────────────────────────────

    def _handle_system_ready(self, event: EventEnvelope) -> None:
        current = self._fsm.state
        if current in {RobotState.BOOTING, RobotState.INITIALIZING}:
            try:
                # Transition BOOTING -> INITIALIZING -> IDLE
                if current == RobotState.BOOTING:
                    self._fsm.transition_to(
                        RobotState.INITIALIZING,
                        reason="System boot checklist started",
                        correlation_id=event.event_id,
                    )
                self._fsm.transition_to(
                    RobotState.IDLE,
                    reason="System ready",
                    correlation_id=event.event_id,
                )
            except InvalidTransitionError as exc:
                logger.error("Manager: Transition fail during SYSTEM_READY: %s", exc)

    def _handle_person_detected(self, event: EventEnvelope) -> None:
        if self._fsm.state == RobotState.IDLE:
            try:
                new_session = str(uuid.uuid4())
                self._context.clear()
                self._context.session_id = new_session
                self._context.interaction_id = str(uuid.uuid4())

                # Transition IDLE -> READY
                self._fsm.transition_to(
                    RobotState.READY,
                    reason="Person detected",
                    session_id=new_session,
                    correlation_id=event.event_id,
                )

                # Publish SESSION_STARTED control event
                self._bus.publish(
                    EventEnvelope.create(
                        event_type=EventType.SESSION_STARTED,
                        source=self._name,
                        payload=SessionPayload(reason="person_detected"),
                        session_id=new_session,
                        correlation_id=event.event_id,
                    )
                )
            except InvalidTransitionError as exc:
                logger.error("Manager: Transition fail: %s", exc)
        else:
            logger.warning(
                "Manager: Ignored PERSON_DETECTED. FSM in %s", self._fsm.state.name
            )

    def _handle_person_left(self, event: EventEnvelope) -> None:
        current = self._fsm.state
        if current in {
            RobotState.READY,
            RobotState.LISTENING,
            RobotState.PROCESSING,
            RobotState.SPEAKING,
        }:
            try:
                active_session = self._context.session_id
                self._fsm.transition_to(
                    RobotState.IDLE,
                    reason="Person left",
                    session_id=active_session,
                    correlation_id=event.event_id,
                )
                self._context.clear()

                # Publish SESSION_ENDED control event
                self._bus.publish(
                    EventEnvelope.create(
                        event_type=EventType.SESSION_ENDED,
                        source=self._name,
                        payload=SessionPayload(reason="person_left"),
                        session_id=active_session,
                        correlation_id=event.event_id,
                    )
                )
            except InvalidTransitionError as exc:
                logger.error("Manager: Transition fail: %s", exc)
        else:
            logger.warning(
                "Manager: Ignored PERSON_LEFT. FSM in %s", self._fsm.state.name
            )

    def _handle_voice_started(self, event: EventEnvelope) -> None:
        if self._fsm.state == RobotState.READY:
            try:
                self._fsm.transition_to(
                    RobotState.LISTENING,
                    reason="Speech detected",
                    session_id=self._context.session_id,
                    correlation_id=event.event_id,
                )
            except InvalidTransitionError as exc:
                logger.error("Manager: Transition fail: %s", exc)
        else:
            logger.warning(
                "Manager: Ignored VOICE_STARTED. FSM in %s", self._fsm.state.name
            )

    def _handle_voice_stopped(self, event: EventEnvelope) -> None:
        if self._fsm.state == RobotState.LISTENING:
            try:
                self._fsm.transition_to(
                    RobotState.PROCESSING,
                    reason="Speech finished, processing audio",
                    session_id=self._context.session_id,
                    correlation_id=event.event_id,
                )
            except InvalidTransitionError as exc:
                logger.error("Manager: Transition fail: %s", exc)
        else:
            logger.warning(
                "Manager: Ignored VOICE_STOPPED. FSM in %s", self._fsm.state.name
            )

    def _handle_transcript_final(self, event: EventEnvelope) -> None:
        current = self._fsm.state
        # Allow transition from LISTENING directly to PROCESSING if voice_stop was missed
        if current in {RobotState.LISTENING, RobotState.PROCESSING}:
            try:
                if current == RobotState.LISTENING:
                    self._fsm.transition_to(
                        RobotState.PROCESSING,
                        reason="Final transcript received directly",
                        session_id=self._context.session_id,
                        correlation_id=event.event_id,
                    )
                self._context.last_transcript_id = event.event_id

                # Publish QUERY_STARTED to activate RAG/inference pipeline
                payload_data = getattr(event.payload, "text", "Unknown query")
                self._bus.publish(
                    EventEnvelope.create(
                        event_type=EventType.QUERY_STARTED,
                        source=self._name,
                        payload=QueryPayload(query=payload_data),
                        session_id=self._context.session_id,
                        correlation_id=event.event_id,
                    )
                )
            except InvalidTransitionError as exc:
                logger.error("Manager: Transition fail: %s", exc)
        else:
            logger.warning(
                "Manager: Ignored TRANSCRIPT_FINAL. FSM in %s", self._fsm.state.name
            )

    def _handle_query_completed(self, event: EventEnvelope) -> None:
        # QUERY_COMPLETED is a middle diagnostic pipeline checkpoint event.
        # FSM should remain in PROCESSING. We only record context.
        if self._fsm.state == RobotState.PROCESSING:
            self._context.correlation_id = event.event_id
        else:
            logger.warning(
                "Manager: Ignored QUERY_COMPLETED. FSM in %s", self._fsm.state.name
            )

    def _handle_answer_ready(self, event: EventEnvelope) -> None:
        if self._fsm.state == RobotState.PROCESSING:
            try:
                self._context.last_answer_id = event.event_id
                self._fsm.transition_to(
                    RobotState.SPEAKING,
                    reason="Answer generated, starting playback",
                    session_id=self._context.session_id,
                    correlation_id=event.event_id,
                )
            except InvalidTransitionError as exc:
                logger.error("Manager: Transition fail: %s", exc)
        else:
            logger.warning(
                "Manager: Ignored ANSWER_READY. FSM in %s", self._fsm.state.name
            )

    def _handle_tts_lifecycle(self, event: EventEnvelope) -> None:
        current = self._fsm.state
        et = event.event_type

        if current == RobotState.SPEAKING:
            if et in {EventType.TTS_COMPLETED, EventType.TTS_INTERRUPTED}:
                try:
                    reason_msg = (
                        "TTS finished playing"
                        if et == EventType.TTS_COMPLETED
                        else "TTS playback interrupted"
                    )
                    self._fsm.transition_to(
                        RobotState.READY,
                        reason=reason_msg,
                        session_id=self._context.session_id,
                        correlation_id=event.event_id,
                    )
                except InvalidTransitionError as exc:
                    logger.error("Manager: Transition fail during TTS finish: %s", exc)
        else:
            logger.warning(
                "Manager: Ignored TTS event %s. FSM in %s",
                et.value,
                current.name,
            )

    def _handle_timeout(self, event: EventEnvelope) -> None:
        # A timeout event was dispatched. The manager executes explicit recovery
        # actions based on the current state.
        current = self._fsm.state
        payload = event.payload
        # Verify the event matches the current state
        if isinstance(payload, TimeoutPayload) and payload.state == current.name:
            try:
                if current == RobotState.READY:
                    # READY timeout -> transition to IDLE
                    self._fsm.transition_to(
                        RobotState.IDLE,
                        reason="Timeout: User inactive in READY",
                        session_id=self._context.session_id,
                        correlation_id=event.event_id,
                    )
                    self._bus.publish(
                        EventEnvelope.create(
                            event_type=EventType.SESSION_ENDED,
                            source=self._name,
                            payload=SessionPayload(reason="timeout"),
                            session_id=self._context.session_id,
                            correlation_id=event.event_id,
                        )
                    )
                    self._context.clear()
                elif current in {RobotState.LISTENING, RobotState.PROCESSING, RobotState.SPEAKING}:
                    # Recoverable timeouts -> transition back to READY
                    self._fsm.transition_to(
                        RobotState.READY,
                        reason=f"Timeout: Recovery reset from {current.name}",
                        session_id=self._context.session_id,
                        correlation_id=event.event_id,
                    )
            except InvalidTransitionError as exc:
                logger.error("Manager: Timeout recovery transition failed: %s", exc)

    def _handle_error(self, event: EventEnvelope) -> None:
        current = self._fsm.state
        if current != RobotState.SHUTDOWN:
            try:
                payload = event.payload
                is_fatal = getattr(payload, "is_fatal", False)
                
                # Only transition state if error is marked as fatal
                if is_fatal:
                    self._fsm.transition_to(
                        RobotState.ERROR,
                        reason=f"Fatal error in service: {getattr(payload, 'message', '')}",
                        session_id=self._context.session_id,
                        correlation_id=event.event_id,
                    )
            except InvalidTransitionError as exc:
                logger.error("Manager: Transition to ERROR state failed: %s", exc)

    # ─────────────────────────────────────────────────────────────────────────
    # Shutdown & Resource Cleanup
    # ─────────────────────────────────────────────────────────────────────────

    def shutdown(self) -> None:
        """Gracefully unsubscribe and shutdown background threads."""
        logger.info("%s shutting down...", self._name)
        self._timeout_event.set()
        if self._timeout_thread and self._timeout_thread.is_alive():
            self._timeout_thread.join(timeout=2.0)

        with self._lock:
            for handle in self._handles:
                self._bus.unsubscribe(handle)
            self._handles.clear()
        logger.info("%s shutdown complete.", self._name)

    # ─────────────────────────────────────────────────────────────────────────
    # Diagnostics & Metrics APIs
    # ─────────────────────────────────────────────────────────────────────────

    def current_state(self) -> RobotState:
        """Get the current state of the FSM."""
        return self._fsm.state

    def current_context(self) -> dict[str, Any]:
        """Get a snapshot dict of the active interaction context."""
        with self._lock:
            return {
                "session_id": self._context.session_id,
                "correlation_id": self._context.correlation_id,
                "interaction_id": self._context.interaction_id,
                "last_transcript_id": self._context.last_transcript_id,
                "last_answer_id": self._context.last_answer_id,
            }

    def statistics(self) -> dict[str, Any]:
        """Retrieve metrics snapshot."""
        with self._lock:
            return {
                "event_count": self._event_count,
                "uptime_seconds": round(time.perf_counter() - self._start_time, 3),
            }

    def last_event(self) -> EventEnvelope | None:
        """Get the last processed EventEnvelope."""
        with self._lock:
            return self._last_event

    def uptime(self) -> float:
        """Get total runtime duration of the manager in seconds."""
        return time.perf_counter() - self._start_time

    def event_count(self) -> int:
        """Get the total number of events processed."""
        with self._lock:
            return self._event_count

    def current_session(self) -> str | None:
        """Get current session UUID."""
        with self._lock:
            return self._context.session_id
