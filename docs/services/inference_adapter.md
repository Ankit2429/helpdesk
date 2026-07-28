# Inference Adapter Documentation

This document describes the design, backend abstraction, queue model, thread boundaries, timeout recovery, and configuration settings for the `InferenceAdapter`.

---

## 1. Architectural Role

The Inference Adapter bridges the real-time Event Bus of the Interaction Engine with the existing offline RAG (Retrieval-Augmented Generation) query pipeline:
* **Orchestration Layer**: It contains no vector database index operations, dense embeddings, or LLM generation logic. It only handles routing and lifecycle events.
* **Flow**: It consumes `TRANSCRIPT_FINAL` events, triggers a `QUERY_STARTED` notification, submits the standalone query to the preloaded RAG pipeline, and outputs an `ANSWER_READY` event containing the text, cited sources, confidence, and latency.

---

## 2. Decoupled Backend Abstraction

The adapter is decoupled from specific LLM or RAG frameworks via the `BaseInferenceBackend` interface:
* **`LocalRAGBackend`**: Wraps the existing `RAGChatService` to query Ollama and local similarity stores (FAISS/BM25) with conversational turn history.
* **`MockInferenceBackend`**: Simulates preconfigured replies, citation lists, confidence levels, and artificial query execution latency for CI/CD environments.

---

## 3. FIFO Worker Thread & Concurrency

* **Worker Loop**: A background thread (`InferenceAdapter-worker`) pulls transcript events sequentially from a FIFO queue.
* **Non-Blocking**: Because local LLM generation and retrieval can block for seconds, enqueuing requests in a FIFO worker thread prevents blocking the central Event Bus thread pool.
* **Sequential Ingestion**: Prevents running multiple heavy GPU/CPU generation requests concurrently, which would exhaust memory and cause model execution thrashing.

---

## 4. Timeout Recovery & Robustness

Local LLM systems can stall due to high system load or driver hangs. The adapter wraps query execution in a separate thread watch joined with a configurable timeout:
* **Timeout threshold (`timeout_seconds`)**: Defaults to `10.0` seconds.
* **Error handling**: If the query exceeds the timeout limit or throws a database exception, the thread monitor aborts the execution path, increments diagnostics error/timeout metrics, and publishes a non-fatal `ERROR` event (of type `InferenceTimeoutError` or `InferenceBackendError`). The adapter worker thread never crashes and remains active for subsequent queries.
