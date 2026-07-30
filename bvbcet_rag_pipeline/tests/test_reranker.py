"""Unit tests for Cross-Encoder re-ranker."""

from retrieval.reranker import CrossEncoderReranker, RerankedCandidate


def test_cross_encoder_reranker():
    reranker = CrossEncoderReranker(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2", score_threshold=0.10)

    candidates = [
        {"text": "Hostel fee structure is 60000 INR per year.", "metadata": {"id": "chunk_02"}, "score": 0.50},
        {"text": "Computer Science department offers B.E. in Artificial Intelligence.", "metadata": {"id": "chunk_01"}, "score": 0.85},
    ]

    reranked = reranker.rerank(query="What degree is offered in Computer Science?", candidates=candidates, top_k=2)

    assert len(reranked) > 0
    assert isinstance(reranked[0], RerankedCandidate)
    assert reranked[0].metadata["id"] == "chunk_01"
