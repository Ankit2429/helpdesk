# Vision Service Documentation

This document describes the design, detector abstraction, operational pipeline, thread configuration, and best practices for the `VisionService` implemented in Phase 3.

---

## 1. Architectural Design

The Vision Service consumes raw image frames and manages perception-level state:
* **Decoupled Perception**: It contains no robot interaction logic, behavior trees, or FSM transition code. It only outputs presence changes.
* **Abstract Detector Interface**: The service interacts with detection algorithms solely through the `BasePersonDetector` interface:
  ```python
  class BasePersonDetector(ABC):
      @abstractmethod
      def detect(self, frame: np.ndarray) -> tuple[bool, float, tuple[int, int, int, int] | None]:
          pass
  ```
  This allows dropping in YOLOv8/11, MediaPipe, or TensorRT later without modifying the service container code.

---

## 2. Detection Implementations

1. **`HOGPersonDetector` (Production default)**: Uses OpenCV's Histogram of Oriented Gradients (HOG) combined with the Default People Detector SVM. Frames are resized to a max width of 640px to maintain latency targets.
2. **`MockPersonDetector` (Testing/CI default)**: Simulates presence flags, bounding boxes, and confidence scores for offline test stability.

---

## 3. Thread Boundaries & Backpressure

* **Dedicated Thread**: Detection runs inside a background worker thread (`vision_service-worker`) to prevent locking the camera publishing loop.
* **Frame Discarding**: Incoming `FRAME_CAPTURED` events are written to a bounded queue of size 1. If the worker thread is busy running inference, older queued frames are popped and skipped. The newest frame always replaces the older one.

---

## 4. Debouncing & Event Deduplication

To prevent presence flickering (e.g. temporary occlusion or SVM detection misses):
* **Entry threshold (`min_hits`)**: Requires `3` (default) consecutive frames containing a person before publishing `PERSON_DETECTED`.
* **Exit threshold (`min_misses`)**: Requires `10` (default) consecutive frames with no person before publishing `PERSON_LEFT`.
* **Deduplication**: Once `PERSON_DETECTED` is published, the service suppresses duplicate detections until `PERSON_LEFT` is emitted, preventing event bus flooding.

---

## 5. Performance Metrics

| Metric | Target | Actual (OpenCV HOG on Windows) |
|---|---|---|
| **Detection Latency** | < 40 ms/frame | **~37.32 ms / frame** |
| **FPS Support** | 15–30 FPS | **Sustained** |
| **Frame Skipping** | Enabled | **Yes** (Drops backlogged frames under heavy load) |
