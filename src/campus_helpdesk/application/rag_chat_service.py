"""RAG-augmented Chat Service combining SimilarityStore and local Ollama model."""

import logging
import time
from typing import Any

from campus_helpdesk.application.chat_models import ChatResult
from campus_helpdesk.application.chat_service import ChatService
from campus_helpdesk.application.llm_service import LLMService
from campus_helpdesk.application.query_rewriter import QueryRewriter
from campus_helpdesk.application.rag_pipeline import RAGPipeline
from campus_helpdesk.application.session_manager import SessionManager
from campus_helpdesk.infrastructure.rag.confidence_engine import (
    ConfidenceEngine,
)
from campus_helpdesk.infrastructure.rag.prompt_context_builder import PromptContextBuilder
from campus_helpdesk.services.answerability_engine import AnswerabilityEngine
from campus_helpdesk.services.citation_validator import CitationValidator
from campus_helpdesk.services.intent_router import IntentRouter, IntentType
from campus_helpdesk.services.language_detector import LanguageDetector
from campus_helpdesk.services.query_normalizer import normalize_query

logger = logging.getLogger(__name__)

FALLBACK_NO_INFO_REPLY = "I couldn't find that information in my knowledge base."

DEFAULT_SYSTEM_PROMPT = (
    "System:\n"
    "You are Sparky (Campus Helpdesk), an offline AI campus helpdesk assistant for KLE Technological University "
    "(BVB Engineering College), Hubballi.\n\n"
    "STRICT GROUNDING RULES:\n"
    "1. Answer ONLY using the information provided in the Context section below.\n"
    "2. If the retrieved context is only partially relevant, answer using what is available and clearly note the limitation — do not fabricate details not present in the context. Only if the retrieved context is completely empty or completely irrelevant to the question, respond EXACTLY:\n"
    "   \"I couldn't find verified information about that in my knowledge base.\"\n"
    "3. NEVER mention real-time access, browsing the web, training data, Student Union Building (SUB), or generic university examples.\n"
    "4. Do NOT invent locations, people, departments, or facilities under any circumstances.\n"
    "5. Keep answers factual, concise, and cite the source title when possible.\n"
    "6. Never infer administrative positions."
)
GENERAL_SYSTEM_PROMPT = DEFAULT_SYSTEM_PROMPT


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
        intent_router: IntentRouter | None = None,
    ) -> None:
        self._llm_service = llm_service
        self._rag_pipeline = rag_pipeline
        self._query_rewriter = query_rewriter or QueryRewriter()
        from campus_helpdesk.config.settings import get_settings
        self._context_builder = context_builder or PromptContextBuilder(
            max_context_size=3500,
            similarity_threshold=get_settings().rag_distance_threshold,
        )

        self.session_manager = session_manager or SessionManager()
        self.confidence_engine = confidence_engine or ConfidenceEngine()
        self._system_prompt = system_prompt
        self._answerability_engine = answerability_engine or AnswerabilityEngine()
        self._context_composer = context_composer
        self._intent_router = intent_router or IntentRouter()

    def _safe_search(self, query: str, limit: int = 5, original_query: str | None = None) -> list[Any]:
        if self._rag_pipeline is None:
            return []
        try:
            return list(self._rag_pipeline.search(query, limit=limit, original_query=original_query))
        except TypeError:
            try:
                return list(self._rag_pipeline.search(query, limit=limit))
            except TypeError:
                return list(self._rag_pipeline.search(query))

    def respond(self, message: str, session_id: str = "default") -> ChatResult:
        """Process user message through intent routing, RAG retrieval, and local LLM."""
        if not message.strip():
            return ChatResult(
                reply="I am listening. How can I help you?",
                status="completed",
                confidence_score=1.0,
                confidence_level="HIGH",
                supporting_sources=[],
                detected_language="en",
            )

        # Normalize user input before processing (lowercasing, spelling, synonyms, etc.)
        from campus_helpdesk.config.settings import get_settings
        debug_mode = get_settings().debug
        t_start_norm = time.perf_counter()
        normalized_message = normalize_query(message, debug=debug_mode)
        logger.info("[LATENCY-PROFILER] Query normalization: %.2f ms", (time.perf_counter() - t_start_norm) * 1000)

        det = LanguageDetector.detect(normalized_message)
        lang_code = det.language
        lang_name = det.language_name

        intent_res = self._intent_router.route(normalized_message, lang_code=lang_code)
        if intent_res.intent != IntentType.CAMPUS_QUERY and intent_res.response:
            logger.info(f"[IntentRouter] Route: {intent_res.intent.value.upper()} (Bypassing RAG)")
            memory = self.session_manager.get_or_create_session(session_id)
            memory.add_message("user", normalized_message)
            memory.add_message("assistant", intent_res.response)
            return ChatResult(
                reply=intent_res.response,
                status="completed",
                confidence_score=1.0,
                confidence_level="HIGH",
                supporting_sources=[],
                detected_language=lang_code,
            )

        memory = self.session_manager.get_or_create_session(session_id)
        history = memory.get_messages()
        from campus_helpdesk.services.prompt_sanitizer import sanitize_user_input
        safe_message = sanitize_user_input(normalized_message)

        # Translation block for non-English queries (translate search and rerank target to English keywords)
        original_query_translated = safe_message
        if lang_code != "en":
            try:
                tr_prompt = (
                    f"Translate the following question into a 1-sentence English search query (keywords only):\n"
                    f"Question: {safe_message}\n"
                    f"English Search Query:"
                )
                translated_q = self._llm_service.generate(tr_prompt).strip().split("\n")[0]
                if translated_q:
                    logger.info(f"Translated query to English: '{safe_message}' -> '{translated_q}'")
                    original_query_translated = translated_q
            except Exception as e:
                logger.warning(f"Failed to translate query to English: {e}")

        t_start_rewrite = time.perf_counter()
        search_query = self._query_rewriter.rewrite(original_query_translated, history)
        logger.info("[LATENCY-PROFILER] Query rewriting: %.2f ms", (time.perf_counter() - t_start_rewrite) * 1000)

        context_str = ""
        confidence_assessment = None
        search_results: list[Any] = []
        if self._rag_pipeline is not None:
            try:
                search_results = self._safe_search(search_query, limit=5, original_query=original_query_translated)

                query_lower = search_query.lower()
                supp_query = None
                if any(k in query_lower for k in ("where is the campus", "where is kle tech", "campus address", "university address", "location of university")):
                    supp_query = "campus address location Vidyanagar Hubballi"
                elif any(k in query_lower for k in ("vice chancellor name", "who is the vc", "chancellor name")):
                    supp_query = "Vice Chancellor Board of Governors Dr Prakash Tewari"

                if supp_query and len(search_results) < 3:
                    try:
                        supp_results = self._safe_search(supp_query, limit=3)
                        seen_contents = {getattr(r.document, "content", "")[:100] for r in search_results}
                        supp_to_add = []
                        for r in supp_results:
                            cid = getattr(r.document, "content", "")[:100]
                            if cid not in seen_contents:
                                seen_contents.add(cid)
                                supp_to_add.append(r)
                        search_results = search_results + supp_to_add
                    except Exception as supp_err:
                        logger.warning(f"Supplemental retrieval exception: {supp_err}")

                if search_results:
                    t_start_ctx = time.perf_counter()
                    if self._context_composer is not None:
                        search_results = self._context_composer.compose(search_results)
                    confidence_assessment = self.confidence_engine.evaluate(search_results)
                    context_str = self._context_builder.build_context(search_results, confidence_assessment)
                    logger.info("[LATENCY-PROFILER] Context assembly: %.2f ms", (time.perf_counter() - t_start_ctx) * 1000)
            except Exception as err:
                logger.warning(f"RAG context retrieval exception: {err}")

        # Check retrieval confidence score threshold
        score = confidence_assessment.confidence_score if confidence_assessment else 0.0
        level = confidence_assessment.confidence_level if confidence_assessment else "Very Low"
        sources = confidence_assessment.supporting_sources if confidence_assessment else []

        top_reranker = confidence_assessment.top_reranker_score if confidence_assessment else -99.0
        top_distance = confidence_assessment.top_distance if confidence_assessment else 99.0

        # Calibrate threshold: Accept if overall score >= 0.35 OR if the top retrieved chunk is highly relevant
        is_accepted = (score >= 0.35) or (top_reranker >= 0.1) or (top_distance <= 1.2)

        # Token Budgeting & Logging
        token_breakdown = memory.get_token_breakdown(self._system_prompt, context_str, safe_message)
        logger.info(
            f"[TokenBudget] System: {token_breakdown['system_prompt_tokens']} | "
            f"History: {token_breakdown['conversation_history_tokens']} | "
            f"Context: {token_breakdown['retrieved_context_tokens']} | "
            f"Query: {token_breakdown['user_query_tokens']} | "
            f"Total: {token_breakdown['total_tokens']}/{token_breakdown['max_context_tokens']}"
        )

        # Log detailed RAG debug statistics for every query
        debug_msg = (
            f"\n--- RAG RETRIEVAL DEBUG INFO ---\n"
            f"User Query: {message}\n"
            f"Confidence Score: {score} | Level: {level}\n"
            f"Top Reranker Score: {top_reranker} | Top Distance: {top_distance}\n"
            f"Decision: {'ACCEPT' if is_accepted else 'REJECT'}\n"
            f"Top Chunks:\n"
        )
        if 'search_results' in locals() and search_results:
            for idx, res in enumerate(search_results[:5]):
                debug_msg += f"  [{idx+1}] Source: {res.document.metadata.get('source')} | Distance: {res.distance:.4f}\n"
        else:
            debug_msg += "  No chunks retrieved.\n"
        debug_msg += "--------------------------------"
        logger.info(debug_msg)

        if not is_accepted:
            logger.info(f"[ConfidenceCheck] Rejected: Score {score} (reranker: {top_reranker}, dist: {top_distance}). Bypassing LLM generation.")
            reply = "I couldn't find reliable information about that. Could you rephrase your question?"
            memory.add_message("user", normalized_message)
            memory.add_message("assistant", reply)
            return ChatResult(
                reply=reply,
                status="completed",
                confidence_score=score,
                confidence_level=level,
                supporting_sources=[],
                detected_language=lang_code,
            )

        # Truncate context & history to fit strictly within max token budget
        budget_history, budget_context, safe_message = memory.truncate_to_token_budget(
            self._system_prompt, context_str, safe_message
        )

        # Merge parts in unambiguous, structured order: System -> History -> Context -> Query
        parts = [self._system_prompt]
        if budget_history:
            parts.append("--- Conversation History ---\n" + budget_history)
        if budget_context:
            parts.append(f"--- Retrieved Knowledge Context ---\n{budget_context}")

        if lang_code != "en":
            parts.append(
                f"LANGUAGE INSTRUCTION: The user asked in {lang_name} ({lang_code.upper()}). "
                f"You MUST write your entire response in native {lang_name} script."
            )

        parts.append(f"User Question: {safe_message}")

        prompt = "\n\n".join(parts)
        t_start_llm = time.perf_counter()
        reply = self._llm_service.generate(prompt)
        logger.info("[LATENCY-PROFILER] LLM completion: %.2f ms", (time.perf_counter() - t_start_llm) * 1000)

        if search_results:
            reply = CitationValidator.validate_citations(reply, [res.document for res in search_results])

        memory.add_message("user", normalized_message)
        memory.add_message("assistant", reply)

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

        from campus_helpdesk.config.settings import get_settings
        debug_mode = get_settings().debug
        t_start_norm = time.perf_counter()
        normalized_message = normalize_query(message, debug=debug_mode)
        logger.info("[LATENCY-PROFILER] Query normalization: %.2f ms", (time.perf_counter() - t_start_norm) * 1000)

        det = LanguageDetector.detect(normalized_message)
        lang_code = det.language

        # Check intent route for all conversational intents
        intent_res = self._intent_router.route(normalized_message, lang_code=lang_code)
        if intent_res.intent != IntentType.CAMPUS_QUERY and intent_res.response:
            logger.info(f"[IntentRouter Stream] Route: {intent_res.intent.value.upper()} (Bypassing RAG)")
            memory = self.session_manager.get_or_create_session(session_id)
            memory.add_message("user", normalized_message)
            memory.add_message("assistant", intent_res.response)
            yield intent_res.response
            return

        memory = self.session_manager.get_or_create_session(session_id)
        history = memory.get_messages()
        from campus_helpdesk.services.prompt_sanitizer import sanitize_user_input
        safe_message = sanitize_user_input(normalized_message)
        # Translation block for non-English queries (translate search and rerank target to English keywords)
        original_query_translated = safe_message
        if lang_code != "en":
            try:
                tr_prompt = (
                    f"Translate the following question into a 1-sentence English search query (keywords only):\n"
                    f"Question: {safe_message}\n"
                    f"English Search Query:"
                )
                translated_q = self._llm_service.generate(tr_prompt).strip().split("\n")[0]
                if translated_q:
                    logger.info(f"Translated query to English (stream): '{safe_message}' -> '{translated_q}'")
                    original_query_translated = translated_q
            except Exception as e:
                logger.warning(f"Failed to translate query to English (stream): {e}")

        t_start_rewrite = time.perf_counter()
        search_query = self._query_rewriter.rewrite(original_query_translated, history)
        logger.info("[LATENCY-PROFILER] Query rewriting: %.2f ms", (time.perf_counter() - t_start_rewrite) * 1000)

        context_str = ""
        confidence_assessment = None
        search_results: list[Any] = []
        if self._rag_pipeline is not None:
            try:
                search_results = self._safe_search(search_query, limit=5, original_query=original_query_translated)
                if search_results:
                    t_start_ctx = time.perf_counter()
                    if self._context_composer is not None:
                        search_results = self._context_composer.compose(search_results)
                    confidence_assessment = self.confidence_engine.evaluate(search_results)
                    context_str = self._context_builder.build_context(search_results, confidence_assessment)
                    logger.info("[LATENCY-PROFILER] Context assembly: %.2f ms", (time.perf_counter() - t_start_ctx) * 1000)
            except Exception as err:
                logger.warning(f"RAG context retrieval exception in respond_stream: {err}")

        # Check retrieval confidence score threshold
        score = confidence_assessment.confidence_score if confidence_assessment else 0.0
        level = confidence_assessment.confidence_level if confidence_assessment else "Very Low"
        top_reranker = confidence_assessment.top_reranker_score if confidence_assessment else -99.0
        top_distance = confidence_assessment.top_distance if confidence_assessment else 99.0

        is_accepted = (score >= 0.35) or (top_reranker >= 0.1) or (top_distance <= 1.2)

        # Token Budgeting & Logging
        token_breakdown = memory.get_token_breakdown(self._system_prompt, context_str, safe_message)
        logger.info(
            f"[TokenBudget Stream] System: {token_breakdown['system_prompt_tokens']} | "
            f"History: {token_breakdown['conversation_history_tokens']} | "
            f"Context: {token_breakdown['retrieved_context_tokens']} | "
            f"Query: {token_breakdown['user_query_tokens']} | "
            f"Total: {token_breakdown['total_tokens']}/{token_breakdown['max_context_tokens']}"
        )

        # Log detailed RAG debug statistics for every query
        debug_msg = (
            f"\n--- RAG RETRIEVAL DEBUG INFO ---\n"
            f"User Query: {message}\n"
            f"Confidence Score: {score} | Level: {level}\n"
            f"Top Reranker Score: {top_reranker} | Top Distance: {top_distance}\n"
            f"Decision: {'ACCEPT' if is_accepted else 'REJECT'}\n"
            f"Top Chunks:\n"
        )
        if search_results:
            for idx, res in enumerate(search_results[:5]):
                debug_msg += f"  [{idx+1}] Source: {res.document.metadata.get('source')} | Distance: {res.distance:.4f}\n"
        else:
            debug_msg += "  No chunks retrieved.\n"
        debug_msg += "--------------------------------"
        logger.info(debug_msg)

        if not is_accepted:
            logger.info(f"[ConfidenceCheck Stream] Rejected: Score {score}. Bypassing LLM generation.")
            reply = "I couldn't find reliable information about that. Could you rephrase your question?"
            memory.add_message("user", normalized_message)
            memory.add_message("assistant", reply)
            yield reply
            return

        # Truncate context & history to fit strictly within max token budget
        budget_history, budget_context, safe_message = memory.truncate_to_token_budget(
            self._system_prompt, context_str, safe_message
        )

        # Merge parts in unambiguous, structured order: System -> History -> Context -> Query
        parts = [self._system_prompt]
        if budget_history:
            parts.append("--- Conversation History ---\n" + budget_history)
        if budget_context:
            parts.append(f"--- Retrieved Knowledge Context ---\n{budget_context}")
        parts.append(f"User Question: {safe_message}")

        prompt = "\n\n".join(parts)
        full_reply_tokens = []
        t_start_llm = time.perf_counter()
        first_token = True
        
        for token in self._llm_service.generate_stream(prompt):
            if first_token:
                logger.info("[LATENCY-PROFILER] LLM first token: %.2f ms", (time.perf_counter() - t_start_llm) * 1000)
                first_token = False
            full_reply_tokens.append(token)
            yield token

        logger.info("[LATENCY-PROFILER] LLM completion: %.2f ms", (time.perf_counter() - t_start_llm) * 1000)
        full_reply = "".join(full_reply_tokens)
        memory.add_message("user", normalized_message)
        memory.add_message("assistant", full_reply)

    def clear_history(self, session_id: str = "default") -> None:
        """Reset conversation memory for a given session."""
        memory = self.session_manager.get_or_create_session(session_id)
        memory.clear()
