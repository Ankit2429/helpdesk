import logging
logging.basicConfig(level=logging.INFO)

from campus_helpdesk.config.settings import get_settings
from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline
from campus_helpdesk.infrastructure.rag.confidence_engine import ConfidenceEngine
from campus_helpdesk.application.query_rewriter import QueryRewriter

def audit():
    settings = get_settings()
    pipeline = create_rag_pipeline(settings)
    confidence_engine = ConfidenceEngine(settings)
    rewriter = QueryRewriter()

    queries = [
        "branch names",
        "names of the department",
        "departments",
        "principal",
        "hostel"
    ]

    for q in queries:
        print("\n" + "="*80)
        rewritten = rewriter.rewrite(q)
        print(f"QUERY: '{q}' -> REWRITTEN: '{rewritten}'")
        print("="*80)

        try:
            results = pipeline._similarity_store.search(rewritten, limit=5)
            if pipeline._reranker:
                results = pipeline._reranker.rerank(rewritten, results)
        except Exception as e:
            print(f"Error: {e}")
            continue

        confidence_assessment = confidence_engine.evaluate(results)
        print(f"Confidence score: {confidence_assessment.confidence_score}")
        print(f"Confidence level: {confidence_assessment.confidence_level}")
        print(f"Diagnostics: {confidence_assessment.diagnostics}")
        print(f"Decision logic: score >= 0.35 OR reranker >= 0.1 OR distance <= 1.2")
        
        top_reranker = confidence_assessment.top_reranker_score
        top_distance = confidence_assessment.top_distance
        is_accepted = (confidence_assessment.confidence_score >= 0.35) or (top_reranker >= 0.1) or (top_distance <= 1.2)
        print(f"ACCEPTED: {is_accepted}")

if __name__ == "__main__":
    audit()
