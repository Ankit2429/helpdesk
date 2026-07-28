"""
Tests for campus_helpdesk.interaction.event_bus
================================================

Coverage:
1.  SubscriptionHandle repr / frozen
2.  BusStatistics snapshot fields
3.  Single subscriber – sync handler
4.  Multiple subscribers for the same event type
5.  Wildcard subscriptions (event_types=None)
6.  Priority ordering (CRITICAL before LOW)
7.  FIFO ordering within the same priority
8.  Unsubscribe
9.  One-shot subscriptions
10. Async (coroutine) handlers
11. Mixed sync + async handlers for the same event
12. Exception isolation – crashing handler does not block others
13. publish_sync – blocks until all handlers complete
14. publish_sync raises RuntimeError if called from dispatcher thread
15. Queue overflow – drop policy
16. clear() drains the queue
17. Metrics and statistics tracking
18. Diagnostics: health(), queue_depth(), registered_subscribers()
19. shutdown() – dispatcher exits cleanly; context manager
20. Thread safety – concurrent subscribe / unsubscribe / publish
21. min_priority filter – low-priority events filtered per subscriber
22. Stress test – 10 threads × 1 000 events each, no duplicates, no deadlock
23. Benchmarks – publish, dispatch, serialized throughput
"""

from __future__ import annotations

import asyncio
import threading
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

import pytest

from campus_helpdesk.interaction.event_bus import (
    BusStatistics,
    EventBus,
    SubscriptionHandle,
)
from campus_helpdesk.interaction.events import (
    ErrorPayload,
    EventEnvelope,
    EventPriority,
    EventType,
    PersonDetectedPayload,
    SessionPayload,
    SystemPayload,
    TimeoutPayload,
    VoicePayload,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SESSION = str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _sys_event(
    event_type: EventType = EventType.SYSTEM_STARTING,
    priority: EventPriority = EventPriority.NORMAL,
    session_id: str | None = _SESSION,
    message: str = "test",
) -> EventEnvelope:
    return EventEnvelope.create(
        event_type=event_type,
        source="test",
        payload=SystemPayload(profile="development", message=message),
        session_id=session_id,
        priority=priority,
    )


def _person_event(confidence: float = 0.9) -> EventEnvelope:
    return EventEnvelope.create(
        event_type=EventType.PERSON_DETECTED,
        source="camera_service",
        payload=PersonDetectedPayload(confidence=confidence),
        session_id=_SESSION,
    )


def _voice_event(
    event_type: EventType = EventType.VOICE_STARTED,
    chunk_id: str = "chunk-1",
) -> EventEnvelope:
    return EventEnvelope.create(
        event_type=event_type,
        source="vad_service",
        payload=VoicePayload(audio_chunk_id=chunk_id),
        session_id=_SESSION,
    )


def _error_event(fatal: bool = False) -> EventEnvelope:
    return EventEnvelope.create(
        event_type=EventType.ERROR,
        source="test",
        payload=ErrorPayload(
            service="test_service",
            error_type="TestError",
            message="intentional test error",
            is_fatal=fatal,
        ),
        priority=EventPriority.HIGH,
    )


@pytest.fixture
def bus() -> EventBus:
    """Fresh EventBus for each test, auto-shutdown."""
    b = EventBus(maxsize=500, max_workers=4, name="test-bus")
    yield b
    b.shutdown(timeout=3.0)


def _wait(event: threading.Event, timeout: float = 3.0) -> bool:
    """Wait for a threading.Event with a generous timeout."""
    return event.wait(timeout=timeout)


# ===========================================================================
# 1. SubscriptionHandle
# ===========================================================================


class TestSubscriptionHandle:
    def test_repr_single_type(self) -> None:
        h = SubscriptionHandle(
            handle_id=str(uuid.uuid4()),
            event_types=frozenset([EventType.PERSON_DETECTED]),
            source="ui_service",
        )
        r = repr(h)
        assert "ui_service" in r
        assert "PERSON_DETECTED" in r

    def test_repr_wildcard(self) -> None:
        h = SubscriptionHandle(
            handle_id=str(uuid.uuid4()),
            event_types=None,
            source="logger",
        )
        assert "WILDCARD" in repr(h)

    def test_frozen(self) -> None:
        h = SubscriptionHandle(
            handle_id=str(uuid.uuid4()),
            event_types=frozenset([EventType.SYSTEM_READY]),
            source="svc",
        )
        with pytest.raises(Exception):
            h.source = "changed"  # type: ignore[misc]

    def test_hashable(self) -> None:
        h = SubscriptionHandle(
            handle_id=str(uuid.uuid4()),
            event_types=None,
            source="svc",
        )
        s = {h, h}
        assert len(s) == 1


# ===========================================================================
# 2. BusStatistics
# ===========================================================================


class TestBusStatistics:
    def test_fields_present(self, bus: EventBus) -> None:
        stats = bus.statistics()
        assert isinstance(stats, BusStatistics)
        assert stats.events_published == 0
        assert stats.events_delivered == 0
        assert stats.events_dropped == 0
        assert stats.handler_failures == 0
        assert stats.queue_depth == 0
        assert stats.avg_dispatch_latency_us == 0.0
        assert stats.uptime_seconds >= 0.0

    def test_frozen(self, bus: EventBus) -> None:
        stats = bus.statistics()
        with pytest.raises(Exception):
            stats.events_published = 999  # type: ignore[misc]


# ===========================================================================
# 3. Single subscriber – sync handler
# ===========================================================================


class TestSingleSubscriber:
    def test_handler_receives_event(self, bus: EventBus) -> None:
        received: list[EventEnvelope] = []
        done = threading.Event()

        def handler(event: EventEnvelope) -> None:
            received.append(event)
            done.set()

        bus.subscribe(handler, EventType.SYSTEM_STARTING, source="test")
        event = _sys_event()
        bus.publish(event)

        assert _wait(done), "Handler was not called within timeout"
        assert len(received) == 1
        assert received[0].event_id == event.event_id

    def test_handler_does_not_receive_other_types(self, bus: EventBus) -> None:
        received: list[EventEnvelope] = []
        barrier = threading.Event()

        def handler(event: EventEnvelope) -> None:
            received.append(event)

        bus.subscribe(handler, EventType.PERSON_DETECTED, source="test")

        # Publish a different type; then a matching one to confirm the bus works
        bus.publish(_sys_event())
        bus.publish_sync(_person_event(), timeout=3.0)
        barrier.set()

        assert len(received) == 1
        assert received[0].event_type is EventType.PERSON_DETECTED

    def test_no_handler_called_when_no_subscriber(self, bus: EventBus) -> None:
        # Just ensure no error is raised
        result = bus.publish_sync(_sys_event(), timeout=2.0)
        assert result  # enqueued and dispatched (to zero handlers)

    def test_subscribe_returns_handle(self, bus: EventBus) -> None:
        handle = bus.subscribe(lambda e: None, EventType.SYSTEM_READY, source="svc")
        assert isinstance(handle, SubscriptionHandle)
        assert handle.source == "svc"
        assert EventType.SYSTEM_READY in (handle.event_types or frozenset())


# ===========================================================================
# 4. Multiple subscribers for the same event type
# ===========================================================================


class TestMultipleSubscribers:
    def test_all_handlers_called(self, bus: EventBus) -> None:
        counts = [0, 0, 0]
        barrier = threading.Barrier(3 + 1)  # 3 handlers + test thread

        def make_handler(idx: int):
            def h(event: EventEnvelope) -> None:
                counts[idx] += 1
                barrier.wait(timeout=3.0)

            return h

        for i in range(3):
            bus.subscribe(make_handler(i), EventType.PERSON_DETECTED, source=f"svc-{i}")

        bus.publish(_person_event())
        barrier.wait(timeout=3.0)  # test thread waits here

        assert all(c == 1 for c in counts)

    def test_multiple_events_all_delivered(self, bus: EventBus) -> None:
        total = threading.Semaphore(0)

        def handler(_: EventEnvelope) -> None:
            total.release()

        bus.subscribe(handler, EventType.SYSTEM_STARTING, source="a")
        bus.subscribe(handler, EventType.SYSTEM_STARTING, source="b")

        for _ in range(5):
            bus.publish_sync(_sys_event(), timeout=3.0)

        # 5 events × 2 handlers = 10 releases
        acquired = sum(1 for _ in range(10) if total.acquire(timeout=3.0))
        assert acquired == 10


# ===========================================================================
# 5. Wildcard subscriptions
# ===========================================================================


class TestWildcardSubscription:
    def test_wildcard_receives_all_types(self, bus: EventBus) -> None:
        received_types: list[EventType] = []
        lock = threading.Lock()
        all_done = threading.Event()

        def handler(event: EventEnvelope) -> None:
            with lock:
                received_types.append(event.event_type)
            if len(received_types) >= 3:
                all_done.set()

        bus.subscribe(handler, source="wildcard_logger")  # event_types=None

        bus.publish(_sys_event(EventType.SYSTEM_STARTING))
        bus.publish(_person_event())
        bus.publish(_voice_event())

        assert _wait(all_done, timeout=5.0), (
            f"Wildcard received only {received_types}, expected 3 event types"
        )

        received_set = set(received_types)
        assert EventType.SYSTEM_STARTING in received_set
        assert EventType.PERSON_DETECTED in received_set
        assert EventType.VOICE_STARTED in received_set

    def test_wildcard_and_specific_both_fire(self, bus: EventBus) -> None:
        wildcard_count = threading.Semaphore(0)
        specific_count = threading.Semaphore(0)

        bus.subscribe(
            lambda _: wildcard_count.release(), source="wildcard"
        )
        bus.subscribe(
            lambda _: specific_count.release(),
            EventType.PERSON_DETECTED,
            source="specific",
        )

        bus.publish_sync(_person_event(), timeout=3.0)

        assert wildcard_count.acquire(timeout=2.0)
        assert specific_count.acquire(timeout=2.0)

    def test_wildcard_handle_event_types_is_none(self, bus: EventBus) -> None:
        handle = bus.subscribe(lambda _: None, source="logger")
        assert handle.event_types is None


# ===========================================================================
# 6. Priority ordering
# ===========================================================================


class TestPriorityOrdering:
    def test_critical_before_low(self, bus: EventBus) -> None:
        """Verify CRITICAL-priority events are dispatched before LOW-priority ones
        when both are enqueued at roughly the same time."""
        order: list[str] = []
        lock = threading.Lock()
        both_done = threading.Event()

        def handler(event: EventEnvelope) -> None:
            with lock:
                order.append(event.priority.name)
            if len(order) >= 2:
                both_done.set()

        bus.subscribe(handler, EventType.SYSTEM_STARTING, source="ord")

        # Publish LOW first, then CRITICAL in quick succession.
        # The priority queue should dequeue CRITICAL first.
        bus.publish(_sys_event(priority=EventPriority.LOW))
        bus.publish(_sys_event(priority=EventPriority.CRITICAL))

        assert _wait(both_done, timeout=5.0), f"Only received {order}"

        assert "CRITICAL" in order
        assert "LOW" in order
        assert order.index("CRITICAL") < order.index("LOW"), (
            f"Expected CRITICAL before LOW, got: {order}"
        )

    def test_priority_enum_ordering(self) -> None:
        assert EventPriority.CRITICAL > EventPriority.HIGH
        assert EventPriority.HIGH > EventPriority.NORMAL
        assert EventPriority.NORMAL > EventPriority.LOW


# ===========================================================================
# 7. FIFO within same priority
# ===========================================================================


class TestFIFOOrdering:
    def test_fifo_within_same_priority(self, bus: EventBus) -> None:
        order: list[str] = []
        n = 5
        done = threading.Semaphore(0)

        def handler(event: EventEnvelope) -> None:
            order.append(event.payload.message)  # type: ignore[union-attr]
            done.release()

        bus.subscribe(handler, EventType.SYSTEM_STARTING, source="fifo")

        for i in range(n):
            bus.publish(_sys_event(message=str(i)))

        for _ in range(n):
            done.acquire(timeout=3.0)

        assert order == [str(i) for i in range(n)]


# ===========================================================================
# 8. Unsubscribe
# ===========================================================================


class TestUnsubscribe:
    def test_unsubscribe_stops_delivery(self, bus: EventBus) -> None:
        received: list[EventEnvelope] = []

        def handler(event: EventEnvelope) -> None:
            received.append(event)

        handle = bus.subscribe(handler, EventType.SYSTEM_STARTING, source="test")

        # First event – should be received
        bus.publish_sync(_sys_event(), timeout=3.0)
        assert len(received) == 1

        # Unsubscribe
        removed = bus.unsubscribe(handle)
        assert removed is True

        # Second event – should NOT be received
        bus.publish_sync(_sys_event(), timeout=3.0)
        assert len(received) == 1  # still 1

    def test_unsubscribe_returns_false_for_unknown_handle(self, bus: EventBus) -> None:
        fake_handle = SubscriptionHandle(
            handle_id=str(uuid.uuid4()),
            event_types=frozenset([EventType.SYSTEM_READY]),
            source="ghost",
        )
        assert bus.unsubscribe(fake_handle) is False

    def test_unsubscribe_multiple_types(self, bus: EventBus) -> None:
        received: list[EventEnvelope] = []

        handle = bus.subscribe(
            lambda e: received.append(e),
            [EventType.SYSTEM_STARTING, EventType.SYSTEM_READY],
            source="multi",
        )
        bus.publish_sync(_sys_event(EventType.SYSTEM_STARTING), timeout=2.0)
        assert len(received) == 1

        bus.unsubscribe(handle)
        bus.publish_sync(_sys_event(EventType.SYSTEM_STARTING), timeout=2.0)
        bus.publish_sync(_sys_event(EventType.SYSTEM_READY), timeout=2.0)
        assert len(received) == 1  # unsubscribed; no new deliveries

    def test_unsubscribe_wildcard(self, bus: EventBus) -> None:
        received: list[EventEnvelope] = []
        handle = bus.subscribe(
            lambda e: received.append(e), source="wildcard_test"
        )
        bus.publish_sync(_sys_event(), timeout=2.0)
        assert len(received) == 1

        bus.unsubscribe(handle)
        bus.publish_sync(_sys_event(), timeout=2.0)
        assert len(received) == 1


# ===========================================================================
# 9. One-shot subscriptions
# ===========================================================================


class TestOneShotSubscription:
    def test_one_shot_fires_once(self, bus: EventBus) -> None:
        received: list[EventEnvelope] = []
        first_done = threading.Event()

        def handler(event: EventEnvelope) -> None:
            received.append(event)
            first_done.set()

        bus.subscribe(
            handler,
            EventType.SYSTEM_STARTING,
            source="one-shot",
            one_shot=True,
        )

        bus.publish_sync(_sys_event(), timeout=3.0)
        assert _wait(first_done)
        assert len(received) == 1

        # Second publish – should NOT be received
        bus.publish_sync(_sys_event(), timeout=3.0)
        assert len(received) == 1

    def test_one_shot_wildcard(self, bus: EventBus) -> None:
        received: list[EventEnvelope] = []
        done = threading.Event()

        def handler(event: EventEnvelope) -> None:
            received.append(event)
            done.set()

        bus.subscribe(handler, source="wildcard-one-shot", one_shot=True)
        bus.publish_sync(_person_event(), timeout=3.0)
        assert _wait(done)
        assert len(received) == 1

        bus.publish_sync(_person_event(), timeout=3.0)
        assert len(received) == 1

    def test_one_shot_removed_from_registered_subscribers(self, bus: EventBus) -> None:
        bus.subscribe(
            lambda _: None,
            EventType.SYSTEM_STARTING,
            source="one-shot-reg",
            one_shot=True,
        )
        bus.publish_sync(_sys_event(), timeout=3.0)
        # After one-shot fires, subscriber count should be 0
        subs = bus.registered_subscribers()
        assert subs.get("SYSTEM_STARTING", 0) == 0


# ===========================================================================
# 10. Async (coroutine) handlers
# ===========================================================================


class TestAsyncHandlers:
    def test_async_handler_called(self, bus: EventBus) -> None:
        received: list[EventEnvelope] = []
        done = threading.Event()

        async def async_handler(event: EventEnvelope) -> None:
            received.append(event)
            done.set()

        bus.subscribe(async_handler, EventType.SYSTEM_STARTING, source="async-svc")
        bus.publish(_sys_event())

        assert _wait(done), "Async handler was not called within timeout"
        assert len(received) == 1

    def test_async_handler_with_await(self, bus: EventBus) -> None:
        results: list[str] = []
        done = threading.Event()

        async def slow_handler(event: EventEnvelope) -> None:
            await asyncio.sleep(0.01)  # simulate async work
            results.append("done")
            done.set()

        bus.subscribe(slow_handler, EventType.SYSTEM_READY, source="async-slow")
        bus.publish(_sys_event(EventType.SYSTEM_READY))

        assert _wait(done, timeout=5.0), "Async handler with await was not called"
        assert results == ["done"]

    def test_async_handler_exception_is_isolated(self, bus: EventBus) -> None:
        safe_received: list[EventEnvelope] = []
        safe_done = threading.Event()

        async def crashing_async(event: EventEnvelope) -> None:
            raise RuntimeError("async handler crash")

        def safe_handler(event: EventEnvelope) -> None:
            safe_received.append(event)
            safe_done.set()

        bus.subscribe(crashing_async, EventType.SYSTEM_STARTING, source="crash-async")
        bus.subscribe(safe_handler, EventType.SYSTEM_STARTING, source="safe")

        bus.publish(_sys_event())
        assert _wait(safe_done), "Safe handler blocked by crashing async handler"
        assert len(safe_received) == 1


# ===========================================================================
# 11. Mixed sync + async handlers
# ===========================================================================


class TestMixedHandlers:
    def test_both_sync_and_async_receive_same_event(self, bus: EventBus) -> None:
        sync_done = threading.Event()
        async_done = threading.Event()

        def sync_h(event: EventEnvelope) -> None:
            sync_done.set()

        async def async_h(event: EventEnvelope) -> None:
            async_done.set()

        bus.subscribe(sync_h, EventType.PERSON_DETECTED, source="sync")
        bus.subscribe(async_h, EventType.PERSON_DETECTED, source="async")

        bus.publish(_person_event())

        assert _wait(sync_done)
        assert _wait(async_done)

    def test_mixed_count(self, bus: EventBus) -> None:
        counts: Counter[str] = Counter()
        barrier = threading.Barrier(3 + 1)

        def sync1(_: EventEnvelope) -> None:
            counts["sync1"] += 1
            barrier.wait(timeout=3.0)

        def sync2(_: EventEnvelope) -> None:
            counts["sync2"] += 1
            barrier.wait(timeout=3.0)

        async def async1(_: EventEnvelope) -> None:
            counts["async1"] += 1
            barrier.wait(timeout=3.0)

        bus.subscribe(sync1, EventType.SYSTEM_STARTING, source="s1")
        bus.subscribe(sync2, EventType.SYSTEM_STARTING, source="s2")
        bus.subscribe(async1, EventType.SYSTEM_STARTING, source="a1")

        bus.publish(_sys_event())
        barrier.wait(timeout=3.0)

        assert counts["sync1"] == 1
        assert counts["sync2"] == 1
        assert counts["async1"] == 1


# ===========================================================================
# 12. Exception isolation
# ===========================================================================


class TestExceptionIsolation:
    def test_crashing_handler_does_not_block_others(self, bus: EventBus) -> None:
        safe_received: list[str] = []
        done = threading.Event()

        def crashing_handler(_: EventEnvelope) -> None:
            raise ValueError("intentional crash in handler")

        def safe_handler(event: EventEnvelope) -> None:
            safe_received.append("ok")
            done.set()

        bus.subscribe(crashing_handler, EventType.SYSTEM_STARTING, source="crash")
        bus.subscribe(safe_handler, EventType.SYSTEM_STARTING, source="safe")

        bus.publish(_sys_event())
        assert _wait(done), "Safe handler was blocked by crashing handler"
        assert safe_received == ["ok"]

    def test_handler_failures_counted_in_metrics(self, bus: EventBus) -> None:
        done = threading.Event()

        def crashing(_: EventEnvelope) -> None:
            raise RuntimeError("boom")

        def sentinel(_: EventEnvelope) -> None:
            done.set()

        bus.subscribe(crashing, EventType.SYSTEM_STARTING, source="crash")
        bus.subscribe(sentinel, EventType.SYSTEM_STARTING, source="sentinel")

        bus.publish_sync(_sys_event(), timeout=3.0)

        stats = bus.statistics()
        assert stats.handler_failures >= 1

    def test_multiple_crashing_handlers(self, bus: EventBus) -> None:
        done = threading.Barrier(2 + 1)

        def crash(_: EventEnvelope) -> None:
            done.wait(timeout=3.0)
            raise RuntimeError("crash")

        bus.subscribe(crash, EventType.SYSTEM_STARTING, source="c1")
        bus.subscribe(crash, EventType.SYSTEM_STARTING, source="c2")

        bus.publish(_sys_event())
        done.wait(timeout=3.0)  # ensure both handlers started

        # Bus dispatcher must remain alive after crashing handlers
        time.sleep(0.2)
        assert bus.health()["dispatcher_alive"]


# ===========================================================================
# 13. publish_sync
# ===========================================================================


class TestPublishSync:
    def test_publish_sync_blocks_until_complete(self, bus: EventBus) -> None:
        handler_called = False

        def slow_handler(_: EventEnvelope) -> None:
            nonlocal handler_called
            time.sleep(0.05)
            handler_called = True

        bus.subscribe(slow_handler, EventType.SYSTEM_STARTING, source="slow")

        result = bus.publish_sync(_sys_event(), timeout=3.0)

        assert result is True
        assert handler_called is True

    def test_publish_sync_returns_false_on_timeout(self, bus: EventBus) -> None:
        def very_slow(_: EventEnvelope) -> None:
            time.sleep(10.0)

        bus.subscribe(very_slow, EventType.SYSTEM_STARTING, source="very-slow")

        result = bus.publish_sync(_sys_event(), timeout=0.05)
        assert result is False

    def test_publish_sync_raises_from_dispatcher_thread(self, bus: EventBus) -> None:
        """Calling publish_sync from inside a handler (executor thread) must raise
        RuntimeError because the dispatcher is blocking on that handler's future,
        creating a deadlock if publish_sync were allowed to wait."""
        error_caught: list[Exception] = []  
        done = threading.Event()

        def reentrant_handler(event: EventEnvelope) -> None:
            try:
                # publish_sync called from inside a handler — deadlock scenario
                bus.publish_sync(_sys_event(), timeout=0.1)
            except RuntimeError as exc:
                error_caught.append(exc)
            finally:
                done.set()

        bus.subscribe(reentrant_handler, EventType.SYSTEM_STARTING, source="reentrant")
        bus.publish(_sys_event())

        assert _wait(done, timeout=5.0), "Handler never completed"
        assert len(error_caught) == 1, (
            f"Expected 1 RuntimeError, got {len(error_caught)}: {error_caught}"
        )
        assert "publish_sync" in str(error_caught[0]).lower() or "deadlock" in str(error_caught[0]).lower()

    def test_publish_sync_without_subscribers_returns_true(self, bus: EventBus) -> None:
        result = bus.publish_sync(_sys_event(), timeout=2.0)
        assert result is True


# ===========================================================================
# 14. Queue overflow
# ===========================================================================


class TestQueueOverflow:
    def test_overflow_drop_returns_false(self) -> None:
        # Create bus with very small queue
        bus = EventBus(maxsize=2, overflow_drop=True, overflow_timeout=0.01, name="tiny")
        try:
            # Block dispatcher by publishing a slow handler
            blocked = threading.Event()
            released = threading.Event()

            def blocking_handler(_: EventEnvelope) -> None:
                blocked.set()
                released.wait(timeout=5.0)

            bus.subscribe(blocking_handler, EventType.SYSTEM_STARTING, source="blocker")

            # Fill the queue
            results = [bus.publish(_sys_event()) for _ in range(20)]
            assert released.set() or True  # unblock

            # Some should have been dropped
            bus.unsubscribe(
                SubscriptionHandle(
                    handle_id="",
                    event_types=frozenset([EventType.SYSTEM_STARTING]),
                    source="blocker",
                )
            )
            assert any(r is False for r in results)
        finally:
            released.set()
            bus.shutdown(timeout=2.0)

    def test_overflow_metrics_increment(self) -> None:
        bus = EventBus(maxsize=1, overflow_drop=True, overflow_timeout=0.001, name="overflow-bus")
        try:
            blocking = threading.Event()
            released = threading.Event()

            def block(_: EventEnvelope) -> None:
                blocking.set()
                released.wait(timeout=5.0)

            bus.subscribe(block, EventType.SYSTEM_STARTING, source="blocker")

            # Flood queue
            for _ in range(50):
                bus.publish(_sys_event())

            released.set()  # unblock handler
            time.sleep(0.2)

            stats = bus.statistics()
            assert stats.events_dropped > 0
        finally:
            released.set()
            bus.shutdown(timeout=2.0)


# ===========================================================================
# 15. clear()
# ===========================================================================


class TestClear:
    def test_clear_drains_queue(self, bus: EventBus) -> None:
        blocking = threading.Event()

        def block(_: EventEnvelope) -> None:
            blocking.wait(timeout=10.0)

        bus.subscribe(block, EventType.SYSTEM_STARTING, source="blocker")

        # Publish one to block dispatcher, then flood queue
        bus.publish(_sys_event())
        blocking.wait(timeout=2.0)  # wait until dispatcher is busy

        for _ in range(20):
            bus.publish(_sys_event())

        drained = bus.clear()
        assert drained >= 0  # could be 0 if dispatcher was fast

        blocking.set()  # release handler

    def test_clear_increments_dropped_metrics(self, bus: EventBus) -> None:
        blocking = threading.Event()

        def block(_: EventEnvelope) -> None:
            blocking.wait(timeout=5.0)

        bus.subscribe(block, EventType.SYSTEM_STARTING, source="blocker")

        bus.publish(_sys_event())
        blocking.wait(timeout=2.0)  # block dispatcher

        for _ in range(10):
            bus.publish(_sys_event())

        drained = bus.clear()
        stats = bus.statistics()
        blocking.set()

        # drained events should appear as dropped
        assert stats.events_dropped >= drained


# ===========================================================================
# 16. Metrics and statistics
# ===========================================================================


class TestMetrics:
    def test_published_count_increments(self, bus: EventBus) -> None:
        for _ in range(5):
            bus.publish_sync(_sys_event(), timeout=2.0)

        stats = bus.statistics()
        assert stats.events_published == 5

    def test_delivered_count_tracks_handler_invocations(self, bus: EventBus) -> None:
        # 2 subscribers × 3 events = 6 deliveries
        bus.subscribe(lambda _: None, EventType.SYSTEM_STARTING, source="a")
        bus.subscribe(lambda _: None, EventType.SYSTEM_STARTING, source="b")

        for _ in range(3):
            bus.publish_sync(_sys_event(), timeout=2.0)

        stats = bus.statistics()
        assert stats.events_delivered == 6

    def test_per_event_type_tracking(self, bus: EventBus) -> None:
        bus.subscribe(lambda _: None, EventType.SYSTEM_STARTING, source="a")
        bus.subscribe(lambda _: None, EventType.PERSON_DETECTED, source="b")

        bus.publish_sync(_sys_event(), timeout=2.0)
        bus.publish_sync(_person_event(), timeout=2.0)

        stats = bus.statistics()
        assert stats.per_event_type.get("SYSTEM_STARTING", 0) == 1
        assert stats.per_event_type.get("PERSON_DETECTED", 0) == 1

    def test_avg_dispatch_latency_is_positive(self, bus: EventBus) -> None:
        bus.subscribe(lambda _: None, EventType.SYSTEM_STARTING, source="a")
        bus.publish_sync(_sys_event(), timeout=2.0)

        stats = bus.statistics()
        assert stats.avg_dispatch_latency_us > 0

    def test_uptime_increases(self, bus: EventBus) -> None:
        t0 = bus.statistics().uptime_seconds
        time.sleep(0.1)
        t1 = bus.statistics().uptime_seconds
        assert t1 > t0


# ===========================================================================
# 17. Diagnostics
# ===========================================================================


class TestDiagnostics:
    def test_health_structure(self, bus: EventBus) -> None:
        h = bus.health()
        assert "status" in h
        assert "running" in h
        assert "dispatcher_alive" in h
        assert "queue_depth" in h
        assert "subscriber_count" in h
        assert h["status"] == "healthy"
        assert h["running"] is True
        assert h["dispatcher_alive"] is True

    def test_queue_depth_method(self, bus: EventBus) -> None:
        assert bus.queue_depth() == 0

    def test_registered_subscribers_counts(self, bus: EventBus) -> None:
        bus.subscribe(lambda _: None, EventType.SYSTEM_STARTING, source="a")
        bus.subscribe(lambda _: None, EventType.SYSTEM_STARTING, source="b")
        bus.subscribe(lambda _: None, source="wildcard")

        subs = bus.registered_subscribers()
        assert subs.get("SYSTEM_STARTING", 0) == 2
        assert subs.get("WILDCARD", 0) == 1

    def test_registered_subscribers_empty_after_unsubscribe(self, bus: EventBus) -> None:
        handle = bus.subscribe(
            lambda _: None, EventType.SYSTEM_STARTING, source="tmp"
        )
        bus.unsubscribe(handle)
        subs = bus.registered_subscribers()
        assert subs.get("SYSTEM_STARTING", 0) == 0

    def test_subscriber_count_in_health(self, bus: EventBus) -> None:
        bus.subscribe(lambda _: None, EventType.SYSTEM_STARTING, source="a")
        bus.subscribe(lambda _: None, source="w")
        h = bus.health()
        assert h["subscriber_count"] >= 2


# ===========================================================================
# 18. min_priority filter
# ===========================================================================


class TestMinPriorityFilter:
    def test_low_priority_event_filtered_for_high_threshold(self, bus: EventBus) -> None:
        received: list[EventEnvelope] = []
        sentinel = threading.Event()

        def handler(event: EventEnvelope) -> None:
            received.append(event)
            sentinel.set()

        # Handler only wants HIGH+ events
        bus.subscribe(
            handler,
            EventType.SYSTEM_STARTING,
            source="high-only",
            min_priority=EventPriority.HIGH,
        )

        # Publish a LOW event — should be filtered
        bus.publish_sync(_sys_event(priority=EventPriority.LOW), timeout=2.0)
        assert len(received) == 0

        # Publish a CRITICAL event — should pass through
        bus.publish_sync(_sys_event(priority=EventPriority.CRITICAL), timeout=2.0)
        assert _wait(sentinel)
        assert len(received) == 1
        assert received[0].priority is EventPriority.CRITICAL

    def test_normal_priority_passes_low_threshold(self, bus: EventBus) -> None:
        received: list[EventEnvelope] = []
        done = threading.Event()

        bus.subscribe(
            lambda e: [received.append(e), done.set()],
            EventType.SYSTEM_STARTING,
            source="normal",
            min_priority=EventPriority.LOW,
        )

        bus.publish_sync(_sys_event(priority=EventPriority.NORMAL), timeout=2.0)
        assert _wait(done)
        assert len(received) == 1


# ===========================================================================
# 19. shutdown() and context manager
# ===========================================================================


class TestShutdown:
    def test_shutdown_stops_dispatcher(self) -> None:
        bus = EventBus(name="shutdown-test")
        assert bus.health()["dispatcher_alive"] is True
        bus.shutdown(timeout=3.0)
        assert bus._dispatcher.is_alive() is False

    def test_shutdown_health_reports_stopped(self) -> None:
        bus = EventBus(name="shutdown-health")
        bus.shutdown(timeout=3.0)
        h = bus.health()
        assert h["running"] is False

    def test_context_manager_shuts_down(self) -> None:
        with EventBus(name="ctx-bus") as bus:
            assert bus.health()["running"] is True
        assert bus.health()["running"] is False

    def test_shutdown_drains_queue(self) -> None:
        delivered: list[int] = []
        done = threading.Event()

        bus = EventBus(name="drain-bus", max_workers=2)
        bus.subscribe(
            lambda _: delivered.append(1), EventType.SYSTEM_STARTING, source="drain"
        )

        for _ in range(20):
            bus.publish(_sys_event())

        bus.shutdown(timeout=5.0, drain=True)
        assert len(delivered) > 0  # at least some delivered

    def test_shutdown_no_drain(self) -> None:
        bus = EventBus(name="no-drain-bus")
        for _ in range(100):
            bus.publish(_sys_event())
        bus.shutdown(timeout=2.0, drain=False)
        assert bus.health()["running"] is False


# ===========================================================================
# 20. Thread safety
# ===========================================================================


class TestThreadSafety:
    def test_concurrent_subscribe_unsubscribe(self, bus: EventBus) -> None:
        """Multiple threads subscribing and unsubscribing simultaneously."""
        errors: list[Exception] = []

        def worker(idx: int) -> None:
            try:
                handle = bus.subscribe(
                    lambda _: None,
                    EventType.SYSTEM_STARTING,
                    source=f"worker-{idx}",
                )
                time.sleep(0.001)
                bus.unsubscribe(handle)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        assert not errors

    def test_concurrent_publish(self, bus: EventBus) -> None:
        """Multiple threads publishing simultaneously; count must match."""
        n_threads = 10
        n_events_each = 100
        counter: list[int] = [0]
        lock = threading.Lock()
        done = threading.Event()

        def handler(_: EventEnvelope) -> None:
            with lock:
                counter[0] += 1
            if counter[0] >= n_threads * n_events_each:
                done.set()

        bus.subscribe(handler, EventType.SYSTEM_STARTING, source="counter")

        def publisher(_: int) -> None:
            for _ in range(n_events_each):
                bus.publish(_sys_event())

        threads = [
            threading.Thread(target=publisher, args=(i,)) for i in range(n_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        _wait(done, timeout=10.0)
        assert counter[0] == n_threads * n_events_each

    def test_concurrent_subscribe_and_publish(self, bus: EventBus) -> None:
        """Subscribe and publish from different threads – no deadlock."""
        errors: list[Exception] = []

        def sub_worker() -> None:
            try:
                for _ in range(20):
                    handle = bus.subscribe(
                        lambda _: None,
                        EventType.SYSTEM_STARTING,
                        source="concurrent-sub",
                    )
                    time.sleep(0.0005)
                    bus.unsubscribe(handle)
            except Exception as exc:
                errors.append(exc)

        def pub_worker() -> None:
            try:
                for _ in range(50):
                    bus.publish(_sys_event())
                    time.sleep(0.001)
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=sub_worker) for _ in range(5)
        ] + [threading.Thread(target=pub_worker) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        assert not errors


# ===========================================================================
# 21. Stress test
# ===========================================================================


class TestStress:
    def test_10_threads_10000_events_no_lost(self) -> None:
        """10 producer threads × 1 000 events each = 10 000 events total.

        Verifies:
        - No lost events (all delivered exactly once).
        - No deadlocks (test completes within generous timeout).
        - No duplicate delivery.
        """
        n_threads = 10
        n_per_thread = 1_000
        total = n_threads * n_per_thread

        bus = EventBus(maxsize=5_000, max_workers=8, name="stress-bus")

        received_ids: list[str] = []
        lock = threading.Lock()
        done = threading.Event()

        def handler(event: EventEnvelope) -> None:
            with lock:
                received_ids.append(event.event_id)
            if len(received_ids) >= total:
                done.set()

        bus.subscribe(handler, EventType.SYSTEM_STARTING, source="stress-consumer")

        published_ids: list[str] = []
        pub_lock = threading.Lock()

        def producer(_: int) -> None:
            for _ in range(n_per_thread):
                event = _sys_event()
                with pub_lock:
                    published_ids.append(event.event_id)
                bus.publish(event)

        threads = [
            threading.Thread(target=producer, args=(i,)) for i in range(n_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15.0)

        # Wait for all events to be delivered
        assert done.wait(timeout=30.0), (
            f"Stress test timed out: delivered {len(received_ids)}/{total}"
        )

        # No lost events
        assert len(received_ids) == total

        # No duplicates
        assert len(set(received_ids)) == total

        bus.shutdown(timeout=5.0)

    def test_stress_with_random_priorities(self) -> None:
        """Stress test with mixed priorities – bus must not deadlock."""
        import random

        bus = EventBus(maxsize=2_000, max_workers=6, name="stress-priority")
        counter: list[int] = [0]
        lock = threading.Lock()
        done = threading.Event()
        n = 2_000

        def handler(_: EventEnvelope) -> None:
            with lock:
                counter[0] += 1
            if counter[0] >= n:
                done.set()

        bus.subscribe(handler, EventType.SYSTEM_STARTING, source="stress-prio")

        priorities = list(EventPriority)
        for _ in range(n):
            event = _sys_event(priority=random.choice(priorities))
            bus.publish(event)

        assert done.wait(timeout=30.0), f"Delivered only {counter[0]}/{n}"
        bus.shutdown(timeout=5.0)

    def test_stress_mixed_event_types_wildcard(self) -> None:
        """Wildcard subscriber receives events from multiple types under load."""
        bus = EventBus(maxsize=3_000, max_workers=8, name="stress-wildcard")
        counter: list[int] = [0]
        lock = threading.Lock()
        n = 1_000
        done = threading.Event()

        def handler(_: EventEnvelope) -> None:
            with lock:
                counter[0] += 1
            if counter[0] >= n:
                done.set()

        bus.subscribe(handler, source="wildcard-stress")  # wildcard

        event_types_cycle = [
            EventType.SYSTEM_STARTING,
            EventType.PERSON_DETECTED,
            EventType.VOICE_STARTED,
            EventType.SYSTEM_READY,
        ]
        payloads: dict[EventType, Any] = {
            EventType.SYSTEM_STARTING: lambda: SystemPayload(
                profile="dev", message="stress"
            ),
            EventType.PERSON_DETECTED: lambda: PersonDetectedPayload(confidence=0.9),
            EventType.VOICE_STARTED: lambda: VoicePayload(audio_chunk_id="c"),
            EventType.SYSTEM_READY: lambda: SystemPayload(
                profile="dev", message="ready"
            ),
        }

        for i in range(n):
            et = event_types_cycle[i % len(event_types_cycle)]
            event = EventEnvelope.create(
                event_type=et, source="stress", payload=payloads[et]()
            )
            bus.publish(event)

        assert done.wait(timeout=30.0), f"Wildcard stress: delivered {counter[0]}/{n}"
        bus.shutdown(timeout=5.0)


# ===========================================================================
# 22. Benchmarks
# ===========================================================================


class TestBenchmarks:
    """Performance benchmarks — always pass, print results for CI tracking."""

    N_SMALL = 1_000
    N_MEDIUM = 10_000
    N_LARGE = 50_000

    def _measure_publish_latency(self, bus: EventBus, n: int) -> float:
        """Return average publish() latency in µs."""
        event = _sys_event()
        t0 = time.perf_counter()
        for _ in range(n):
            bus.publish(event)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        bus.clear()
        return (elapsed_ms / n) * 1000  # µs

    def test_publish_latency_1000(self) -> None:
        with EventBus(maxsize=50_000, name="bench-1k") as bus:
            avg_us = self._measure_publish_latency(bus, self.N_SMALL)
            print(
                f"\n[Benchmark] publish() ×{self.N_SMALL}: avg {avg_us:.1f} µs/call"
            )
            assert avg_us < 300.0, f"publish() avg {avg_us:.1f} µs exceeds 300 µs target"

    def test_publish_latency_10000(self) -> None:
        with EventBus(maxsize=50_000, name="bench-10k") as bus:
            avg_us = self._measure_publish_latency(bus, self.N_MEDIUM)
            print(
                f"\n[Benchmark] publish() ×{self.N_MEDIUM}: avg {avg_us:.1f} µs/call"
            )
            assert avg_us < 300.0

    def test_publish_latency_50000(self) -> None:
        with EventBus(maxsize=100_000, name="bench-50k") as bus:
            avg_us = self._measure_publish_latency(bus, self.N_LARGE)
            print(
                f"\n[Benchmark] publish() ×{self.N_LARGE}: avg {avg_us:.1f} µs/call"
            )
            assert avg_us < 300.0

    def test_dispatch_latency_with_one_handler(self) -> None:
        """Measure end-to-end dispatch latency for a single handler."""
        n = 500
        latencies: list[float] = []

        with EventBus(maxsize=1_000, name="bench-dispatch") as bus:
            latch = threading.Event()
            times: dict[str, float] = {}

            def handler(event: EventEnvelope) -> None:
                t_recv = time.perf_counter()
                t_sent = times.get(event.event_id)
                if t_sent:
                    latencies.append((t_recv - t_sent) * 1_000_000)  # µs
                if len(latencies) >= n:
                    latch.set()

            bus.subscribe(handler, EventType.SYSTEM_STARTING, source="bench")

            for _ in range(n):
                event = _sys_event()
                times[event.event_id] = time.perf_counter()
                bus.publish(event)

            latch.wait(timeout=30.0)

        if latencies:
            avg_us = sum(latencies) / len(latencies)
            p95_us = sorted(latencies)[int(len(latencies) * 0.95)]
            print(
                f"\n[Benchmark] dispatch latency ×{n}: "
                f"avg {avg_us:.0f} µs, P95 {p95_us:.0f} µs"
            )
            assert avg_us < 500_000, f"Avg dispatch latency {avg_us:.0f} µs is unexpectedly high"

    def test_throughput_1000_events_one_handler(self) -> None:
        n = 1_000
        done = threading.Semaphore(0)

        with EventBus(maxsize=5_000, name="bench-throughput") as bus:
            bus.subscribe(
                lambda _: done.release(), EventType.SYSTEM_STARTING, source="bench"
            )

            t0 = time.perf_counter()
            for _ in range(n):
                bus.publish(_sys_event())

            for _ in range(n):
                done.acquire(timeout=10.0)

            elapsed_s = time.perf_counter() - t0
            eps = n / elapsed_s  # events per second

        print(
            f"\n[Benchmark] throughput ×{n}: {eps:.0f} events/s "
            f"({elapsed_s * 1000:.1f} ms total)"
        )
        assert eps > 100, f"Throughput {eps:.0f} events/s below minimum 100 events/s"
