"""
Campus Helpdesk Robot – Phase 3: Finite State Machine (FSM)
==========================================================

Module: campus_helpdesk.interaction.robot_state
File:   src/campus_helpdesk/interaction/robot_state.py
Version: 1.0

This module implements the core Finite State Machine (FSM) for the robot's
real-time Interaction Engine. The state machine is the single source of truth
for the robot's lifecycle. No service is allowed to maintain its own robot
state; every state transition must be validated through this FSM.

States
------
*  **BOOTING** – The initial power-on state.
*  **INITIALIZING** – Hardware interfaces and dependencies are loading.
*  **IDLE** – The robot is active but waiting for a person to approach.
*  **READY** – A person has been detected; the robot is ready for input.
*  **LISTENING** – The microphone is open and voice activity is being captured.
*  **PROCESSING** – Speech is being transcribed and the RAG engine is running.
*  **SPEAKING** – The robot is playing back an answer via TTS.
*  **ERROR** – A fatal service failure has occurred.
*  **SHUTDOWN** – The system is shutting down gracefully.

Thread Model
------------
The state machine is fully thread-safe. All state checks, transition
validations, hook execution, and history insertions are protected by a
reentrant lock (``threading.RLock``). Multiple service threads may query or
request state changes concurrently.

Hooks
-----
Callbacks can be registered to fire on FSM lifecycle events:
*  ``on_enter(state, callback)`` – fired when transitioning INTO a state.
*  ``on_exit(state, callback)`` – fired when transitioning OUT of a state.
*  ``on_transition(callback)`` – fired on any valid state transition.

Hooks run synchronously on the thread that initiated the transition.
Exceptions raised within a hook are logged and isolated; they do not crash the
FSM, prevent the state from changing, or corrupt the FSM's internal state.

Timeouts
--------
States can have configured timeouts. A timeout helper ``check_timeout()`` returns
a boolean indicating whether the current state has exceeded its allocated limit.
This does NOT change the state automatically; the Interaction Manager is
responsible for handling state recovery policies.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum, unique
from typing import Callable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class InvalidTransitionError(Exception):
    """Raised when a state transition is requested that violates the FSM rules."""

    def __init__(self, from_state: RobotState, to_state: RobotState) -> None:
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(
            f"Invalid transition from {from_state.name} to {to_state.name}"
        )


# ---------------------------------------------------------------------------
# RobotState Enum
# ---------------------------------------------------------------------------


@unique
class RobotState(str, Enum):
    """Lifecycle states for the robot.

    Each state value is a string so it is serialisable to JSON/logs easily.
    """

    BOOTING = "BOOTING"
    """Initial boot sequence when process starts.
    - Entry: Main application bootstrap.
    - Exit: Config and environment loaded.
    - Timeout: None.
    - Recovery: Restart process.
    """

    INITIALIZING = "INITIALIZING"
    """Bootstrapping hardware interfaces and services (VAD, STT, TTS, RAG).
    - Entry: Configuration successfully loaded.
    - Exit: All services report healthy.
    - Timeout: None.
    - Recovery: Transition to ERROR state.
    """

    IDLE = "IDLE"
    """Waiting for a person to be detected by the camera.
    - Entry: Initialization complete, or person left the conversation.
    - Exit: Camera detects a person.
    - Timeout: None (low-power standby).
    - Recovery: None.
    """

    READY = "READY"
    """A person is detected and present. Waiting for speech/interaction.
    - Entry: Camera reports person present, or TTS completes talking.
    - Exit: VAD triggers speech detection, or person leaves.
    - Timeout: Configurable (e.g., 30s). If exceeded, transition to IDLE.
    - Recovery: Transition back to IDLE.
    """

    LISTENING = "LISTENING"
    """Audio capture is in progress (microphone active).
    - Entry: VAD triggers voice start.
    - Exit: VAD triggers voice stop.
    - Timeout: Configurable (e.g., 15s). If silence timeout, return to READY.
    - Recovery: Transition back to READY.
    """

    PROCESSING = "PROCESSING"
    """Speech is being transcribed and RAG/LLM inference is processing.
    - Entry: Speech stops, audio segment dispatched.
    - Exit: LLM generation completes and answer is ready.
    - Timeout: Configurable (e.g., 30s). If exceeded, transition to ERROR.
    - Recovery: Transition to READY with error voice prompt.
    """

    SPEAKING = "SPEAKING"
    """Audio output is playing (TTS active).
    - Entry: Answer generation ready.
    - Exit: Playback completed, or user interrupts.
    - Timeout: Configurable (e.g., 60s). If exceeded, transition to READY.
    - Recovery: Force stop audio playback, transition to READY.
    """

    ERROR = "ERROR"
    """A fatal error has occurred in one of the background services.
    - Entry: Any unhandled service exception or timeout failure.
    - Exit: Admin reset or recovery checklist completed.
    - Timeout: None.
    - Recovery: Transition to INITIALIZING to attempt a soft reload.
    """

    SHUTDOWN = "SHUTDOWN"
    """Graceful exit of all services and processes.
    - Entry: SIGTERM or system shutdown event.
    - Exit: Terminal process termination.
    - Timeout: None.
    - Recovery: Hard power cycle.
    """


# ---------------------------------------------------------------------------
# Transition History Record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TransitionRecord:
    """Immutable record of an FSM transition.

    Attributes
    ----------
    from_state:
        The state the FSM exited.
    to_state:
        The state the FSM entered.
    timestamp:
        System time (monotonic seconds) when the transition took place.
    duration:
        Time in seconds spent in ``from_state``.
    reason:
        Optional description/cause of the transition.
    session_id:
        Optional session identifier.
    correlation_id:
        Optional correlation identifier for tracing.
    """

    from_state: RobotState
    to_state: RobotState
    timestamp: float
    duration: float
    reason: str | None = None
    session_id: str | None = None
    correlation_id: str | None = None


# ---------------------------------------------------------------------------
# Transition Map
# ---------------------------------------------------------------------------

_VALID_TRANSITIONS: dict[RobotState, set[RobotState]] = {
    RobotState.BOOTING: {RobotState.INITIALIZING, RobotState.ERROR, RobotState.SHUTDOWN},
    RobotState.INITIALIZING: {RobotState.IDLE, RobotState.ERROR, RobotState.SHUTDOWN},
    RobotState.IDLE: {RobotState.READY, RobotState.ERROR, RobotState.SHUTDOWN},
    RobotState.READY: {RobotState.LISTENING, RobotState.IDLE, RobotState.ERROR, RobotState.SHUTDOWN},
    RobotState.LISTENING: {RobotState.PROCESSING, RobotState.READY, RobotState.ERROR, RobotState.SHUTDOWN},
    RobotState.PROCESSING: {RobotState.SPEAKING, RobotState.READY, RobotState.ERROR, RobotState.SHUTDOWN},
    RobotState.SPEAKING: {RobotState.READY, RobotState.ERROR, RobotState.SHUTDOWN},
    RobotState.ERROR: {RobotState.INITIALIZING, RobotState.SHUTDOWN},
    RobotState.SHUTDOWN: set(),  # Terminal state
}


# ---------------------------------------------------------------------------
# RobotStateMachine
# ---------------------------------------------------------------------------


class RobotStateMachine:
    """Thread-safe FSM tracking the robot state.

    Parameters
    ----------
    initial_state:
        The state to start in. Defaults to ``RobotState.BOOTING``.
    max_history_size:
        Maximum transition records to retain in memory. Defaults to ``1000``.
    """

    def __init__(
        self,
        initial_state: RobotState = RobotState.BOOTING,
        max_history_size: int = 1000,
    ) -> None:
        self._lock = time.perf_counter  # Just using import reference to ensure precision
        import threading
        self._fsm_lock = threading.RLock()

        self._state = initial_state
        self._previous_state: RobotState | None = None
        self._max_history = max_history_size
        self._history: list[TransitionRecord] = []

        # Lifecycle timestamps
        self._start_time = time.perf_counter()
        self._state_entered_at = time.perf_counter()

        # Configured timeouts (state -> seconds)
        self._timeouts: dict[RobotState, float] = {}

        # Hooks
        # Key: RobotState -> list of Callable[[RobotState], None]
        self._on_enter_hooks: dict[RobotState, list[Callable[[RobotState], None]]] = {
            s: [] for s in RobotState
        }
        self._on_exit_hooks: dict[RobotState, list[Callable[[RobotState], None]]] = {
            s: [] for s in RobotState
        }
        self._on_transition_hooks: list[Callable[[RobotState, RobotState], None]] = []

        logger.info("RobotStateMachine initialized in state %s", initial_state.name)

    # ─────────────────────────────────────────────────────────────────────────
    # State Accessors
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def state(self) -> RobotState:
        """Get the current robot state."""
        with self._fsm_lock:
            return self._state

    @property
    def previous_state(self) -> RobotState | None:
        """Get the immediately preceding robot state (or None)."""
        with self._fsm_lock:
            return self._previous_state

    def time_in_state(self) -> float:
        """Get the duration (in seconds) the FSM has been in the current state."""
        with self._fsm_lock:
            return time.perf_counter() - self._state_entered_at

    def transition_count(self) -> int:
        """Get the total number of valid transitions executed."""
        with self._fsm_lock:
            return len(self._history)

    def uptime(self) -> float:
        """Get the total uptime of the FSM since creation (in seconds)."""
        return time.perf_counter() - self._start_time

    # ─────────────────────────────────────────────────────────────────────────
    # Transition Logic
    # ─────────────────────────────────────────────────────────────────────────

    def transition_to(
        self,
        to_state: RobotState,
        *,
        reason: str | None = None,
        session_id: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Request a transition to another state.

        Parameters
        ----------
        to_state:
            The target state to enter.
        reason:
            Optional context string detailing why the transition was triggered.
        session_id:
            Optional session UUID.
        correlation_id:
            Optional trace correlation UUID.

        Raises
        ------
        InvalidTransitionError
            If the requested transition violates FSM constraints.
        """
        with self._fsm_lock:
            from_state = self._state

            # Short-circuit if transitioning to the exact same state (noop)
            if from_state == to_state:
                return

            # Validate transition legality
            allowed = _VALID_TRANSITIONS.get(from_state, set())
            # SHUTDOWN and ERROR are universally transitionable to from any state
            # EXCEPT from SHUTDOWN itself (which is terminal)
            is_legal = (
                to_state in allowed
                or (to_state == RobotState.SHUTDOWN and from_state != RobotState.SHUTDOWN)
                or (to_state == RobotState.ERROR and from_state != RobotState.SHUTDOWN)
            )

            if not is_legal:
                logger.warning(
                    "FSM: Illegal transition requested from %s to %s",
                    from_state.name,
                    to_state.name,
                )
                raise InvalidTransitionError(from_state, to_state)

            now = time.perf_counter()
            duration = now - self._state_entered_at

            # 1. Execute Exit Hooks for from_state
            for hook in self._on_exit_hooks[from_state]:
                try:
                    hook(from_state)
                except Exception as exc:
                    logger.error(
                        "FSM: Exception inside on_exit hook for %s: %s",
                        from_state.name,
                        exc,
                    )

            # 2. Transition State
            self._previous_state = from_state
            self._state = to_state
            self._state_entered_at = now

            # 3. Log and Record Transition History
            record = TransitionRecord(
                from_state=from_state,
                to_state=to_state,
                timestamp=now,
                duration=duration,
                reason=reason,
                session_id=session_id,
                correlation_id=correlation_id,
            )
            self._history.append(record)
            if len(self._history) > self._max_history:
                self._history.pop(0)

            logger.info(
                "FSM Transition: %s -> %s (duration=%.3fs, reason=%r)",
                from_state.name,
                to_state.name,
                duration,
                reason,
            )

            # 4. Execute Transition Hooks
            for transition_hook in self._on_transition_hooks:
                try:
                    transition_hook(from_state, to_state)
                except Exception as exc:
                    logger.error("FSM: Exception inside transition hook: %s", exc)

            # 5. Execute Enter Hooks for to_state
            for hook in self._on_enter_hooks[to_state]:
                try:
                    hook(to_state)
                except Exception as exc:
                    logger.error(
                        "FSM: Exception inside on_enter hook for %s: %s",
                        to_state.name,
                        exc,
                    )

    # ─────────────────────────────────────────────────────────────────────────
    # Hooks API
    # ─────────────────────────────────────────────────────────────────────────

    def register_on_enter(
        self, state: RobotState, callback: Callable[[RobotState], None]
    ) -> None:
        """Register a callback to invoke when entering a specific state."""
        with self._fsm_lock:
            self._on_enter_hooks[state].append(callback)

    def register_on_exit(
        self, state: RobotState, callback: Callable[[RobotState], None]
    ) -> None:
        """Register a callback to invoke when exiting a specific state."""
        with self._fsm_lock:
            self._on_exit_hooks[state].append(callback)

    def register_on_transition(
        self, callback: Callable[[RobotState, RobotState], None]
    ) -> None:
        """Register a callback to invoke on any valid transition."""
        with self._fsm_lock:
            self._on_transition_hooks.append(callback)

    # ─────────────────────────────────────────────────────────────────────────
    # Timeouts & Checkers
    # ─────────────────────────────────────────────────────────────────────────

    def configure_timeout(self, state: RobotState, timeout_seconds: float) -> None:
        """Set a timeout limit for a state.

        A timeout value <= 0 removes the configuration.
        """
        with self._fsm_lock:
            if timeout_seconds <= 0:
                self._timeouts.pop(state, None)
            else:
                self._timeouts[state] = timeout_seconds

    def get_timeout(self, state: RobotState) -> float | None:
        """Get the configured timeout limit for a state (or None)."""
        with self._fsm_lock:
            return self._timeouts.get(state)

    def check_timeout(self) -> bool:
        """Check if the current state has exceeded its configured timeout.

        Returns
        -------
        bool
            ``True`` if a timeout is configured for the current state and the FSM
            has resided in it longer than the timeout limit; ``False`` otherwise.
        """
        with self._fsm_lock:
            limit = self._timeouts.get(self._state)
            if limit is None:
                return False
            return self.time_in_state() > limit

    # ─────────────────────────────────────────────────────────────────────────
    # Diagnostics & History
    # ─────────────────────────────────────────────────────────────────────────

    def history(self) -> list[TransitionRecord]:
        """Get a copy of the transition history list."""
        with self._fsm_lock:
            return list(self._history)

    def state_statistics(self) -> dict[str, Any]:
        """Aggregate stats regarding time spent in states and transition counts.

        Returns
        -------
        dict with keys:
            ``transitions_total`` – Total number of state transitions executed.
            ``state_durations``   – Dict mapping state name to total seconds spent.
            ``transition_counts`` – Dict mapping transition tuple to count.
        """
        with self._fsm_lock:
            state_durations: dict[str, float] = {s.name: 0.0 for s in RobotState}
            transition_counts: dict[str, int] = {}

            # Sum history records
            for record in self._history:
                state_durations[record.from_state.name] += record.duration
                key = f"{record.from_state.name}->{record.to_state.name}"
                transition_counts[key] = transition_counts.get(key, 0) + 1

            # Account for the current state's ongoing duration
            state_durations[self._state.name] += self.time_in_state()

            return {
                "transitions_total": len(self._history),
                "state_durations": state_durations,
                "transition_counts": transition_counts,
            }

    def diagnostics(self) -> dict[str, Any]:
        """Retrieve full diagnostics payload for the UI/CLI.

        Returns
        -------
        dict
        """
        with self._fsm_lock:
            last_record = self._history[-1] if self._history else None
            return {
                "current_state": self._state.name,
                "previous_state": self._previous_state.name if self._previous_state else None,
                "time_in_current_state_seconds": round(self.time_in_state(), 3),
                "last_transition": (
                    {
                        "from_state": last_record.from_state.name,
                        "to_state": last_record.to_state.name,
                        "duration_prev": round(last_record.duration, 3),
                        "reason": last_record.reason,
                    }
                    if last_record
                    else None
                ),
                "transition_count": len(self._history),
                "history_size": len(self._history),
                "configured_timeouts": {k.name: v for k, v in self._timeouts.items()},
                "uptime_seconds": round(self.uptime(), 3),
            }
