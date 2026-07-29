"""
Campus Helpdesk Robot – Phase 3: Event Bus
==========================================

Module: campus_helpdesk.interaction.event_bus
File:   src/campus_helpdesk/interaction/event_bus.py
Version: 1.0

This module implements the central publish-subscribe Event Bus for the
Real-Time Interaction Engine.  Every service in the robot runtime
communicates **exclusively** through this bus — no service calls another
service directly.

Architecture
------------
::

    Publishers (any thread)
           │
           │  publish() / publish_async()  →  non-blocking put to priority queue
           │  publish_sync()               →  blocking: waits for all handlers
           ▼
    ┌─────────────────────────────┐
    │   PriorityQueue             │  FIFO within same priority,
    │   (CRITICAL … LOW)          │  CRITICAL first overall.
    └─────────────────────────────┘
           │
           │  pulled by single dispatcher thread
           ▼
    ┌─────────────────────────────┐
    │   Dispatcher Thread         │  collects matching handlers,
    │                             │  submits each to ThreadPoolExecutor,
    │                             │  waits for all futures before next event.
    └─────────────────────────────┘
           │
           ▼
    ┌─────────────────────────────┐
    │   ThreadPoolExecutor        │  handlers run in isolation;
    │   (N worker threads)        │  exceptions are caught per-handler.
    └─────────────────────────────┘

Thread model
------------
*  **Publisher threads** – any service thread.  ``publish()`` acquires a
   sequence lock, puts one entry on the ``PriorityQueue`` and returns.
   Overhead is O(log n) where n = current queue depth.

*  **Dispatcher thread** – single background thread.  Pulls one entry at a
   time, resolves subscribers (holding ``_lock`` briefly), submits handlers
   to the pool, waits for completion, then signals any ``publish_sync``
   caller.

*  **Handler threads** – drawn from ``ThreadPoolExecutor``.  All handlers for
   a single event run **concurrently**.  The dispatcher serialises events:
   event N+1 is dispatched only after every handler for event N has returned.
   This guarantees FSM state-transition ordering.

*  **publish_sync callers** – wait on a per-event ``threading.Event`` that
   the dispatcher sets after all handlers finish.  Calling ``publish_sync``
   from the dispatcher thread raises ``RuntimeError`` (would deadlock).

Priority model
--------------
Queue entries are keyed by ``(-priority.value, sequence_number)`` so that:

* CRITICAL (value=3) → key=-3 → smallest → earliest dequeue
* LOW      (value=0) → key=0  → largest  → latest dequeue

Sequence number provides strict FIFO within the same priority level.

Subscription model
------------------
* **Specific** – handler receives events of exactly the requested
  ``EventType`` values.
* **Wildcard** – ``event_types=None`` → handler receives every event.
* **One-shot** – auto-removed after the first delivery.
* **Priority filter** – ``min_priority`` silently skips events below
  the subscriber's threshold.

Overflow policy
---------------
When the queue is full:

* ``overflow_drop=True`` (default) – event is dropped, metrics counter
  incremented, ``publish()`` returns ``False``.
* ``overflow_drop=False`` – publisher blocks until space is available.

Error isolation
---------------
Each handler invocation is wrapped in a ``try/except``.  A crashing handler
is logged, counted in ``handler_failures``, and all remaining handlers for
the same event still execute.

Changelog
---------
* 1.0 (2026-07-28) – Initial implementation for Task 13.
"""

from __future__ import annotations

import asyncio
import logging
import queue
import threading
import time
import uuid
from collections import defaultdict
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

from campus_helpdesk.interaction.events import (
    EventEnvelope,
    EventPriority,
    EventType,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

HandlerType = Callable[[EventEnvelope], None | Coroutine[Any, Any, None]]


# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SubscriptionHandle:
    """Opaque handle returned by :meth:`EventBus.subscribe`.

    Pass this back to :meth:`EventBus.unsubscribe` to remove the subscription.

    Attributes
    ----------
    handle_id:
        Unique UUID4 string identifying this specific subscription.
    event_types:
        Frozenset of :class:`EventType` values this handle is registered for,
        or ``None`` for a wildcard subscription.
    source:
        Human-readable name of the subscribing service (for diagnostics).
    """

    handle_id: str
    event_types: frozenset[EventType] | None
    source: str

    def __repr__(self) -> str:
        types_str = (
            "WILDCARD"
            if self.event_types is None
            else ", ".join(sorted(e.name for e in self.event_types))
        )
        return f"SubscriptionHandle(source={self.source!r}, types=[{types_str}], id={self.handle_id[:8]})"


@dataclass(frozen=True)
class BusStatistics:
    """Immutable snapshot of Event Bus metrics.

    Returned by :meth:`EventBus.statistics`.  All counters are cumulative
    since the bus was started.

    Attributes
    ----------
    events_published:
        Total events successfully enqueued (not counting dropped).
    events_delivered:
        Total successful handler invocations across all events.
    events_dropped:
        Events discarded due to queue overflow or ``clear()``.
    handler_failures:
        Number of handler invocations that raised an unhandled exception.
    queue_depth:
        Current number of events waiting in the queue at snapshot time.
    avg_dispatch_latency_us:
        Average time from dequeue to all handlers complete, in microseconds.
    subscriber_count:
        Total number of registered subscription records (sum across all keys,
        including wildcards).
    uptime_seconds:
        Seconds since the bus was created.
    per_event_type:
        Mapping of ``{EventType.value: delivered_count}`` for delivered events.
    """

    events_published: int
    events_delivered: int
    events_dropped: int
    handler_failures: int
    queue_depth: int
    avg_dispatch_latency_us: float
    subscriber_count: int
    uptime_seconds: float
    per_event_type: dict[str, int]


# ---------------------------------------------------------------------------
# Internal types
# ---------------------------------------------------------------------------


@dataclass
class _SubscriptionRecord:
    """Internal record stored in the subscriber registry."""

    handle_id: str
    handler: HandlerType
    event_types: frozenset[EventType] | None  # None = wildcard
    is_one_shot: bool
    source: str
    min_priority: EventPriority


@dataclass(order=False)
class _QueueEntry:
    """Priority queue entry wrapping an EventEnvelope.

    Comparison uses ``(priority_key, sequence)`` only, so EventEnvelope never
    needs to implement ``__lt__`` or ``__le__``.

    ``priority_key = -event.priority.value`` so CRITICAL (3) → -3 dequeues
    first from the min-heap.
    """

    priority_key: int
    sequence: int
    event: EventEnvelope

    def __lt__(self, other: _QueueEntry) -> bool:
        if self.priority_key != other.priority_key:
            return self.priority_key < other.priority_key
        return self.sequence < other.sequence

    def __le__(self, other: _QueueEntry) -> bool:
        return self == other or self < other

    def __gt__(self, other: _QueueEntry) -> bool:
        return not self <= other

    def __ge__(self, other: _QueueEntry) -> bool:
        return not self < other

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _QueueEntry):
            return NotImplemented
        return self.priority_key == other.priority_key and self.sequence == other.sequence


# ---------------------------------------------------------------------------
# EventBus
# ---------------------------------------------------------------------------


class EventBus:
    """Thread-safe, priority-ordered, publish-subscribe event bus.

    See module docstring for full architecture description.

    Parameters
    ----------
    maxsize:
        Maximum number of events in the queue.  ``0`` means unlimited.
    max_workers:
        Maximum number of handler threads in the ``ThreadPoolExecutor``.
    overflow_drop:
        When ``True`` (default), events that cannot be enqueued within
        ``overflow_timeout`` seconds are silently dropped and counted.
        When ``False``, the publisher blocks until space is available.
    overflow_timeout:
        Seconds to wait for queue space before dropping (only when
        ``overflow_drop=True``).
    name:
        Human-readable name for this bus instance (used in log messages
        and thread names).

    Example
    -------
    ::

        bus = EventBus()

        def on_person(event: EventEnvelope) -> None:
            logger.info("Person detected: %s", event.payload.confidence)

        handle = bus.subscribe(
            on_person,
            event_types=EventType.PERSON_DETECTED,
            source="ui_service",
        )

        bus.publish(
            EventEnvelope.create(
                event_type=EventType.PERSON_DETECTED,
                source="camera_service",
                payload=PersonDetectedPayload(confidence=0.92),
            )
        )

        time.sleep(0.1)   # or use publish_sync for guaranteed delivery
        bus.unsubscribe(handle)
        bus.shutdown()
    """

    def __init__(
        self,
        maxsize: int = 1_000,
        max_workers: int = 8,
        overflow_drop: bool = True,
        overflow_timeout: float = 0.1,
        name: str = "EventBus",
    ) -> None:
        self._name = name
        self._maxsize = maxsize
        self._overflow_drop = overflow_drop
        self._overflow_timeout = overflow_timeout

        # ── Priority queue ────────────────────────────────────────────────
        self._queue: queue.PriorityQueue[_QueueEntry] = queue.PriorityQueue(
            maxsize=maxsize
        )

        # ── Subscriber registry ───────────────────────────────────────────
        # Key = EventType.value string (e.g. "PERSON_DETECTED") or None (wildcard)
        self._subscribers: dict[str | None, list[_SubscriptionRecord]] = defaultdict(list)
        self._lock = threading.RLock()  # protects _subscribers and _pending_sync

        # ── Sequence counter (FIFO within same priority) ───────────────────
        self._sequence: int = 0
        self._seq_lock = threading.Lock()

        # ── Sync-publish completion tracking ─────────────────────────────
        # Maps event_id → threading.Event that publish_sync() waits on.
        self._pending_sync: dict[str, threading.Event] = {}

        # ── Metrics ───────────────────────────────────────────────────────
        self._events_published: int = 0
        self._events_delivered: int = 0
        self._events_dropped: int = 0
        self._handler_failures: int = 0
        self._total_dispatch_ns: int = 0
        self._dispatch_count: int = 0
        self._per_event_type: dict[str, int] = defaultdict(int)
        self._stats_lock = threading.Lock()

        # ── Thread pool for handler execution ─────────────────────────────
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix=f"{name}-handler",
        )

        # ── Per-thread marker: True inside any handler invocation on THIS bus ─
        # Used by publish_sync() to detect the reentrant-deadlock scenario.
        self._handler_local = threading.local()

        # ── Dispatcher thread ─────────────────────────────────────────────
        self._stop_event = threading.Event()
        self._dispatcher = threading.Thread(
            target=self._dispatch_loop,
            name=f"{name}-dispatcher",
            daemon=True,
        )
        self._start_time = time.monotonic()
        self._dispatcher.start()

        logger.info(
            "EventBus %r started (maxsize=%d, workers=%d, overflow_drop=%s)",
            name,
            maxsize,
            max_workers,
            overflow_drop,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Subscription management
    # ─────────────────────────────────────────────────────────────────────────

    def subscribe(
        self,
        handler: HandlerType,
        event_types: EventType | list[EventType] | None = None,
        *,
        source: str = "unknown",
        one_shot: bool = False,
        min_priority: EventPriority = EventPriority.LOW,
    ) -> SubscriptionHandle:
        """Register a handler for one or more event types.

        Parameters
        ----------
        handler:
            Callable ``(EventEnvelope) → None``.  May be a regular function or
            an ``async`` coroutine function.
        event_types:
            * :class:`EventType` – subscribe to a single event type.
            * ``list[EventType]`` – subscribe to multiple event types.
            * ``None`` – **wildcard**: receive every event on the bus.
        source:
            Name of the subscribing service (used in logs and
            :meth:`registered_subscribers`).
        one_shot:
            When ``True`` the subscription is automatically removed after the
            first successful delivery.
        min_priority:
            Events below this priority are silently skipped for this handler.

        Returns
        -------
        SubscriptionHandle
            Use with :meth:`unsubscribe` to deregister.
        """
        if event_types is None:
            et_frozenset: frozenset[EventType] | None = None
        elif isinstance(event_types, EventType):
            et_frozenset = frozenset([event_types])
        else:
            et_frozenset = frozenset(event_types)

        handle_id = str(uuid.uuid4())
        record = _SubscriptionRecord(
            handle_id=handle_id,
            handler=handler,
            event_types=et_frozenset,
            is_one_shot=one_shot,
            source=source,
            min_priority=min_priority,
        )

        with self._lock:
            if et_frozenset is None:
                self._subscribers[None].append(record)
            else:
                for et in et_frozenset:
                    self._subscribers[et.value].append(record)

        handle = SubscriptionHandle(
            handle_id=handle_id,
            event_types=et_frozenset,
            source=source,
        )

        logger.debug(
            "EventBus %r: subscribed handle=%s source=%r events=%s one_shot=%s",
            self._name,
            handle_id[:8],
            source,
            "WILDCARD" if et_frozenset is None else sorted(e.name for e in et_frozenset),
            one_shot,
        )
        return handle

    def unsubscribe(self, handle: SubscriptionHandle) -> bool:
        """Remove a subscription by its handle.

        Parameters
        ----------
        handle:
            The :class:`SubscriptionHandle` returned by :meth:`subscribe`.

        Returns
        -------
        bool
            ``True`` if the subscription was found and removed.
        """
        removed = False

        with self._lock:
            if handle.event_types is None:
                before = len(self._subscribers[None])
                self._subscribers[None] = [
                    r
                    for r in self._subscribers[None]
                    if r.handle_id != handle.handle_id
                ]
                removed = len(self._subscribers[None]) < before
            else:
                for et in handle.event_types:
                    before = len(self._subscribers[et.value])
                    self._subscribers[et.value] = [
                        r
                        for r in self._subscribers[et.value]
                        if r.handle_id != handle.handle_id
                    ]
                    if len(self._subscribers[et.value]) < before:
                        removed = True

        if removed:
            logger.debug(
                "EventBus %r: unsubscribed handle=%s source=%r",
                self._name,
                handle.handle_id[:8],
                handle.source,
            )
        return removed

    # ─────────────────────────────────────────────────────────────────────────
    # Publishing
    # ─────────────────────────────────────────────────────────────────────────

    def publish(self, event: EventEnvelope) -> bool:
        """Publish an event asynchronously (fire-and-forget, non-blocking).

        The event is placed in the priority queue and dispatched by the
        background dispatcher thread.  Returns immediately.

        Parameters
        ----------
        event:
            The :class:`~campus_helpdesk.interaction.events.EventEnvelope`
            to publish.

        Returns
        -------
        bool
            ``True`` if the event was enqueued; ``False`` if it was dropped
            due to queue overflow.
        """
        return self._enqueue(event)

    def publish_async(self, event: EventEnvelope) -> bool:
        """Alias for :meth:`publish`.  Explicitly non-blocking."""
        return self._enqueue(event)

    def publish_sync(self, event: EventEnvelope, timeout: float = 5.0) -> bool:
        """Publish an event and block until all handlers have completed.

        Useful in tests and in cases where the caller must guarantee the event
        is fully processed before proceeding.

        Parameters
        ----------
        event:
            The :class:`~campus_helpdesk.interaction.events.EventEnvelope`
            to publish.
        timeout:
            Maximum seconds to wait for dispatch completion.

        Returns
        -------
        bool
            ``True`` if all handlers completed within *timeout*; ``False`` if
            the timeout expired or the event was dropped.

        Raises
        ------
        RuntimeError
            If called from the dispatcher thread itself (would deadlock).
        """
        # Detect deadlock: if we are the dispatcher thread itself, or if we are
        # a handler thread that the dispatcher is currently waiting on, calling
        # publish_sync() would block forever.
        in_dispatcher = threading.current_thread() is self._dispatcher
        in_handler = getattr(self._handler_local, "is_bus_handler", False)
        if in_dispatcher or in_handler:
            raise RuntimeError(
                "publish_sync() must not be called from within a bus handler or "
                "the dispatcher thread — use publish() or publish_async() to "
                "avoid deadlocks."
            )

        completion = threading.Event()
        with self._lock:
            self._pending_sync[event.event_id] = completion

        enqueued = self._enqueue(event)
        if not enqueued:
            with self._lock:
                self._pending_sync.pop(event.event_id, None)
            return False

        dispatched = completion.wait(timeout=timeout)

        with self._lock:
            self._pending_sync.pop(event.event_id, None)

        return dispatched

    def _enqueue(self, event: EventEnvelope) -> bool:
        """Internal: assign sequence number and put entry on the queue."""
        with self._seq_lock:
            self._sequence += 1
            seq = self._sequence

        entry = _QueueEntry(
            priority_key=-event.priority.value,
            sequence=seq,
            event=event,
        )

        try:
            if self._overflow_drop:
                self._queue.put(entry, timeout=self._overflow_timeout)
            else:
                self._queue.put(entry, block=True)

            with self._stats_lock:
                self._events_published += 1

            logger.debug(
                "EventBus %r: enqueued event_type=%s id=%s priority=%s",
                self._name,
                event.event_type.value,
                event.event_id[:8],
                event.priority.name,
            )
            return True

        except queue.Full:
            with self._stats_lock:
                self._events_dropped += 1

            logger.warning(
                "EventBus %r: queue full – dropped event_type=%s id=%s",
                self._name,
                event.event_type.value,
                event.event_id[:8],
            )
            return False

    # ─────────────────────────────────────────────────────────────────────────
    # Dispatcher
    # ─────────────────────────────────────────────────────────────────────────

    def _dispatch_loop(self) -> None:
        """Background dispatcher thread: pull events and invoke handlers."""
        logger.debug("EventBus %r: dispatcher thread started", self._name)

        while not self._stop_event.is_set():
            try:
                entry = self._queue.get(timeout=0.05)
            except queue.Empty:
                continue

            try:
                self._dispatch_event(entry.event)
            except Exception:
                logger.exception(
                    "EventBus %r: unhandled error dispatching %s",
                    self._name,
                    entry.event.event_type.value,
                )
            finally:
                self._queue.task_done()

        # Drain remaining events gracefully on shutdown
        _drained = 0
        while True:
            try:
                entry = self._queue.get_nowait()
            except queue.Empty:
                break
            try:
                self._dispatch_event(entry.event)
                _drained += 1
            except Exception:
                pass
            finally:
                self._queue.task_done()

        if _drained:
            logger.debug(
                "EventBus %r: drained %d events during shutdown", self._name, _drained
            )
        logger.debug("EventBus %r: dispatcher thread stopped", self._name)

    def _dispatch_event(self, event: EventEnvelope) -> None:
        """Dispatch a single event to all matching subscribers."""
        # Use perf_counter_ns() for highest resolution (especially on Windows
        # where monotonic_ns() can have ~100 µs granularity).
        t_start_ns = time.perf_counter_ns()

        # ── Collect matching subscriber records ────────────────────────────
        with self._lock:
            specific: list[_SubscriptionRecord] = list(
                self._subscribers.get(event.event_type.value, [])
            )
            wildcards: list[_SubscriptionRecord] = list(
                self._subscribers.get(None, [])
            )

        # Deduplicate: a wildcard record should not appear in specific too
        # (by design they can't, but guard with handle_id set)
        seen: set[str] = set()
        all_records: list[_SubscriptionRecord] = []
        for r in specific + wildcards:
            if r.handle_id not in seen:
                seen.add(r.handle_id)
                all_records.append(r)

        # ── Filter by min_priority ─────────────────────────────────────────
        matching = [r for r in all_records if event.priority >= r.min_priority]

        # ── Identify one-shot records before dispatch (they may be removed) ─
        one_shot_records = [r for r in matching if r.is_one_shot]

        # ── Submit handlers to thread pool ────────────────────────────────
        futures: list[Future[None]] = [
            self._executor.submit(self._invoke_handler, r.handler, event)
            for r in matching
        ]

        # ── Wait for all handlers to complete ────────────────────────────
        delivered = 0
        failures = 0
        for future in futures:
            try:
                future.result(timeout=10.0)
                delivered += 1
            except Exception:
                failures += 1
                # Exception already logged inside _invoke_handler

        # ── Remove one-shot subscriptions ─────────────────────────────────
        if one_shot_records:
            with self._lock:
                for record in one_shot_records:
                    if record.event_types is None:
                        # Wildcard one-shot
                        self._subscribers[None] = [
                            r
                            for r in self._subscribers[None]
                            if r.handle_id != record.handle_id
                        ]
                    else:
                        for et in record.event_types:
                            self._subscribers[et.value] = [
                                r
                                for r in self._subscribers[et.value]
                                if r.handle_id != record.handle_id
                            ]

        # ── Update metrics ────────────────────────────────────────────────
        elapsed_ns = time.perf_counter_ns() - t_start_ns
        with self._stats_lock:
            self._events_delivered += delivered
            self._handler_failures += failures
            self._total_dispatch_ns += elapsed_ns
            self._dispatch_count += 1
            if delivered:
                self._per_event_type[event.event_type.value] += delivered

        logger.debug(
            "EventBus %r: dispatched %s to %d/%d handlers in %.1f µs",
            self._name,
            event.event_type.value,
            delivered,
            len(matching),
            elapsed_ns / 1_000,
        )

        # ── Signal publish_sync callers ───────────────────────────────────
        with self._lock:
            completion = self._pending_sync.get(event.event_id)
        if completion is not None:
            completion.set()

    def _invoke_handler(
        self, handler: HandlerType, event: EventEnvelope
    ) -> None:
        """Invoke a single handler with full error isolation.

        Marks the calling thread as a bus-handler thread via a thread-local
        flag so that :meth:`publish_sync` can detect the reentrant-deadlock
        scenario and raise :exc:`RuntimeError` instead of hanging.

        Supports both synchronous and ``async`` coroutine handlers.

        Raises
        ------
        Exception
            Re-raises the handler's exception so the dispatcher can count it.
            The exception is also logged here for immediate visibility.
        """
        # Mark this executor thread as a bus-handler thread for the lifetime
        # of this invocation so publish_sync() can detect the deadlock.
        self._handler_local.is_bus_handler = True
        try:
            if asyncio.iscoroutinefunction(handler):
                asyncio.run(handler(event))  # type: ignore[arg-type]
            else:
                handler(event)
        except Exception as exc:
            logger.error(
                "EventBus %r: handler %r raised %s: %s",
                self._name,
                getattr(handler, "__name__", repr(handler)),
                type(exc).__name__,
                exc,
            )
            raise  # re-raise so dispatcher counts it in handler_failures
        finally:
            self._handler_local.is_bus_handler = False

    # ─────────────────────────────────────────────────────────────────────────
    # Control
    # ─────────────────────────────────────────────────────────────────────────

    def clear(self) -> int:
        """Drain all pending events without dispatching them.

        Use during tests or after an error reset to start fresh.

        Returns
        -------
        int
            Number of events drained.
        """
        drained = 0
        while True:
            try:
                self._queue.get_nowait()
                self._queue.task_done()
                drained += 1
            except queue.Empty:
                break

        if drained:
            with self._stats_lock:
                self._events_dropped += drained
            logger.debug(
                "EventBus %r: cleared %d queued events", self._name, drained
            )
        return drained

    def shutdown(self, timeout: float = 5.0, *, drain: bool = True) -> None:
        """Gracefully stop the event bus.

        Sets the stop flag, optionally drains remaining queued events, waits
        for the dispatcher thread to exit, then shuts down the thread pool.

        Parameters
        ----------
        timeout:
            Maximum seconds to wait for the dispatcher thread.
        drain:
            When ``True`` (default) the dispatcher finishes processing any
            events already in the queue before stopping.  When ``False`` the
            dispatcher stops immediately after the current event.
        """
        logger.info("EventBus %r: shutdown requested (drain=%s)", self._name, drain)

        if not drain:
            self.clear()

        self._stop_event.set()
        self._dispatcher.join(timeout=timeout)

        if self._dispatcher.is_alive():
            logger.warning(
                "EventBus %r: dispatcher did not stop within %.1fs",
                self._name,
                timeout,
            )

        self._executor.shutdown(wait=False, cancel_futures=False)
        logger.info("EventBus %r: shutdown complete", self._name)

    # ─────────────────────────────────────────────────────────────────────────
    # Diagnostics
    # ─────────────────────────────────────────────────────────────────────────

    def health(self) -> dict[str, Any]:
        """Return a health status dictionary.

        Suitable for the ``/diagnostics`` HTTP endpoint and the debug CLI.

        Returns
        -------
        dict with keys:
            ``status``           – ``"healthy"`` or ``"stopped"``
            ``running``          – dispatcher loop is active
            ``dispatcher_alive`` – dispatcher thread is live
            ``queue_depth``      – current queue size
            ``subscriber_count`` – total subscription records
            ``handler_failures`` – cumulative failure count
            ``events_dropped``   – cumulative dropped-event count
            ``uptime_seconds``   – seconds since construction
        """
        with self._lock:
            sub_count = sum(len(v) for v in self._subscribers.values())

        with self._stats_lock:
            failures = self._handler_failures
            dropped = self._events_dropped

        running = not self._stop_event.is_set()
        alive = self._dispatcher.is_alive()

        return {
            "status": "healthy" if (running and alive) else "stopped",
            "running": running,
            "dispatcher_alive": alive,
            "queue_depth": self._queue.qsize(),
            "subscriber_count": sub_count,
            "handler_failures": failures,
            "events_dropped": dropped,
            "uptime_seconds": round(time.monotonic() - self._start_time, 3),
        }

    def statistics(self) -> BusStatistics:
        """Return an immutable snapshot of all bus metrics.

        Returns
        -------
        BusStatistics
        """
        with self._lock:
            sub_count = sum(len(v) for v in self._subscribers.values())

        with self._stats_lock:
            avg_us = (
                (self._total_dispatch_ns / self._dispatch_count) / 1_000
                if self._dispatch_count > 0
                else 0.0
            )
            return BusStatistics(
                events_published=self._events_published,
                events_delivered=self._events_delivered,
                events_dropped=self._events_dropped,
                handler_failures=self._handler_failures,
                queue_depth=self._queue.qsize(),
                avg_dispatch_latency_us=round(avg_us, 2),
                subscriber_count=sub_count,
                uptime_seconds=round(time.monotonic() - self._start_time, 3),
                per_event_type=dict(self._per_event_type),
            )

    def queue_depth(self) -> int:
        """Return the current number of pending events in the queue."""
        return self._queue.qsize()

    def registered_subscribers(self) -> dict[str, int]:
        """Return ``{event_type_name: count}`` for all non-empty subscriber lists.

        The key ``"WILDCARD"`` represents wildcard subscriptions.

        Returns
        -------
        dict[str, int]
        """
        with self._lock:
            return {
                ("WILDCARD" if key is None else key): len(records)
                for key, records in self._subscribers.items()
                if records
            }

    # ─────────────────────────────────────────────────────────────────────────
    # Context manager support
    # ─────────────────────────────────────────────────────────────────────────

    def __enter__(self) -> "EventBus":
        return self

    def __exit__(self, *_: Any) -> None:
        self.shutdown()

    def __repr__(self) -> str:
        return (
            f"EventBus(name={self._name!r}, "
            f"queue_depth={self._queue.qsize()}, "
            f"running={not self._stop_event.is_set()})"
        )


# ---------------------------------------------------------------------------
# Public API surface
# ---------------------------------------------------------------------------

__all__ = [
    "EventBus",
    "SubscriptionHandle",
    "BusStatistics",
    "HandlerType",
]
