# Speech-to-Text (STT) Service Documentation

This document describes the design, backend abstraction, queue architecture, threading boundaries, and usage best practices for the `STTService`.

---

## 1. Architectural Role

The STT Service converts recorded speech files into structured text:
* **Event-Driven**: It consumes `VOICE_STOPPED` events and produces `TRANSCRIPT_FINAL` events.
* **Microphone Independent**: It does NOT listen to or manage microphone hardware or VAD streams directly. It only operates on generated audio segment WAV files.

---

## 2. Decoupled Backend Abstraction

The service delegates all speech recognition tasks to the `BaseTranscriptionBackend` interface:
```python
class BaseTranscriptionBackend(ABC):
    @abstractmethod
    def load_model(self) -> float:
        pass

    @abstractmethod
    def transcribe(self, audio_path: str) -> tuple[str, str, float]:
        pass
```
* **`FasterWhisperBackend`**: Implements offline inference using preloaded ctranslate2-optimized Whisper models.
* **`MockTranscriptionBackend`**: Provides predefined return strings for unit testing and headless CI pipelines without model overhead.

---

## 3. FIFO Worker Thread

* **Dedicated Thread**: Transcription is executed on the background worker thread `STTService-worker`.
* **Sequential Queue**: Transcription requests enter a FIFO `queue.Queue`. Because Whisper inference is resource-intensive and blocks the thread, the FIFO queue guarantees that incoming audio segments are processed in order without interrupting or corrupting active model inference tasks.

---

## 4. Metadata Tracing

Because `TranscriptPayload` follows a strict schema, extra diagnostic metrics are attached directly to the `EventEnvelope.metadata` key-value store:
* **`duration_ms`**: Duration of the transcribed audio file.
* **`transcription_latency_ms`**: Time spent processing inference.
* **`model_name`**: Name, device type, and compute type of the model that executed the recognition.

---

## 5. Performance Tuning & Offline Best Practices

* **Compute Types**: For low-power deployments (such as Raspberry Pi 5), use `int8` or `int8_float16` compute types on CPU to reduce memory overhead and latency.
* **Preloading**: Always invoke `initialize()` to preload the model during service bootstrap to avoid overhead during the first user interaction.
