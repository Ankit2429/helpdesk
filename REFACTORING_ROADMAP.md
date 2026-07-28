# Production-Grade Refactoring Roadmap: Campus Helpdesk Robot

This roadmap outlines a phased approach to refactoring the repository into a production-grade, offline-first AI product. It is based entirely on the evidence collected in the Architectural Analysis and Engineering Audit.

---

## Phase 1 – Safe Quick Wins (Low-risk immediate improvements)

### 1.1 Remove Unused Dependencies
- **Priority:** Low
- **Category:** Maintainability / Deployment
- **Problem Statement:** Bloated environment increasing Docker image size and provisioning time.
- **Evidence:** `beautifulsoup4`, `hf-xet`, `chromadb`, and `pocketsphinx` are listed in `pyproject.toml` but `grep` confirms they are never imported in the `src/` or root logic.
- **Root Cause:** Leftovers from early prototyping.
- **Exact Files Affected:** `pyproject.toml`, `requirements.txt`.
- **Implementation Plan:** Remove the dependencies from the build configuration files.
- **Potential Risks:** None.
- **Backward Compatibility:** Yes, no runtime logic uses them.
- **How to Verify:**
  - **Unit tests:** Re-run existing `pytest` suite.
  - **Integration tests:** Build the virtual environment and ensure no `ImportError` occurs.
  - **Manual verification:** Start the API (`main.py`) and GUI (`demo.py`).
- **Estimated Time:** 1 Hour
- **Expected Benefits:** Faster CI/CD pipelines, smaller edge deployment footprints.
- **Validation:** ✅ Proven by code analysis.

### 1.2 Unify Configuration Loading
- **Priority:** Medium
- **Category:** Maintainability
- **Problem Statement:** Configuration parsing is split between Pydantic and raw `os.getenv`.
- **Evidence:** `src/campus_helpdesk/config/settings.py` loads `ollama_base_url` properly via Pydantic, but `demo.py` (line ~60) uses `os.getenv("OLLAMA_HOST", settings.ollama_base_url)`.
- **Root Cause:** Legacy migration incomplete.
- **Exact Files Affected:** `demo.py`, `assistant_loop.py`, `stt_service.py` (root), `tts_service.py` (root), `presence_service.py` (root).
- **Implementation Plan:** Replace all `os.getenv` calls with `from campus_helpdesk.config.settings import get_settings`.
- **Potential Risks:** Minor regression if a deployment script relies on a non-standard env var name (like `OLLAMA_HOST` vs `.env` standard).
- **Backward Compatibility:** Yes.
- **How to Verify:**
  - **Unit tests:** Ensure `get_settings()` unit tests pass.
  - **Integration tests:** None needed.
  - **Manual verification:** Run `demo.py` and `assistant_loop.py` to ensure they connect to Ollama.
- **Estimated Time:** 4 Hours
- **Expected Benefits:** Single source of truth for all configurations, strong typing, and centralized validation.
- **Validation:** ✅ Proven by code analysis.

---

## Phase 2 – Medium Refactors (Moderate changes, limited architectural impact)

### 2.1 Standardize Exception Handling
- **Priority:** Medium
- **Category:** Error Handling / Maintainability
- **Problem Statement:** Bare exception catching hides critical bugs.
- **Evidence:** Over 40 instances of `except Exception as e:` or `except Exception:` found via `grep` (e.g., `main.py`, `demo.py`, `tts_service.py`).
- **Root Cause:** Hasty error wrapping during MVP development.
- **Exact Files Affected:** `main.py`, `demo.py`, `src/campus_helpdesk/infrastructure/**/*.py`, `src/campus_helpdesk/api/**/*.py`.
- **Implementation Plan:** Replace broad `Exception` catches with specific types (e.g., `httpx.RequestError`, `cv2.error`). Where broad catches remain necessary, add `exc_info=True` to logging.
- **Potential Risks:** A previously swallowed exception might now crash the app if the specific type isn't caught.
- **Backward Compatibility:** Yes.
- **How to Verify:**
  - **Unit tests:** Inject faults (e.g., mock Ollama to return 500) and assert the correct exception is raised/logged.
  - **Manual verification:** Disconnect the webcam or stop the Ollama server and verify logs are actionable.
- **Estimated Time:** 1 Day
- **Expected Benefits:** Actionable logs, predictable failure modes.
- **Validation:** ✅ Proven by code analysis.

### 2.2 Async FastAPI Endpoints
- **Priority:** High
- **Category:** Performance / Concurrency
- **Problem Statement:** Synchronous HTTP endpoints block the ASGI worker during long LLM inference times.
- **Evidence:** `src/campus_helpdesk/api/routes/chat.py` defines `def chat(payload: ChatRequest...)`.
- **Root Cause:** Using synchronous Ollama Python client calls directly in a FastAPI route.
- **Exact Files Affected:** `src/campus_helpdesk/api/routes/chat.py`, `src/campus_helpdesk/application/rag_chat_service.py`, `src/campus_helpdesk/infrastructure/llm/ollama_service.py`.
- **Implementation Plan:**
  1. Change `def chat` to `async def chat`.
  2. Use FastAPI's `run_in_threadpool(chat_service.respond, ...)` OR migrate `OllamaLLMService` to use the `ollama.AsyncClient`.
- **Potential Risks:** Thread safety issues if underlying infrastructure components (like FAISS) are not thread-safe. (Note: `FAISSSimilarityStore` currently uses an `RLock`, so it should be safe).
- **Backward Compatibility:** Yes, API contract remains identical.
- **How to Verify:**
  - **Integration tests:** Use `pytest-asyncio` and `httpx.AsyncClient` to send concurrent `/chat` requests.
  - **Manual verification:** Send two long prompts simultaneously via Postman/curl and verify they process concurrently.
- **Estimated Time:** 1-2 Days
- **Expected Benefits:** Prevents connection timeouts, drastically improves API throughput.
- **Validation:** ✅ Proven by code analysis.

---

## Phase 3 – Major Architecture Changes (Large structural improvements)

### 3.1 Resolve "Split Brain" Architecture (Eliminate Root Services)
- **Priority:** Critical
- **Category:** Architecture
- **Problem Statement:** Parallel, duplicate logic exists in the root folder (`assistant_loop.py`, `ttt_service.py`, etc.) bypassing the modern clean architecture in `src/`.
- **Evidence:** `assistant_loop.py` imports from `stt_service.py` (root), not `src.campus_helpdesk.infrastructure.audio.stt_service.py`. Duplicate implementations exist for STT, TTS, and Vision.
- **Root Cause:** An older MVP was kept alive in the root directory while the layered architecture was built in `src/`.
- **Exact Files Affected:** `assistant_loop.py`, `presence_service.py`, `stt_service.py`, `tts_service.py`, `ttt_service.py`.
- **Implementation Plan:**
  1. Refactor `assistant_loop.py` to instantiate `PersonDetector`, `FasterWhisperSTTService`, and `NonBlockingTTSService` from `src/campus_helpdesk/infrastructure/`.
  2. Implement the hardware orchestration logic inside a new Application-layer service (e.g., `src/campus_helpdesk/application/robot_orchestrator.py`).
  3. Delete the 4 legacy root services.
- **Potential Risks:** High. The root services have subtle logic differences (e.g., `ttt_service.py` has hardcoded Hindi regex FAQs, while `src/` relies solely on RAG). Replacing them will change runtime behavior.
- **Backward Compatibility:** No, this is an internal breaking change to how the Pi loop operates.
- **How to Verify:**
  - **Unit tests:** High coverage required on the new `RobotOrchestrator`.
  - **Manual verification:** Run the refactored `assistant_loop.py` on a Raspberry Pi with a camera and mic to ensure the wake/listen/speak cycle works identically.
- **Estimated Time:** 3-5 Days
- **Expected Benefits:** Halves maintenance surface area. Bug fixes to `src/` instantly benefit the hardware loop.
- **Validation:** ✅ Proven by code analysis.

### 3.2 Remove Hardcoded Localization (SOLID Violation)
- **Priority:** Medium
- **Category:** Architecture / Maintainability
- **Problem Statement:** `ttt_service.py` hardcodes Indic language FAQs via regex, bypassing the LLM and RAG pipeline entirely.
- **Evidence:** `ttt_service.py` lines ~23-53 define `CANNED_FAQ = {"kn": {...}, "hi": {...}}` and regex matching functions.
- **Root Cause:** A workaround implemented because the older LLM hallucinated Indic responses. (As per `ARCHITECTURE.md`, `qwen2.5` now handles this well).
- **Exact Files Affected:** `ttt_service.py` (to be deleted in 3.1), `src/campus_helpdesk/application/rag_chat_service.py`.
- **Implementation Plan:**
  1. Translate the hardcoded FAQs into the PDF/Text knowledge base (`data/knowledge/`).
  2. Rely on the `RAGChatService` and `qwen2.5` to retrieve and format the answers in the target language natively.
- **Potential Risks:** Increased latency for Indic queries (moving from O(1) regex to LLM inference).
- **Backward Compatibility:** No, response phrasing will become dynamic rather than static.
- **How to Verify:**
  - **Integration tests:** Ask the LLM specific Indic queries ("ಗ್ರಂಥಾಲಯವು ಎಲ್ಲಿದೆ?") and assert the RAG context is hit and translation is accurate.
- **Estimated Time:** 2 Days
- **Expected Benefits:** Centralized knowledge management, adherence to Open/Closed principle.
- **Validation:** ✅ Proven by code analysis.

---

## Phase 4 – Production Hardening

### 4.1 Memory & Resource Lifecycle Management
- **Priority:** High
- **Category:** Performance / Reliability
- **Problem Statement:** Hardware resources (Cameras, Microphones) are not strictly managed via context managers, risking memory leaks on 24/7 edge deployments.
- **Evidence:** `presentation/chat_window.py` runs an infinite Tkinter `after(40, self._update_camera_feed)` loop. If the UI crashes, the camera handle (`cv2.VideoCapture`) might not be released cleanly.
- **Root Cause:** Lack of robust lifecycle teardown hooks.
- **Exact Files Affected:** `presentation/chat_window.py`, `src/campus_helpdesk/infrastructure/vision/person_detector.py`, `src/campus_helpdesk/infrastructure/audio/stt_service.py`.
- **Implementation Plan:** Implement Python Context Managers (`__enter__`, `__exit__`) for all hardware adapters. Wrap main loops in strict `try/finally` blocks.
- **Potential Risks:** None.
- **Backward Compatibility:** Yes.
- **How to Verify:**
  - **Manual verification:** Force kill (SIGTERM) the process and verify `lsof /dev/video0` shows no hanging locks.
- **Estimated Time:** 1-2 Days
- **Expected Benefits:** 24/7 stability on Raspberry Pi hardware.
- **Validation:** ✅ Proven by code analysis.

### 4.2 Increase Test Coverage
- **Priority:** Critical
- **Category:** Testing
- **Problem Statement:** The project lacks automated tests, making refactoring dangerous.
- **Evidence:** `tests/` contains only `test_person_detector.py`.
- **Root Cause:** MVP development focus.
- **Exact Files Affected:** `/tests/`
- **Implementation Plan:**
  - Mock `ollama.Client` to test `RAGChatService`.
  - Mock `FAISS` to test vector retrieval logic.
  - Implement pytest fixtures for hardware (dummy audio/video streams).
- **Expected Benefits:** Safe future deployments.
- **Validation:** ✅ Proven by code analysis.

---

## Recommended Implementation Order

To minimize risk and preserve functionality, execute the roadmap in this exact order:

1. **Phase 4.2 (Testing)**: **CRITICAL**. Before touching the architecture, write unit tests for the `src/` modules (RAG, Chat, API). You cannot safely refactor the Pi loop without these.
2. **Phase 1 (Quick Wins)**: Clean up dependencies and centralize configuration to establish a clean baseline.
3. **Phase 2.2 (Async API)** & **Phase 2.1 (Exceptions)**: Harden the `src/` boundary so it is robust enough to handle the headless loop traffic.
4. **Phase 3 (Major Architecture)**: Now that `src/` is tested and async-safe, kill the "Split Brain" by migrating `assistant_loop.py` to use `src/` and deleting the root files.
5. **Phase 4.1 (Resource Lifecycle)**: Final hardening of hardware handles for the production Pi deployment.
