#!/usr/bin/env python
"""
debug_rag.py — Interactive & Command-line RAG Debugging Utility for AUNTII

Traces every stage of the RAG pipeline:
  1. User Query
  2. Query Rewriting
  3. Embedding Generation (Dimension, Norm)
  4. FAISS Search Results
  5. BM25 Search Results
  6. Hybrid RRF Ranking
  7. Filtered Results (with explicit ACCEPT/REJECT reasons)
  8. Final Context Sent to Ollama
  9. Final System Prompt
 10. Ollama Raw Response
 11. Comprehensive Summary & Diagnosis
"""

import sys
import math
import numpy as np
from typing import List, Dict, Any, Tuple

sys.stdout.reconfigure(encoding="utf-8")

from campus_helpdesk.config.settings import get_settings
from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline
from campus_helpdesk.infrastructure.llm.factory import create_llm_service
from campus_helpdesk.application.query_rewriter import QueryRewriter
from campus_helpdesk.infrastructure.rag.prompt_context_builder import PromptContextBuilder
from campus_helpdesk.infrastructure.rag.confidence_engine import ConfidenceEngine
from campus_helpdesk.infrastructure.rag.context_composer import ContextComposer
from campus_helpdesk.application.rag_chat_service import DEFAULT_SYSTEM_PROMPT, FALLBACK_NO_INFO_REPLY
from campus_helpdesk.services.answerability_engine import AnswerabilityEngine


def debug_query(query: str, history_str: str = "") -> None:
    print("\n" + "=" * 80)
    print("USER QUERY")
    print("=" * 80)
    print(query)

    settings = get_settings()

    # 1. Query Rewriter
    rewriter = QueryRewriter()
    rewritten_query = rewriter.rewrite(query, history_str)
    print("\n" + "-" * 80)
    print("QUERY AFTER REWRITING")
    print("-" * 80)
    print(rewritten_query)

    # 2. Embedding Generation
    pipeline = create_rag_pipeline(settings)
    if settings.faiss_index_path.exists():
        pipeline.load_index()

    faiss_store = pipeline._similarity_store
    embeddings_model = getattr(faiss_store, "_embeddings", None)

    dim = 0
    norm = 0.0
    if embeddings_model is not None:
        try:
            query_vec = embeddings_model.embed_query(rewritten_query)
            vec_arr = np.array(query_vec, dtype=np.float32)
            dim = len(vec_arr)
            norm = float(np.linalg.norm(vec_arr))
        except Exception as e:
            dim = 384
            norm = 1.0

    print("\n" + "-" * 80)
    print("EMBEDDING GENERATED")
    print("-" * 80)
    print(f"Dimension: {dim}")
    print(f"Norm: {norm:.6f}")

    # 3. FAISS Results
    faiss_results = []
    if hasattr(faiss_store, "search"):
        try:
            faiss_results = faiss_store.search(rewritten_query, limit=10)
        except Exception as e:
            pass

    print("\n" + "-" * 80)
    print("FAISS RESULTS")
    print("-" * 80)
    if not faiss_results:
        print("No FAISS matches returned.")
    else:
        for idx, res in enumerate(faiss_results[:5], start=1):
            doc = res.document
            src = doc.metadata.get("source") or doc.metadata.get("source_filename", "unknown")
            chunk_id = doc.metadata.get("chunk_id", f"chunk_{idx}")
            snippet = doc.content[:120].replace("\n", " ")
            print(f"Rank {idx:2d} | Distance: {res.distance:8.4f} | Source: {src} | ID: {chunk_id}")
            print(f"        Preview: {snippet}...")

    # 4. BM25 Results
    bm25_store = getattr(pipeline, "_bm25_store", None) or getattr(getattr(pipeline, "_similarity_store", None), "bm25_store", None)
    bm25_results = []
    if bm25_store and hasattr(bm25_store, "search") and getattr(bm25_store, "_documents", []):
        try:
            bm25_results = bm25_store.search(rewritten_query, limit=10)
        except Exception:
            pass

    print("\n" + "-" * 80)
    print("BM25 RESULTS")
    print("-" * 80)
    if not bm25_results:
        print("No BM25 matches returned (or BM25 store unindexed).")
    else:
        for idx, res in enumerate(bm25_results[:5], start=1):
            doc = res.document
            src = doc.metadata.get("source") or doc.metadata.get("source_filename", "unknown")
            snippet = doc.content[:120].replace("\n", " ")
            score = -res.distance  # BM25 distance is stored as -score
            print(f"Rank {idx:2d} | Score: {score:8.4f} | Source: {src}")
            print(f"        Preview: {snippet}...")

    # 5. Hybrid Ranking (RRF / Reranker + Pipeline search)
    raw_search_results = pipeline.search(rewritten_query, limit=5)

    print("\n" + "-" * 80)
    print("HYBRID RANKING")
    print("-" * 80)
    for idx, res in enumerate(raw_search_results, start=1):
        doc = res.document
        src = doc.metadata.get("source") or doc.metadata.get("source_filename", "unknown")
        snippet = doc.content[:100].replace("\n", " ")
        print(f"Final Rank {idx:2d} | Combined Score (dist): {res.distance:8.4f} | Source: {src}")
        print(f"            Snippet: {snippet}...")

    # 6. Filtered Results (Context Composer + PromptContextBuilder filtering)
    composer = ContextComposer(settings=settings)
    composed_results = composer.compose(raw_search_results)

    context_builder = PromptContextBuilder(
        max_context_size=7000,
        similarity_threshold=settings.rag_distance_threshold,
    )
    confidence_engine = ConfidenceEngine(settings=settings)
    confidence_assessment = confidence_engine.evaluate(composed_results)
    context_str = context_builder.build_context(composed_results, confidence_assessment)

    print("\n" + "-" * 80)
    print("FILTERED RESULTS")
    print("-" * 80)
    
    seen_hashes = set()
    accepted_count = 0
    rejected_count = 0

    for idx, res in enumerate(raw_search_results, start=1):
        doc = res.document
        src = doc.metadata.get("source") or doc.metadata.get("source_filename", "unknown")
        dist = res.distance
        
        reasons = []
        if dist > settings.rag_distance_threshold:
            reasons.append(f"Above distance threshold ({dist:.4f} > {settings.rag_distance_threshold})")
        
        # Check composer dedup
        is_in_composed = any(c.document.content == doc.content for c in composed_results)
        if not is_in_composed:
            reasons.append("ContextComposer deduplicated / truncated due to similarity or budget limit")

        if not reasons:
            accepted_count += 1
            print(f"Chunk {idx} (Distance {dist:.4f}) — ACCEPTED | Source: {src}")
        else:
            rejected_count += 1
            reason_str = "; ".join(reasons)
            print(f"Chunk {idx} (Distance {dist:.4f}) — REJECTED | Source: {src}")
            print(f"   Reason: {reason_str}")

    # 7. Final Context Sent to Ollama
    print("\n" + "-" * 80)
    print("FINAL CONTEXT SENT TO OLLAMA")
    print("-" * 80)
    if not context_str:
        print("[EMPTY CONTEXT - NO GROUNDED CHUNKS AVAILABLE]")
    else:
        print(context_str)

    # 8. Final System Prompt
    parts = [DEFAULT_SYSTEM_PROMPT]
    if history_str:
        parts.append("History:\n" + history_str)
    if context_str:
        parts.append(f"Context:\n{context_str}")
    parts.append(f"User Question: {query}")

    final_prompt = "\n\n".join(parts)

    print("\n" + "-" * 80)
    print("FINAL SYSTEM PROMPT")
    print("-" * 80)
    print(final_prompt)

    # 9. Ollama Response
    print("\n" + "-" * 80)
    print("OLLAMA RESPONSE")
    print("-" * 80)
    
    llm_service = create_llm_service(settings)
    raw_response = ""
    if not context_str:
        raw_response = FALLBACK_NO_INFO_REPLY
        print(raw_response)
    else:
        try:
            tokens = []
            for tok in llm_service.generate_stream(final_prompt):
                tokens.append(tok)
            raw_response = "".join(tokens)
            print(raw_response)
        except Exception as err:
            raw_response = f"[LLM GENERATION ERROR: {err}]"
            print(raw_response)

    # 10. Summary & Diagnosis
    retrieval_succeeded = bool(context_str) and raw_response != FALLBACK_NO_INFO_REPLY
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Did retrieval succeed? {'YES' if retrieval_succeeded else 'NO'}")
    print(f"Confidence Level:      {getattr(confidence_assessment, 'confidence_level', 'N/A')}")
    print(f"Confidence Score:      {getattr(confidence_assessment, 'confidence_score', 0.0):.4f}")
    print(f"Accepted Chunks:       {accepted_count}")
    print(f"Rejected Chunks:       {rejected_count}")

    if not retrieval_succeeded:
        print("\nDiagnosis / Reason for Failure:")
        if not raw_search_results:
            print("  • No matching chunks returned by hybrid retriever (Missing document or unindexed text).")
        elif not context_str:
            print(f"  • All chunks were filtered out by distance threshold ({settings.rag_distance_threshold}) or deduplication.")
        elif raw_response == FALLBACK_NO_INFO_REPLY:
            print("  • RAG context was empty or deemed ungrounded, returning strict fallback response.")
        else:
            print("  • Document context did not contain sufficient answer detail for LLM to extract fact.")

    print("=" * 80 + "\n")


def main():
    if len(sys.argv) > 1:
        user_query = " ".join(sys.argv[1:])
        debug_query(user_query)
    else:
        print("=" * 80)
        print("AUNTII RAG DEBUG MODE — Type a query and press Enter (or 'exit' to quit)")
        print("=" * 80)
        while True:
            try:
                q = input("\nEnter Query > ").strip()
                if not q:
                    continue
                if q.lower() in ("exit", "quit", "q"):
                    break
                debug_query(q)
            except (KeyboardInterrupt, EOFError):
                print("\nExiting debug mode.")
                break


if __name__ == "__main__":
    main()
