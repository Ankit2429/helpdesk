# Campus Helpdesk Robot — Module Roadmap

This document outlines completed architectural milestones and approved future roadmap initiatives for the Campus Helpdesk Robot.

---

## Completed Milestones (Phase 1 & 2)

- [x] **Clean Layered Architecture**: Full separation into `domain`, `infrastructure`, `application`, `presentation`, and `api` layers.
- [x] **Hybrid Vector Retrieval**: BM25 keyword search + FAISS dense similarity search (384d `all-MiniLM-L6-v2`) fused via Reciprocal Rank Fusion (RRF).
- [x] **Cross-Encoder Reranking**: Re-ranking candidate chunks with `cross-encoder/ms-marco-MiniLM-L-6-v2` (`local_files_only=True`).
- [x] **Offline LLM Integration**: Ollama engine running `qwen2.5:7b` / `llama3.2:3b` with streaming response generation.
- [x] **Touch UI Kiosk**: Streamlined CustomTkinter touch application (`campus_helpdesk.touch_app`) with multi-script language selector.
- [x] **Speech Pipeline**: `FasterWhisperSTTService` (int8 CPU) for STT and `NonBlockingTTSService` (Piper ONNX) for TTS.
- [x] **Comprehensive Test Suite**: 550+ unit, integration, and RAG retrieval tests in `pytest`.
- [x] **Strict Offline Enforcement**: Pinned model loaders with `local_files_only=True` and disabled cloud routing.

---

## Active & Future Roadmap Initiatives

### Phase 3 – Performance & Async Architecture
1. **Async Uvicorn Endpoints**:
   - Migrate synchronous REST endpoints in `api/routes/chat.py` to `async def` using `run_in_threadpool` or `ollama.AsyncClient` to prevent worker thread blocking during peak loads.

2. **Perception & Dual-Screen Vision Integration**:
   - Re-embed the `CameraView` panel when a dual-display hardware configuration is active (separate secondary display for live camera detection and mascot eye-contact interaction).

3. **Edge Deployment Hardening**:
   - Create systemd service unit files and ARM64-optimized Docker containers for production deployment on Raspberry Pi 5 (8GB RAM).
