"""RAG-augmented Chat Service combining SimilarityStore and local Ollama model."""

import logging
from typing import Optional

from campus_helpdesk.application.chat_models import ChatResult
from campus_helpdesk.application.chat_service import ChatService
from campus_helpdesk.application.llm_service import LLMService
from campus_helpdesk.application.rag_pipeline import RAGPipeline

logger = logging.getLogger(__name__)


class RAGChatService(ChatService):
    """Chat service using local vector search (RAG) and local Ollama LLM."""

    def __init__(
        self,
        llm_service: LLMService,
        rag_pipeline: Optional[RAGPipeline] = None,
        system_prompt: str = (
            "You are an offline autonomous Campus Helpdesk Robot. "
            "Answer student and visitor questions concisely and politely based on the provided context."
        ),
    ) -> None:
        self._llm_service = llm_service
        self._rag_pipeline = rag_pipeline
        self._system_prompt = system_prompt

    def respond(self, message: str) -> ChatResult:
        """Process user message through RAG retrieval and generate answer via local LLM."""
        if not message.strip():
            return ChatResult(reply="I am listening. How can I help you?", status="completed")

        context_str = ""
        if self._rag_pipeline is not None:
            try:
                search_results = self._rag_pipeline.search(message)
                if search_results:
                    retrieved_chunks = [res.content for res in search_results]
                    context_str = "\n---\n".join(retrieved_chunks)
            except Exception as err:
                logger.warning(f"RAG context retrieval exception: {err}")

        if context_str:
            prompt = f"{self._system_prompt}\n\nContext:\n{context_str}\n\nUser Question: {message}"
        else:
            prompt = f"{self._system_prompt}\n\nUser Question: {message}"

        reply = self._llm_service.generate(prompt)
        return ChatResult(reply=reply, status="completed")
