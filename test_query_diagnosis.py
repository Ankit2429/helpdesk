#!/usr/bin/env python
"""
test_query_diagnosis.py — Detailed Phase 1 RAG Retrieval & Knowledge Base Diagnosis
"""

import sys
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")

from campus_helpdesk.config.settings import get_settings
from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline
from campus_helpdesk.application.query_rewriter import QueryRewriter

TEST_QUERIES = [
    "How many departments exist in the college?",
    "Information of BE",
    "Tell me about BE",
    "What is BE?",
    "List all departments",
    "Tell me about the ISE department",
    "What courses are offered?",
]

def diagnose():
    settings = get_settings()
    rewriter = QueryRewriter()
    pipeline = create_rag_pipeline(settings)
    if settings.faiss_index_path.exists():
        pipeline.load_index()

    retriever = pipeline._similarity_store
    faiss_store = getattr(retriever, "similarity_store", None)
    bm25_retriever = getattr(retriever, "bm25_retriever", None)

    print("=" * 80)
    print("PHASE 1 DIAGNOSTIC RESULTS")
    print("=" * 80)

    for q in TEST_QUERIES:
        print("\n" + "=" * 80)
        print(f"USER QUERY: '{q}'")
        print("=" * 80)

        # 1. Rewritten query
        rewritten = rewriter.rewrite(q, history=None)
        print(f"1. REWRITTEN QUERY: '{rewritten}'")

        # 2. FAISS retrieval
        print("\n2. FAISS RETRIEVAL RESULTS:")
        if faiss_store:
            try:
                faiss_res = faiss_store.search(rewritten, limit=5)
                for i, r in enumerate(faiss_res, 1):
                    doc = r.document
                    src = doc.metadata.get("source") or doc.metadata.get("source_filename", "unknown")
                    snippet = doc.content[:150].replace("\n", " ")
                    print(f"   [{i}] Dist: {r.distance:8.4f} | Source: {src}")
                    print(f"       Text: {snippet}...")
            except Exception as e:
                print(f"   FAISS error: {e}")

        # 3. BM25 retrieval
        print("\n3. BM25 RETRIEVAL RESULTS:")
        if bm25_retriever:
            try:
                bm25_res = bm25_retriever.search(rewritten, top_k=5)
                for i, r in enumerate(bm25_res, 1):
                    doc = r.document
                    snippet = doc.content[:150].replace("\n", " ")
                    print(f"   [{i}] Score: {r.score:8.4f} | Source: {doc.metadata.get('source', 'unknown')}")
                    print(f"       Text: {snippet}...")
            except Exception as e:
                print(f"   BM25 error: {e}")

        # 4. Hybrid ranking
        print("\n4. HYBRID RETRIEVAL (Dense + Sparse RRF):")
        try:
            hybrid_res = retriever.retrieve(rewritten, limit=5)
            for i, r in enumerate(hybrid_res, 1):
                doc = r.document
                src = doc.metadata.get("source") or doc.metadata.get("source_filename", "unknown")
                snippet = doc.content[:150].replace("\n", " ")
                print(f"   [{i}] Score: {r.score:8.4f} | Source: {src}")
                print(f"       Text: {snippet}...")
        except Exception as e:
            print(f"   Hybrid error: {e}")

        # 5. Pipeline Search (Reranked + Deduplicated)
        print("\n5. PIPELINE SEARCH RESULTS (Final Context Candidates):")
        try:
            pipe_res = pipeline.search(q, limit=5)
            for i, r in enumerate(pipe_res, 1):
                doc = r.document
                src = doc.metadata.get("source") or doc.metadata.get("source_filename", "unknown")
                snippet = doc.content[:200].replace("\n", " ")
                print(f"   [{i}] Dist/Score: {r.distance:8.4f} | Source: {src}")
                print(f"       Text: {snippet}...")
        except Exception as e:
            print(f"   Pipeline error: {e}")

    # Inspect Knowledge Base Corpus for indexed documents
    print("\n" + "=" * 80)
    print("KNOWLEDGE BASE CORPUS INSPECTION")
    print("=" * 80)
    if bm25_retriever and hasattr(bm25_retriever, "corpus_documents"):
        corpus = bm25_retriever.corpus_documents
        print(f"Total Chunks in Corpus: {len(corpus)}")
        sources = set()
        for d in corpus:
            src = d.metadata.get("source") or d.metadata.get("source_filename", "unknown")
            sources.add(src)
        print("Indexed Source Files in Knowledge Base:")
        for s in sorted(sources):
            print(f"  - {s}")

if __name__ == "__main__":
    diagnose()
