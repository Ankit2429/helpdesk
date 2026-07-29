"""RAG-augmented Chat Service combining SimilarityStore and local Ollama model."""

import logging

from campus_helpdesk.application.chat_models import ChatResult
from campus_helpdesk.application.chat_service import ChatService
from campus_helpdesk.application.session_manager import SessionManager
from campus_helpdesk.application.llm_service import LLMService
from campus_helpdesk.application.query_rewriter import QueryRewriter
from campus_helpdesk.application.rag_pipeline import RAGPipeline
from campus_helpdesk.infrastructure.rag.confidence_engine import ConfidenceAssessment, ConfidenceEngine
from campus_helpdesk.infrastructure.rag.prompt_context_builder import PromptContextBuilder
from campus_helpdesk.services.answerability_engine import AnswerabilityEngine
from campus_helpdesk.services.citation_validator import CitationValidator

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
    """Chat service using local vector search (RAG) and local Ollama LLM with multi-turn memory and confidence scoring."""

    def __init__(
        self,
        llm_service: LLMService,
        rag_pipeline: RAGPipeline | None = None,
        query_rewriter: QueryRewriter | None = None,
        context_builder: PromptContextBuilder | None = None,
        session_manager: SessionManager | None = None,
        confidence_engine: ConfidenceEngine | None = None,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        answerability_engine: AnswerabilityEngine | None = None,
    ) -> None:
        self._llm_service = llm_service
        self._rag_pipeline = rag_pipeline
        self._query_rewriter = query_rewriter or QueryRewriter()
        self._context_builder = context_builder
        self.session_manager = session_manager or SessionManager()
        self.confidence_engine = confidence_engine or ConfidenceEngine()
        self._system_prompt = system_prompt
        self._answerability_engine = answerability_engine or AnswerabilityEngine()

    def respond(self, message: str, session_id: str = "default") -> ChatResult:
        """Process user message through RAG retrieval, evaluate confidence, and generate answer via local LLM. User input is sanitized to prevent prompt injection."""
        if not message.strip():
            return ChatResult(reply="I am listening. How can I help you?", status="completed")

        memory = self.session_manager.get_or_create_session(session_id)
        history = memory.get_messages()
        
        # Format history string for query rewriting
        history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
        # Sanitize user input before rewrite
        from campus_helpdesk.services.prompt_sanitizer import sanitize_user_input
        safe_message = sanitize_user_input(message)
        search_query = self._query_rewriter.rewrite(safe_message, history_str)

        context_str = ""
        confidence_assessment: ConfidenceAssessment | None = None
        search_results = []
        
        # Retrieve RAG results and attempt to build context. If context is empty (e.g., all results exceed distance threshold),
        # we fallback to using the LLM without answerability gating.
        if self._rag_pipeline is not None:
            try:
                search_results = self._rag_pipeline.search(search_query)
                if search_results:
                    confidence_assessment = self.confidence_engine.evaluate(search_results)
                    context_str = self._context_builder.build_context(search_results, confidence_assessment)
            except Exception as err:
                logger.warning(f"RAG context retrieval exception: {err}")
        
        # Determine if we have usable RAG context
        rag_context_available = bool(context_str)
        if not rag_context_available:
            # No RAG context, directly generate response via LLM
            parts = [self._system_prompt]
            if history:
                parts.append("History:\n" + history_str)
            parts.append(f"User Question: {safe_message}")
            prompt = "\n\n".join(parts)
            reply = self._llm_service.generate(prompt)
            # Record conversation and return early
            memory.add_message("user", message)
            memory.add_message("assistant", reply)
            score = confidence_assessment.confidence_score if confidence_assessment else 1.0
            level = confidence_assessment.confidence_level if confidence_assessment else "HIGH"
            sources = confidence_assessment.supporting_sources if confidence_assessment else []
            return ChatResult(
                reply=reply,
                status="completed",
                confidence_score=score,
                confidence_level=level,
                supporting_sources=sources,
            )

        # Check answerability before sending to LLM
        # This block is now unreachable when RAG context is unavailable because early return handled above.
        confidence_level = confidence_assessment.confidence_level if confidence_assessment else "LOW"
        answerability = AnswerabilityEngine.evaluate_answerability(
            message, 
            [res.document for res in search_results], 
            confidence_level
        )
        
        if answerability == "Insufficient":
            reply = FALLBACK_NO_INFO_REPLY
        else:
            parts = [self._system_prompt]
            if history:
                parts.append("History:\n" + history_str)
            if context_str:
                parts.append(f"Context:\n{context_str}")
            parts.append(f"User Question: {message}")

            prompt = "\n\n".join(parts)
            reply = self._llm_service.generate(prompt)
            
            # Post-validate citations
            reply = CitationValidator.validate_citations(reply, [res.document for res in search_results])

        # Record conversation turns
        memory.add_message("user", message)
        memory.add_message("assistant", reply)

        score = confidence_assessment.confidence_score if confidence_assessment else 1.0
        level = confidence_assessment.confidence_level if confidence_assessment else "HIGH"
        sources = confidence_assessment.supporting_sources if confidence_assessment else []

        return ChatResult(
            reply=reply,
            status="completed",
            confidence_score=score,
            confidence_level=level,
            supporting_sources=sources,
        )

    def respond_stream(self, message: str, session_id: str = "default"):
        """Process user message through RAG retrieval and yield answer tokens via local LLM."""
        if not message.strip():
            yield "I am listening. How can I help you?"
            return

        memory = self.session_manager.get_or_create_session(session_id)
        history = memory.get_messages()
        history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
        from campus_helpdesk.services.prompt_sanitizer import sanitize_user_input
        safe_message = sanitize_user_input(message)
        search_query = self._query_rewriter.rewrite(safe_message, history_str)

        context_str = ""
        if self._rag_pipeline is not None:
            try:
                # Retrieve RAG results and try to build context. If no context, fallback to LLM directly.
                search_results = self._rag_pipeline.search(search_query)
                if search_results:
                    context_str = self._context_builder.build_context(search_results)
            except Exception as err:
                logger.warning(f"RAG context retrieval exception: {err}")

        rag_context_available = bool(context_str)
        if not rag_context_available:
            # No RAG context, generate via LLM directly
            parts = [self._system_prompt]
            if history:
                parts.append("History:\n" + history_str)
            parts.append(f"User Question: {message}")
            prompt = "\n\n".join(parts)
            reply = self._llm_service.generate(prompt)
            # Record and yield tokens after full reply
            full_reply = reply
            memory.add_message("user", message)
            memory.add_message("assistant", full_reply)
            for token in self._llm_service.generate_stream(prompt):
                yield token
            return


        parts = [self._system_prompt]
        if history:
            parts.append("History:\n" + history_str)
        if context_str:
            parts.append(f"Context:\n{context_str}")
        parts.append(f"User Question: {safe_message}")

        prompt = "\n\n".join(parts)
        full_reply_tokens = []
        for token in self._llm_service.generate_stream(prompt):
            full_reply_tokens.append(token)
            yield token

        full_reply = "".join(full_reply_tokens)
        memory.add_message("user", message)
        memory.add_message("assistant", full_reply)

    def clear_history(self, session_id: str = "default") -> None:
        """Reset conversation memory for a given session."""
        memory = self.session_manager.get_or_create_session(session_id)
        memory.clear()

