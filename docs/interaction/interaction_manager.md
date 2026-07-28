# Interaction Manager Documentation

This document describes the design, operational responsibilities, event flow mappings, thread safety model, and error recovery policies for the central robot controller (`InteractionManager`).

---

## 1. Architectural Role

The Interaction Manager is the single brain of the robot runtime. It has the following constraints and guidelines:
* **Control plane only**: It coordinates services but does NOT perform heavy execution tasks (such as STT, TTS, RAG, or computer vision).
* **Decoupled from Hardware**: It interacts with components strictly by subscribing and publishing events through the `EventBus` and updating state via the `RobotStateMachine`.

---

## 2. Event-State Matrix

For every incoming event type, the Interaction Manager checks the FSM's current state, transitions the state machine, and triggers downstream actions:

| Incoming Event | Expected State | Target State | Published Events / Actions |
|---|---|---|---|
| `SYSTEM_READY` | `BOOTING`/`INITIALIZING` | `IDLE` | Begins the main interaction loop. |
| `PERSON_DETECTED` | `IDLE` | `READY` | Generates a new session and interaction context; publishes `SESSION_STARTED`. |
| `VOICE_STARTED` | `READY` | `LISTENING` | Captures microphone input stream. |
| `VOICE_STOPPED` | `LISTENING` | `PROCESSING` | Buffers recording, sends it for speech-to-text. |
| `TRANSCRIPT_FINAL` | `LISTENING`/`PROCESSING` | `PROCESSING` | Captures input string; publishes `QUERY_STARTED` to activate RAG. |
| `ANSWER_READY` | `PROCESSING` | `SPEAKING` | Collects LLM answer; triggers TTS voice generation. |
| `TTS_COMPLETED` | `SPEAKING` | `READY` | Reset to ready, waiting for next question. |
| `PERSON_LEFT` | Any conversation state | `IDLE` | Clears interaction context; publishes `SESSION_ENDED`. |
| `TIMEOUT` | Any active state | `IDLE` / `READY` | Performs state recovery depending on the timed-out state. |
| `ERROR` | Any state (except `SHUTDOWN`) | `ERROR` | Resets pipeline safely if the error payload is marked as fatal. |

---

## 3. Active Timeouts & Recovery

A background daemon thread (`InteractionManager-timeout-monitor`) checks FSM state residencies twice a second. When the current state exceeds its configured timeout duration, the FSM publishes a `TIMEOUT` event:
* **`READY` Timeout**: Indicates the user has walked away or stopped speaking. The manager transitions to `IDLE` and ends the session.
* **`LISTENING` / `PROCESSING` / `SPEAKING` Timeouts**: Recoverable pipeline timeouts. The manager resets the FSM back to `READY` to prompt another interaction loop.

---

## 4. Thread Safety Model

Multiple events may be dispatched from separate thread pools (Camera, Mic/VAD, STT/TTS executors) concurrently.
* **Mutual Exclusion**: State transitions, context modifications (such as updating active session IDs), and diagnostics tracking are guarded by a reentrant lock (`threading.RLock`).
* **Sequence Integrity**: If conflicting events arrive simultaneously (for example, a `PERSON_LEFT` and a `VOICE_STARTED`), FSM validation locks guarantee that only the legally valid pathway progresses. Invalid sequences are discarded, and warning logs are generated.
