"""RAG-augmented Chat Service combining SimilarityStore and local Ollama model."""

import logging
from typing import Any

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
from campus_helpdesk.services.language_detector import LanguageDetector

logger = logging.getLogger(__name__)

FALLBACK_NO_INFO_REPLY = "I don't have information about that in my knowledge base."
DEFAULT_SYSTEM_PROMPT = (
    "You are the KLE Technological University (BVB) Campus Helpdesk Assistant. "
    "Answer the user's question clearly in 1 to 2 concise sentences based on the provided context. "
    "Note that all schools, departments, and centers belong to KLE Technological University's campus. "
    "If reasonable campus/university location or contact details are present in the context, synthesize a direct, helpful answer. "
    "Only say you don't have information if the context has no relevant information at all."
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
        context_composer: Any | None = None,
    ) -> None:
        self._llm_service = llm_service
        self._rag_pipeline = rag_pipeline
        self._query_rewriter = query_rewriter or QueryRewriter()
        self._context_builder = context_builder or PromptContextBuilder(max_context_size=7000)

        self.session_manager = session_manager or SessionManager()
        self.confidence_engine = confidence_engine or ConfidenceEngine()
        self._system_prompt = system_prompt
        self._answerability_engine = answerability_engine or AnswerabilityEngine()
        self._context_composer = context_composer

    def respond(self, message: str, session_id: str = "default") -> ChatResult:
        """Process user message through RAG retrieval, evaluate confidence, and generate answer via local LLM. User input is sanitized to prevent prompt injection."""
        if not message.strip():
            return ChatResult(reply="I am listening. How can I help you?", status="completed")

        # 1. Detect language of user query
        det = LanguageDetector.detect(message)
        lang_code = det.language
        lang_name = det.language_name

        # Check for simple conversational greetings
        clean_msg = message.strip().lower().rstrip("!").rstrip(".")
        if clean_msg in {"hi", "hello", "hey", "good morning", "good afternoon", "good evening", "namaste", "greetings", "hi there"}:
            greeting_reply = (
                "Hello! Welcome to the KLE Technological University (BVB) Campus Helpdesk. How can I assist you today?"
                if lang_code == "en" else
                "नमस्ते! केएलई टेक्नोलॉजिकल यूनिवर्सिटी कैंपस हेल्पडेस्क में आपका स्वागत है। मैं आपकी क्या सहायता कर सकता हूँ?"
                if lang_code == "hi" else
                "ನಮಸ್ಕಾರ! ಕೆಎಲ್‌ಇ ತಾಂತ್ರಿಕ ವಿಶ್ವವಿದ್ಯಾಲಯ ಕ್ಯಾಂಪಸ್ ಹೆಲ್ಪ್‌ಡೆಸ್ಕ್‌ಗೆ സ്വാಗತ. ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?"
            )
            memory = self.session_manager.get_or_create_session(session_id)
            memory.add_message("user", message)
            memory.add_message("assistant", greeting_reply)
            return ChatResult(reply=greeting_reply, status="completed", detected_language=lang_code)

        memory = self.session_manager.get_or_create_session(session_id)
        history = memory.get_messages()
        
        # Format history string for query rewriting
        history_str = "\n".join([
            f"{msg['role']}: {msg['content']}" if isinstance(msg, dict)
            else f"{getattr(msg, 'role', 'user')}: {getattr(msg, 'content', str(msg))}"
            for msg in history
        ])
        # Sanitize user input before rewrite
        from campus_helpdesk.services.prompt_sanitizer import sanitize_user_input
        safe_message = sanitize_user_input(message)
        search_query = self._query_rewriter.rewrite(safe_message, history_str)

        # If user query is in non-English script, translate search_query to English keywords for RAG vector search
        if lang_code != "en":
            try:
                tr_prompt = (
                    f"Translate the following question into a 1-sentence English search query (keywords only):\n"
                    f"Question: {search_query}\n"
                    f"English Search Query:"
                )
                translated_q = self._llm_service.generate(tr_prompt).strip().split("\n")[0]
                if translated_q:
                    logger.info(f"Translated '{search_query}' -> '{translated_q}' for English RAG vector search")
                    search_query = translated_q
            except Exception as e:
                logger.warning(f"Failed to translate query to English for RAG search: {e}")

        context_str = ""
        confidence_assessment: ConfidenceAssessment | None = None
        search_results = []
        
        # Retrieve RAG results and attempt to build context. If context is empty (e.g., all results exceed distance threshold),
        # we fallback to using the LLM without answerability gating.
        if self._rag_pipeline is not None:
            try:
                search_results = list(self._rag_pipeline.search(search_query, limit=10))
                
                # Supplemental query for location/address queries to ensure main campus directory is included
                query_lower = search_query.lower()
                supp_query = None
                if any(k in query_lower for k in ("where", "located", "location", "address", "campus")):
                    supp_query = "campus address location Vidyanagar Hubballi"
                elif any(k in query_lower for k in ("vice chancellor", "chancellor", "board of governors", "president")):
                    supp_query = "Vice Chancellor Board of Governors Dr Ashok Shettar"
                
                if supp_query:
                    try:
                        supp_results = self._rag_pipeline.search(supp_query, limit=5)
                        seen_contents = {getattr(r.document, "content", "")[:100] for r in search_results}
                        supp_to_add = []
                        for r in supp_results:
                            cid = getattr(r.document, "content", "")[:100]
                            if cid not in seen_contents:
                                seen_contents.add(cid)
                                supp_to_add.append(r)
                        search_results = supp_to_add + search_results
                    except Exception as supp_err:
                        logger.warning(f"Supplemental retrieval exception: {supp_err}")

                if search_results:
                    if self._context_composer is not None:
                        search_results = self._context_composer.compose(search_results)
                    for i, res in enumerate(search_results):
                        logger.debug(f"Chunk {i+1} distance: {res.distance}")
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
            if lang_code != "en":
                parts.append(
                    f"IMPORTANT: Respond in {lang_name} language ({lang_code}). Write the response in {lang_name} script."
                )
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
                detected_language=lang_code,
            )

        # Check answerability before sending to LLM
        # This block is now unreachable when RAG context is unavailable because early return handled above.
        confidence_level = confidence_assessment.confidence_level if confidence_assessment else "LOW"
        answerability = AnswerabilityEngine.evaluate_answerability(
            message, 
            [res.document for res in search_results], 
            confidence_level
        )
        
        parts = [self._system_prompt]
        if history:
            parts.append("History:\n" + history_str)
        if context_str:
            parts.append(f"Context:\n{context_str}")
        
        if lang_code != "en":
            parts.append(
                f"LANGUAGE INSTRUCTION: The user asked in {lang_name} ({lang_code.upper()}). "
                f"You MUST write your entire response in native {lang_name} script. "
                f"Accurately translate the factual information from the English context above into {lang_name}."
            )

        parts.append(f"User Question: {message}")

        prompt = "\n\n".join(parts)
        
        num_citations = len(confidence_assessment.supporting_sources) if confidence_assessment and confidence_assessment.supporting_sources else 0
        logger.debug(
            "--- GENERATED PROMPT INFO ---\n"
            f"Retrieved chunks: {len(search_results)}\n"
            f"Context length (chars): {len(context_str)}\n"
            f"Prompt length (chars): {len(prompt)}\n"
            f"Number of citations: {num_citations}\n"
            f"Prompt Content:\n{prompt}\n"
            "-----------------------------"
        )

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
            detected_language=lang_code,
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
            
            full_reply_tokens = []
            for token in self._llm_service.generate_stream(prompt):
                full_reply_tokens.append(token)
                yield token

            full_reply = "".join(full_reply_tokens)
            memory.add_message("user", message)
            memory.add_message("assistant", full_reply)
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

