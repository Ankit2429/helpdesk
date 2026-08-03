import pytest
import os
import time
from pathlib import Path
from campus_helpdesk.domain.knowledge import KnowledgeDocument
from campus_helpdesk.infrastructure.rag.bm25_store import BM25SearchStore
from campus_helpdesk.infrastructure.rag.faiss_store import FAISSSimilarityStore
from campus_helpdesk.infrastructure.rag.hybrid_retriever import HybridRetriever
from campus_helpdesk.infrastructure.rag.cross_encoder_reranker import CrossEncoderReranker
from campus_helpdesk.infrastructure.rag.confidence_engine import ConfidenceEngine
from campus_helpdesk.infrastructure.logging.tracer import get_tracer
from campus_helpdesk.config.settings import get_settings
from campus_helpdesk.infrastructure.rag.sentence_transformer_embeddings import SentenceTransformerEmbeddings

def test_sprint2_retrieval_pipeline_integration(tmp_path):
    settings = get_settings()
    
    # 1. Initialize embeddings service
    embeddings = SentenceTransformerEmbeddings(
        model_name=settings.embedding_model,
        device=settings.embedding_device,
        batch_size=settings.embedding_batch_size,
        normalize_embeddings=settings.embedding_normalize,
        show_progress=settings.embedding_show_progress,
        local_files_only=settings.embedding_local_files_only
    )
    
    # 2. Setup mock documents
    docs = [
        KnowledgeDocument(
            content="B.E. Computer Science and Engineering fees for COMEDK is Rs. 3,04,100 per annum.",
            metadata={"source": "fee-structure.md", "category": "admissions"}
        ),
        KnowledgeDocument(
            content="Central Library timings are Monday to Friday from 8 AM to 8 PM.",
            metadata={"source": "library-rules.md", "category": "infrastructure"}
        ),
        KnowledgeDocument(
            content="The chairperson of the Anti-Ragging committee is Prof. Sanjay Kotabagi.",
            metadata={"source": "anti-ragging.md", "category": "miscellaneous"}
        )
    ]
    
    # 3. Setup BM25 and FAISS Stores
    bm25_store = BM25SearchStore()
    faiss_store = FAISSSimilarityStore(
        embeddings=embeddings,
        index_path=tmp_path / "faiss",
        allow_dangerous_deserialization=True,
        embedding_metadata={"model": settings.embedding_model}
    )
    
    # Add documents
    faiss_store.add(docs)
    bm25_store.index_documents(docs)
    
    # 4. Setup Hybrid Retriever
    hybrid = HybridRetriever(
        similarity_store=faiss_store,
        bm25_store=bm25_store,
        bm25_top_k=3,
        dense_top_k=3,
        final_top_k=3
    )
    
    # 5. Setup Reranker & Confidence Engine
    reranker = CrossEncoderReranker(
        model_name=settings.reranker_model,
        enabled=True,
        top_n=3,
        top_m=3
    )
    confidence_engine = ConfidenceEngine()
    
    # Start Tracing
    tracer = get_tracer()
    span = tracer.start_span("What are the B.E. CSE fees?")
    
    # Run full query pipeline
    start_time = time.perf_counter()
    
    # Step A: Hybrid Search
    results, retrieval_stats = hybrid.search_with_stats(span["query"])
    assert len(results) > 0
    
    # Step B: Rerank
    reranked, rerank_stats = reranker.rerank_with_stats(span["query"], results)
    assert len(reranked) > 0
    
    # Step C: Confidence Evaluation
    assessment = confidence_engine.evaluate(reranked)
    latency_ms = (time.perf_counter() - start_time) * 1000.0
    
    # Log to DiagnosticTracer
    tracer.log_retrieval_step(
        span=span,
        vector_candidates=[{"source": match.document.metadata.get("source", "unknown")} for match in results],
        bm25_candidates=[{"source": match.document.metadata.get("source", "unknown")} for match in results],
        rrf_output=[{"source": match.document.metadata.get("source", "unknown")} for match in results],
        confidence_score=assessment.confidence_score,
        latency_ms=latency_ms
    )
    
    # Verify outputs
    assert span["retrieval"]["confidence_score"] == assessment.confidence_score
    assert span["retrieval"]["latency_ms"] == latency_ms
    assert len(span["retrieval"]["vector_candidates"]) > 0
