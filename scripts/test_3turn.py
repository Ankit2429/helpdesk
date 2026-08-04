"""Test 3-turn multi-turn conversation sequence."""

from campus_helpdesk.application.rag_chat_service import RAGChatService
from campus_helpdesk.application.query_rewriter import QueryRewriter
from campus_helpdesk.application.session_manager import SessionManager
from campus_helpdesk.infrastructure.llm.factory import create_llm_service
from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline
from campus_helpdesk.config.settings import get_settings

settings = get_settings()
llm = create_llm_service(settings)
rag = create_rag_pipeline(settings)
if settings.faiss_index_path.exists():
    rag.load_index()

sm = SessionManager()
qr = QueryRewriter()
service = RAGChatService(
    llm_service=llm,
    rag_pipeline=rag,
    query_rewriter=qr,
    session_manager=sm,
)

session_id = "test_multi_turn_sequence"

print("==================================================")
print("TURN 1: where is the admission office")
r1 = service.respond("where is the admission office", session_id=session_id)
print("Reply 1:\n", r1.reply)
print("Confidence 1:", r1.confidence_level, f"(Score: {r1.confidence_score:.4f})")

print("\n==================================================")
print("TURN 2: what are its timings")
mem1 = sm.get_or_create_session(session_id)
hist1_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in mem1.get_messages()])
rw2 = qr.rewrite("what are its timings", hist1_str)
print("Rewritten Query 2:", rw2)
r2 = service.respond("what are its timings", session_id=session_id)
print("Reply 2:\n", r2.reply)
print("Confidence 2:", r2.confidence_level, f"(Score: {r2.confidence_score:.4f})")

print("\n==================================================")
print("TURN 3: what about the library")
mem2 = sm.get_or_create_session(session_id)
hist2_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in mem2.get_messages()])
rw3 = qr.rewrite("what about the library", hist2_str)
print("Rewritten Query 3:", rw3)
r3 = service.respond("what about the library", session_id=session_id)
print("Reply 3:\n", r3.reply)
print("Confidence 3:", r3.confidence_level, f"(Score: {r3.confidence_score:.4f})")
print("==================================================")
