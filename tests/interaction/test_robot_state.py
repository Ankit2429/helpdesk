"""
Tests for campus_helpdesk.interaction.robot_state
=================================================

Coverage:
1.  All valid transitions in the state transition matrix
2.  All invalid transitions (verifying InvalidTransitionError)
3.  Any state -> ERROR and Any state -> SHUTDOWN (except from SHUTDOWN)
4.  FSM Hook registrations (on_enter, on_exit, on_transition)
5.  Exception isolation in hooks (hook crashes do not rollback state changes)
6.  Transition history tracking, retention limit, durations
7.  State timeouts configuration and checking (check_timeout)
8.  Thread safety (concurrent state transitions)
9.  FSM Statistics generation & Diagnostics payload
10. Latency Benchmarks (transition_to overhead)
"""

from __future__ import annotations

import time
import uuid
import threading
from typing import Any

import pytest

from campus_helpdesk.interaction.robot_state import (
    InvalidTransitionError,
    RobotState,
    RobotStateMachine,
    TransitionRecord,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fsm() -> RobotStateMachine:
    return RobotStateMachine(initial_state=RobotState.BOOTING, max_history_size=100)


# ===========================================================================
# 1. State Enum & Metadata Checks
# ===========================================================================


class TestRobotStateEnum:
    def test_all_states_exist(self) -> None:
        expected = {
            "BOOTING",
            "INITIALIZING",
            "IDLE",
            "READY",
            "LISTENING",
            "PROCESSING",
            "SPEAKING",
            "ERROR",
            "SHUTDOWN",
        }
        actual = {s.name for s in RobotState}
        assert actual == expected

    def test_values_are_strings(self) -> None:
        for s in RobotState:
            assert isinstance(s.value, str)
            assert s.value == s.name


# ===========================================================================
# 2. Transition Matrix Verification
# ===========================================================================


class TestTransitions:
    def test_initial_state(self, fsm: RobotStateMachine) -> None:
        assert fsm.state is RobotState.BOOTING
        assert fsm.previous_state is None
        assert fsm.transition_count() == 0

    def test_valid_pathway_normal_flow(self, fsm: RobotStateMachine) -> None:
        # BOOTING -> INITIALIZING
        fsm.transition_to(RobotState.INITIALIZING, reason="Booted ok")
        assert fsm.state is RobotState.INITIALIZING
        assert fsm.previous_state is RobotState.BOOTING

        # INITIALIZING -> IDLE
        fsm.transition_to(RobotState.IDLE, reason="Services ready")
        assert fsm.state is RobotState.IDLE

        # IDLE -> READY
        fsm.transition_to(RobotState.READY, reason="Person approach")
        assert fsm.state is RobotState.READY

        # READY -> LISTENING
        fsm.transition_to(RobotState.LISTENING, reason="Speech start")
        assert fsm.state is RobotState.LISTENING

        # LISTENING -> PROCESSING
        fsm.transition_to(RobotState.PROCESSING, reason="Speech stop")
        assert fsm.state is RobotState.PROCESSING

        # PROCESSING -> SPEAKING
        fsm.transition_to(RobotState.SPEAKING, reason="Answer ready")
        assert fsm.state is RobotState.SPEAKING

        # SPEAKING -> READY
        fsm.transition_to(RobotState.READY, reason="TTS complete")
        assert fsm.state is RobotState.READY

        # READY -> IDLE
        fsm.transition_to(RobotState.IDLE, reason="Person left")
        assert fsm.state is RobotState.IDLE

    def test_transition_to_self_is_noop(self, fsm: RobotStateMachine) -> None:
        # BOOTING -> BOOTING
        fsm.transition_to(RobotState.BOOTING)
        assert fsm.state is RobotState.BOOTING
        assert fsm.transition_count() == 0

    @pytest.mark.parametrize(
        "from_state, to_state",
        [
            (RobotState.BOOTING, RobotState.LISTENING),
            (RobotState.INITIALIZING, RobotState.SPEAKING),
            (RobotState.IDLE, RobotState.PROCESSING),
            (RobotState.READY, RobotState.INITIALIZING),
            (RobotState.SPEAKING, RobotState.LISTENING),
            (RobotState.SHUTDOWN, RobotState.BOOTING),
            (RobotState.SHUTDOWN, RobotState.READY),
        ],
    )
    def test_invalid_transitions_raise_exception(
        self, from_state: RobotState, to_state: RobotState
    ) -> None:
        fsm = RobotStateMachine(initial_state=from_state)
        with pytest.raises(InvalidTransitionError) as exc_info:
            fsm.transition_to(to_state)
        assert exc_info.value.from_state is from_state
        assert exc_info.value.to_state is to_state

    @pytest.mark.parametrize(
        "start_state",
        [
            RobotState.BOOTING,
            RobotState.INITIALIZING,
            RobotState.IDLE,
            RobotState.READY,
            RobotState.LISTENING,
            RobotState.PROCESSING,
            RobotState.SPEAKING,
            RobotState.ERROR,
        ],
    )
    def test_universal_transition_to_error_and_shutdown(
        self, start_state: RobotState
    ) -> None:
        # Check transition to ERROR
        f1 = RobotStateMachine(initial_state=start_state)
        f1.transition_to(RobotState.ERROR, reason="Crash test")
        assert f1.state is RobotState.ERROR

        # Check transition to SHUTDOWN
        f2 = RobotStateMachine(initial_state=start_state)
        f2.transition_to(RobotState.SHUTDOWN, reason="Power off")
        assert f2.state is RobotState.SHUTDOWN

    def test_error_state_transitions(self, fsm: RobotStateMachine) -> None:
        fsm.transition_to(RobotState.ERROR)
        assert fsm.state is RobotState.ERROR

        # Can go ERROR -> INITIALIZING
        fsm.transition_to(RobotState.INITIALIZING)
        assert fsm.state is RobotState.INITIALIZING

        # Reset back to error
        fsm.transition_to(RobotState.ERROR)
        # Can go ERROR -> SHUTDOWN
        fsm.transition_to(RobotState.SHUTDOWN)
        assert fsm.state is RobotState.SHUTDOWN


# ===========================================================================
# 3. Transition Hooks & Exception Isolation
# ===========================================================================


class TestTransitionHooks:
    def test_enter_hooks(self, fsm: RobotStateMachine) -> None:
        entered: list[RobotState] = []
        fsm.register_on_enter(RobotState.INITIALIZING, lambda s: entered.append(s))
        fsm.register_on_enter(RobotState.IDLE, lambda s: entered.append(s))

        fsm.transition_to(RobotState.INITIALIZING)
        fsm.transition_to(RobotState.IDLE)

        assert entered == [RobotState.INITIALIZING, RobotState.IDLE]

    def test_exit_hooks(self, fsm: RobotStateMachine) -> None:
        exited: list[RobotState] = []
        fsm.register_on_exit(RobotState.BOOTING, lambda s: exited.append(s))
        fsm.register_on_exit(RobotState.INITIALIZING, lambda s: exited.append(s))

        fsm.transition_to(RobotState.INITIALIZING)
        fsm.transition_to(RobotState.IDLE)

        assert exited == [RobotState.BOOTING, RobotState.INITIALIZING]

    def test_transition_hooks(self, fsm: RobotStateMachine) -> None:
        changes: list[tuple[RobotState, RobotState]] = []
        fsm.register_on_transition(lambda f, t: changes.append((f, t)))

        fsm.transition_to(RobotState.INITIALIZING)
        fsm.transition_to(RobotState.IDLE)

        assert changes == [
            (RobotState.BOOTING, RobotState.INITIALIZING),
            (RobotState.INITIALIZING, RobotState.IDLE),
        ]

    def test_hook_exception_isolation(self, fsm: RobotStateMachine) -> None:
        """Exceptions in hooks must not block transition or corrupt state."""
        def bad_exit(s: RobotState) -> None:
            raise RuntimeError("broken exit hook")

        def bad_enter(s: RobotState) -> None:
            raise ValueError("broken enter hook")

        def bad_transition(f: RobotState, t: RobotState) -> None:
            raise KeyError("broken transition hook")

        fsm.register_on_exit(RobotState.BOOTING, bad_exit)
        fsm.register_on_transition(bad_transition)
        fsm.register_on_enter(RobotState.INITIALIZING, bad_enter)

        # Transition should still execute completely
        fsm.transition_to(RobotState.INITIALIZING)

        assert fsm.state is RobotState.INITIALIZING
        assert fsm.previous_state is RobotState.BOOTING


# ===========================================================================
# 4. History Tracking & Retention
# ===========================================================================


class TestHistory:
    def test_history_records_details(self, fsm: RobotStateMachine) -> None:
        session = str(uuid.uuid4())
        correlation = str(uuid.uuid4())

        time.sleep(0.005)  # Make sure booting duration is non-zero
        fsm.transition_to(
            RobotState.INITIALIZING,
            reason="Init start",
            session_id=session,
            correlation_id=correlation,
        )

        h = fsm.history()
        assert len(h) == 1
        record = h[0]
        assert isinstance(record, TransitionRecord)
        assert record.from_state is RobotState.BOOTING
        assert record.to_state is RobotState.INITIALIZING
        assert record.reason == "Init start"
        assert record.session_id == session
        assert record.correlation_id == correlation
        assert record.duration > 0.0
        assert record.timestamp > 0.0

    def test_history_retention_limit(self) -> None:
        # Create FSM with retention limit of 2
        fsm = RobotStateMachine(initial_state=RobotState.BOOTING, max_history_size=2)
        fsm.transition_to(RobotState.INITIALIZING)
        fsm.transition_to(RobotState.IDLE)
        fsm.transition_to(RobotState.READY)

        h = fsm.history()
        assert len(h) == 2
        # Oldest (BOOTING -> INITIALIZING) should be discarded
        assert h[0].from_state is RobotState.INITIALIZING
        assert h[1].from_state is RobotState.IDLE


# ===========================================================================
# 5. Timeouts
# ===========================================================================


class TestTimeouts:
    def test_timeout_checking(self, fsm: RobotStateMachine) -> None:
        assert fsm.check_timeout() is False  # No timeout configured

        # Configure timeout of 5 milliseconds
        fsm.configure_timeout(RobotState.BOOTING, 0.005)
        assert fsm.get_timeout(RobotState.BOOTING) == 0.005

        assert fsm.check_timeout() is False
        time.sleep(0.01)
        assert fsm.check_timeout() is True

    def test_timeout_clear(self, fsm: RobotStateMachine) -> None:
        fsm.configure_timeout(RobotState.BOOTING, 5.0)
        assert fsm.get_timeout(RobotState.BOOTING) == 5.0

        fsm.configure_timeout(RobotState.BOOTING, 0.0)  # clearing timeout
        assert fsm.get_timeout(RobotState.BOOTING) is None


# ===========================================================================
# 6. Statistics, Diagnostics & Uptime
# ===========================================================================


class TestDiagnosticsAndStats:
    def test_diagnostics_structure(self, fsm: RobotStateMachine) -> None:
        diag = fsm.diagnostics()
        assert diag["current_state"] == "BOOTING"
        assert diag["previous_state"] is None
        assert diag["transition_count"] == 0
        assert diag["uptime_seconds"] >= 0.0

        fsm.transition_to(RobotState.INITIALIZING, reason="step 1")
        diag2 = fsm.diagnostics()
        assert diag2["current_state"] == "INITIALIZING"
        assert diag2["previous_state"] == "BOOTING"
        assert diag2["last_transition"]["reason"] == "step 1"

    def test_statistics(self, fsm: RobotStateMachine) -> None:
        time.sleep(0.002)
        fsm.transition_to(RobotState.INITIALIZING)
        time.sleep(0.002)
        fsm.transition_to(RobotState.IDLE)

        stats = fsm.state_statistics()
        assert stats["transitions_total"] == 2
        assert stats["state_durations"]["BOOTING"] > 0
        assert stats["state_durations"]["INITIALIZING"] > 0
        assert stats["transition_counts"]["BOOTING->INITIALIZING"] == 1
        assert stats["transition_counts"]["INITIALIZING->IDLE"] == 1


# ===========================================================================
# 7. Thread Safety
# ===========================================================================


class TestThreadSafety:
    def test_concurrent_transitions(self) -> None:
        """Stress FSM with threads competing to transition into different allowed states.

        Legitimate targets from READY: LISTENING or IDLE.
        """
        fsm = RobotStateMachine(initial_state=RobotState.READY)
        errors: list[Exception] = []

        def worker(target: RobotState) -> None:
            try:
                # One thread will win, the other must raise InvalidTransitionError
                # once the state has changed to a state where the target is invalid.
                fsm.transition_to(target)
            except InvalidTransitionError:
                pass
            except Exception as exc:
                errors.append(exc)

        # Spawning 2 threads transitioning to different targets
        t1 = threading.Thread(target=worker, args=(RobotState.LISTENING,))
        t2 = threading.Thread(target=worker, args=(RobotState.IDLE,))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert not errors
        # The FSM state must end up in one of the two target states cleanly
        assert fsm.state in {RobotState.LISTENING, RobotState.IDLE}


# ===========================================================================
# 8. Benchmarks
# ===========================================================================


class TestBenchmarks:
    N = 10_000

    def test_transition_latency(self) -> None:
        fsm = RobotStateMachine(initial_state=RobotState.READY)
        # Alternate valid states to avoid InvalidTransitionError
        # READY -> LISTENING -> READY -> LISTENING
        t0 = time.perf_counter()
        for _ in range(self.N):
            fsm.transition_to(RobotState.LISTENING)
            fsm.transition_to(RobotState.READY)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        avg_us = (elapsed_ms / (self.N * 2)) * 1000

        print(
            f"\n[Benchmark] FSM transition: {elapsed_ms:.1f} ms for {self.N*2} transitions "
            f"(avg {avg_us:.2f} µs/transition)"
        )
        assert avg_us < 100.0, f"Average transition overhead {avg_us:.2f} µs exceeds 100 µs target"
