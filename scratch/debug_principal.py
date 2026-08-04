import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(r"d:\AUNTII").resolve()))
sys.path.insert(0, str(Path(r"d:\AUNTII\src").resolve()))

from campus_helpdesk.config.settings import get_settings
from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline
from campus_helpdesk.application.query_rewriter import QueryRewriter
from campus_helpdesk.application.rag_chat_service import RAGChatService
from campus_helpdesk.application.llm_service import LLMService
from campus_helpdesk.services.query_normalizer import normalize_query
from campus_helpdesk.services.intent_router import IntentRouter
from campus_helpdesk.infrastructure.rag.prompt_context_builder import PromptContextBuilder

def debug():
    settings = get_settings()
    pipeline = create_rag_pipeline(settings)
    if settings.faiss_index_path.exists():
        pipeline.load_index()

    from campus_helpdesk.infrastructure.llm.factory import create_llm_service
    llm_service = create_llm_service(settings)
    rag_chat_service = RAGChatService(
        llm_service=llm_service,
        rag_pipeline=pipeline
    )
    
    intent_router = IntentRouter()
    rewriter = QueryRewriter()
    queries = [
        "Who is the principal of BVBCET?",
        "Who is the Vice Chancellor?",
        "Who is the Registrar?",
        "Who heads the School of Computer Science?"
    ]
    for query in queries:
        print("="*40)
        print("Original query:", query)
        
        normalized = normalize_query(query)
        print("Normalized query:", normalized)
        
        intent_res = intent_router.route(normalized)
        print("Intent:", intent_res.intent)
        
        rewritten = rewriter.rewrite(normalized)
        print("Rewritten query:", rewritten)
        
        chunks = list(pipeline.search(rewritten, limit=5, original_query=normalized))
        print("\n--- Retrieved top 5 chunks ---")
        for i, c in enumerate(chunks):
            print(f"Chunk {i+1}:")
            print(f"  Filename: {getattr(c, 'source', getattr(c, 'metadata', {}).get('source', 'unknown'))}")
            print(f"  Title: {getattr(c, 'metadata', {}).get('title', getattr(c, 'title', 'unknown'))}")
            sim_score = getattr(c, 'similarity_score', getattr(c, 'score', None))
            reranker_score = getattr(c, 'reranker_score', None)
            print(f"  Similarity score: {sim_score}")
            print(f"  Reranker score: {reranker_score}")
            content_text = str(getattr(c, 'text', getattr(c, 'content', getattr(c, 'document', ''))))
            print(f"  Content: {content_text[:200]}...")
            print("-" * 20)

        print("\nExecuting chat service response...")
        result = rag_chat_service.respond(query)
        print("\n--- Final response ---")
        print(result.reply)
        print("Confidence score:", result.confidence_score)
        print("========================================")

if __name__ == "__main__":
    debug()
