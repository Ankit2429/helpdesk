from pathlib import Path

artifact_dir = Path(r"C:\Users\CMCY\.gemini\antigravity-ide\brain\a28e4b8f-6f0f-4c8a-aed1-a029b8bd7f47")

report_content = """# Voice Audit Report

This report presents a technical audit of the voice pipeline components for the Sparky Offline Campus Helpdesk Robot.

---

## 1. Wake Word Detector
- **Status**: Complete
- **File Locations**:
  - Service: [wake_word_service.py](file:///d:/AUNTII/src/campus_helpdesk/services/wake_word_service.py)
  - Engine: [wake_word.py](file:///d:/AUNTII/src/campus_helpdesk/infrastructure/audio/wake_word.py)
- **Evaluation**: Fully functional offline wake-word monitoring. Integrates openwakeword `hey_jarvis_v0.1` model with a reliable RMS audio-energy burst detector fallback.
- **Current Limitations**: Falling back to acoustic energy spikes can lead to false triggers in highly echoey rooms.
- **Recommended Improvements**: Pre-download offline ONNX models locally to avoid runtime fallback in remote network deployment.

---

## 2. Voice Activity Detection (VAD)
- **Status**: Complete
- **File Locations**:
  - Service: [vad_service.py](file:///d:/AUNTII/src/campus_helpdesk/services/vad_service.py)
- **Evaluation**: Uses `webrtcvad` wrapped in a multi-threaded chunk-buffering loop. Accurately publishes EventBus signals (`VOICE_STARTED`, `VOICE_STOPPED`).
- **Current Limitations**: WebRTC VAD is sensitive to rapid high-energy noises (like keyboard keystrokes or mouse clicks next to a desk mic).
- **Recommended Improvements**: Incorporate a simple spectral variance filter before WebRTC processing to filter out high-frequency transient click events.

---

## 3. Speech-to-Text (STT)
- **Status**: Complete
- **File Locations**:
  - Service: [stt_service.py](file:///d:/AUNTII/src/campus_helpdesk/services/stt_service.py)
  - Engine: [stt_service.py](file:///d:/AUNTII/src/campus_helpdesk/infrastructure/audio/stt_service.py)
- **Evaluation**: Powered by `faster-whisper` (ctranslate2 implementation of Whisper base/tiny). Supports auto-detecting Kannada, Hindi, and English.
- **Current Limitations**: Processing audio segments sequentially introduces a small transcription delay after the user stops speaking.
- **Recommended Improvements**: Transition from block-file transcription to Whisper's streaming chunk transcriber mode.

---

## 4. Text-to-Speech (TTS)
- **Status**: Complete
- **File Locations**:
  - Service: [tts_service.py](file:///d:/AUNTII/src/campus_helpdesk/services/tts_service.py)
  - Engine: [tts_service.py](file:///d:/AUNTII/src/campus_helpdesk/infrastructure/audio/tts_service.py)
- **Evaluation**: Powered by `Piper` ONNX TTS. Features sentence-by-sentence streaming, enabling spoken output playback in under 1 second.
- **Current Limitations**: Piper synthesizes speech locally using CPU execution, which can slightly spike latency during complex multi-clause sentence generation.
- **Recommended Improvements**: Enable sentence length constraints in LLM system prompt outputs to shorten target synthesis buffers.

---

## 5. Conversation Manager
- **Status**: Complete
- **File Locations**:
  - Manager: [conversation_manager.py](file:///d:/AUNTII/src/campus_helpdesk/application/conversation_manager.py)
- **Evaluation**: Implements Assistant state machine and wraps memory sessions. Features reliable barge-in detection (stops TTS playback and resets generation instantly upon user speech detection).
- **Current Limitations**: Multi-turn history lacks active semantic summarization, meaning long conversation runs can load the context window.
- **Recommended Improvements**: Incorporate rolling memory summaries for dialogue history turns exceeding count threshold.

---

## 6. Touch App Integration
- **Status**: Complete
- **File Locations**:
  - UI View: [touch_app.py](file:///d:/AUNTII/src/campus_helpdesk/touch_app.py)
- **Evaluation**: Connects UI views directly to RAG chat services, binding STT transcriber hooks, camera panels, and NonBlockingTTSService speech calls in-process.
"""

with open(artifact_dir / "voice_audit_report.md", "w", encoding="utf-8") as f:
    f.write(report_content)

print("Generated voice_audit_report.md successfully.")
