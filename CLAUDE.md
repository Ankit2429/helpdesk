# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Offline-first RAG chatbot ("campus helpdesk") for a college. Local Ollama LLM + FAISS/hybrid (BM25) vector retrieval, plus an optional Raspberry Pi robot stack (STT/TTS/vision). The HTTP API is the primary production surface; the robot stack (`interaction/`, `runtime/`, `services/`, `presentation/`) is a separate concern deployed on a Pi.

There are **two parallel code stacks** that do not import each other:

- **`src/campus_helpdesk/`** — the layered, production FastAPI/RAG stack (this is the one to work on).
- **`bvbcet_rag_pipeline/`**, **`archive/bvbcet_scraper/`**, and the **root-level scripts** (`assistant_loop.py`, `stt_service.py`, `ttt_service.py`, `presence_service.py`, `benchmark.py`) — legacy/dead code. Not imported by `src/`. Do not extend; prefer migrating anything still needed into `src/`.

## Commands

Python runs from the local venv. On Windows: `.venv/Scripts/python.exe` (UV-managed, Python 3.11).

- Run the API server (requires Ollama running at `OLLAMA_BASE_URL`):
  ```bash
  .venv/Scripts/python.exe -m uvicorn campus_helpdesk.main:app --app-dir src --reload
  ```
- Run all tests:
  ```bash
  .venv/Scripts/python.exe -m pytest
  ```
- Run one test file / one test:
  ```bash
  .venv/Scripts/python.exe -m pytest tests/api/test_chat_route.py
  .venv/Scripts/python.exe -m pytest tests/unit/test_confidence_engine.py::test_confidence_engine_high_confidence
  ```
  `pyproject.toml` sets `testpaths = ["tests", "bvbcet_rag_pipeline/tests"]` and adds `src`, `bvbcet_rag_pipeline`, `bvbcet_scraper` to `pythonpath`.
- Lint:
  ```bash
  .venv/Scripts/python.exe -m ruff check src
  ```
- Full verification gate (pytest + ruff + smoke + coverage, writes report to `data/analytics/reports/`):
  ```bash
  .venv/Scripts/python.exe scripts/verify_project.py
  ```
- Build the FAISS/BM25 index from canonical Markdown:
  ```bash
  .venv/Scripts/python.exe -m campus_helpdesk.ingest
  ```
  Console entry point `campus-helpdesk-ingest` also exists.

## Configuration

Settings live in `src/campus_helpdesk/config/settings.py` (Pydantic `Settings`). Sources, in load order — **later sources override earlier**:

1. `config.yaml` at repo root (nested `app:`/`retrieval:`/`ollama:`/`embedding:` sections) — flattens into settings.
2. Environment variables (`.env` file), e.g. `OLLAMA_MODEL`, `RAG_SEARCH_LIMIT`.

Important quirk: `config.yaml` is applied via a `model_validator(mode="before")` that **overwrites** the same-named env keys, so `config.yaml` wins over `.env` for overlapping settings (e.g. `retrieval.top_k` → `rag_search_limit`, `ollama.model` → `ollama_model`). Keep both files in sync or you will chase phantom config drift. Unknown keys are ignored (`extra="ignore"`).

Notable settings: `FAISS_ALLOW_DANGEROUS_DESERIALIZATION` gates index loading (off by default in `.env.example` — the pipeline runs degraded without a loaded index), `EMBEDDING_LOCAL_FILES_ONLY=true` keeps embedding model offline.

## Architecture

### Layered core (`src/campus_helpdesk/`)

- `main.py` — FastAPI app factory; wires settings → `OllamaLLMService` → `create_rag_pipeline` → `RAGChatService`; global `app = create_app()` at import.
- `api/` — routes (`routes/chat.py`, `routes/system.py`), schemas, DI (`dependencies.py`). `system.py` embeds the entire web chat UI as a large HTML string.
- `application/` — use cases and orchestration. `rag_chat_service.py` (the `/chat` flow), `session_manager.py` (thread-safe TTL sessions), `rag_pipeline.py`, `query_rewriter.py`.
- `domain/` — entities: `KnowledgeDocument`, `SearchResult`, `ChatMessage`, `ConversationMemory` (frozen dataclasses).
- `infrastructure/` — adapters:
  - `rag/` — `factory.py` (wiring), `hybrid_retriever.py` (BM25 + FAISS RRF fusion), `faiss_store.py` (persist/load, manifest validation), `cross_encoder_reranker.py`, `confidence_engine.py`, `prompt_context_builder.py`, `semantic_chunker.py` / `markdown_chunker.py`, `sentence_transformer_embeddings.py` (lazy model + manual cache).
  - `llm/ollama_service.py` — Ollama client wrapper with retry.
  - `knowledge/`, `loaders/`, `audio/`, `vision/`, `evaluation/`.
- `services/` — STT/TTS/VAD/camera/vision, `prompt_sanitizer.py` (input injection blacklist), `answerability_engine.py`, `citation_validator.py`, `language_detector.py`.
- `analytics/` — observability subsystem (event bus, metrics store, dashboards, alerts). **Dormant**: nothing in `application/` or `api/` publishes to it.
- `interaction/` + `runtime/` + `presentation/` — the robot stack (event bus/FSM, `system_runtime.py` orchestration, PySide6 UI). Not wired into the API.

### The `/chat` request flow

1. `POST /chat` → `RAGChatService.respond(message, session_id)`.
2. Language detection (`services/language_detector.py`) → optional translation prompt if not English.
3. Query rewrite via `QueryRewriter` (expects `Sequence[ChatMessage]` history — do not pass a string).
4. `RAGPipeline.search` → `HybridRetriever` (BM25 + FAISS → RRF) → `CrossEncoderReranker` → doc-dedup → top-k `SearchResult`s.
5. `ConfidenceEngine.evaluate` scores them; `PromptContextBuilder` formats context (max 3000 chars, distance-threshold filtered).
6. System prompt + history + context + user question → `OllamaLLMService.generate` (single `user`-role message; no separate system role).
7. `CitationValidator` strips fabricated `[n]` citations and URLs post-generation; replies stored into the session's `ConversationMemory`.

### Tests

`tests/` mirrors the layered layout (`api/`, `application/`, `unit/`, `integration/`, `services/`, `interaction/`). Integration tests exercise real threading/state machines with mock backends; `tests/integration/test_rag_consistency.py` defines only `verify_*` helpers under `__main__` and is not collected by pytest. Some tests encode current (quirky) behavior, e.g. `test_sprint1_core.py` asserts `rag_search_limit == 50` from `config.yaml`. `bvbcet_rag_pipeline/tests/` tests legacy modules.

## Known production risks (do not silently reintroduce)

- `rag_chat_service.py` builds the final prompt with the **raw** user message (line ~163) while only the search query is sanitized — prompt-injection surface; sanitizer is a regex blacklist.
- `OllamaLLMService.generate_stream` retry wrapper never executes the generator body, so streaming has no retry.
- `vad_service.py` uses `logger` without defining it (`logger = logging.getLogger(__name__)` missing) — the VAD worker crashes on voice start.
- `main.py` sets CORS `allow_origins=["*"]` with `allow_credentials=True`; the API has no auth or rate limiting; the web UI renders replies via `innerHTML` (XSS).
- Robot stack mocks: `system_runtime.py` hardcodes mic `device_index=99` (always mock), `tts_service.py` Piper backend is a stub, `camera_service.py` Windows detection uses `time.asctime().startswith("Win")` (always false).
- The repo tracks large build artifacts (`chunks.jsonl` ~19MB, `embedding_metadata.jsonl` ~47MB, `archive/` binaries) — `.git` is ~900MB.
