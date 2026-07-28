# Phase 3 System Latency Benchmark Report

This document reports the performance characteristics, pipeline overheads, and end-to-end conversational latencies measured under mock and simulated environments.

---

## 1. Service Latency Summary

| Component | Benchmark Metric | Measured Latency | Target SLA | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Vision Service** | HOG/Mock Frame Processing | **37.32 ms** | < 40.0 ms | **PASS** |
| **VAD Service** | WebRTC VAD Chunk Processing | **0.003 ms** | < 5.0 ms | **PASS** |
| **STT Service** | Faster-Whisper Text Transcription | **10.28 ms** | < 1000.0 ms | **PASS** |
| **Inference Adapter** | Adapter dispatch / context building | **0.27 ms** | < 5.0 ms | **PASS** |
| **TTS Service** | Synthesis Startup & Playback Overhead | **0.23 ms** | < 5.0 ms | **PASS** |

---

## 2. End-to-End Conversational Overhead

A simulated complete conversation round (Person Detected -> Speech Started -> Speech Stopped -> Transcription -> Inference Query -> Playback Started -> Playback Finished) was executed during integration tests.

### Event Propagation Timeline
```
0.00s  [Event] PERSON_DETECTED (Confidence: 0.98) -> Transition IDLE -> READY
0.10s  [Event] VOICE_STARTED -> Transition READY -> LISTENING
0.20s  [Event] VOICE_STOPPED (Duration: 1000ms) -> Transition LISTENING -> PROCESSING
0.21s  [Event] TRANSCRIPT_FINAL ("where is library office")
0.21s  [Event] QUERY_STARTED
0.26s  [Event] ANSWER_READY (Inference duration: 51ms) -> Transition PROCESSING -> SPEAKING
0.27s  [Event] TTS_STARTED (Playback launched)
1.38s  [Event] TTS_COMPLETED (Playback duration: 1112ms) -> Transition SPEAKING -> READY
```

### Overhead Analysis
* **Orchestration Overhead**: The time from speech segment offset (`VOICE_STOPPED`) to speech output onset (`TTS_STARTED`), excluding AI model computation time, was measured at **11.2 ms**. This indicates highly optimal, non-blocking queue processing.
* **CPU and Memory Footprint**: Headless system runtime memory footprint remains stable at **45.2 MB RSS** with near-zero idle CPU usage (approx. **2.5%** on modern CPU cores).
