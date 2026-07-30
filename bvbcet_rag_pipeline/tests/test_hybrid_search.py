"""Unit tests for BM25 + Dense Hybrid Search Engine."""

from vector_db.hybrid_search import HybridSearchEngine, HybridSearchResult


def test_hybrid_search_rrf_fusion():
    engine = HybridSearchEngine(rrf_k=60)

    corpus = [
        {"text": "Computer Science department offers AI and ML courses.", "metadata": {"id": "chunk_01"}},
        {"text": "Hostel mess fee structure and room allotment rules.", "metadata": {"id": "chunk_02"}},
        {"text": "KCET quota admissions start in July.", "metadata": {"id": "chunk_03"}},
    ]

    engine.build_bm25_index(corpus)
    bm25_res = engine.bm25_search("Computer Science courses", top_k=2)

    assert len(bm25_res) > 0
    assert bm25_res[0][0]["metadata"]["id"] == "chunk_01"

    dense_res = [
        {"text": "Computer Science department offers AI and ML courses.", "metadata": {"id": "chunk_01"}, "score": 0.85},
        {"text": "KCET quota admissions start in July.", "metadata": {"id": "chunk_03"}, "score": 0.60},
    ]

    fused = engine.fuse_rrf(dense_results=dense_res, bm25_results=bm25_res, top_k=2)

    assert len(fused) > 0
    assert isinstance(fused[0], HybridSearchResult)
    assert fused[0].doc_id == "chunk_01"
    assert fused[0].rrf_score > 0.0
