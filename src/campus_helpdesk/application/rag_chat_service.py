"""RAG-augmented Chat Service combining SimilarityStore and local Ollama model."""

import logging

from campus_helpdesk.application.chat_models import ChatResult
from campus_helpdesk.application.chat_service import ChatService
from campus_helpdesk.application.conversation_manager import ConversationManager
from campus_helpdesk.application.llm_service import LLMService
from campus_helpdesk.application.query_rewriter import QueryRewriter
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
    """Chat service using local vector search (RAG) and local Ollama LLM with multi-turn memory."""

    def __init__(
        self,
        llm_service: LLMService,
        rag_pipeline: RAGPipeline | None = None,
        distance_threshold: float = 2.0,
        max_context_size: int = 3000,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        conversation_manager: ConversationManager | None = None,
    ) -> None:
        self._llm_service = llm_service
        self._rag_pipeline = rag_pipeline
        self._distance_threshold = distance_threshold
        self._system_prompt = system_prompt
        self._context_builder = PromptContextBuilder(
            max_context_size=max_context_size,
            similarity_threshold=distance_threshold,
        )
        self.conversation_manager = conversation_manager or ConversationManager()
        self._query_rewriter = QueryRewriter()

    def respond(self, message: str, session_id: str = "default") -> ChatResult:
        """Process user message through RAG retrieval and generate answer via local LLM."""
        if not message.strip():
            return ChatResult(reply="I am listening. How can I help you?", status="completed")

        history = self.conversation_manager.get_recent_history(session_id)
        search_query = self._query_rewriter.rewrite(message, history)
        history_prompt = self.conversation_manager.format_history_prompt(session_id)

        context_str = ""
        if self._rag_pipeline is not None:
            try:
                search_results = self._rag_pipeline.search(search_query)
                if search_results:
                    context_str = self._context_builder.build_context(search_results)
                    if not context_str:
                        logger.info(
                            "All search results exceeded similarity distance threshold (%f). Skipping RAG context.",
                            self._distance_threshold,
                        )
            except Exception as err:
                logger.warning(f"RAG context retrieval exception: {err}")

        parts = [self._system_prompt]
        if history_prompt:
            parts.append(history_prompt)
        if context_str:
            parts.append(f"Context:\n{context_str}")
        parts.append(f"User Question: {message}")

        prompt = "\n\n".join(parts)
        reply = self._llm_service.generate(prompt)

        # Record conversation turns
        self.conversation_manager.add_user_message(message, session_id)
        self.conversation_manager.add_assistant_message(reply, session_id)

        return ChatResult(reply=reply, status="completed")

    def respond_stream(self, message: str, session_id: str = "default"):
        """Process user message through RAG retrieval and yield answer tokens via local LLM."""
        if not message.strip():
            yield "I am listening. How can I help you?"
            return

        history = self.conversation_manager.get_recent_history(session_id)
        search_query = self._query_rewriter.rewrite(message, history)
        history_prompt = self.conversation_manager.format_history_prompt(session_id)

        context_str = ""
        if self._rag_pipeline is not None:
            try:
                search_results = self._rag_pipeline.search(search_query)
                if search_results:
                    context_str = self._context_builder.build_context(search_results)
                    if not context_str:
                        logger.info(
                            "All search results exceeded similarity distance threshold (%f). Skipping RAG context.",
                            self._distance_threshold,
                        )
            except Exception as err:
                logger.warning(f"RAG context retrieval exception: {err}")

        parts = [self._system_prompt]
        if history_prompt:
            parts.append(history_prompt)
        if context_str:
            parts.append(f"Context:\n{context_str}")
        parts.append(f"User Question: {message}")

        prompt = "\n\n".join(parts)
        full_reply_tokens = []
        for token in self._llm_service.generate_stream(prompt):
            full_reply_tokens.append(token)
            yield token

        full_reply = "".join(full_reply_tokens)
        self.conversation_manager.add_user_message(message, session_id)
        self.conversation_manager.add_assistant_message(full_reply, session_id)

    def clear_history(self, session_id: str = "default") -> None:
        """Reset conversation memory for a given session."""
        self.conversation_manager.reset_session(session_id)

