import logging
from campus_helpdesk.config.settings import get_settings
from campus_helpdesk.infrastructure.llm.factory import create_llm_service
from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline
from campus_helpdesk.infrastructure.rag.prompt_context_builder import PromptContextBuilder
from campus_helpdesk.infrastructure.rag.context_composer import ContextComposer
from campus_helpdesk.application.rag_chat_service import RAGChatService, DEFAULT_SYSTEM_PROMPT
from campus_helpdesk.application.session_manager import SessionManager
from campus_helpdesk.application.query_rewriter import QueryRewriter
from campus_helpdesk.infrastructure.rag.confidence_engine import ConfidenceEngine
from campus_helpdesk.services.answerability_engine import AnswerabilityEngine

logging.basicConfig(level=logging.INFO)

settings = get_settings()
llm_service = create_llm_service(settings)
rag_pipeline = create_rag_pipeline(settings)
if settings.faiss_index_path.exists():
    rag_pipeline.load_index()

context_builder = PromptContextBuilder(max_context_size=7000, similarity_threshold=settings.rag_distance_threshold)
context_composer = ContextComposer(settings=settings)

chat_service = RAGChatService(
    llm_service=llm_service,
    rag_pipeline=rag_pipeline,
    query_rewriter=QueryRewriter(),
    context_builder=context_builder,
    session_manager=SessionManager(),
    confidence_engine=ConfidenceEngine(),
    answerability_engine=AnswerabilityEngine(),
    system_prompt=DEFAULT_SYSTEM_PROMPT,
    context_composer=context_composer,
)

queries = ["hi", "hello", "who are you", "departments", "hostel", "library"]

for q in queries:
    print(f"\n--- QUERY: '{q}' (respond) ---")
    res = chat_service.respond(q)
    print(f"Reply: {res.reply}")
    
    print(f"--- QUERY: '{q}' (respond_stream) ---")
    tokens = list(chat_service.respond_stream(q))
    print(f"Stream Reply: {''.join(tokens)}")
