# Comprehensive RAG Benchmarking Pipeline Debug & Verification Report

**Timestamp**: `2026-07-29T11:34:00Z`  
**Evaluation Scope**: Verification of standard retrieval benchmarking engine against active system RAG retriever.

---

## 1. System Architecture

The Offline AI Campus Helpdesk Robot RAG system consists of the following decoupled pipeline architecture:

```
Scraped College Data & PDFs
         │
         ▼
Canonical Markdown Documents (data/canonical_markdown/ - 432 .md files)
         │
         ▼
Semantic Document Chunker (800 char chunk size, 120 overlap)
         │
         ▼
Sentence Transformers (sentence-transformers/all-MiniLM-L6-v2)
         │
         ▼
FAISS Similarity Store + BM25 Search Store (data/faiss/ - 11,440 chunks)
         │
         ▼
Hybrid Retriever (Reciprocal Rank Fusion RRF) + Cross-Encoder Reranker (ms-marco-MiniLM-L-6-v2)
         │
         ▼
Retrieval Benchmark Suite (evaluation/benchmarks/benchmark.py)
```

---

## 2. Retriever Verification

- **Retrieval Engine**: `HybridRetriever` combining FAISS vector search + BM25 keyword store + `CrossEncoderReranker`.
- **Embedding Model**: `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions, normalized).
- **Reranker Model**: `cross-encoder/ms-marco-MiniLM-L-6-v2`.
- **Top-K Cut-off**: Top-5 final search results evaluated per question.
- **Verification Result**: The benchmark connects directly to `RAGPipeline.search()` via `create_rag_pipeline(settings)`.

---

## 3. Vector Database Verification

- **Storage Location**: `data/faiss/`
- **Manifest File**: `data/faiss/index-manifest.json`
- **FAISS Index File**: `data/faiss/index.faiss` (17.57 MB)
- **Docstore Pickle File**: `data/faiss/index.pkl` (8.12 MB)
- **Total Indexed Documents**: 432 canonical Markdown files.
- **Total Vector Chunks**: 11,440 text chunks.
- **Vector Dimension**: 384 dimensions.

---

## 4. Metadata Verification

Inspection of chunk metadata inside `data/faiss/index.pkl`:
- `source_filename`: `19krf_about_kle_technological_universityhubba_1bddac.md`
- `source`: `about/19krf_about_kle_technological_universityhubba_1bddac.md`
- `title`: `PDF Document: 19krf-About-KLE-Technological-UniversityHubballi`
- `sha256`: Hash of source content.

Metadata accurately maps retrieved chunks back to their canonical Markdown source file.

---

## 5. Dataset Verification

- **Dataset Location**: `evaluation/datasets/*.json` (9 category files)
- **Total Query Records**: 1,014 QA records.
- **Filename Match Verification**: Every `expected_document` entry in the dataset corresponds to a valid Markdown file in `data/canonical_markdown/`.

---

## 6. Filename Normalization Verification

Document match comparison uses `_normalize_doc_name` and `_is_doc_match`:
- Extracts basename (`Path(doc_name).name.lower().strip()`).
- Normalizes path separators (handles both `\`, `/`, and relative paths).
- Preserves unique 6-character hex hash suffixes.

Example:
`203imguf_call_for_admission_mse_2024_25_15878c.md` matches `D:\AUNTII\data\canonical_markdown\203imguf_call_for_admission_mse_2024_25_15878c.md`.

---

## 7. Single-Query Debug Trace

**Query**: `Which documents should I bring for admission?`  
**Expected Document**: `admission_for_ug_program_252fd1.md`  
**Top 5 Retrieved Documents**:
1. `international_admission_f40bc8.md` (Score: -2.4114)
2. `under_graduate_program_252fd1.md` (Score: -1.3599)
3. `under_graduate_program_252fd1.md` (Score: -1.0092)
4. `admission_for_pg_program_2ba0e8.md` (Score: -0.9967)
5. `intenational_admission_496103.md` (Score: -0.0738)

---

## 8. Failure Analysis & Root Cause

The initial 0% Recall@1, 0% Recall@5, and 100% Failure Rate were caused by 4 distinct bugs:

1. **Unbuilt / Incomplete Vector Store**: `data/faiss` only contained 9 chunks from a dummy `campus_guide.txt` file instead of the 432 canonical Markdown documents.
2. **`lru_cache` NameError**: `SentenceTransformerEmbeddings` used `@lru_cache` without importing `lru_cache` from `functools`, causing `create_rag_pipeline()` to crash and trigger silent fallback to a mock retriever returning `simulated_document_1.md`.
3. **`RetrievalError` Import Bug**: `FAISSSimilarityStore` raised `RetrievalError` without importing it, causing `load()` to fail with `NameError`.
4. **Retriever Adapter Method Mismatch**: Benchmark initially called `pipeline.similarity_store.search` instead of `pipeline.search()`, causing `AttributeError` when extracting metadata attributes.

---

## 9. Recommended Fixes Applied

- Fixed `lru_cache` and `RetrievalError` imports in `sentence_transformer_embeddings.py`, `faiss_store.py`, and `hybrid_retriever.py`.
- Populated `data/canonical_markdown` with all 432 Markdown files and rebuilt the FAISS index (11,440 chunks).
- Updated `retrieval_benchmark.py` to use `pipeline.search()` and extract `source_filename` metadata.
