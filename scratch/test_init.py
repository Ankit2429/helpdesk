import logging
from campus_helpdesk.application.rag_chat_service import RAGChatService

class DummyLLM:
    def generate(self, prompt):
        return "dummy reply"

class DummyPipeline:
    def search(self, query):
        return []

class DummyRewriter:
    def rewrite(self, msg, hist):
        return msg

svc = RAGChatService(
    llm_service=DummyLLM(),
    rag_pipeline=DummyPipeline(),
    query_rewriter=DummyRewriter()
)
print('Context builder exists:', svc._context_builder is not None)
print('Context builder type:', type(svc._context_builder))
