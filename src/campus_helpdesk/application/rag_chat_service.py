"""RAG-augmented Chat Service combining SimilarityStore and local Ollama model."""

import logging

from campus_helpdesk.application.chat_models import ChatResult
from campus_helpdesk.application.chat_service import ChatService
from campus_helpdesk.application.llm_service import LLMService
from campus_helpdesk.application.rag_pipeline import RAGPipeline
from campus_helpdesk.infrastructure.rag.prompt_context_builder import PromptContextBuilder

logger = logging.getLogger(__name__)

FALLBACK_NO_INFO_REPLY = "I don't have information about that in my knowledge base."
DEFAULT_SYSTEM_PROMPT = (
    "You are an offline autonomous Campus Helpdesk Robot for BVB Engineering College (KLE Tech), Hubballi. "
    "Be direct and extremely concise. Answer in 1 to 2 short sentences only using the provided context. "
    "If the answer is not clearly present in the provided context, say you don't have that information — "
    "do not invent, guess, or estimate any fact, number, name, or detail not explicitly stated in the context."
)
GENERAL_SYSTEM_PROMPT = (
    "You are a helpful campus helpdesk assistant for BVB Engineering College (KLE Tech), Hubballi. "
    "Be direct and extremely concise. Answer in 1 to 2 short sentences only."
)


class RAGChatService(ChatService):
    """Chat service using local vector search (RAG) and local Ollama LLM."""

    def __init__(
        self,
        llm_service: LLMService,
        rag_pipeline: RAGPipeline | None = None,
        distance_threshold: float = 2.0,
        max_context_size: int = 3000,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    ) -> None:
        self._llm_service = llm_service
        self._rag_pipeline = rag_pipeline
        self._distance_threshold = distance_threshold
        self._system_prompt = system_prompt
        self._context_builder = PromptContextBuilder(
            max_context_size=max_context_size,
            similarity_threshold=distance_threshold,
        )

    def respond(self, message: str) -> ChatResult:
        """Process user message through RAG retrieval and generate answer via local LLM."""
        if not message.strip():
            return ChatResult(reply="I am listening. How can I help you?", status="completed")

        context_str = ""
        if self._rag_pipeline is not None:
            try:
                search_results = self._rag_pipeline.search(message)
                if search_results:
                    context_str = self._context_builder.build_context(search_results)
                    if not context_str:
                        logger.info(
                            "All search results exceeded similarity distance threshold (%f). Skipping RAG context.",
                            self._distance_threshold,
                        )
            except Exception as err:
                logger.warning(f"RAG context retrieval exception: {err}")

        if context_str:
            prompt = f"{self._system_prompt}\n\nContext:\n{context_str}\n\nUser Question: {message}"
        else:
            prompt = f"{GENERAL_SYSTEM_PROMPT}\n\nUser Question: {message}"

        reply = self._llm_service.generate(prompt)
        return ChatResult(reply=reply, status="completed")

    def respond_stream(self, message: str):
        """Process user message through RAG retrieval and yield answer tokens via local LLM."""
        if not message.strip():
            yield "I am listening. How can I help you?"
            return

        context_str = ""
        if self._rag_pipeline is not None:
            try:
                search_results = self._rag_pipeline.search(message)
                if search_results:
                    context_str = self._context_builder.build_context(search_results)
                    if not context_str:
                        logger.info(
                            "All search results exceeded similarity distance threshold (%f). Skipping RAG context.",
                            self._distance_threshold,
                        )
            except Exception as err:
                logger.warning(f"RAG context retrieval exception: {err}")

        if context_str:
            prompt = f"{self._system_prompt}\n\nContext:\n{context_str}\n\nUser Question: {message}"
        else:
            prompt = f"{GENERAL_SYSTEM_PROMPT}\n\nUser Question: {message}"

        yield from self._llm_service.generate_stream(prompt)

