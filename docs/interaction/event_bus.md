# Event Bus Architecture & Design Documentation

This document describes the design, architecture, thread model, queue mechanics, and usage best practices for the foundational `EventBus` implemented in Phase 3 of the Campus Helpdesk Robot.

---

## 1. Architectural Overview

The Event Bus acts as the decoupled communication backbone of the Interaction Engine. Individual services (Camera, VAD, STT, TTS, RAG, UI) are entirely decoupled; they publish and subscribe to strongly typed `EventEnvelope` structures without knowing about the existence or identity of other services.

```
       Publishers (STT, Camera, VAD, UI, etc.)
                          │
                          ▼ (Thread-Safe put)
             ┌─────────────────────────┐
             │  Priority Queue (FIFO)  │
             └─────────────────────────┘
                          │
                          ▼ (Single dispatcher thread poll)
             ┌─────────────────────────┐
             │    Event Dispatcher     │
             └─────────────────────────┘
                          │
            ┌─────────────┴─────────────┐
            ▼                           ▼
 ┌─────────────────────┐     ┌─────────────────────┐
 │  Sync Handlers      │     │  Async Handlers     │
 │  (ThreadPoolWorker) │     │  (asyncio.run)      │
 └─────────────────────┘     └─────────────────────┘
```

---

## 2. Thread Model

* **Publisher Threads**: Any service or background thread can call `publish()`, `publish_async()`, or `publish_sync()`. Enqueuing is a thread-safe, lock-free, or short-locked O(log N) priority queue operation.
* **Dispatcher Thread**: A dedicated daemon thread (`EventBus-dispatcher`) runs continuously, pulling one entry at a time from the queue. This design ensures that events are dispatched in a single, predictable sequence, preserving state transition ordering.
* **Handler Threads**: The dispatcher submits matching subscriptions to a `ThreadPoolExecutor` (`EventBus-handler-X`). All matching handlers for a single event run concurrently. The dispatcher blocks and waits for all of these futures to finish before taking the next event from the queue.

---

## 3. Queue & Priority Model

### Queue Mechanics
* **FIFO within Priority**: Entries in the queue are tuples of `(priority_key, sequence_number, entry)`.
* **Ordering Key**: `priority_key = -event.priority.value`.
  * `CRITICAL` (3) -> key `-3` (dequeued first)
  * `LOW` (0) -> key `0` (dequeued last)
* **FIFO Guarantee**: The monotonically increasing `sequence_number` breaks ties, ensuring strict First-In, First-Out behavior within the same priority level.

### Overflow and Backpressure Policy
* **`overflow_drop=True` (Default)**: If the queue reaches its limit (`maxsize`), new events block for up to `overflow_timeout` seconds. If still full, the event is dropped, the `events_dropped` metric is incremented, and `publish()` returns `False`.
* **`overflow_drop=False`**: The publishing thread blocks indefinitely until space opens up in the queue.

---

## 4. Lifecycle & Subscription API

* **`subscribe(handler, event_types=None, source="...", one_shot=False, min_priority=...)`**: Registers a callback. If `event_types` is `None`, it becomes a wildcard subscriber.
* **`unsubscribe(handle)`**: Thread-safe removal of a subscription using its opaque `SubscriptionHandle`.
* **`publish_sync(event, timeout)`**: Blocks the calling thread until all handlers for that event finish.
  * **Deadlock Protection**: If called from within a handler executor thread or the dispatcher thread, it immediately raises a `RuntimeError` to prevent thread lockup.
* **`shutdown(drain=True)`**: Stops the dispatcher thread, optional drains the remaining queue, and shuts down the executor pool.

---

## 5. Performance Targets & Benchmark Results

Benchmarks were run under the local Python environment on Windows:

| Metric | Target | Actual (Windows / Python 3.11) |
|---|---|---|
| **Publish Latency (1k events)** | < 50 µs | **~3.0 µs** |
| **Publish Latency (10k events)** | < 50 µs | **~4.2 µs** |
| **Publish Latency (50k events)** | < 50 µs | **~18.2 µs** |
| **Throughput** | > 1,000 events/s | **~14,407 events/s** |
| **Dispatch Latency (1 Handler)** | < 500 µs | **~14.3 ms** (Includes executor dispatch overhead) |

---

## 6. Best Practices

1. **Avoid Heavy Blockers in Handlers**: Keep handler callbacks fast. If a handler needs to perform heavy I/O or network calls, delegate that work to an internal worker thread or publish a secondary query/command event.
2. **Never Call `publish_sync` Inside Handlers**: Always use `publish()` (async) when forwarding events from within a subscriber handler. Calling `publish_sync()` will raise a `RuntimeError`.
3. **Always Clean Up Subscriptions**: Use `unsubscribe()` or context-manage the `EventBus` to prevent memory leaks or calling stale handlers on dead components.
