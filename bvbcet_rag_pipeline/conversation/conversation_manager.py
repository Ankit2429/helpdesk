"""Central Conversation Manager Orchestrator.

Implements the end-to-end user message processing pipeline with mandatory stage-by-stage
visual terminal logging:
User Input -> Intent Detection -> Memory Lookup -> Query Rewriter -> Retriever -> Reranker -> Prompt Builder -> Local LLM -> Response Generator -> Memory Update.
"""

from typing import Any, Dict, List, Optional
from langchain_core.documents import Document

from conversation.intent_classifier import Intent, IntentClassifier
from conversation.memory import ConversationMemory
from conversation.query_rewriter import QueryRewriter
from llm.inference import LocalLLMInference, OllamaInferenceBackend
from llm.prompt_builder import PromptBuilder
from llm.response_generator import FinalResponse, ResponseGenerator
from retrieval.reranker import CrossEncoderReranker
from retrieval.retriever import ChromaRetriever
from logger.logger import get_logger

logger = get_logger("conversation_manager")


class ConversationManager:
    """Central Orchestrator combining Intent Classifier, Memory, Query Rewriter,
    Retriever, Reranker, Prompt Builder, Local LLM, and Response Generator."""

    def __init__(
        self,
        intent_classifier: Optional[IntentClassifier] = None,
        memory: Optional[ConversationMemory] = None,
        query_rewriter: Optional[QueryRewriter] = None,
        retriever: Optional[ChromaRetriever] = None,
        reranker: Optional[CrossEncoderReranker] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        llm_inference: Optional[LocalLLMInference] = None,
        response_generator: Optional[ResponseGenerator] = None,
        top_k: int = 5,
        score_threshold: float = 0.35,
        verbose_logging: bool = True,
    ) -> None:
        self.intent_classifier = intent_classifier or IntentClassifier()
        self.memory = memory or ConversationMemory()
        self.query_rewriter = query_rewriter or QueryRewriter()
        self.retriever = retriever or ChromaRetriever(top_k=top_k, score_threshold=score_threshold)
        self.reranker = reranker or CrossEncoderReranker(score_threshold=score_threshold)
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.llm_inference = llm_inference or LocalLLMInference(backend=OllamaInferenceBackend())
        self.response_generator = response_generator or ResponseGenerator()

        self.top_k = top_k
        self.score_threshold = score_threshold
        self.verbose_logging = verbose_logging

    def handle(self, user_input: str, language: Optional[str] = None) -> FinalResponse:
        """Process user message through full conversation pipeline."""
        if not user_input or not user_input.strip():
            return FinalResponse(
                answer="Please enter a valid question or query.",
                intent=Intent.UNKNOWN,
                resolved_query="",
                citations=[],
                metrics={},
                status="empty_input",
            )

        raw_query = user_input.strip()

        # Stage 1: Log Original User Message
        self._log_stage("Original User Message", raw_query)

        # Stage 2: Intent Classification
        intent = self.intent_classifier.classify(raw_query)
        self._log_stage("Detected Intent", intent.value)

        # Handle direct canned responses for non-question intents (BYPASS CHROMADB ENTIRELY)
        if intent in [Intent.GREETING, Intent.THANKS, Intent.GOODBYE, Intent.SMALL_TALK]:
            canned_ans = self.intent_classifier.get_canned_response(intent)
            self._log_stage("ChromaDB Status", "BYPASSED (Non-question conversational intent)")
            self._log_stage("Final Response", canned_ans)

            self.memory.add_user_message(raw_query)
            self.memory.add_assistant_message(canned_ans)

            return FinalResponse(
                answer=canned_ans,
                intent=intent,
                resolved_query=raw_query,
                citations=[],
                metrics={"inference_time_s": 0.0, "search_time_ms": 0.0},
                status="direct_canned_response",
            )

        # Stage 3: Conversation Memory & Context Retrieval
        history_msgs = self.memory.get_history()
        last_user_turn = history_msgs[-1].content if history_msgs else "None"
        self.memory.add_user_message(raw_query)
        self._log_stage("Conversation Context", f"History Size: {len(history_msgs)} msgs | Prior Turn: '{last_user_turn}'")

        # Stage 4: Query Rewriter
        history_prior = self.memory.get_history()[:-1]  # Exclude current query
        rewritten_query = self.query_rewriter.rewrite(raw_query, history_prior)
        self._log_stage("Rewritten Query", rewritten_query)

        # Stage 5: Embedding Query & Retriever (ChromaDB)
        self._log_stage("Embedding Query", rewritten_query)
        retrieved_docs: List[Document] = self.retriever.retrieve(
            question=rewritten_query,
            top_k=self.top_k,
            score_threshold=self.score_threshold,
            rerank=True,
        )

        retrieved_summary = "\n".join(
            [f"  [{idx+1}] {doc.metadata.get('source', 'doc')} (Score: {doc.metadata.get('score', 0.0):.4f})" for idx, doc in enumerate(retrieved_docs)]
        ) if retrieved_docs else "  No matching chunks found in ChromaDB."
        self._log_stage("Retrieved Chunks (ChromaDB + Reranker)", retrieved_summary)

        # Stage 6: Prompt Builder
        formatted_prompt = self.prompt_builder.build_prompt(
            question=rewritten_query,
            history=history_prior,
            retrieved_docs=retrieved_docs,
        )
        self._log_stage("LLM Prompt Preview", formatted_prompt[:300] + "...\n[Truncated]")

        # Stage 7: Local LLM Inference
        raw_llm_answer, inference_time_s, error_detail = self.llm_inference.generate(formatted_prompt)

        # Stage 8: Response Generator & Final Answer
        final_response = self.response_generator.generate_response(
            raw_llm_answer=raw_llm_answer,
            intent=intent,
            resolved_query=rewritten_query,
            retrieved_docs=retrieved_docs,
            inference_time_s=inference_time_s,
            error_detail=error_detail,
        )

        self._log_stage("Final Response", final_response.answer)

        # Update Memory with Assistant Answer
        self.memory.add_assistant_message(final_response.answer)

        return final_response

    def _log_stage(self, title: str, content: str) -> None:
        """Print visual stage-by-stage terminal log."""
        if not self.verbose_logging:
            return
        print("\n" + "=" * 52)
        print(title)
        print("=" * 52)
        print(content)

    def reset_session(self) -> None:
        """Reset conversation memory session."""
        self.memory.clear()
        logger.info("ConversationManager session reset.")
