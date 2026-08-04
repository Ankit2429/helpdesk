#!/usr/bin/env python
"""
phase1_analysis.py — Phase 1 Analysis Script for RAG Queries

Traces:
- "How many departments exist in the college?"
- "Information of BE"
- "Tell me about BE"
- "What is BE?"
- "List all departments"
- "Tell me about the ISE department"
- "What courses are offered?"

Outputs full trace of:
1. Rewritten query
2. FAISS retrieval
3. BM25 retrieval
4. Hybrid ranking
5. Retrieved chunks & Source docs
6. Analysis of retrieval failure / missing info
"""

import sys
import numpy as np
from typing import List, Dict, Any

sys.stdout.reconfigure(encoding="utf-8")

from campus_helpdesk.config.settings import get_settings
from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline
from campus_helpdesk.application.query_rewriter import QueryRewriter

QUERIES = [
    "How many departments exist in the college?",
    "Information of BE",
    "Tell me about BE",
    "What is BE?",
    "List all departments",
    "Tell me about the ISE department",
    "What courses are offered?",
]

def run_analysis():
    print("=" * 80)
    print("PHASE 1 — RAG RETRIEVAL ANALYSIS")
    print("=" * 80)

    settings = get_settings()
    rewriter = QueryRewriter()

    # Load RAG Pipeline
    pipeline = create_rag_pipeline(settings)
    if settings.faiss_index_path.exists():
        pipeline.load_index()

    hybrid_retriever = pipeline._similarity_store
    faiss_store = getattr(hybrid_retriever, "similarity_store", getattr(pipeline, "_similarity_store", None))
    bm25_retriever = getattr(hybrid_retriever, "bm25_retriever", None)

    for q in QUERIES:
        print("\n" + "=" * 80)
        print(f"QUERY: '{q}'")
        print("=" * 80)

        # 1. Rewritten Query
        rewritten = rewriter.rewrite(q, history=None)
        print(f"1. REWRITTEN QUERY: '{rewritten}'")

        # 2. FAISS Retrieval
        print("\n2. FAISS RETRIEVAL (Top 5):")
        faiss_results = []
        try:
            if faiss_store and hasattr(faiss_store, "search"):
                faiss_results = faiss_store.search(rewritten, limit=5)
            for i, r in enumerate(faiss_results, 1):
                doc = r.document
                src = doc.metadata.get("source") or doc.metadata.get("source_filename", "unknown")
                snippet = doc.content[:150].replace("\n", " ")
                print(f"   [{i}] Dist: {r.distance:8.4f} | Source: {src} | ID: {doc.id}")
                print(f"       Text: {snippet}...")
        except Exception as e:
            print(f"   Error in FAISS search: {e}")

        # 3. BM25 Retrieval
        print("\n3. BM25 RETRIEVAL (Top 5):")
        bm25_results = []
        try:
            if hasattr(hybrid_retriever, "_bm25_search"):
                bm25_results = hybrid_retriever._bm25_search(rewritten, top_k=5)
            elif hasattr(bm25_retriever, "search"):
                bm25_results = bm25_retriever.search(rewritten, top_k=5)
            
            for i, r in enumerate(bm25_results, 1):
                doc = getattr(r, "document", r)
                score = getattr(r, "score", getattr(r, "distance", 0.0))
                src = doc.metadata.get("source") or doc.metadata.get("source_filename", "unknown")
                snippet = doc.content[:150].replace("\n", " ")
                print(f"   [{i}] Score: {score:8.4f} | Source: {src} | ID: {doc.id}")
                print(f"       Text: {snippet}...")
        except Exception as e:
            print(f"   Error in BM25 search: {e}")

        # 4. Hybrid Retrieval
        print("\n4. HYBRID RANKING (Top 5):")
        try:
            hybrid_results = hybrid_retriever.retrieve(rewritten, limit=5)
            for i, r in enumerate(hybrid_results, 1):
                doc = r.document
                src = doc.metadata.get("source") or doc.metadata.get("source_filename", "unknown")
                snippet = doc.content[:150].replace("\n", " ")
                print(f"   [{i}] Score: {r.score:8.4f} | Source: {src} | ID: {doc.id}")
                print(f"       Text: {snippet}...")
        except Exception as e:
            print(f"   Error in Hybrid retrieval: {e}")

    print("\n" + "=" * 80)
    print("INSPECTING KNOWLEDGE BASE FOR SPECIFIC ENTITIES")
    print("=" * 80)

    # Inspect documents containing "BE", "Bachelor of Engineering", "department", "courses"
    keywords = ["Bachelor of Engineering", "BE ", "B.E.", "department", "courses offered", "Information Science"]
    all_docs = []
    if hasattr(bm25_retriever, "corpus_documents"):
        all_docs = bm25_retriever.corpus_documents
    elif hasattr(hybrid_retriever, "documents"):
        all_docs = hybrid_retriever.documents

    print(f"Total Chunks in Corpus: {len(all_docs)}")

    for kw in keywords:
        matches = [d for d in all_docs if kw.lower() in d.content.lower()]
        print(f"\nKeyword: '{kw}' -> Found {len(matches)} matching chunks in KB")
        for idx, m in enumerate(matches[:3], 1):
            src = m.metadata.get("source") or m.metadata.get("source_filename", "unknown")
            snippet = m.content[:200].replace("\n", " ")
            print(f"   Matching Chunk [{idx}] Source: {src}")
            print(f"   Text: {snippet}...")

if __name__ == "__main__":
    run_analysis()
