# Camera Service Documentation

This document describes the design, thread execution model, connection recovery, and usage best practices for the foundational `CameraService`.

---

## 1. Architectural Design

The Camera Service is responsible solely for frame ingestion and lifecycle management:
* **Separation of Concerns**: It does NOT perform computer vision, person detection, face recognition, or any downstream inference work. It simply streams raw image frames.
* **Format**: Frames are read via OpenCV, encoded to JPEG bytes to maintain a compact, fast payload footprint, and wrapped into `CameraPayload` instances.

---

## 2. Thread Model & Backpressure

* **Dedicated Thread**: Frame capturing runs in a background daemon loop (`camera_service-capture`) at the configured target FPS.
* **Newest Frame Wins**: The service publishes frames to the `EventBus` without blocking the capture thread. If the event bus queue becomes congested or subscribers are processing slowly, the publishing operation fails and the frame is immediately dropped. This prevents latency build-up, ensuring the robot always acts on the newest captured state.

---

## 3. Auto-Recovery & Reconnection Strategy

When frame reading fails (for example, if a USB camera is unplugged):
1. The service logs the issue and publishes a `CAMERA_DISCONNECTED` event.
2. It transitions to an offline state and attempts reconnection every `reconnect_delay` seconds.
3. Once the camera becomes available again, it re-initializes, publishes `CAMERA_RECONNECTED`, and resumes streaming.
4. **Mock Fallback**: If `use_mock_fallback` is enabled, the camera service automatically falls back to generating synthetic test frames using NumPy (a black frame containing text counters and color patterns) if a physical device cannot be opened. This ensures unit tests and simulation flows remain stable.

---

## 4. Diagnostics & Diagnostics API

Call `diagnostics()` to query the service state:
* **`connected`**: Whether the camera index is currently open.
* **`current_fps`**: Running average of actual captured frames per second.
* **`frames_dropped`**: Cumulative count of frames discarded due to bus congestion.
* **`capture_latency_ms`**: Running average time taken to read and prepare a frame.
