# Comprehensive Engineering Audit: Campus Helpdesk Robot

## 1. Dead Code (Files, Classes, Methods)

**Issue**: The repository contains an entire parallel implementation of audio, vision, and state logic located in the root directory that is effectively decoupled from the modern `src/` layered architecture.
- **Evidence**: `ttt_service.py`, `presence_service.py`, `tts_service.py`, `stt_service.py`, `assistant_loop.py`.
- **Why it is a problem**: Modifying the application logic in `src/` does not reflect in the headless Pi loops. Maintenance overhead is doubled.
- **Risk Level**: Critical
- **Recommended Fix**: Refactor `assistant_loop.py` to use `src.campus_helpdesk.infrastructure` implementations. Delete all legacy files in the root.
- **Estimated Effort**: 2-3 Days

## 2. Duplicate Implementations

**Issue**: Speech synthesis and Voice Transcription logic is implemented twice.
- **Evidence**:
  - STT: `src/campus_helpdesk/infrastructure/audio/stt_service.py` vs. root `stt_service.py`.
  - TTS: `src/campus_helpdesk/infrastructure/audio/tts_service.py` vs. root `tts_service.py`.
  - Vision: `PersonDetector` (src) vs `PresenceService` (root).
- **Why it is a problem**: Both implementations use different underlying libraries (e.g. `PersonDetector` uses HOG/Haar while `PresenceService` only uses Haar). Bug fixes in one are not ported to the other.
- **Risk Level**: High
- **Recommended Fix**: Consolidate around the `src/` implementations which support dependency injection and abstract protocols.
- **Estimated Effort**: 1-2 Days

## 3. Dependency Injection & Clean Architecture Violations

**Issue**: Hidden Service Locators and Inline Imports
- **Evidence**:
  - `assistant_loop.py`: Hardcoded `from ollama import Client` and manual `from campus_helpdesk.config.settings import get_settings` deep inside `_warmup_ollama`.
  - `ttt_service.py`: Instantiates `RAGChatService` internally inside `_init_rag()`, completely bypassing the Application Layer boundary.
- **Why it is a problem**: Violates the Dependency Inversion principle. Components cannot be mocked for unit testing, and initialization state is tightly coupled to the environment.
- **Risk Level**: High
- **Recommended Fix**: Pass fully constructed `ChatService` and `STTService` instances to the loops via constructors (`__init__`).
- **Estimated Effort**: 1 Day

## 4. SOLID Principle Violations

**Issue**: `TTTService` violates the Single Responsibility Principle and Open/Closed Principle.
- **Evidence**: `ttt_service.py` contains hardcoded regex patterns for Hindi/Kannada FAQs (`_handle_indic_canned`).
- **Why it is a problem**: Adding a new department or FAQ requires modifying source code rather than updating a knowledge base.
- **Risk Level**: Medium
- **Recommended Fix**: Extract canned intents into a configuration file (JSON/YAML) or rely completely on the multilingual LLM (`qwen2.5`) with localized system prompts.
- **Estimated Effort**: 1-2 Days

## 5. Performance Bottlenecks & Threading Issues

**Issue**: Blocking operations on the Main Thread / Web Server
- **Evidence**: `main.py` -> `chat()` endpoint is a synchronous `def` (not `async def`). It calls `self._llm_service.generate(prompt)`.
- **Why it is a problem**: A single request to Ollama (which takes ~3-5 seconds on CPU) will block the entire Uvicorn ASGI worker, resulting in connection timeouts for other concurrent users.
- **Risk Level**: Critical
- **Recommended Fix**: Change `def chat` to `async def chat`, and use `run_in_threadpool` or an async Ollama client wrapper.
- **Estimated Effort**: 1 Day

## 6. Memory Usage Hotspots

**Issue**: Memory leaks in PyAudio/OpenCV Headless Loop
- **Evidence**: `presentation/chat_window.py` continuously runs OpenCV `detect_in_frame` inside a Tkinter `after()` loop without yielding properly, and manual instantiation of `PyAudio()` streams inside `listen_and_transcribe_stream` are missing strict `try/finally` resource cleanup.
- **Why it is a problem**: Headless operations running 24/7 on a Raspberry Pi 8GB will eventually exhaust RAM or crash the camera pipeline (`v4l2` buffers).
- **Risk Level**: High
- **Recommended Fix**: Adopt context managers (`with`) for all hardware streams. Limit the OpenCV evaluation rate (FPS capping).
- **Estimated Effort**: 1 Day

## 7. Error Handling

**Issue**: Bare Exception Catching
- **Evidence**: `except Exception as e:` appears over 40 times in the codebase (e.g., `main.py` line 40, `tts_service.py` line 64, `stt_service.py` line 140).
- **Why it is a problem**: Swallows `KeyboardInterrupt`, `SystemExit`, and hides critical initialization errors, making debugging impossible.
- **Risk Level**: Medium
- **Recommended Fix**: Replace with specific exceptions (`OSError`, `httpx.RequestError`), or properly log with `exc_info=True`.
- **Estimated Effort**: 1 Day

## 8. Configuration Problems

**Issue**: Secret/Configuration leakage
- **Evidence**: `settings.py` loads `ollama_base_url` but `demo.py` re-invents loading with `os.getenv("OLLAMA_HOST")`.
- **Why it is a problem**: Configuration is not centralized, leading to divergent behavior between the API and GUI.
- **Risk Level**: Low
- **Recommended Fix**: Enforce strict usage of the `get_settings()` Pydantic class across the entire codebase.
- **Estimated Effort**: 0.5 Days

## 9. Testing Coverage

**Issue**: Abysmally low test coverage.
- **Evidence**: Only one test file exists (`test_person_detector.py` with 3.3KB size) for a project with complex integrations.
- **Why it is a problem**: Refactoring the duplicated code will be highly risky without regression tests.
- **Risk Level**: High
- **Recommended Fix**: Write unit tests mocking the FAISS, Ollama, and Whisper boundaries before starting the major refactor.
- **Estimated Effort**: 3 Days

## 10. Unused Dependencies

**Issue**: Bloated environment.
- **Evidence**: `beautifulsoup4`, `hf-xet`, `chromadb`, and `pocketsphinx` are in `pyproject.toml` but are never imported or used.
- **Why it is a problem**: Increases Docker image size and Raspberry Pi provisioning time.
- **Risk Level**: Low
- **Recommended Fix**: Remove from `pyproject.toml`.
- **Estimated Effort**: 1 Hour
