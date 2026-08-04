import sys
import logging
logging.basicConfig(level=logging.INFO)

from campus_helpdesk.config.settings import get_settings
from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline
from campus_helpdesk.infrastructure.rag.confidence_engine import ConfidenceEngine

def audit():
    settings = get_settings()
    pipeline = create_rag_pipeline(settings)
    confidence_engine = ConfidenceEngine(settings)

    queries = [
        "branch names",
        "names of the department",
        "departments",
        "principal",
        "hostel"
    ]

    for q in queries:
        print("\n" + "="*80)
        print(f"QUERY: '{q}'")
        print("="*80)

        # 1. Search hybrid retriever
        try:
            results = pipeline._similarity_store.search(q, limit=5)
            # Apply reranker if enabled
            if pipeline._reranker:
                results = pipeline._reranker.rerank(q, results)
        except Exception as e:
            print(f"Error during search: {e}")
            continue

        print(f"Total retrieved chunks: {len(results)}")
        
        # Evaluate confidence
        confidence_assessment = confidence_engine.evaluate(results)
        print(f"Confidence score: {confidence_assessment.confidence_score}")
        print(f"Confidence level: {confidence_assessment.confidence_level}")
        print(f"Hallucination risk: {confidence_assessment.hallucination_risk}")
        print(f"Diagnostics: {confidence_assessment.diagnostics}")

        for idx, res in enumerate(results[:5]):
            print(f"\n[{idx+1}] Source: {res.document.metadata.get('source')}")
            print(f"    Distance (FAISS/RRF): {res.distance}")
            print(f"    Content snippet: {res.document.content[:200].strip()}...")

if __name__ == "__main__":
    audit()
