"""
test_retrieval_tuning.py
Tests RRF weight adjustments and canonical metadata boosting for DEP001, REG001, REG007.
"""

import sys
import hashlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from campus_helpdesk.config.settings import Settings
from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline

def test_tuned_search(query_text, weight_dense=0.75, weight_sparse=0.25, canonical_boost=0.015):
    settings = Settings(rag_search_limit=5, candidate_window=20, reranker_top_n=20)
    pipeline = create_rag_pipeline(settings)
    pipeline.load_index()

    hybrid = pipeline._similarity_store
    hybrid.weight_dense = weight_dense
    hybrid.weight_sparse = weight_sparse

    # Search BM25 & FAISS
    bm25_results = hybrid.bm25_store.search(query_text, limit=25) if hybrid._bm25_indexed else []
    dense_results = hybrid.similarity_store.search(query_text, limit=25)

    rrf_scores = {}
    doc_map = {}
    distance_map = {}

    for rank, match in enumerate(bm25_results, start=1):
        doc = match.document
        doc_hash = hashlib.sha256(doc.content.strip().encode("utf-8")).hexdigest()
        rrf_scores[doc_hash] = rrf_scores.get(doc_hash, 0.0) + weight_sparse * (1.0 / (60 + rank))
        doc_map[doc_hash] = doc
        distance_map[doc_hash] = min(distance_map.get(doc_hash, match.distance), match.distance)

    for rank, match in enumerate(dense_results, start=1):
        doc = match.document
        doc_hash = hashlib.sha256(doc.content.strip().encode("utf-8")).hexdigest()
        rrf_scores[doc_hash] = rrf_scores.get(doc_hash, 0.0) + weight_dense * (1.0 / (60 + rank))
        doc_map[doc_hash] = doc
        distance_map[doc_hash] = min(distance_map.get(doc_hash, match.distance), match.distance)

    # Apply canonical source boost
    for doc_hash, doc in doc_map.items():
        src = doc.metadata.get("source", "")
        # Boost canonical directories over news-media
        if any(canon_prefix in src for canon_prefix in ["facilities/", "02-academics/", "03-admissions-fees/"]):
            rrf_scores[doc_hash] += 0.035
        elif "07-news-media/" in src or "01-governance-policy/" in src:
            rrf_scores[doc_hash] -= 0.015 # Penalty for old news & governance minutes

    sorted_hashes = sorted(rrf_scores.keys(), key=lambda h: rrf_scores[h], reverse=True)
    
    fused = []
    for h in sorted_hashes:
        from campus_helpdesk.domain.knowledge import SearchResult
        fused.append(SearchResult(document=doc_map[h], distance=distance_map[h]))

    # Now rerank top fused candidates
    if pipeline._reranker:
        reranked = pipeline._reranker.rerank(query_text, fused[:20], top_m=20)
    else:
        reranked = fused[:20]

    # Deduplicate by document
    seen = set()
    deduped = []
    for r in reranked:
        src = r.document.metadata.get("source")
        if src not in seen:
            seen.add(src)
            deduped.append(r)

    print(f"\nQUERY: \"{query_text}\"")
    print(f"Top 3 Retained Documents:")
    for rank, r in enumerate(deduped[:3], 1):
        src = r.document.metadata.get("source")
        print(f"  {rank}. Source: {src} | Headings: {r.document.metadata.get('headings')}")
        print(f"     Snippet: {r.document.content[:100].replace(chr(10), ' ')}")

def main():
    print("=" * 90)
    print("      TESTING TUNED RETRIEVAL PIPELINE (DENSE WEIGHT 0.75 + CANONICAL BOOST)")
    print("=" * 90)

    test_tuned_search("What specialization streams are offered under B.E. Computer Science and Engineering?")
    test_tuned_search("Where is the library located in campus?")
    test_tuned_search("What are the admissions office hours?")

if __name__ == "__main__":
    main()
