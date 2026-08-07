"""
diagnose_retrieval_failures.py
Diagnoses exact retrieval scores and ranks for DEP001, REG001, REG007.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from campus_helpdesk.config.settings import Settings
from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline

def inspect_query(pipeline, query_text):
    print("=" * 90)
    print(f"QUERY: \"{query_text}\"")
    print("=" * 90)
    
    # 1. Raw FAISS dense search
    faiss_store = pipeline._similarity_store.similarity_store if hasattr(pipeline._similarity_store, 'similarity_store') else pipeline._similarity_store
    
    print("\n--- [1] FAISS Top-10 Dense Results ---")
    try:
        dense_res = faiss_store.search(query_text, limit=10)
        for rank, r in enumerate(dense_res, 1):
            src = r.document.metadata.get("source")
            print(f"  {rank}. Dist: {r.distance:.4f} | Source: {src} | Headings: {r.document.metadata.get('headings')}")
    except Exception as e:
        print("Dense search error:", e)

    print("\n--- [2] Hybrid RRF Top-10 Results (Before Reranker) ---")
    try:
        hybrid_res = pipeline._similarity_store.search(query_text, limit=10)
        for rank, r in enumerate(hybrid_res, 1):
            src = r.document.metadata.get("source")
            print(f"  {rank}. Score: {r.distance:.4f} | Source: {src} | Headings: {r.document.metadata.get('headings')}")
    except Exception as e:
        print("Hybrid search error:", e)

    print("\n--- [3] Final RAG Pipeline Search (After Reranker & Dedup) ---")
    final_res = pipeline.search(query_text, limit=5)
    for rank, r in enumerate(final_res, 1):
        src = r.document.metadata.get("source")
        print(f"  {rank}. Source: {src} | Headings: {r.document.metadata.get('headings')}")
        print(f"     Text Snippet: {r.document.content[:120].replace(chr(10), ' ')}")

def main():
    settings = Settings()
    pipeline = create_rag_pipeline(settings)
    pipeline.load_index()

    inspect_query(pipeline, "What specialization streams are offered under B.E. Computer Science and Engineering?")
    inspect_query(pipeline, "Where is the library located in campus?")
    inspect_query(pipeline, "What are the admissions office hours?")

if __name__ == "__main__":
    main()
