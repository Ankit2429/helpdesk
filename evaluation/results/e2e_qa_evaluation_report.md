# Sparky E2E QA Evaluation & Benchmark Report

## 1. Global Performance Metrics

- **Accuracy**: 95.00% (190 / 200 Correct)
- **Precision**: 93.83%
- **Recall**: 100.00%
- **Failure Rate**: 5.00% (10 failures)
- **Hallucination Rate**: 4.00% (8 hallucinations)
- **Average E2E Latency**: 4821.58 ms

---

## 2. Most Common Failure Reasons

1. **LLM hallucination**: 8 occurrences (4.0% of total queries)
2. **Intent routing**: 2 occurrences (1.0% of total queries)

---

## 3. Top 20 Recommended Improvements Ranked by Impact

1. **Embedding Model Upgrade (High Impact)**: Upgrade from sentence-transformers/all-MiniLM-L6-v2 to BAAI/bge-large-en-v1.5 or all-mpnet-base-v2 to significantly boost dense semantic mapping accuracy.
2. **Additional Intent Router Regex Calibrations**: Include common Kannada/Hindi variations for small talk and capabilities queries.
3. **Advanced Query Expansion for Synonyms**: Map "seats", "capacity", and "size" terms directly to facilities metrics in QueryRewriter.
4. **Enhanced Markdown Chunker Headings Parsing**: Retain upper hierarchical headings context in nested tables/lists.
5. **Context Composer Deduplication Optimization**: Prevent redundant context chips from taking up LLM context space.
6. **Cross-Encoder Reranker Score Sigmoid Scaling**: Calibrate reranker signals for non-English script queries.
7. **Bilingual Hindi-English Keyword Translation**: Translate queries containing Devnagari script to English search keywords before RAG lookup.
8. **Bilingual Kannada-English Keyword Translation**: Translate Kannada search keywords to match English documents in BM25.
9. **Citation Verification Extraction Enhancements**: Prevent citation validator from stripping valid answer sentences.
10. **Session Memory Compression**: Condense multi-turn chat history into short bullet points to conserve context window space.
11. **Direct Map Coordinate Retrieval**: Inject lat/long or office floor coordinates when matching location-specific queries.
12. **Circular Date Normalization**: Standardize date expressions (e.g. April 2025, Odd Semester 2023) in Scraper parser.
13. **VAD Audio Sensitivity Parameter Calibration**: Expose noise floor calibration sliders on touchscreen UI status footer.
14. **Custom Speech Recognition Vocab Loader**: Load campus-specific acronyms (KLE, BVB, HOD, CARR) directly into faster-whisper vocabulary.
15. **Adaptive RAG Search Top-K Increment**: Dynamically increase retrieved chunks count when query length is short.
16. **Permanent UI Status Panel Diagnostics Toggle**: Allow administrators to view latency and active RAG index state via touch overlay.
17. **CIE Exam Evaluation Formula ground rules**: Pin exam assessment rules at the top of LLM system prompts.
18. **PDF Mandatory Disclosure Table parser**: Improve table schema parsing in Canonical Markdown Ingest pipeline.
19. **Mascot Eye Animation State machine sync**: Align visual eye blinking rates to STT silence detection intervals.
20. **Snapshot Gallery Local Storage Auto-rotation**: Limit stored local snaps to 100 files to avoid disk exhaustion.
