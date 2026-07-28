# Offline Campus Helpdesk Robot — Troubleshooting Guide

## Common Issues & Diagnostics

### 1. Ollama Connection Error ("Failed to connect to Ollama")

- **Symptom**: Application throws `LLMServiceError` or status 503 on `/chat`.
- **Cause**: Ollama background service is not running or listening on port 11434.
- **Resolution**:
  ```powershell
  # Check if Ollama is running
  curl http://127.0.0.1:11434/api/tags

  # Restart Ollama service
  ollama serve
  ```

---

### 2. Camera Stream Failure / Webcam Not Found

- **Symptom**: GUI displays `"⚠️ Camera Unavailable"`.
- **Cause**: OpenCV cannot lock the webcam index or another app is using the camera.
- **Resolution**:
  - Close other video software (Zoom, Teams, Camera app).
  - Verify webcam index in `.env`: `WEBCAM_INDEX=0` (or try index 1 or 2).

---

### 3. FAISS Vector Index Missing or Empty

- **Symptom**: API returns `"I don't have information about that in my knowledge base."` for all queries.
- **Cause**: Markdown documents in `data/canonical_markdown/` have not been ingested into `data/faiss/`.
- **Resolution**:
  ```powershell
  # Re-ingest canonical knowledge base
  uv run python -m campus_helpdesk.ingest
  ```

---

### 4. Audio Input / Speech Recognition Timeout

- **Symptom**: Speech recognition fails to transcribe voice input.
- **Cause**: Microphone level too low or Faster-Whisper local model cache missing.
- **Resolution**:
  - Test microphone input level in system settings.
  - Verify `WHISPER_MODEL_SIZE=base` and `WHISPER_DEVICE=cpu` in `.env`.

---

### 5. TTS Sounds Like Default System Voice, Not Piper

- **Symptom**: Log shows `Piper voice files not found... Falling back to pyttsx3.`
- **Cause**: `data/piper/<TTS_VOICE_MODEL>.onnx` and `.onnx.json` are missing.
- **Resolution**: Download the voice files per `docs/MODEL_SETUP.md` section 4,
  ensure the filenames exactly match `TTS_VOICE_MODEL`.

---

### 6. Out-of-Domain Hallucination Guarding

- **Symptom**: System declines to answer question.
- **Cause**: The search distance score exceeded `RAG_DISTANCE_THRESHOLD` (default 2.0).
- **Resolution**:
  - If question is valid campus domain knowledge, add relevant Markdown documentation to `data/canonical_markdown/` and run `campus_helpdesk.ingest`.
