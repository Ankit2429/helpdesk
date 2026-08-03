# Implementation Plan: Generation Router & Context Composer

This document outlines the detailed technical design and implementation plan for adding the **Generation Router** (dynamic cloud/local LLM switching based on connectivity and latency) and the **Context Composer** (semantic deduplication, ranking fusion, and passage merging for RAG chunks).

> [!IMPORTANT]
> **Planning-Only Step:** No source code changes will be made until this plan is reviewed and approved.

---

## 1. Exact Call Sites That Will Be Touched

The table below lists every file in the codebase that constructs or invokes `RAGChatService`, whether it will be modified, and how its behavior changes.

| File Location | Role / Context | Proposed Change | Behavior Change? |
|---|---|---|---|
| [`src/campus_helpdesk/main.py`](file:///d:/helpdesk/anti/src/campus_helpdesk/main.py#L60-L75) | FastAPI backend application entry point | Update dependency wiring to instantiate `GenerationRouter` (wrapping `CloudLLMService` and local offline `OllamaLLMService`) and pass it as `llm_service` to `RAGChatService`. Optionally pass `ContextComposer` to `RAGChatService`. | **No user-facing breaking change.** Clean fallback to local offline model if cloud credentials/endpoint are unset or offline. |
| [`src/campus_helpdesk/demo.py`](file:///d:/helpdesk/anti/src/campus_helpdesk/demo.py#L140-L150) | Interactive voice/text web demo | Update initialization to use `GenerationRouter` + `RAGChatService`. | **No user-facing breaking change.** Enhances response latency when cloud is connected. |
| [`scripts/chat_cli.py`](file:///d:/helpdesk/anti/scripts/chat_cli.py#L40-L55) | Terminal CLI interface | Update service construction to use router setup. | **No breaking change.** |
| [`ttt_service.py`](file:///d:/helpdesk/anti/ttt_service.py#L95-L110) | Text-to-Text standalone service wrapper | Update `RAGChatService` instantiation to pass router-backed LLM service. | **No breaking change.** |
| [`src/campus_helpdesk/services/inference_adapter.py`](file:///d:/helpdesk/anti/src/campus_helpdesk/services/inference_adapter.py#L85-L100) | Bridge adapter for inference tasks | Accepts injected `RAGChatService` instance. | **No breaking change.** |
| [`tests/application/test_rag_chat_service.py`](file:///d:/helpdesk/anti/tests/application/test_rag_chat_service.py#L30-L40) | Unit tests for `RAGChatService` | No change required for existing mock tests. Add new test cases for `ContextComposer` integration. | **No breaking change.** |

### Explicit Confirmation regarding `factory.py`
- **[`src/campus_helpdesk/infrastructure/rag/factory.py`](file:///d:/helpdesk/anti/src/campus_helpdesk/infrastructure/rag/factory.py)**: **Confirmed explicitly:** `factory.py` does **NOT** construct or call `RAGChatService` anywhere. It contains only `create_rag_pipeline()`, which constructs the `RAGPipeline` (embeddings, FAISS store, HybridRetriever, and CrossEncoderReranker). It will remain completely untouched by the router/composer wiring.

---

## 2. Interface Compatibility

### Current `RAGChatService` Constructor & `LLMService` Protocol

`LLMService` is defined in [`src/campus_helpdesk/application/llm_service.py`](file:///d:/helpdesk/anti/src/campus_helpdesk/application/llm_service.py) as a Python `Protocol`:

```python
class LLMService(Protocol):
    def generate(self, prompt: str) -> str:
        ...
```

`RAGChatService` constructor signature in [`src/campus_helpdesk/application/rag_chat_service.py`](file:///d:/helpdesk/anti/src/campus_helpdesk/application/rag_chat_service.py#L36-L56):

```python
class RAGChatService(ChatService):
    def __init__(
        self,
        llm_service: LLMService,
        rag_pipeline: RAGPipeline | None = None,
        query_rewriter: QueryRewriter | None = None,
        context_builder: PromptContextBuilder | None = None,
        session_manager: SessionManager | None = None,
        confidence_engine: ConfidenceEngine | None = None,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        answerability_engine: AnswerabilityEngine | None = None,
        context_composer: ContextComposer | None = None,  # Optional new dependency
    ) -> None:
```

### Confirmation of Drop-In Compatibility
- `GenerationRouter` implements the `LLMService` protocol (`def generate(self, prompt: str) -> str:`).
- Therefore, **`GenerationRouter` is 100% drop-in compatible** with `RAGChatService` without changing `RAGChatService`'s primary `llm_service` parameter or `respond()` signature.
- `RAGChatService` will be updated only to accept an optional `context_composer: ContextComposer | None = None` parameter in `__init__`. In `respond()`, right before calling `_context_builder.build_context()`, `_context_composer.compose()` will deduplicate and merge `search_results` if a composer is provided.

---

## 3. New Files and Their Responsibilities

1. **`src/campus_helpdesk/infrastructure/llm/connectivity_checker.py`**
   - **Single Responsibility:** Lightweight, cached internet/cloud endpoint health checking (pinging configured cloud URL or fast DNS check with configurable timeout and TTL caching).
   - **Dependencies:** Standard library `urllib` / `socket` or `httpx`.
   - **Called By:** `GenerationRouter`.

2. **`src/campus_helpdesk/infrastructure/llm/cloud_llm_service.py`**
   - **Single Responsibility:** Implements `LLMService` protocol for cloud-hosted LLM endpoints with automatic retry and short timeouts.
   - **Dependencies:** `httpx` or standard `requests`, `src/campus_helpdesk/application/llm_service.py`.
   - **Called By:** `GenerationRouter`.

3. **`src/campus_helpdesk/infrastructure/llm/generation_router.py`**
   - **Single Responsibility:** Dynamic selection between `CloudLLMService` and local offline `OllamaLLMService` (running `OFFLINE_LLM_MODEL`) based on connectivity check and fallback rules.
   - **Dependencies:** `ConnectivityChecker`, `CloudLLMService`, `OllamaLLMService`, `LLMService` protocol.
   - **Called By:** `RAGChatService` (injected as `llm_service`).

4. **`src/campus_helpdesk/infrastructure/rag/context_composer.py`**
   - **Single Responsibility:** Consolidates, deduplicates (via exact content hashing & semantic overlap), and merges contiguous RAG search results before context building.
   - **Dependencies:** `src/campus_helpdesk/domain/models.py` (`SearchResult`, `Document`).
   - **Called By:** `RAGChatService` (in `respond()`).

---

## 4. Hardware Constraints & Offline Model Selection (8GB Raspberry Pi 5 Target)

To run fully offline on edge target hardware (e.g. an **8GB Raspberry Pi 5**), the local offline branch cannot use heavy models like `7b` alongside other system components.

### Shared Memory Allocation Budget (8GB RAM Target)
- **Whisper STT (base/small int8):** ~1.2 GB RAM
- **Piper TTS (ONNX / C++ runtime):** ~300 MB RAM
- **FAISS Vector Store + SentenceTransformer Embeddings:** ~800 MB RAM
- **CrossEncoder Reranker (`ms-marco-MiniLM-L-6-v2`):** ~400 MB RAM
- **OS + Python Runtime + System Buffer:** ~1.5 GB RAM
- **Available VRAM/RAM for Offline LLM:** **~3.8 GB RAM**

### Offline LLM Model Configuration
- When running in offline/local fallback mode, `GenerationRouter` delegates to an `OllamaLLMService` instance configured with a lightweight quantized model: **`qwen2.5:1.5b`** (~986 MB RAM) or **`qwen2.5:3b`** (~1.9 GB RAM).
- A new explicit setting `OFFLINE_LLM_MODEL` is introduced so the local offline model can be tuned independently of cloud settings.

---

## 5. Data Flow Diagram

```text
                                USER QUERY
                                    │
                                    ▼
                         [ LanguageDetector ]
                                    │
                                    ▼
                       [ QueryRewriter (BM25/HyDE) ]
                                    │
                                    ▼
                          [ HybridRetriever ]
                 (BM25 Sparse + FAISS Dense Search)
                                    │
                                    ▼
                       [ CrossEncoderReranker ]
                 (Top-N Scoring & Re-ordering)
                                    │
                                    ▼
                          [ ConfidenceEngine ]
                     (Calculates Confidence Score)
                                    │
                                    ▼
                       [ CONTEXT COMPOSER ]  <--- NEW COMPONENT
              (Deduplicates & Merges Overlapping Chunks)
                                    │
                                    ▼
                       [ PromptContextBuilder ]
               (Formats Citations & Context Window String)
                                    │
                                    ▼
                        [ GENERATION ROUTER ] <--- NEW COMPONENT
                                    │
           ┌────────────────────────┴────────────────────────┐
           ▼                                                 ▼
[ ConnectivityChecker ]                             [ ConnectivityChecker ]
    (Cloud Online)                                      (Cloud Offline/Fail)
           │                                                 │
           ▼                                                 ▼
[ CloudLLMService ]                                [ OllamaLLMService ]
  (Fast Cloud LLM)                                (Local Offline LLM:
CLOUD_LLM_MODEL="nemotron-3-super:cloud"           OFFLINE_LLM_MODEL="qwen2.5:1.5b")
           │                                                 │
           └────────────────────────┬────────────────────────┘
                                    │
                                    ▼
                              FINAL ANSWER
```

---

## 6. Risks and Specific Verification

The table below lists each of the 4 new/modified components, its specific failure mode, potential impact, and the exact test function that will catch that specific failure.

| Component | Concrete Risk / Failure Mode | Potential Impact | Exact Verification Test |
|---|---|---|---|
| **`connectivity_checker.py`** | **Socket / Network Flooding:** Health check runs a fresh socket query on every prompt turn without TTL caching. | High CPU/network overhead per query turn. | `tests/infrastructure/llm/test_connectivity_checker.py::test_health_check_ttl_caching` invokes `check_connection()` 10 times in rapid succession and asserts that only 1 underlying network socket request is executed within the 15-second TTL window. |
| **`cloud_llm_service.py`** | **Missing API Credentials Crash:** If `CLOUD_LLM_API_KEY` or URL are missing or malformed, invoking `generate()` crashes the app with an unhandled exception. | System outage when cloud is enabled without keys. | `tests/infrastructure/llm/test_cloud_llm_service.py::test_missing_credentials_graceful_fallback` initializes `CloudLLMService` with empty credentials, calls `generate()`, and asserts that a `CloudServiceError` is caught gracefully and falls back to local execution without crashing. |
| **`generation_router.py`** | **Cloud Endpoint Hang / SLA Breach:** When cloud API stalls, the router blocks waiting for cloud completion instead of switching to local execution. | Target goal: verify local fallback executes under SLA threshold (e.g. 500ms). | `tests/infrastructure/llm/test_generation_router.py::test_cloud_timeout_falls_back_to_local` mocks a hanging cloud HTTP call that exceeds `CLOUD_CONNECTIVITY_TIMEOUT_MS` and asserts that `GenerationRouter` immediately delegates generation to the local `OllamaLLMService`. |
| **`context_composer.py`** | **Over-aggressive Deduplication:** `ContextComposer`'s dedup logic collapses two genuinely different source chunks that happen to share similar introductory phrasing, losing real factual information. | Missing information in context $\rightarrow$ false "I don't have that information" replies. | `tests/infrastructure/rag/test_context_composer.py::test_distinct_sources_not_merged` uses two synthetic chunks with similar introductory boilerplate (`"KLE Technological University, Hubballi..."`) but different facts (one stating tuition fees, one stating hostel rules), passes them to `compose()`, and asserts that both distinct chunks survive deduplication. |

---

## 7. Settings and Configuration Changes

The following settings will be added to [`src/campus_helpdesk/config/settings.py`](file:///d:/helpdesk/anti/src/campus_helpdesk/config/settings.py) and `.env.example`.

```ini
# --- Cloud LLM & Generation Router Settings ---
ENABLE_CLOUD_LLM_ROUTER=false            # Default: false (Backward compatible: uses direct local Ollama)
CLOUD_LLM_API_KEY=""                    # API key for cloud LLM provider
CLOUD_LLM_BASE_URL=""                   # Cloud endpoint URL (e.g. https://api.together.xyz/v1 or Nemotron cloud)
CLOUD_LLM_MODEL="nemotron-3-super:cloud"# Model identifier for cloud LLM
CLOUD_CONNECTIVITY_TIMEOUT_MS=500        # Target threshold for connectivity health check (ms)
CLOUD_CONNECTIVITY_TTL_SECONDS=15        # Health check cache TTL (seconds)

# --- Offline / Edge LLM Settings (8GB Pi 5 Target) ---
OFFLINE_LLM_MODEL="qwen2.5:1.5b"        # Local offline LLM model sized for edge hardware (1.5b or 3b)

# --- Context Composer Settings ---
ENABLE_CONTEXT_COMPOSER=true            # Enable smart chunk deduplication & merging
CONTEXT_COMPOSER_DEDUP_THRESHOLD=0.85   # Similarity threshold for deduplication
```

### Backward Compatibility Guarantee
- When `ENABLE_CLOUD_LLM_ROUTER=false` (the default), `GenerationRouter` is bypassed or defaults strictly to local `OllamaLLMService` using `OFFLINE_LLM_MODEL`.
- The system will behave **identically** to the current working local setup when no cloud settings are provided in `.env`.

---

## 8. Rollback Plan

If any issue arises during or after deployment:

1. **Immediate Zero-Downtime Rollback (Feature Flags):**
   - Set `ENABLE_CLOUD_LLM_ROUTER=false` in `.env`.
   - Set `ENABLE_CONTEXT_COMPOSER=false` in `.env`.
   - The system instantly reverts to using local `OllamaLLMService` and direct `PromptContextBuilder` without restarting code dependencies or rebuilding indexes.

2. **Code-Level Revert:**
   - Because `GenerationRouter` implements `LLMService` protocol and `ContextComposer` is passed as an optional dependency (`context_composer: ContextComposer | None = None`), removing them requires zero changes to `RAGChatService`'s public API contract.

---

## Verification Plan

### Automated Tests
- `uv run pytest tests/infrastructure/llm/`
- `uv run pytest tests/infrastructure/rag/`
- `uv run pytest tests/application/`

### Manual Verification
- Execute `uv run python scripts/chat_cli.py "hi" "Who is the Vice Chancellor?" "Where is the School of Mechanical Engineering located?"`
- Verify local and cloud routing behavior under simulated network offline/online conditions.
