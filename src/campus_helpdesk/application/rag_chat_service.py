"""RAG-augmented Chat Service combining SimilarityStore and local Ollama model."""

import logging

from campus_helpdesk.application.chat_models import ChatResult
from campus_helpdesk.application.chat_service import ChatService
from campus_helpdesk.application.llm_service import LLMService
from campus_helpdesk.application.rag_pipeline import RAGPipeline

logger = logging.getLogger(__name__)

FALLBACK_NO_INFO_REPLY = "I don't have information about that in my knowledge base."
DEFAULT_SYSTEM_PROMPT = (
    "You are an offline autonomous Campus Helpdesk Robot. "
    "Only answer using the provided context. If the context does not contain the answer, "
    "say you don't have that information — do not guess."
)


class RAGChatService(ChatService):
    """Chat service using local vector search (RAG) and local Ollama LLM."""

    def __init__(
        self,
        llm_service: LLMService,
        rag_pipeline: RAGPipeline | None = None,
        distance_threshold: float = 1.0,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    ) -> None:
        self._llm_service = llm_service
        self._rag_pipeline = rag_pipeline
        self._distance_threshold = distance_threshold
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
                    top_distance = search_results[0].distance
                    if top_distance <= self._distance_threshold:
                        retrieved_chunks = [
                            res.document.content
                            for res in search_results
                            if res.distance <= self._distance_threshold
                        ]
                        context_str = "\n---\n".join(retrieved_chunks)
                    else:
                        logger.info(
                            f"Top search result distance ({top_distance:.4f}) exceeds threshold ({self._distance_threshold}). "
                            "Skipping LLM context retrieval."
                        )
            except Exception as err:
                logger.warning(f"RAG context retrieval exception: {err}")

        if not context_str:
            return ChatResult(reply=FALLBACK_NO_INFO_REPLY, status="completed")

        prompt = f"{self._system_prompt}\n\nContext:\n{context_str}\n\nUser Question: {message}"
        reply = self._llm_service.generate(prompt)
        return ChatResult(reply=reply, status="completed")

